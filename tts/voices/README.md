# List voices

Use `GET /v1/voices?model=kitten-tts-2-latest` to discover the voices you can
pass to `POST /v1/audio/speech` and `WSS /v1/tts/realtime`. The response lists
the saved voices your organization owns, then the public voices that KittenML
makes available to every organization, each with its language. The request is
authenticated because saved voice IDs are private to their owner.

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

`--no-ensure-ascii` keeps the voice names and non-Latin language names
readable.

Both programs print the model and its languages, then the public voices and
your saved voices, each with its ID, name, and language. This output is
shortened; the full list has every public voice:

```text
model: kitten-tts-2-latest
languages: hi, zh, ru, pt, it, fr, es, en, de, ar, he, fi, da, sv, id, pl, nl, tr, ko, ja
public voices: 173 (send the id as the voice string)
- priya_hi "Priya — Hindi (हिन्दी)" [hi]
- lin_zh "Lin — Chinese (Simplified) (简体中文)" [zh]
- alexei_ru "Alexei — Russian (Русский)" [ru]
...
- eleanor_en "Eleanor — Somber Female" [en]
...
- frank_en "Frank — Reserved Announcer" [en]
...
saved voices: 1 (send as {"id": "voice_..."})
- voice_0123456789abcdef0123456789abcdef "My saved voice" [en]
request_id: req_...
```

## Find voices by language and listening tags

`find_voices.py` and `find-voices.mjs` add `include_metadata=true` and filters
to the same route, then print each matching voice with its short description:

```bash
python voices/find_voices.py
node voices/find-voices.mjs gender=female use_case=audiobook
```

With no arguments, both search for calm English audiobook voices
(`language=en use_case=audiobook tone=calm`). Pass filters as `name=value`:
`language`, `use_case`, `tone`, `gender`, `pitch`, `accent`, or
`perceived_age`, one value each. Different filters combine with AND. This
output is shortened:

```text
filters: language=en use_case=audiobook tone=calm
public voices: ...
- otis_en "Otis — Rumbling Male" [en]
  Low-pitched, resonant voice that sounds middle-aged, with a calm and confident delivery. Suggested for narration and announcements.
...
saved voices: 0
accepted filter values:
  gender: female, male
  accent: american, brazilian, standard, english_accented
  use_case: audiobook, education, conversational, news, announcements, podcast, characters, advertising, relaxation, tours
  tone: calm, confident, serious, friendly, energetic, reserved
  pitch: low, medium, high
  perceived_age: young_adult, middle_aged, older_adult
request_id: req_...
```

Or with cURL:

```bash
curl -L --fail-with-body -sS \
  'https://api.kittenml.com/v1/voices?model=kitten-tts-2-latest&language=en&use_case=audiobook&tone=calm&include_metadata=true' \
  -H "Authorization: Bearer $KITTENML_API_KEY" \
  | python3 -m json.tool --no-ensure-ascii
```

`language` takes any `code` from the response's `languages`. An unknown value
returns `400 invalid_request_error`, with `param` naming the filter. A voice
without a value for a field never matches a filter on that field. Saved voices
have no metadata, so any filter other than `language` leaves them out.
`metadata` is `null` for a voice with no published metadata yet.

## Use a listed voice

Every entry has `object: "audio.voice"`, an `id`, a `name`, a `type`, the
`model`, its `language`, `experimental`, and `created_at`, a Unix timestamp in
seconds. A public voice's `name` is its display name, such as
`Frank — Reserved Announcer`; a saved voice's `name` is the name it was saved
with.

| `type` | What it is | How to pass it as `voice` |
| --- | --- | --- |
| `public` | A voice that KittenML makes available to every organization | Its `id` string, for example `"voice": "frank_en"`. Voice IDs are case-sensitive. |
| `custom` | A saved voice your organization owns | An object with its ID, for example `"voice": {"id": "voice_0123456789abcdef0123456789abcdef"}`. A bare `voice_...` string is rejected with `400 invalid_voice`. |

The official OpenAI SDKs accept both forms directly, for example
`voice="frank_en"` or `voice={"id": "voice_..."}` in Python.

For `WSS /v1/tts/realtime`, put the public voice's `id` or your saved voice's
`voice_...` ID in the `voice` query parameter, URL-encoded. A public voice
reports the language it speaks; a saved voice reports the language of its
reference audio, or `en` when that language is unclear.

## Pagination

Each page lists up to `limit` of your saved voices, newest first, then all the
public voices. `limit` (1–100) and `after` page only through your saved
voices; the public voices repeat on every page and are not counted by `limit`.
When `has_more` is `true`, both programs send the response's `last_custom_id`
as `after` and keep reading until the list is complete, and print each public
voice once.

If the public voices cannot be read, the response still lists your saved
voices and sets `public_voices_unavailable` to `true`; both programs print a
note and you can retry.

Only Kitten TTS 2 has a voice catalog here; a KittenTTS 0.8 model ID returns
`404 model_not_found`. The three 0.8 models use the fixed voices `Bella`,
`Jasper`, `Luna`, `Bruno`, `Rosie`, `Hugo`, `Kiki`, and `Leo`.

See [List voices](https://docs.kittenml.com/tts/list-voices) for the complete
response reference.
