# Node.js upload transcription

Use the official OpenAI JavaScript package to upload an ordinary audio file.

```bash
cd stt/upload/javascript
npm install
cp .env.example .env
# Put your KittenML API key in .env.
npm start
```

Expected output has this shape:

```text
enriched: [low][slow]A (cold), lucid indifference...[/slow][/low]
clean: A cold, lucid indifference reigned in his soul.
accent: General American
duration: 4.275s
request_id: <request-id>
```

Pass another supported file as the first argument:

```bash
npm start -- recording.flac
```
