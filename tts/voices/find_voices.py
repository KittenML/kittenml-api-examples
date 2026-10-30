import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

# GET /v1/voices accepts one value for each of these filters.
FILTERS = ("language", "use_case", "tone", "gender", "pitch", "accent", "perceived_age")
# With no arguments, search like the docs example: calm English audiobook voices.
DEFAULT_FILTERS = {"language": "en", "use_case": "audiobook", "tone": "calm"}


def main() -> None:
    # Voice names and descriptions can include non-Latin script; print them as
    # UTF-8 even where the console defaults to another encoding.
    sys.stdout.reconfigure(encoding="utf-8")
    here = Path(__file__).resolve().parent
    load_dotenv(here.parent / ".env")
    api_key = os.environ.get("KITTENML_API_KEY")
    if not api_key:
        raise SystemExit("Copy .env.example to .env and add KITTENML_API_KEY before running.")

    # Read filters such as gender=female from the command line.
    filters: dict[str, str] = {}
    for argument in sys.argv[1:]:
        name, _, value = argument.partition("=")
        if name not in FILTERS or not value:
            raise SystemExit(f"Pass filters as name=value, with a name from: {', '.join(FILTERS)}")
        filters[name] = value
    filters = filters or DEFAULT_FILTERS

    base_url = (os.environ.get("KITTENML_BASE_URL") or "https://api.kittenml.com/v1").rstrip("/")
    public: dict[str, dict] = {}
    saved: list[dict] = []
    after = None
    while True:
        # include_metadata adds each voice's description and listening tags.
        # Filters combine with AND, with or without include_metadata.
        params = {"model": "kitten-tts-2-latest", "include_metadata": "true", "limit": 100}
        params.update(filters)
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
            # An unknown filter value returns 400 with param naming the filter.
            raise SystemExit(f"Voice list failed ({error.code}): {error.read().decode()}") from None
        for voice in catalog["data"]:
            if voice["type"] == "custom":
                saved.append(voice)
            else:
                # Public voices match on every page; keep each one once.
                public[voice["id"]] = voice
        if not catalog.get("has_more"):
            break
        after = catalog["last_custom_id"]

    print(f"filters: {' '.join(f'{name}={value}' for name, value in filters.items())}")
    # Send a public voice's id as the voice string, for example "voice": "otis_en".
    print(f"public voices: {len(public)}")
    for voice in public.values():
        # metadata is null for a voice with no published metadata yet.
        metadata = voice.get("metadata") or {}
        print(f"- {voice['id']} \"{voice['name']}\" [{voice['language']}]")
        if metadata.get("description"):
            print(f"  {metadata['description']}")
    # Saved voices have no metadata, so any filter other than language leaves
    # them out. Send one as an object, "voice": {"id": "voice_..."}.
    print(f"saved voices: {len(saved)}")
    for voice in saved:
        print(f"- {voice['id']} \"{voice['name']}\" [{voice['language']}]")
    if catalog.get("public_voices_unavailable"):
        print("note: the public voices could not be read this time; retry to see them.")
    # metadata_filters lists the values each filter accepts; language takes
    # any code from languages.
    print("accepted filter values:")
    for name, values in (catalog.get("metadata_filters") or {}).items():
        print(f"  {name}: {', '.join(values)}")
    print(f"request_id: {request_id}")


if __name__ == "__main__":
    main()
