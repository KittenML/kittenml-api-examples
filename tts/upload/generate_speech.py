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
    # Kitten TTS 2 voice IDs look like eleanor_en; the 0.8 models use Bella and friends.
    voice = os.environ.get("KITTENML_TTS_VOICE") or (
        "Bella" if model.endswith("-0.8") else "eleanor_en"
    )
    if voice.startswith("voice_"):
        # A saved voice is sent as an object; a bare "voice_..." string is
        # rejected with 400 invalid_voice.
        voice = {"id": voice}
    # KITTENML_TTS_STREAM=false asks Kitten TTS 2 for quality over speed: one
    # complete file with higher audio quality, sent once all of it is generated.
    # The OpenAI SDK has no parameter for it, so extra_body adds it to the JSON.
    extra_body = {"stream": False} if os.environ.get("KITTENML_TTS_STREAM") == "false" else None
    output = here / "kitten-output.mp3"
    # This complete-response example waits for the finished MP3 before saving it.
    audio = client.audio.speech.create(
        model=model,
        input="Hello from the KittenML API.",
        voice=voice,
        response_format="mp3",
        speed=1.0,
        extra_body=extra_body,
    )
    # The SDK preserves x-request-id on the underlying HTTP response.
    audio.write_to_file(output)
    print(f"saved: {output}")
    print(f"request_id: {audio.response.headers.get('x-request-id') or 'unknown'}")


if __name__ == "__main__":
    main()
