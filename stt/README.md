# Speech to text

Choose the workflow based on when you need the transcript:

| Workflow | Transport | Best for |
| --- | --- | --- |
| [`upload/`](upload/) | HTTPS | Complete recordings and one final response |
| [`realtime/`](realtime/) | WebSocket or WebRTC | Live captions, microphones, calls, and media streams |

Hosted examples default to `kitten-asr-pro-enhanced` and require a KittenML API
key with the `asr:transcribe` scope. Upload accepts common encoded audio formats.
Realtime WebSocket examples send 24 kHz mono PCM16; the browser WebRTC example
captures the microphone directly.

For a self-hosted Docker server, point the examples at its local OpenAI-compatible
API and select the model it serves:

```bash
export KITTENML_API_KEY=local
export KITTENML_BASE_URL=http://127.0.0.1:8000/v1
export KITTENML_REALTIME_URL='ws://127.0.0.1:8000/v1/realtime?model=kitten-asr-small-enhanced'
export KITTENML_MODEL=kitten-asr-small-enhanced  # or kitten-asr-tiny
```

Upload, WebSocket, OpenAI Realtime SDK, and WebRTC examples support both model
IDs. `kitten-asr-tiny` returns plain transcripts;
`kitten-asr-small-enhanced` also returns enriched markup and accent metadata.

Start with [`upload/`](upload/) for the shortest integration or
[`realtime/`](realtime/) when partial transcripts must arrive before the audio
ends.
