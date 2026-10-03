# Upload transcription

Already have the whole recording? Drop it here. Use
`POST /v1/audio/transcriptions` when you want one final result, or switch to
[`../realtime/`](../realtime/) when the words should appear while audio is still
arriving.

## Make one final JSON response

From the repository root:

```bash
curl -L --fail-with-body -sS \
  https://api.kittenml.com/v1/audio/transcriptions \
  -H "Authorization: Bearer $KITTENML_API_KEY" \
  -F "file=@stt/realtime/assets/sample.wav" \
  -F "model=kitten-asr-pro-enhanced" \
  -F "response_format=json" \
  | python3 -m json.tool
```

The clean transcript tells you what was said; KittenML's emotion-aware fields
help preserve how it was said. This abridged example omits the `tags` and
`segments` arrays:

```json
{
  "text": "A cold, lucid indifference reigned in his soul.",
  "enriched_text": "[low][slow]A (cold), [pause_short] (lucid) (indifference) reigned in his (soul).[/slow][/low]",
  "accent": "General American",
  "request_id": "<request-id>"
}
```

Model wording, enrichment, and accent can vary. `text` is the clean transcript;
`enriched_text` preserves model annotations.

The accepted `response_format` values are `json`, `verbose_json`, `text`,
`srt`, and `vtt`. Add `-F "language=en"` when you have a useful language hint.
WAV, FLAC, MP3, M4A, MP4, OGG, and WebM inputs are accepted up to 25 MiB.
There is no separate audio-duration limit; practical duration depends on the
container, codec, and bitrate of the encoded file.

The cURL examples use `-L` so a long transcription follows its continuation
URL automatically if processing crosses the hosting platform's synchronous
response window.

For a plain-text response:

```bash
curl -L --fail-with-body -sS \
  https://api.kittenml.com/v1/audio/transcriptions \
  -H "Authorization: Bearer $KITTENML_API_KEY" \
  -F "file=@stt/realtime/assets/sample.wav" \
  -F "model=kitten-asr-pro-enhanced" \
  -F "response_format=text"
```

## Stream the result with SSE

Set `stream=true` to receive transcript events before the final response:

```bash
curl -L --fail-with-body -sS -N \
  https://api.kittenml.com/v1/audio/transcriptions \
  -H "Authorization: Bearer $KITTENML_API_KEY" \
  -F "file=@stt/realtime/assets/sample.wav" \
  -F "model=kitten-asr-pro-enhanced" \
  -F "stream=true"
```

The response is `text/event-stream` and ends after a final event. The events
below are abridged; the terminal `transcript.text.done` event also includes
`accent`, `tags`, and `segments`:

```text
data: {"type":"transcript.text.delta","delta":"A cold, lucid","clean_text":"A cold, lucid","request_id":"<request-id>"}

data: {"type":"transcript.text.done","text":"A cold, lucid indifference reigned in his soul.","request_id":"<request-id>"}

data: [DONE]
```

With `stream=true`, `response_format` does not change the SSE event protocol.

## SDK examples

- [`python/`](python/) uses the official OpenAI Python package.
- [`javascript/`](javascript/) uses the official OpenAI JavaScript package.

Run the Python example:

```bash
cd stt/upload/python
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
# Put your KittenML API key in .env.
python transcribe.py
```
