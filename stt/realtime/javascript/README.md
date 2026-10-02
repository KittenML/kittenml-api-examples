# Node.js realtime file streaming

This example uses the standard `ws` package and KittenML's explicit realtime
URL. It streams the included audio in paced 200 ms chunks.

## Run

```bash
cd stt/realtime/javascript
npm install
cp .env.example .env
# Put your KittenML API key in .env.
npm start
```

Expected output has this shape:

```text
connected: <session-id>
enriched partial: [low][slow]A (cold), [pause_short] (lucid)...[/slow][/low]
clean partial: A cold lucid indifference...
enriched final: [low][slow]A (cold), [pause_short] (lucid)...[/slow][/low]
clean final: A cold lucid indifference reigned in his soul.
```

Enriched output is printed first. Its markup carries emotion, tone, pause, and
stress information; clean output removes that markup. The wording and tags can
vary slightly because this is model output.

Realtime errors include both `error.code` and `request_id` for correlation. A
socket close before the final transcript is treated as a failed request even
when the WebSocket close code is `1000`.

## Use your own audio

Convert it to 24 kHz mono PCM16, then pass the resulting file:

```bash
ffmpeg -y -i input.wav -ac 1 -ar 24000 -f s16le input.pcm
npm start -- input.pcm
```

Set an optional language hint as the second argument:

```bash
npm start -- input.pcm es
```
