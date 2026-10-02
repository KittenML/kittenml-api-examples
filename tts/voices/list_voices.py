import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from dotenv import load_dotenv


def main() -> None:
    # Voice names include Arabic, Cyrillic, Chinese, and Hindi script; print them
    # as UTF-8 even where the console or a redirected file defaults to another
    # encoding.
    sys.stdout.reconfigure(encoding="utf-8")
    here = Path(__file__).resolve().parent
    load_dotenv(here.parent / ".env")
    api_key = os.environ.get("KITTENML_API_KEY")
    if not api_key:
        raise SystemExit("Copy .env.example to .env and add KITTENML_API_KEY before running.")

    base_url = (os.environ.get("KITTENML_BASE_URL") or "https://api.kittenml.com/v1").rstrip("/")
    built_in: list[dict] = []
    custom: list[dict] = []
    shared: dict[str, dict] = {}
    after = None
    while True:
        # Built-in and shared voices come back on every page; limit and after
        # page only your custom voices.
        params = {"model": "kitten-tts-2-latest", "limit": 100}
        if after:
            params["after"] = after
        request = urllib.request.Request(
            f"{base_url}/voices?{urllib.parse.urlencode(params)}",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                # Keep x-request-id with your application logs for support correlation.
                request_id = response.headers.get("x-request-id") or "unknown"
                catalog = json.load(response)
        except urllib.error.HTTPError as error:
            raise SystemExit(f"Voice list failed ({error.code}): {error.read().decode()}") from None
        if not built_in:
            built_in = [voice for voice in catalog["data"] if voice["type"] == "built_in"]
        custom += [voice for voice in catalog["data"] if voice["type"] == "custom"]
        shared.update(
            (voice["id"], voice) for voice in catalog["data"] if voice["type"] == "public"
        )
        if not catalog.get("has_more"):
            break
        after = catalog["last_custom_id"]

    languages = [row["code"] for row in catalog["languages"]]
    print(f"model: {catalog['model']}")
    print(f"languages: {', '.join(languages)}")
    # Pass a built-in voice's id as the request's voice value; its name is the title.
    print(f"built-in voices: {len(built_in)}")
    for voice in built_in:
        print(f"- {voice['id']} \"{voice['name']}\" [{voice['language']}]")
    # Pass a custom voice as {"id": "voice_..."}; its name is only a display label.
    print(f"custom voices: {len(custom)}")
    for voice in custom:
        print(f"- {voice['id']} \"{voice['name']}\" [{voice['language']}]")
    # Shared voices are ones KittenML makes available to every organization.
    # Pass them like custom voices, as {"id": "voice_..."}.
    print(f"shared voices: {len(shared)}")
    for voice in shared.values():
        print(f"- {voice['id']} \"{voice['name']}\" [{voice['language']}]")
    if catalog.get("public_voices_unavailable"):
        print("note: shared voices could not be read this time; retry to see them.")
    print(f"request_id: {request_id}")


if __name__ == "__main__":
    main()
