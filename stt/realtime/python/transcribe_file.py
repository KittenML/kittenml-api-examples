import argparse
import asyncio
import base64
import json
import os
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from websockets.asyncio.client import connect


DEFAULT_MODEL = "kitten-asr-pro-enhanced"
SAMPLE_RATE = 24_000
BYTES_PER_SECOND = SAMPLE_RATE * 2
CHUNK_MILLISECONDS = 200
# Realtime input is 24 kHz, mono, signed 16-bit PCM (two bytes per sample).
CHUNK_BYTES = BYTES_PER_SECOND * CHUNK_MILLISECONDS // 1_000
DEFAULT_AUDIO = Path(__file__).resolve().parents[1] / "assets" / "sample.pcm"


def realtime_error(event: dict, fallback: str) -> RuntimeError:
    error = event.get("error") if isinstance(event.get("error"), dict) else {}
    code = error.get("code") or "unknown_error"
    request_id = event.get("request_id") or error.get("request_id") or "unknown"
    message = error.get("message") or fallback
    return RuntimeError(f"{message} (code={code}, request_id={request_id})")


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stream PCM audio to KittenASR Enhanced.")
    parser.add_argument("audio", nargs="?", type=Path, default=DEFAULT_AUDIO)
    parser.add_argument("--language", help="Optional language hint, for example en or es.")
    return parser.parse_args()


async def transcribe(audio_path: Path, language: Optional[str], api_key: str) -> None:
    pcm = audio_path.read_bytes()
    model = os.environ.get("KITTENML_MODEL", DEFAULT_MODEL)
    url = os.environ.get(
        "KITTENML_REALTIME_URL",
        f"wss://api.kittenml.com/v1/realtime?model={model}",
    )
    async with connect(
        url,
        additional_headers={"Authorization": f"Bearer {api_key}"},
        max_size=None,
    ) as socket:
        # The server creates the connection first; configure it before sending audio.
        created = json.loads(await socket.recv())
        if created.get("type") == "error":
            raise realtime_error(created, "Connection rejected.")
        if created.get("type") != "session.created":
            raise RuntimeError(f"Expected session.created, received {created.get('type')}")
        print(f"connected: {created['session']['id']}")

        transcription = {"model": model}
        if language:
            transcription["language"] = language
        await socket.send(json.dumps({
            "type": "session.update",
            "session": {
                "type": "transcription",
                "audio": {"input": {
                    "format": {"type": "audio/pcm", "rate": SAMPLE_RATE},
                    "transcription": transcription,
                    "turn_detection": None,
                }},
            },
        }))
        updated = json.loads(await socket.recv())
        if updated.get("type") != "session.updated":
            raise RuntimeError(f"Expected session.updated, received {updated.get('type')}")

        async def read_events() -> None:
            previous_enriched = ""
            previous_clean = ""
            final_received = False
            async for raw_event in socket:
                event = json.loads(raw_event)
                event_type = event.get("type")
                if event_type == "conversation.item.input_audio_transcription.delta":
                    # Partials are snapshots and may revise earlier words.
                    enriched = str(event.get("enriched_text") or event.get("text") or "")
                    clean = str(event.get("clean_text") or event.get("delta") or "")
                    if enriched and enriched != previous_enriched:
                        previous_enriched = enriched
                        print(f"enriched partial: {enriched}")
                    if clean and clean != previous_clean:
                        previous_clean = clean
                        print(f"clean partial: {clean}")
                elif event_type == "conversation.item.input_audio_transcription.completed":
                    # Treat only the completed event as a successful transcript.
                    print(f"enriched final: {event.get('enriched_text') or event.get('text') or ''}")
                    print(f"clean final: {event.get('transcript') or event.get('clean_text') or ''}")
                    final_received = True
                    return
                elif event_type == "error":
                    raise realtime_error(event, "Realtime request failed.")
            if not final_received:
                raise RuntimeError(
                    "Realtime connection closed before the completed transcript "
                    "(code=connection_closed, request_id=unknown)"
                )

        reader = asyncio.create_task(read_events())
        # Pace prerecorded PCM in 200 ms frames to behave like a microphone stream.
        stream_started = time.monotonic()
        for offset in range(0, len(pcm), CHUNK_BYTES):
            chunk = pcm[offset : offset + CHUNK_BYTES]
            await socket.send(json.dumps({
                "type": "input_audio_buffer.append",
                "audio": base64.b64encode(chunk).decode("ascii"),
            }))
            target = (offset + len(chunk)) / BYTES_PER_SECOND
            await asyncio.sleep(max(0, target - (time.monotonic() - stream_started)))
        await socket.send(json.dumps({"type": "input_audio_buffer.commit"}))
        # Keep receiving after commit until the terminal transcript arrives.
        await reader


def main() -> None:
    args = arguments()
    load_dotenv(Path(__file__).with_name(".env"))
    api_key = os.environ.get("KITTENML_API_KEY")
    if not api_key:
        raise SystemExit("Copy .env.example to .env and add KITTENML_API_KEY before running.")
    asyncio.run(transcribe(args.audio, args.language, api_key))


if __name__ == "__main__":
    main()
