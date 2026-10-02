import "dotenv/config";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import WebSocket from "ws";

const MODEL = process.env.KITTENML_MODEL || "kitten-asr-pro-enhanced";
const URL = process.env.KITTENML_REALTIME_URL ||
  `wss://api.kittenml.com/v1/realtime?model=${MODEL}`;
const SAMPLE_RATE = 24_000;
const BYTES_PER_SECOND = SAMPLE_RATE * 2;
// Send 16-bit mono PCM in realtime-sized frames instead of uploading the file at once.
const CHUNK_MILLISECONDS = 200;
const CHUNK_BYTES = BYTES_PER_SECOND * CHUNK_MILLISECONDS / 1000;
const here = path.dirname(fileURLToPath(import.meta.url));
const audioPath = process.argv[2] || path.join(here, "..", "assets", "sample.pcm");
const language = process.argv[3];
const apiKey = process.env.KITTENML_API_KEY;

if (!apiKey) throw new Error("Copy .env.example to .env and add KITTENML_API_KEY before running.");

const pcm = fs.readFileSync(audioPath);
// Browser clients should use a temporary token; this server-side example can send the API key.
const socket = new WebSocket(URL, { headers: { Authorization: `Bearer ${apiKey}` } });
const sleep = ms => new Promise(resolve => setTimeout(resolve, Math.max(0, ms)));

function realtimeError(event, fallback) {
  const code = event.error?.code || "unknown_error";
  const requestId = event.request_id || event.error?.request_id || "unknown";
  const message = event.error?.message || fallback;
  return new Error(`${message} (code=${code}, request_id=${requestId})`);
}

await new Promise((resolve, reject) => {
  let previousEnriched = "";
  let previousClean = "";
  let finalReceived = false;
  const timeout = setTimeout(() => reject(new Error("Timed out waiting for a final transcript.")), 90_000);
  const fail = error => {
    clearTimeout(timeout);
    socket.close();
    reject(error instanceof Error ? error : new Error(String(error)));
  };

  socket.on("message", async raw => {
    try {
      const event = JSON.parse(raw.toString());
      if (event.type === "session.created") {
        // Configure transcription before sending any audio.
        console.log(`connected: ${event.session.id}`);
        const transcription = { model: MODEL };
        if (language) transcription.language = language;
        socket.send(JSON.stringify({
          type: "session.update",
          session: {
            type: "transcription",
            audio: { input: {
              format: { type: "audio/pcm", rate: SAMPLE_RATE },
              transcription,
              turn_detection: null,
            }},
          },
        }));
      } else if (event.type === "session.updated") {
        // Pace prerecorded audio like a live microphone so partials arrive naturally.
        const started = performance.now();
        for (let offset = 0; offset < pcm.length; offset += CHUNK_BYTES) {
          const chunk = pcm.subarray(offset, Math.min(offset + CHUNK_BYTES, pcm.length));
          socket.send(JSON.stringify({
            type: "input_audio_buffer.append",
            audio: chunk.toString("base64"),
          }));
          const targetMs = (offset + chunk.length) / BYTES_PER_SECOND * 1000;
          await sleep(targetMs - (performance.now() - started));
        }
        socket.send(JSON.stringify({ type: "input_audio_buffer.commit" }));
      } else if (event.type === "conversation.item.input_audio_transcription.delta") {
        // Delta events can revise prior text, so print only changed snapshots.
        const enriched = event.enriched_text || event.text || "";
        const clean = event.clean_text || event.delta || "";
        if (enriched && enriched !== previousEnriched) {
          previousEnriched = enriched;
          console.log(`enriched partial: ${enriched}`);
        }
        if (clean && clean !== previousClean) {
          previousClean = clean;
          console.log(`clean partial: ${clean}`);
        }
      } else if (event.type === "conversation.item.input_audio_transcription.completed") {
        // The completed event is the only successful terminal event.
        finalReceived = true;
        console.log(`enriched final: ${event.enriched_text || event.text || ""}`);
        console.log(`clean final: ${event.transcript || event.clean_text || ""}`);
        clearTimeout(timeout);
        socket.close();
        resolve();
      } else if (event.type === "error") {
        fail(realtimeError(event, "Realtime request failed."));
      }
    } catch (error) {
      fail(error);
    }
  });
  socket.on("error", fail);
  socket.on("close", (code) => {
    // A clean WebSocket close is still a failure if no final transcript arrived.
    if (!finalReceived) {
      fail(new Error(
        `WebSocket closed with ${code} before the completed transcript ` +
        "(code=connection_closed, request_id=unknown)",
      ));
    }
  });
});
