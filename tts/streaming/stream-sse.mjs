import "dotenv/config";
import { createWriteStream } from "node:fs";
import { once } from "node:events";

const apiKey = process.env.KITTENML_API_KEY;
if (!apiKey) {
  throw new Error("Copy .env.example to .env and add KITTENML_API_KEY before running.");
}

const baseURL = (process.env.KITTENML_BASE_URL || "https://api.kittenml.com/v1").replace(/\/$/, "");
const model = process.env.KITTENML_TTS_MODEL || "kitten-tts-2-latest";
// Kitten TTS 2 voices are numbered labels; the 0.8 models use Bella and friends.
const voice = process.env.KITTENML_TTS_VOICE ||
  (model.endsWith("-0.8") ? "Bella" : "eleanor_somber_female_32");
// Request SSE when your application needs explicit audio-delta event boundaries.
const response = await fetch(`${baseURL}/audio/speech`, {
  method: "POST",
  headers: {
    Authorization: `Bearer ${apiKey}`,
    Accept: "text/event-stream",
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    model,
    input: "The first phrase can play while the next phrase is generated. This keeps longer speech responsive.",
    voice,
    response_format: "mp3",
    stream_format: "sse",
    speed: 1.0,
  }),
});

if (!response.ok || !response.body) {
  throw new Error(`Speech request failed (${response.status}): ${await response.text()}`);
}

const outputURL = new URL("kitten-output-sse.mp3", import.meta.url);
const output = createWriteStream(outputURL);
const decoder = new TextDecoder();
let buffered = "";
let deltaCount = 0;
let byteCount = 0;
let completed = false;
const started = performance.now();

function handleBlock(block) {
  // An SSE event can span several data: lines; join them before parsing JSON.
  const data = block
    .split("\n")
    .filter((line) => line.startsWith("data: "))
    .map((line) => line.slice(6))
    .join("\n");
  if (!data) return;
  const event = JSON.parse(data);
  if (event.type === "speech.audio.delta") {
    // Decode and append each audio piece in arrival order to reconstruct the MP3.
    const chunk = Buffer.from(event.audio, "base64");
    output.write(chunk);
    deltaCount += 1;
    byteCount += chunk.length;
    console.log(
      `audio delta ${deltaCount}: ${chunk.length} bytes ` +
      `at +${(performance.now() - started).toFixed(0)} ms`,
    );
  } else if (event.type === "speech.audio.done") {
    // The stream is valid only after this terminal event arrives.
    completed = true;
    console.log(`speech.audio.done at +${(performance.now() - started).toFixed(0)} ms`);
  } else if (event.type === "error") {
    const code = event.error?.code || "unknown_error";
    const requestId = event.request_id || event.error?.request_id ||
      response.headers.get("x-request-id") || "unknown";
    throw new Error(
      `${event.error?.message || "Speech stream failed"} ` +
      `(code=${code}, request_id=${requestId})`,
    );
  }
}

try {
  // Network chunks do not necessarily align with SSE event boundaries.
  for await (const chunk of response.body) {
    buffered += decoder.decode(chunk, { stream: true });
    let boundary;
    while ((boundary = buffered.indexOf("\n\n")) !== -1) {
      handleBlock(buffered.slice(0, boundary));
      buffered = buffered.slice(boundary + 2);
    }
  }
  buffered += decoder.decode();
  if (buffered.trim()) handleBlock(buffered);
  output.end();
  await once(output, "finish");
} catch (error) {
  output.destroy();
  throw error;
}

if (!completed) {
  // A 200 response can still be incomplete if the connection drops mid-stream.
  throw new Error("Speech stream ended before speech.audio.done");
}
console.log(`saved: ${outputURL.pathname}`);
console.log(`stream: ${deltaCount} audio delta events, ${byteCount} bytes total`);
console.log(`request_id: ${response.headers.get("x-request-id") || "unknown"}`);
