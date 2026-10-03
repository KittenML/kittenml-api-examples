# Browser microphone transcription with WebRTC

Browser microphone? This is the clean path. The page captures audio with native
WebRTC while a small Node.js server keeps the permanent API key safely out of
the browser and mints a short-lived token for each connection.

This is the WebRTC example. It does not convert microphone audio into base64 or
send audio over a WebSocket. The browser adds its microphone track to an
`RTCPeerConnection`, exchanges SDP through `/v1/realtime/calls`, and receives
OpenAI-style transcript events on the `oai-events` data channel.

## Run

```bash
cd stt/realtime/webrtc
npm install
cp .env.example .env
# Replace your_api_key_here in .env with an ASR-enabled KittenML API key.
npm start
```

Open `http://localhost:3000`, select **Start mic**, allow microphone access,
and make some noise. Speak normally, whisper, add emphasis—give KittenASR Enhanced
something interesting to hear—then select **Stop**. The emotion-aware enriched
transcript appears first, with clean plain text below it. Both update while
recording and finalize after Stop.

Expected terminal output:

```text
Open http://localhost:3000
```

The permanent key is read only by `server.mjs`. The browser receives an `ek_...`
token that is valid for opening a connection for five minutes. After signaling,
media follows the negotiated direct ICE or TURN path; transcript events arrive
on the `oai-events` data channel.

For production, authenticate your users and rate-limit `/api/realtime-token`
before issuing a token. Mint a new token for each Start or reconnect action.

If it behaves differently on your browser or network, keep the request details
and tell us what happened.
