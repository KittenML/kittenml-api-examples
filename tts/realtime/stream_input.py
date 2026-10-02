import base64
import json
import os
import threading
import time
from pathlib import Path
from urllib.parse import urlencode

import websocket
from dotenv import load_dotenv


def main() -> None:
    here = Path(__file__).resolve().parent
    load_dotenv(here.parent / ".env")
    api_key = os.environ.get("KITTENML_API_KEY")
    if not api_key:
        raise SystemExit("Copy .env.example to .env and add KITTENML_API_KEY before running.")

    base_url = os.environ.get("KITTENML_BASE_URL") or "https://api.kittenml.com/v1"
    model = os.environ.get("KITTENML_TTS_MODEL") or "kitten-tts-2-latest"
    # Kitten TTS 2 voices are numbered labels; the 0.8 models use Bella and friends.
    voice = os.environ.get("KITTENML_TTS_VOICE") or (
        "Bella" if model.endswith("-0.8") else "eleanor_somber_female_32"
    )
    websocket_base = base_url.replace("https://", "wss://").replace("http://", "ws://")
    # urlencode escapes the spaces and dashes in voice names.
    query = urlencode({"model": model, "voice": voice, "speed": 1, "response_format": "pcm"})
    url = f"{websocket_base.rstrip('/')}/tts/realtime?{query}"
    connection = websocket.create_connection(
        url,
        header=[f"Authorization: Bearer {api_key}"],
        timeout=30,
    )
    # Keep long sessions alive after the shorter connection timeout has passed.
    connection.settimeout(600)
    response_headers = connection.headers or {}
    request_id = (
        response_headers.get("x-request-id")
        or response_headers.get("X-Request-ID")
        or "unknown"
    )
    output_path = here / "kitten-output-input-stream.pcm"
    output = output_path.open("wb")
    stream_started = time.monotonic()
    input_done_sent = threading.Event()
    result: dict[str, object] = {
        "done": None,
        "error": None,
        "bytes": 0,
        "chunks": 0,
        "first_audio_ms": None,
        "audio_before_input_done": False,
        "request_id": request_id,
    }

    def receive_audio() -> None:
        # Receive concurrently so text can continue arriving while audio is written.
        try:
            while True:
                event = json.loads(connection.recv())
                event_type = event.get("type")
                if event_type == "session.created":
                    session = event.get("session") if isinstance(event.get("session"), dict) else {}
                    result["request_id"] = (
                        event.get("request_id") or session.get("id") or result["request_id"]
                    )
                elif event_type == "speech.audio.delta":
                    # Deltas are contiguous 24 kHz, mono, 16-bit PCM bytes.
                    body = base64.b64decode(event["audio"], validate=True)
                    output.write(body)
                    result["bytes"] = int(result["bytes"]) + len(body)
                    result["chunks"] = int(result["chunks"]) + 1
                    elapsed_ms = (time.monotonic() - stream_started) * 1_000
                    if result["first_audio_ms"] is None:
                        result["first_audio_ms"] = elapsed_ms
                    phase = "after" if input_done_sent.is_set() else "before"
                    if phase == "before":
                        result["audio_before_input_done"] = True
                    print(
                        f"audio chunk {result['chunks']}: {len(body)} bytes "
                        f"at +{elapsed_ms:.0f} ms ({phase} input_text.done)",
                        flush=True,
                    )
                elif event_type == "input_text.batch_done":
                    elapsed_ms = (time.monotonic() - stream_started) * 1_000
                    print(
                        f"input batch synthesized through "
                        f"{event.get('input_characters', '?')} characters "
                        f"at +{elapsed_ms:.0f} ms",
                        flush=True,
                    )
                elif event_type == "speech.audio.done":
                    # This terminal event is the success boundary for the output file.
                    result["done"] = event
                    return
                elif event_type == "error":
                    result["error"] = event
                    return
        except Exception as error:  # surfaced on the main thread below
            result["error"] = error

    receiver = threading.Thread(target=receive_audio, daemon=True)
    receiver.start()

    # Replace these fragments with tokens or sentences from your LLM or text producer.
    fragments = (
        "The text can arrive incrementally. ",
        "Audio starts before the full response exists. ",
        "This is the final fragment.",
    )
    for fragment_number, fragment in enumerate(fragments, start=1):
        connection.send(json.dumps({"type": "input_text.append", "text": fragment}))
        elapsed_ms = (time.monotonic() - stream_started) * 1_000
        print(f"text fragment {fragment_number} sent at +{elapsed_ms:.0f} ms", flush=True)
        # Simulate text becoming available over time, for example from an LLM.
        if fragment_number < len(fragments):
            time.sleep(2.0)
    connection.send(json.dumps({"type": "input_text.done"}))
    input_done_sent.set()
    elapsed_ms = (time.monotonic() - stream_started) * 1_000
    print(f"input_text.done sent at +{elapsed_ms:.0f} ms", flush=True)

    # Never accept a socket close as success unless speech.audio.done was received.
    receiver.join(timeout=600)
    output.close()
    connection.close()
    if receiver.is_alive():
        raise RuntimeError("TTS input stream timed out")
    if result["error"]:
        if not isinstance(result["error"], dict):
            raise RuntimeError(
                "TTS input stream closed before speech.audio.done "
                f"(code=connection_closed, request_id={result['request_id']}): "
                f"{result['error']}"
            )
        event = result["error"]
        # Preserve code and request_id so support can correlate the failed session.
        error = event.get("error") if isinstance(event.get("error"), dict) else {}
        code = error.get("code") or "unknown_error"
        event_request_id = (
            event.get("request_id")
            or error.get("request_id")
            or result["request_id"]
        )
        message = error.get("message") or "TTS input stream failed"
        raise RuntimeError(f"{message} (code={code}, request_id={event_request_id})")
    if not result["done"]:
        raise RuntimeError(
            "TTS input stream ended before speech.audio.done "
            f"(code=connection_closed, request_id={result['request_id']})"
        )

    audio_seconds = int(result["bytes"]) / 2 / 24_000
    print(f"saved: {output_path} ({audio_seconds:.3f} seconds of 24 kHz PCM)")
    print(
        f"stream: {result['chunks']} audio chunks; first audio at "
        f"+{float(result['first_audio_ms'] or 0):.0f} ms; "
        f"audio before input_text.done: {str(result['audio_before_input_done']).lower()}"
    )
    print(f"request_id: {result['request_id']}")


if __name__ == "__main__":
    main()
