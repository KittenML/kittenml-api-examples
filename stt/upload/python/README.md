# Python upload transcription

Use the official OpenAI Python client to upload an ordinary audio file. This
is the easiest path when you need one final result rather than live partials.

## Run

```bash
cd stt/upload/python
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
# Put your KittenML API key in .env.
python transcribe.py
```

Expected output has this shape:

```text
enriched: [low][slow]A (cold), lucid indifference...[/slow][/low]
clean: A cold, lucid indifference reigned in his soul.
accent: General American
request_id: <request-id>
```

Pass a WAV, FLAC, MP3, M4A, MP4, OGG, or WebM file up to 25 MiB:

```bash
python transcribe.py recording.mp3 --language en
```

Omit `--language` for automatic detection. The API also supports `text`,
`verbose_json`, `srt`, and `vtt` response formats.
