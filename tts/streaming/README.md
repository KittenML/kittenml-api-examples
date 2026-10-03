# Stream speech output

Send complete text to `POST /v1/audio/speech`, then consume audio while it is
generated. The input still arrives in one HTTP request; only the output is
streamed.

From the repository root, complete the shared setup once:

```bash
cd tts
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
npm install
cp .env.example .env
# Put your tts:generate-enabled KittenML API key in .env.
```

Stream binary MP3 bytes directly to a file:

```bash
python streaming/stream_audio.py
node streaming/stream-audio.mjs
```

Or parse Server-Sent Events and concatenate each decoded
`speech.audio.delta` until `speech.audio.done`:

```bash
python streaming/stream_sse.py
node streaming/stream-sse.mjs
```

All four use Kitten TTS 2 with the `eleanor_somber_female_32` voice unless
`KITTENML_TTS_MODEL` or `KITTENML_TTS_VOICE` is set; see
[Pick a voice](../README.md#pick-a-voice).

The examples save their outputs under `tts/streaming/`. Treat a stream that
ends without its terminal event as incomplete. Successful runs print the
response's `x-request-id`; SSE errors print both their machine-readable
`error.code` and `request_id`.

Each client also prints every chunk or audio-delta event as it arrives, with
its byte size and elapsed time. The binary examples show progressive HTTP
response reads. The SSE examples additionally expose the API's explicit
`speech.audio.delta` boundaries and terminal `speech.audio.done` event. The
saved MP3 is the ordered concatenation of those streamed pieces, not a second
non-streaming response.
