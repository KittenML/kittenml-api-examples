import "dotenv/config";
import { createWriteStream } from "node:fs";
import { once } from "node:events";
import WebSocket from "ws";

const apiKey = process.env.KITTENML_API_KEY;
if (!apiKey) {
  throw new Error("Copy .env.example to .env and add KITTENML_API_KEY before running.");
}

const baseURL = (process.env.KITTENML_BASE_URL || "https://api.kittenml.com/v1")
  .replace(/^https:/, "wss:")
  .replace(/^http:/, "ws:")
  .replace(/\/$/, "");
const model = process.env.KITTENML_TTS_MODEL || "kitten-tts-2-latest";
// Kitten TTS 2 voices are numbered labels; the 0.8 models use Bella and friends.
const voice = process.env.KITTENML_TTS_VOICE ||
  (model.endsWith("-0.8") ? "Bella" : "eleanor_somber_female_32");
// URLSearchParams escapes the spaces and dashes in voice names.
const query = new URLSearchParams({ model, voice, speed: "1", response_format: "pcm" });
const url = `${baseURL}/tts/realtime?${query}`;
// This is a server-side example. Browser clients should use a temporary token.
const socket = new WebSocket(url, { headers: { Authorization: `Bearer ${apiKey}` } });
const outputURL = new URL("kitten-output-input-stream.pcm", import.meta.url);
const output = createWriteStream(outputURL);
const outputFinished = once(output, "finish");
let audioBytes = 0;
let audioChunks = 0;
let firstAudioMs = null;
let audioBeforeInputDone = false;
let inputDoneSent = false;
let requestId = "unknown";
let terminalReceived = false;
const streamStarted = performance.now();

socket.on("upgrade", (response) => {
  // Save the handshake request ID for support and telemetry correlation.
  requestId = response.headers["x-request-id"] || "unknown";
});

const completed = new Promise((resolve, reject) => {
  let settled = false;
  const fail = (error) => {
    if (settled) return;
    settled = true;
    output.destroy();
    reject(error);
  };
  socket.on("message", (raw) => {
    try {
      const event = JSON.parse(raw.toString());
      if (event.type === "session.created") {
        requestId = event.request_id || event.session?.id || requestId;
      } else if (event.type === "speech.audio.delta") {
        // Each delta is the next contiguous piece of 24 kHz, mono, 16-bit PCM.
        const body = Buffer.from(event.audio, "base64");
        output.write(body);
        audioBytes += body.length;
        audioChunks += 1;
        const elapsedMs = performance.now() - streamStarted;
        firstAudioMs ??= elapsedMs;
        const phase = inputDoneSent ? "after" : "before";
        audioBeforeInputDone ||= !inputDoneSent;
        console.log(
          `audio chunk ${audioChunks}: ${body.length} bytes ` +
          `at +${elapsedMs.toFixed(0)} ms (${phase} input_text.done)`,
        );
      } else if (event.type === "input_text.batch_done") {
        const elapsedMs = performance.now() - streamStarted;
        console.log(
          `input batch synthesized through ${event.input_characters ?? "?"} ` +
          `characters at +${elapsedMs.toFixed(0)} ms`,
        );
      } else if (event.type === "speech.audio.done") {
        // Only this terminal event confirms the PCM file is complete.
        requestId = event.request_id || requestId;
        terminalReceived = true;
        settled = true;
        output.end();
        resolve(event);
      } else if (event.type === "error") {
        const code = event.error?.code || "unknown_error";
        const eventRequestId = event.request_id || event.error?.request_id || requestId;
        fail(new Error(
          `${event.error?.message || "TTS input stream failed"} ` +
          `(code=${code}, request_id=${eventRequestId})`,
        ));
      }
    } catch (error) {
      fail(error);
    }
  });
  socket.on("error", fail);
  socket.on("close", (code) => {
    if (!terminalReceived) {
      fail(new Error(
        `WebSocket closed with ${code} before speech.audio.done ` +
        `(code=connection_closed, request_id=${requestId})`,
      ));
    }
  });
});

await once(socket, "open");
// Replace these fragments with tokens or sentences from your LLM or text producer.
const fragments = [
  "The text can arrive incrementally. ",
  "Audio starts before the full response exists. ",
  "This is the final fragment.",
];
for (const [index, text] of fragments.entries()) {
  socket.send(JSON.stringify({ type: "input_text.append", text }));
  console.log(`text fragment ${index + 1} sent at +${(performance.now() - streamStarted).toFixed(0)} ms`);
  // Simulate text becoming available over time, for example from an LLM.
  if (index < fragments.length - 1) {
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
}
socket.send(JSON.stringify({ type: "input_text.done" }));
inputDoneSent = true;
console.log(`input_text.done sent at +${(performance.now() - streamStarted).toFixed(0)} ms`);

// Wait for speech.audio.done and for the file stream to flush before exiting.
await completed;
await outputFinished;
socket.close();
console.log(`saved: ${outputURL.pathname} (${(audioBytes / 2 / 24_000).toFixed(3)} seconds of 24 kHz PCM)`);
console.log(
  `stream: ${audioChunks} audio chunks; first audio at +${(firstAudioMs || 0).toFixed(0)} ms; ` +
  `audio before input_text.done: ${audioBeforeInputDone}`,
);
console.log(`request_id: ${requestId}`);
