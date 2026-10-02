# List voices

Use `GET /v1/voices?model=kitten-tts-2-latest` to discover the voices you can
pass to `POST /v1/audio/speech` and `WSS /v1/tts/realtime`. The response lists
every Kitten TTS 2 built-in voice with its language, followed by the saved
custom voices your organization owns and any shared voices that KittenML makes
available to every organization. The request is authenticated because custom
voice IDs are private to their owner.

From the repository root:

```bash
cd tts
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
npm install
cp .env.example .env
# Put your tts:generate-enabled KittenML API key in .env.

python voices/list_voices.py
node voices/list-voices.mjs
```

Or call the route directly with cURL:

```bash
curl -L --fail-with-body -sS \
  'https://api.kittenml.com/v1/voices?model=kitten-tts-2-latest' \
  -H "Authorization: Bearer $KITTENML_API_KEY" \
  | python3 -m json.tool --no-ensure-ascii
```

`--no-ensure-ascii` keeps the voice titles and non-Latin language names
readable.

Both programs print the model, its languages, each built-in voice's ID and
title, and the ID of each custom and shared voice:

```text
model: kitten-tts-2-latest
languages: en, ar, de, es, fr, it, pt, ru, zh, hi
built-in voices: 47
- matthew_exhausted_mechanic_male_01 "01 — Matthew — Exhausted Mechanic Male" [en]
- willow_hushed_young_female_02 "02 — Willow — Hushed Young Female" [en]
...
- frank_gravelly_male_18 "18 — Frank — Gravelly Male" [en]
...
- hindi_47 "47 — Hindi (हिन्दी)" [hi]
custom voices: 1
- voice_0123456789abcdef0123456789abcdef "My saved voice" [en]
shared voices: 0
request_id: req_...
```

## Use a listed voice

Every entry has `object: "audio.voice"`, an `id`, a `name`, a `type`, the
`model`, and its `language`. For a built-in voice, `name` is its title. Custom
and shared entries also have `created_at`, a Unix timestamp in seconds.

| `type` | How to pass it as `voice` |
| --- | --- |
| `built_in` | Its `id` string, for example `"frank_gravelly_male_18"`. Voice IDs are case-sensitive. |
| `custom` | An object with its ID, for example `{"id": "voice_0123456789abcdef0123456789abcdef"}`. A bare string is matched against the built-in voice IDs only. |
| `public` | A shared voice that KittenML makes available to every organization. Pass it like a custom voice: `{"id": "voice_..."}`. |

The official OpenAI SDKs accept the object form directly, for example
`voice={"id": "voice_..."}` in Python.

For `WSS /v1/tts/realtime`, put the built-in name or the custom or shared
`voice_...` ID in the `voice` query parameter, URL-encoded. Custom and shared
voices currently use English reference audio and report `language: "en"`.

## Pagination

Every page lists the 47 built-in voices first, then a page of your custom
voices, then any shared voices. `limit` (1–100) and `after` page only through
custom voices; built-in and shared voices repeat on every page. When
`has_more` is `true`, both programs send the response's `last_custom_id` as
`after` and keep reading until the list is complete.

If the shared voices cannot be read, the response still lists your own voices
and sets `public_voices_unavailable` to `true`; both programs print a note and
you can retry.

Only Kitten TTS 2 has a voice catalog here; a KittenTTS 0.8 model ID returns
`404 model_not_found`. The three 0.8 models use the fixed voices `Bella`,
`Jasper`, `Luna`, `Bruno`, `Rosie`, `Hugo`, `Kiki`, and `Leo`.

See [List voices](https://docs.kittenml.com/tts/list-voices) for the complete
response reference.
