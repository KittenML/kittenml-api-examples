import "dotenv/config";
import { createWriteStream } from "node:fs";
import { once } from "node:events";
import OpenAI from "openai";

const apiKey = process.env.KITTENML_API_KEY;
if (!apiKey) {
  throw new Error("Copy .env.example to .env and add KITTENML_API_KEY before running.");
}

const client = new OpenAI({
  apiKey,
  baseURL: process.env.KITTENML_BASE_URL || "https://api.kittenml.com/v1",
});
const model = process.env.KITTENML_TTS_MODEL || "kitten-tts-2-latest";
// Kitten TTS 2 voices are numbered labels; the 0.8 models use Bella and friends.
const voice = process.env.KITTENML_TTS_VOICE ||
  (model.endsWith("-0.8") ? "Bella" : "eleanor_somber_female_32");
// withResponse() exposes x-request-id while data remains the SDK audio response.
const { data: audio, request_id: requestId } = await client.audio.speech.create({
  model,
  input: "The first sentence can play while the next sentence is generated.",
  voice,
  response_format: "mp3",
  speed: 1.0,
}).withResponse();

const output = new URL("kitten-output-stream.mp3", import.meta.url);
if (!audio.body) {
  throw new Error("The speech response did not include an audio stream.");
}
// Write network chunks directly to disk instead of buffering the complete MP3.
const outputFile = createWriteStream(output);
const started = performance.now();
let chunkCount = 0;
let byteCount = 0;
for await (const chunk of audio.body) {
  chunkCount += 1;
  byteCount += chunk.length;
  if (!outputFile.write(chunk)) await once(outputFile, "drain");
  console.log(
    `audio chunk ${chunkCount}: ${chunk.length} bytes ` +
    `at +${(performance.now() - started).toFixed(0)} ms`,
  );
}
outputFile.end();
await once(outputFile, "finish");
console.log(`saved: ${output.pathname}`);
console.log(`stream: ${chunkCount} response chunks, ${byteCount} bytes total`);
console.log(`request_id: ${requestId || "unknown"}`);
