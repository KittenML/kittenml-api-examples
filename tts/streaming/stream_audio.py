import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


def main() -> None:
    here = Path(__file__).resolve().parent
    load_dotenv(here.parent / ".env")
    api_key = os.environ.get("KITTENML_API_KEY")
    if not api_key:
        raise SystemExit("Copy .env.example to .env and add KITTENML_API_KEY before running.")

    client = OpenAI(
        api_key=api_key,
        base_url=os.environ.get("KITTENML_BASE_URL") or "https://api.kittenml.com/v1",
    )
    model = os.environ.get("KITTENML_TTS_MODEL") or "kitten-tts-2-latest"
    # Kitten TTS 2 voices are numbered labels; the 0.8 models use Bella and friends.
    voice = os.environ.get("KITTENML_TTS_VOICE") or (
        "Bella" if model.endswith("-0.8") else "eleanor_somber_female_32"
    )
    output = here / "kitten-output-stream.mp3"
    # The streaming context exposes headers before it copies response chunks to disk.
    with client.audio.speech.with_streaming_response.create(
        model=model,
        input="The first sentence can play while the next sentence is generated.",
        voice=voice,
        response_format="mp3",
        speed=1.0,
    ) as audio:
        # Keep x-request-id with your application logs for support correlation.
        request_id = audio.headers.get("x-request-id") or "unknown"
        # Write each response chunk immediately instead of buffering the MP3.
        started = time.monotonic()
        chunk_count = 0
        byte_count = 0
        with output.open("wb") as output_file:
            for chunk in audio.iter_bytes(chunk_size=16 * 1024):
                output_file.write(chunk)
                chunk_count += 1
                byte_count += len(chunk)
                elapsed_ms = (time.monotonic() - started) * 1_000
                print(
                    f"audio chunk {chunk_count}: {len(chunk)} bytes "
                    f"at +{elapsed_ms:.0f} ms",
                    flush=True,
                )
    print(f"saved: {output}")
    print(f"stream: {chunk_count} response chunks, {byte_count} bytes total")
    print(f"request_id: {request_id}")


if __name__ == "__main__":
    main()
