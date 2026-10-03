# Realtime transcription

KittenASR Enhanced streams raw audio over
WebSocket, returns provisional words while someone is still speaking, and
preserves expression in the final transcript.

```text
wss://api.kittenml.com/v1/realtime?model=kitten-asr-pro-enhanced
```

Pick the path closest to your application:

- [`python/`](python/) includes both the official OpenAI client and Python's
  `websockets` package.
- [`javascript/`](javascript/) uses the Node.js `ws` package.
- [`webrtc/`](webrtc/) captures a browser microphone with native WebRTC while
  keeping the permanent key on a small token server.

The Python and Node.js examples feed the included 24 kHz mono PCM16 file at
wall-clock speed in 200 ms appends. This exercises the same public route used
for microphone, call, and media-stream integrations.

The prerecorded-file examples use manual commit.
[`python/manual_turns.py`](python/manual_turns.py) sends one file per explicit
turn, while [`python/microphone.py`](python/microphone.py) keeps listening and
uses server VAD to create natural conversational turns.

The WebSocket event protocol follows the OpenAI Realtime transcription event
shape, with additional KittenML fields for enriched text, accent, and tags.
The canonical `/v1/realtime` route works with the official OpenAI client URL
construction as well as standard WebSocket libraries. The older
`/v1/stt/realtime` route remains a compatibility alias.

Permanent API keys belong only in trusted server, desktop, or command-line
code. For browser microphone input, use [`webrtc/`](webrtc/): its server mints
a short-lived token and the permanent key never enters browser JavaScript.

Realtime sessions have no KittenML-enforced duration limit. Keep one open for
as many turns as your application needs; network, client, or infrastructure
disconnects can still end the connection.
