import base64
import json
import os
import time
import urllib.request
from pathlib import Path

from dotenv import load_dotenv


def main() -> None:
    here = Path(__file__).resolve().parent
    load_dotenv(here.parent / ".env")
    api_key = os.environ.get("KITTENML_API_KEY")
    if not api_key:
        raise SystemExit("Copy .env.example to .env and add KITTENML_API_KEY before running.")

    base_url = (os.environ.get("KITTENML_BASE_URL") or "https://api.kittenml.com/v1").rstrip("/")
    model = os.environ.get("KITTENML_TTS_MODEL") or "kitten-tts-2-latest"
    # Kitten TTS 2 voices are numbered labels; the 0.8 models use Bella and friends.
    voice = os.environ.get("KITTENML_TTS_VOICE") or (
        "Bella" if model.endswith("-0.8") else "eleanor_somber_female_32"
    )
    # SSE is useful when the application needs typed audio-delta events.
    body = json.dumps(
        {
            "model": model,
            "input": (
                "The first phrase can play while the next phrase is generated. "
                "This keeps longer speech responsive."
            ),
            "voice": voice,
            "response_format": "mp3",
            "stream_format": "sse",
            "speed": 1.0,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/audio/speech",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "text/event-stream",
            "Content-Type": "application/json",
        },
    )

    output = here / "kitten-output-sse.mp3"
    delta_count = 0
    byte_count = 0
    completed = False
    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=120) as response, output.open("wb") as audio:
        # Keep the response request ID for support and telemetry correlation.
        request_id = response.headers.get("x-request-id") or "unknown"
        for raw_line in response:
            # Blank lines and other SSE fields are not JSON payloads.
            if not raw_line.startswith(b"data: "):
                continue
            event = json.loads(raw_line[len(b"data: ") :])
            if event.get("type") == "speech.audio.delta":
                # Append decoded pieces in order to reconstruct the requested format.
                chunk = base64.b64decode(event["audio"], validate=True)
                audio.write(chunk)
                delta_count += 1
                byte_count += len(chunk)
                elapsed_ms = (time.monotonic() - started) * 1_000
                print(
                    f"audio delta {delta_count}: {len(chunk)} bytes "
                    f"at +{elapsed_ms:.0f} ms",
                    flush=True,
                )
            elif event.get("type") == "speech.audio.done":
                # Only this terminal event confirms a complete audio file.
                completed = True
                elapsed_ms = (time.monotonic() - started) * 1_000
                print(f"speech.audio.done at +{elapsed_ms:.0f} ms", flush=True)
            elif event.get("type") == "error":
                error = event.get("error") if isinstance(event.get("error"), dict) else {}
                code = error.get("code") or "unknown_error"
                event_request_id = event.get("request_id") or error.get("request_id") or request_id
                message = error.get("message") or "Speech stream failed"
                raise RuntimeError(f"{message} (code={code}, request_id={event_request_id})")

    if not completed:
        # A dropped HTTP connection must not be mistaken for successful synthesis.
        raise RuntimeError("Speech stream ended before speech.audio.done")
    print(f"saved: {output}")
    print(f"stream: {delta_count} audio delta events, {byte_count} bytes total")
    print(f"request_id: {request_id}")


if __name__ == "__main__":
    main()
