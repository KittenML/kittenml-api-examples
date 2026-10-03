import argparse
import asyncio
import base64
import json
import os
import platform
import signal
from pathlib import Path

from dotenv import load_dotenv
from websockets.asyncio.client import connect


DEFAULT_MODEL = "kitten-asr-pro-enhanced"
DEFAULT_SAMPLE_RATE = 24_000
DEFAULT_CHUNK_MS = 200


def microphone_setup_error(exc: Exception) -> SystemExit:
    system = platform.system()
    if system == "Linux":
        hint = (
            "Install PortAudio first (Ubuntu/Debian: sudo apt install "
            "libportaudio2), then reinstall the Python requirements."
        )
    elif system == "Darwin":
        hint = (
            "Reinstall the Python requirements, then allow your terminal or IDE "
            "to use the microphone in System Settings > Privacy & Security > "
            "Microphone."
        )
    elif system == "Windows":
        hint = (
            "Reinstall the Python requirements, then enable microphone access for "
            "desktop apps in Settings > Privacy & security > Microphone."
        )
    else:
        hint = "Install PortAudio and reinstall the Python requirements."
    return SystemExit(f"Microphone capture is unavailable. {hint} ({exc})")


def realtime_error(event: dict, fallback: str) -> RuntimeError:
    error = event.get("error") if isinstance(event.get("error"), dict) else {}
    code = error.get("code") or "unknown_error"
    request_id = event.get("request_id") or error.get("request_id") or "unknown"
    message = error.get("message") or fallback
    return RuntimeError(f"{message} (code={code}, request_id={request_id})")


def parse_device(value: str | None) -> int | str | None:
    if value is None:
        return None
    return int(value) if value.isdecimal() else value


async def receive_events(socket, stopping: asyncio.Event) -> None:
    previous_partial: dict[str, str] = {}
    async for raw_event in socket:
        event = json.loads(raw_event)
        event_type = event.get("type")
        item_id = str(event.get("item_id") or "current")

        if event_type == "input_audio_buffer.speech_started":
            print(f"speech started: {item_id}")
        elif event_type == "input_audio_buffer.speech_stopped":
            print(f"speech stopped: {item_id}")
        elif event_type == "conversation.item.input_audio_transcription.delta":
            partial = str(event.get("clean_text") or event.get("delta") or "")
            if partial and previous_partial.get(item_id) != partial:
                previous_partial[item_id] = partial
                print(f"partial: {partial}")
        elif event_type == "conversation.item.input_audio_transcription.completed":
            previous_partial.pop(item_id, None)
            clean = event.get("transcript") or event.get("clean_text") or ""
            enriched = event.get("enriched_text") or event.get("text") or ""
            print(f"final [{item_id}]: {clean}")
            print(f"enriched [{item_id}]: {enriched}")
        elif event_type == "error":
            raise realtime_error(event, "Realtime request failed.")

    if not stopping.is_set():
        raise RuntimeError("Realtime connection closed unexpectedly.")


async def send_audio(socket, audio_queue: asyncio.Queue[bytes]) -> None:
    while True:
        chunk = await audio_queue.get()
        await socket.send(json.dumps({
            "type": "input_audio_buffer.append",
            "audio": base64.b64encode(chunk).decode("ascii"),
        }))


async def run(args: argparse.Namespace, api_key: str, sounddevice) -> None:
    model = os.environ.get("KITTENML_MODEL", DEFAULT_MODEL)
    url = os.environ.get(
        "KITTENML_REALTIME_URL",
        f"wss://api.kittenml.com/v1/realtime?model={model}",
    )
    stopping = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signum, stopping.set)
        except NotImplementedError:
            pass

    async with connect(
        url,
        additional_headers={"Authorization": f"Bearer {api_key}"},
        max_size=None,
    ) as socket:
        created = json.loads(await socket.recv())
        if created.get("type") == "error":
            raise realtime_error(created, "Connection rejected.")
        if created.get("type") != "session.created":
            raise RuntimeError(f"Expected session.created, received {created.get('type')}")

        await socket.send(json.dumps({
            "type": "session.update",
            "session": {
                "type": "transcription",
                "audio": {"input": {
                    "format": {"type": "audio/pcm", "rate": args.sample_rate},
                    "transcription": {"model": model, "delay": "medium"},
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": args.vad_threshold,
                        "prefix_padding_ms": args.prefix_padding_ms,
                        "silence_duration_ms": args.silence_duration_ms,
                    },
                }},
            },
        }))
        updated = json.loads(await socket.recv())
        if updated.get("type") != "session.updated":
            raise RuntimeError(f"Expected session.updated, received {updated.get('type')}")

        audio_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=25)
        callback_error: list[RuntimeError] = []

        def enqueue_audio(chunk: bytes) -> None:
            if audio_queue.full():
                if not callback_error:
                    callback_error.append(
                        RuntimeError("Microphone sender fell behind; audio was not sent.")
                    )
                stopping.set()
                return
            audio_queue.put_nowait(chunk)

        def audio_callback(indata, _frames, _time_info, status) -> None:
            if status:
                loop.call_soon_threadsafe(print, f"microphone status: {status}")
            loop.call_soon_threadsafe(enqueue_audio, bytes(indata))

        blocksize = max(1, args.sample_rate * args.chunk_ms // 1_000)
        sender = asyncio.create_task(send_audio(socket, audio_queue))
        receiver = asyncio.create_task(receive_events(socket, stopping))
        stop_waiter = asyncio.create_task(stopping.wait())

        print(f"connected: {created['session']['id']}")
        print("Listening. Speak naturally; pause to let server VAD finish each turn.")
        print("Press Ctrl+C after the final transcript to stop.")

        try:
            with sounddevice.RawInputStream(
                samplerate=args.sample_rate,
                blocksize=blocksize,
                device=parse_device(args.device),
                channels=1,
                dtype="int16",
                callback=audio_callback,
            ):
                done, _pending = await asyncio.wait(
                    {receiver, stop_waiter}, return_when=asyncio.FIRST_COMPLETED
                )
                if receiver in done:
                    await receiver
                if callback_error:
                    raise callback_error[0]
        finally:
            stopping.set()
            for task in (sender, receiver, stop_waiter):
                task.cancel()
            await asyncio.gather(sender, receiver, stop_waiter, return_exceptions=True)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe continuous microphone audio with server VAD."
    )
    parser.add_argument("--device", help="Input device index or name.")
    parser.add_argument(
        "--sample-rate", type=int, choices=(16_000, 24_000), default=DEFAULT_SAMPLE_RATE
    )
    parser.add_argument("--chunk-ms", type=int, default=DEFAULT_CHUNK_MS)
    parser.add_argument("--vad-threshold", type=float, default=0.3)
    parser.add_argument("--prefix-padding-ms", type=int, default=350)
    parser.add_argument("--silence-duration-ms", type=int, default=700)
    parser.add_argument("--list-devices", action="store_true")
    args = parser.parse_args()
    if args.chunk_ms <= 0:
        parser.error("--chunk-ms must be positive")
    if not 0.01 <= args.vad_threshold <= 1.0:
        parser.error("--vad-threshold must be between 0.01 and 1.0")
    if not 0 <= args.prefix_padding_ms <= 5_000:
        parser.error("--prefix-padding-ms must be between 0 and 5000")
    if not 100 <= args.silence_duration_ms <= 10_000:
        parser.error("--silence-duration-ms must be between 100 and 10000")
    return args


def main() -> None:
    args = arguments()
    try:
        import sounddevice
    except (ImportError, OSError) as exc:
        raise microphone_setup_error(exc) from exc

    if args.list_devices:
        print(sounddevice.query_devices())
        return

    load_dotenv(Path(__file__).with_name(".env"))
    api_key = os.environ.get("KITTENML_API_KEY")
    if not api_key:
        raise SystemExit("Copy .env.example to .env and add KITTENML_API_KEY before running.")
    asyncio.run(run(args, api_key, sounddevice))


if __name__ == "__main__":
    main()
