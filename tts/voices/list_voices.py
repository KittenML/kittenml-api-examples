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
    public: dict[str, dict] = {}
    saved: list[dict] = []
    after = None
    while True:
        # The public voices come back on every page; limit and after page only
        # your saved voices.
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
        for voice in catalog["data"]:
            if voice["type"] == "custom":
                saved.append(voice)
            else:
                # Every other voice (type "public") is selected by its id string.
                public[voice["id"]] = voice
        if not catalog.get("has_more"):
            break
        after = catalog["last_custom_id"]

    languages = [row["code"] for row in catalog["languages"]]
    print(f"model: {catalog['model']}")
    print(f"languages: {', '.join(languages)}")
    # Public voices are the ones KittenML makes available to every organization.
    # Send the id as the voice string, for example "voice": "frank_en".
    print(f"public voices: {len(public)} (send the id as the voice string)")
    for voice in public.values():
        print(f"- {voice['id']} \"{voice['name']}\" [{voice['language']}]")
    # Saved voices are your organization's own. Send one as an object,
    # "voice": {"id": "voice_..."}; its name is only a display label.
    print(f"saved voices: {len(saved)} (send as {{\"id\": \"voice_...\"}})")
    for voice in saved:
        print(f"- {voice['id']} \"{voice['name']}\" [{voice['language']}]")
    if catalog.get("public_voices_unavailable"):
        print("note: the public voices could not be read this time; retry to see them.")
    print(f"request_id: {request_id}")


if __name__ == "__main__":
    main()
