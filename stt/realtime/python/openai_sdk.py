import asyncio
import base64
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI


DEFAULT_MODEL = "kitten-asr-pro-enhanced"
SAMPLE_RATE = 24_000
CHUNK_MS = 200
CHUNK_BYTES = SAMPLE_RATE * 2 * CHUNK_MS // 1_000
DEFAULT_AUDIO = Path(__file__).resolve().parents[1] / "assets" / "sample.pcm"


def realtime_error(event: dict, fallback: str) -> RuntimeError:
    error = event.get("error") if isinstance(event.get("error"), dict) else {}
    code = error.get("code") or "unknown_error"
    request_id = event.get("request_id") or error.get("request_id") or "unknown"
    message = error.get("message") or fallback
    return RuntimeError(f"{message} (code={code}, request_id={request_id})")


async def main() -> None:
    here = Path(__file__).resolve().parent
    load_dotenv(here / ".env")
    api_key = os.environ.get("KITTENML_API_KEY")
    if not api_key:
        raise SystemExit("Copy .env.example to .env and add KITTENML_API_KEY before running.")

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=os.environ.get("KITTENML_BASE_URL", "https://api.kittenml.com/v1"),
    )
    model = os.environ.get("KITTENML_MODEL", DEFAULT_MODEL)
    pcm = DEFAULT_AUDIO.read_bytes()

    # The OpenAI SDK supplies the transport; KittenML uses the same event protocol.
    async with client.realtime.connect(model=model) as connection:
        created = json.loads(await connection.recv_bytes())
        if created.get("type") != "session.created":
            raise RuntimeError(f"Expected session.created, received {created}")
        print(f"connected: {created['session']['id']}")

        await connection.send_raw(json.dumps({
            # Configure transcription before appending audio.
            "type": "session.update",
            "session": {
                "type": "transcription",
                "audio": {"input": {
                    "format": {"type": "audio/pcm", "rate": SAMPLE_RATE},
                    "transcription": {"model": model},
                    "turn_detection": None,
                }},
            },
        }))
        updated = json.loads(await connection.recv_bytes())
        if updated.get("type") != "session.updated":
            raise RuntimeError(f"Expected session.updated, received {updated}")

        final_received = asyncio.Event()

        async def read_events() -> None:
            # Read events concurrently while the producer sends paced PCM frames.
            while not final_received.is_set():
                event = json.loads(await connection.recv_bytes())
                event_type = event.get("type")
                if event_type == "conversation.item.input_audio_transcription.delta":
                    text = event.get("clean_text") or event.get("delta") or ""
                    if text:
                        print(f"partial: {text}")
                elif event_type == "conversation.item.input_audio_transcription.completed":
                    # A completed event, not socket closure, marks success.
                    print(f"final: {event.get('clean_text') or event.get('transcript') or ''}")
                    final_received.set()
                elif event_type == "error":
                    raise realtime_error(event, "Realtime error")

        reader = asyncio.create_task(read_events())
        # Reproduce realtime microphone timing for this prerecorded sample.
        started = time.monotonic()
        for offset in range(0, len(pcm), CHUNK_BYTES):
            target = offset / (SAMPLE_RATE * 2)
            await asyncio.sleep(max(0.0, started + target - time.monotonic()))
            await connection.send_raw(json.dumps({
                "type": "input_audio_buffer.append",
                "audio": base64.b64encode(pcm[offset : offset + CHUNK_BYTES]).decode("ascii"),
            }))
        await connection.send_raw(json.dumps({"type": "input_audio_buffer.commit"}))
        # Commit ends this turn; it does not itself contain the final transcript.
        # CPU self-hosts can take longer than hosted GPU inference to finalize.
        await asyncio.wait_for(reader, timeout=120)
        await connection.send_raw(json.dumps({"type": "session.close"}))


if __name__ == "__main__":
    asyncio.run(main())
