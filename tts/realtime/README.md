# Realtime text input and audio output

Use `WSS /v1/tts/realtime` when text itself becomes available over time, such
as tokens from an LLM. Send text fragments with `input_text.append`; audio
deltas can arrive before `input_text.done`.

From the repository root:

```bash
cd tts
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
npm install
cp .env.example .env
# Put your tts:generate-enabled KittenML API key in .env.

python realtime/stream_input.py
node realtime/stream-input.mjs
```

Both use Kitten TTS 2 with the `eleanor_somber_female_32` voice unless
`KITTENML_TTS_MODEL` or `KITTENML_TTS_VOICE` is set, and URL-encode the voice
into the connection's query string; see
[Pick a voice](../README.md#pick-a-voice).

Both examples concatenate Base64 `speech.audio.delta` payloads and save
headerless 24 kHz mono PCM16 under `tts/realtime/`. A final
`speech.audio.done` confirms a complete generation. Successful runs print the
session request ID. Error output includes both `error.code` and `request_id`
for correlation, and a clean socket close before the terminal event is still
treated as an incomplete generation.

The clients print every audio chunk as it arrives, including its size, elapsed
time, and whether it arrived before or after `input_text.done`.The `.pcm` file is the ordered
concatenation of those chunks so it can be played or stored after the stream.

From the `tts` directory, convert the raw PCM result to a portable WAV file:

```bash
ffmpeg -y \
  -f s16le -ar 24000 -ac 1 \
  -i realtime/kitten-output-input-stream.pcm \
  realtime/kitten-output-input-stream.wav
```

A session accepts up to 262,144 cumulative characters, 8,192 characters per
append, and 64 KiB per WebSocket frame. Send 50–500 characters at a time,
preferably complete phrases. Sessions close after five idle minutes or two
total hours.
