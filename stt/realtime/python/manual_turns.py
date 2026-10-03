import argparse
import asyncio
import base64
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from websockets.asyncio.client import connect


DEFAULT_MODEL = "kitten-asr-pro-enhanced"
SAMPLE_RATE = 24_000


def realtime_error(event: dict, fallback: str) -> RuntimeError:
    error = event.get("error") if isinstance(event.get("error"), dict) else {}
    code = error.get("code") or "unknown_error"
    request_id = event.get("request_id") or error.get("request_id") or "unknown"
    message = error.get("message") or fallback
    return RuntimeError(f"{message} (code={code}, request_id={request_id})")


async def run(args: argparse.Namespace, api_key: str) -> None:
    model = os.environ.get("KITTENML_MODEL", DEFAULT_MODEL)
    url = os.environ.get(
        "KITTENML_REALTIME_URL",
        f"wss://api.kittenml.com/v1/realtime?model={model}",
    )
    bytes_per_second = SAMPLE_RATE * 2
    chunk_bytes = max(2, round(bytes_per_second * args.chunk_ms / 1_000))
    chunk_bytes -= chunk_bytes % 2

    async with connect(
        url,
        additional_headers={"Authorization": f"Bearer {api_key}"},
        max_size=None,
    ) as socket:
        # One WebSocket session can carry several independent transcription turns.
        created = json.loads(await socket.recv())
        if created.get("type") == "error":
            raise realtime_error(created, "Connection rejected.")
        await socket.send(json.dumps({
            "type": "session.update",
            "session": {
                "type": "transcription",
                "audio": {"input": {
                    "format": {"type": "audio/pcm", "rate": SAMPLE_RATE},
                    "transcription": {"model": model, "delay": "medium"},
                    "turn_detection": None,
                }},
            },
        }))
        updated = json.loads(await socket.recv())
        if updated.get("type") != "session.updated":
            raise RuntimeError(f"Expected session.updated, received {updated.get('type')}")

        for turn_number, audio_path in enumerate(args.audio, start=1):
            pcm = audio_path.read_bytes()
            started = time.monotonic()
            for offset in range(0, len(pcm), chunk_bytes):
                # Pace file bytes so the service receives microphone-like audio.
                chunk = pcm[offset : offset + chunk_bytes]
                await socket.send(json.dumps({
                    "type": "input_audio_buffer.append",
                    "audio": base64.b64encode(chunk).decode("ascii"),
                }))
                target = (offset + len(chunk)) / bytes_per_second
                await asyncio.sleep(max(0, target - (time.monotonic() - started)))
            await socket.send(json.dumps({"type": "input_audio_buffer.commit"}))

            # Do not start the next turn until this turn has a terminal transcript.
            while True:
                event = json.loads(await socket.recv())
                event_type = event.get("type")
                if event_type == "input_audio_buffer.speech_started":
                    print(f"turn {turn_number}: speech started")
                elif event_type == "input_audio_buffer.speech_stopped":
                    print(f"turn {turn_number}: speech stopped")
                elif event_type == "conversation.item.input_audio_transcription.completed":
                    print(f"turn {turn_number} item: {event.get('item_id')}")
                    print(f"turn {turn_number} enriched: {event.get('enriched_text') or event.get('text') or ''}")
                    print(f"turn {turn_number} clean: {event.get('transcript') or event.get('clean_text') or ''}")
                    break
                elif event_type == "error":
                    # Preserve code and request_id so support can correlate the failure.
                    raise realtime_error(event, "Realtime request failed.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Send one PCM file per manually committed realtime turn."
    )
    parser.add_argument(
        "audio",
        nargs="+",
        type=Path,
        help="24 kHz mono PCM16 files, in conversation order.",
    )
    parser.add_argument("--chunk-ms", type=int, default=200)
    args = parser.parse_args()
    if args.chunk_ms <= 0:
        raise SystemExit("--chunk-ms must be positive")

    load_dotenv(Path(__file__).with_name(".env"))
    api_key = os.environ.get("KITTENML_API_KEY")
    if not api_key:
        raise SystemExit("Copy .env.example to .env and add KITTENML_API_KEY before running.")
    asyncio.run(run(args, api_key))


if __name__ == "__main__":
    main()
