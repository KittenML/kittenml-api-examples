import os
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
    output = here / "kitten-output.mp3"
    # This complete-response example waits for the finished MP3 before saving it.
    audio = client.audio.speech.create(
        model=model,
        input="Hello from the KittenML API.",
        voice=voice,
        response_format="mp3",
        speed=1.0,
    )
    # The SDK preserves x-request-id on the underlying HTTP response.
    audio.write_to_file(output)
    print(f"saved: {output}")
    print(f"request_id: {audio.response.headers.get('x-request-id') or 'unknown'}")


if __name__ == "__main__":
    main()
