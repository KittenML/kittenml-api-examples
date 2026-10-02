import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# The same line, read once with each Kitten TTS 2 decoding preset.
TEXT = "[joyful] We actually won the grant! I read the email three times before I believed it."
TAKES = {
    "stable": {"mode": "stable"},  # 0.8 / 0.8 / 50 / 0.
    "expressive": {},  # No decoding fields: the default, expressive, 0.9 / 0.9 / 50 / 0.
    "expressive-top-k-40": {"mode": "expressive", "top_k": 40},  # A sent field overrides the preset.
}


def main() -> None:
    here = Path(__file__).resolve().parent
    load_dotenv(here.parent / ".env")
    api_key = os.environ.get("KITTENML_API_KEY")
    if not api_key:
        raise SystemExit("Copy .env.example to .env and add KITTENML_API_KEY before running.")
    model = os.environ.get("KITTENML_TTS_MODEL") or "kitten-tts-2-latest"
    if model.endswith("-0.8"):
        raise SystemExit("Decoding controls are Kitten TTS 2 only; unset KITTENML_TTS_MODEL.")

    client = OpenAI(
        api_key=api_key,
        base_url=os.environ.get("KITTENML_BASE_URL") or "https://api.kittenml.com/v1",
    )
    voice = os.environ.get("KITTENML_TTS_VOICE") or "eleanor_somber_female_32"
    for name, controls in TAKES.items():
        output = here / f"kitten-output-{name}.mp3"
        # The OpenAI SDK has no parameters for these fields, so extra_body adds them to the JSON.
        audio = client.audio.speech.create(
            model=model,
            input=TEXT,
            voice=voice,
            response_format="mp3",
            extra_body=controls,
        )
        audio.write_to_file(output)
        print(f"saved: {output}")
        print(f"request_id: {audio.response.headers.get('x-request-id') or 'unknown'}")


if __name__ == "__main__":
    main()
