# Decoding controls

Kitten TTS 2 draws each audio token at random from the model's predictions.
The optional `mode`, `temperature`, `top_p`, `top_k`, `min_p`, and
`max_new_tokens` fields control that draw. They are the decoding options of
the Kitten TTS demo, with the same presets and ranges:

| `mode` | `temperature` | `top_p` | `top_k` | `min_p` |
| --- | --- | --- | --- | --- |
| `stable` | `0.8` | `0.8` | `50` | `0` |
| `expressive` (default) | `0.9` | `0.9` | `50` | `0` |

From the repository root:

```bash
cd tts
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
npm install
cp .env.example .env
# Put your tts:generate-enabled KittenML API key in .env.

python controls/decoding_controls.py
node controls/decoding-controls.mjs
```

Both programs read one `[joyful]` line three times and save
`kitten-output-stable.mp3`, `kitten-output-expressive.mp3`, and
`kitten-output-expressive-top-k-40.mp3` in `tts/controls/`. The last take shows that
a field you send overrides the preset. Each request is a fresh take, so running
the program again gives slightly different readings.

The OpenAI SDKs have no parameters for these fields. Python adds them with
`extra_body`; the JavaScript SDK sends extra body fields unchanged.

Or with cURL:

```bash
curl -L --fail-with-body -sS \
  https://api.kittenml.com/v1/audio/speech \
  -H "Authorization: Bearer $KITTENML_API_KEY" \
  -H "Content-Type: application/json" \
  --data '{
    "model": "kitten-tts-2-latest",
    "input": "The harbor lights came on one by one.",
    "voice": "maeve_cozy_female_22",
    "mode": "expressive",
    "top_k": 40
  }' \
  --output kitten-output.mp3
```

An out-of-range value returns `400` with `"code": "invalid_request_error"`
and `param` naming the field; for example, `"top_p": 0.2` is rejected. The
same fields work as realtime WebSocket query parameters, such as
`&mode=expressive&top_k=40`. Start from a preset and change one value at a
time. See
[Decoding controls](https://docs.kittenml.com/tts/generate-speech#decoding-controls)
for every range and rule.
