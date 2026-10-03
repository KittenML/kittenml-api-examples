# Complete speech response

Send complete text to `POST /v1/audio/speech` and save the complete audio
response. This is the simplest workflow for short prompts, offline generation,
and SDK integrations that do not need playback to begin immediately.

From the repository root:

```bash
cd tts
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
npm install
cp .env.example .env
# Put your tts:generate-enabled KittenML API key in .env.

python upload/generate_speech.py
node upload/generate-speech.mjs
```

Both programs use the official OpenAI SDK and save
`tts/upload/kitten-output.mp3`. A successful run also prints the response's
`x-request-id`; include that ID when correlating a request with KittenML logs
or support.

Both use Kitten TTS 2 with the `eleanor_somber_female_32` voice unless
`KITTENML_TTS_MODEL` or `KITTENML_TTS_VOICE` is set; see
[Pick a voice](../README.md#pick-a-voice).

The HTTP endpoint accepts up to 40,000 input characters. Keep ordinary
requests around 400–5,000 characters for predictable latency.
