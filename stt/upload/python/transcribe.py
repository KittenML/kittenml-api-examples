import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


DEFAULT_MODEL = "kitten-asr-pro-enhanced"
DEFAULT_AUDIO = Path(__file__).resolve().parents[2] / "realtime" / "assets" / "sample.wav"


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload audio to KittenASR Enhanced.")
    parser.add_argument("audio", nargs="?", type=Path, default=DEFAULT_AUDIO)
    parser.add_argument("--language", help="Optional hint such as en or es.")
    args = parser.parse_args()

    load_dotenv(Path(__file__).with_name(".env"))
    api_key = os.environ.get("KITTENML_API_KEY")
    if not api_key:
        raise SystemExit("Copy .env.example to .env and add KITTENML_API_KEY before running.")

    base_url = os.environ.get("KITTENML_BASE_URL", "https://api.kittenml.com/v1")
    model = os.environ.get("KITTENML_MODEL", DEFAULT_MODEL)
    # The OpenAI client handles multipart encoding and response parsing.
    client = OpenAI(api_key=api_key, base_url=base_url)
    options = {
        "model": model,
        "response_format": "json",
    }
    if args.language:
        # Omit language to let the model detect it automatically.
        options["language"] = args.language

    # Keep the file open until the SDK has finished the upload.
    with args.audio.open("rb") as audio:
        result = client.audio.transcriptions.create(file=audio, **options)

    # Log request_id with the result so support can trace this request.
    print(f"enriched: {result.enriched_text}")
    print(f"clean: {result.text}")
    print(f"accent: {result.accent or '-'}")
    print(f"request_id: {result.request_id}")


if __name__ == "__main__":
    main()
