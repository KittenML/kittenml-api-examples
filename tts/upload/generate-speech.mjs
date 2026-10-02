import "dotenv/config";
import { writeFile } from "node:fs/promises";
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
// withResponse() keeps the response metadata, including x-request-id.
const { data: audio, request_id: requestId } = await client.audio.speech.create({
  model,
  input: "Hello from the KittenML API.",
  voice,
  response_format: "mp3",
  speed: 1.0,
}).withResponse();

const output = new URL("kitten-output.mp3", import.meta.url);
// Complete-response mode buffers the finished MP3 before writing it once.
await writeFile(output, Buffer.from(await audio.arrayBuffer()));
console.log(`saved: ${output.pathname}`);
console.log(`request_id: ${requestId || "unknown"}`);
