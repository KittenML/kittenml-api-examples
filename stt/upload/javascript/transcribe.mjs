import "dotenv/config";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import OpenAI from "openai";

const apiKey = process.env.KITTENML_API_KEY;
if (!apiKey) {
  throw new Error("Copy .env.example to .env and add KITTENML_API_KEY before running.");
}

const here = path.dirname(fileURLToPath(import.meta.url));
const audioPath = process.argv[2] || path.join(here, "..", "..", "realtime", "assets", "sample.wav");
// The OpenAI client builds the multipart upload and parses the JSON response.
const client = new OpenAI({
  apiKey,
  baseURL: process.env.KITTENML_BASE_URL || "https://api.kittenml.com/v1",
});
const result = await client.audio.transcriptions.create({
  file: fs.createReadStream(audioPath),
  model: process.env.KITTENML_MODEL || "kitten-asr-pro-enhanced",
  response_format: "verbose_json",
});

// Keep request_id in application logs so API failures can be correlated later.
console.log(`enriched: ${result.enriched_text}`);
console.log(`clean: ${result.text}`);
console.log(`accent: ${result.accent || "-"}`);
console.log(`duration: ${result.duration}s`);
console.log(`request_id: ${result.request_id}`);
