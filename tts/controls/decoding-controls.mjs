import "dotenv/config";
import { writeFile } from "node:fs/promises";
import OpenAI from "openai";

// The same line, read once with each Kitten TTS 2 decoding preset.
const text = "[joyful] We actually won the grant! I read the email three times before I believed it.";
const takes = {
  stable: { mode: "stable" }, // 0.8 / 0.8 / 50 / 0.
  expressive: {}, // No decoding fields: the default, expressive, 0.9 / 0.9 / 50 / 0.
  "expressive-top-k-40": { mode: "expressive", top_k: 40 }, // A sent field overrides the preset.
};

const apiKey = process.env.KITTENML_API_KEY;
if (!apiKey) {
  throw new Error("Copy .env.example to .env and add KITTENML_API_KEY before running.");
}
const model = process.env.KITTENML_TTS_MODEL || "kitten-tts-2-latest";
if (model.endsWith("-0.8")) {
  throw new Error("Decoding controls are Kitten TTS 2 only; unset KITTENML_TTS_MODEL.");
}

const client = new OpenAI({
  apiKey,
  baseURL: process.env.KITTENML_BASE_URL || "https://api.kittenml.com/v1",
});
const voice = process.env.KITTENML_TTS_VOICE || "eleanor_somber_female_32";
for (const [name, controls] of Object.entries(takes)) {
  // The SDK sends body fields it has no types for unchanged.
  const { data: audio, request_id: requestId } = await client.audio.speech.create({
    model,
    input: text,
    voice,
    response_format: "mp3",
    ...controls,
  }).withResponse();
  const output = new URL(`kitten-output-${name}.mp3`, import.meta.url);
  await writeFile(output, Buffer.from(await audio.arrayBuffer()));
  console.log(`saved: ${output.pathname}`);
  console.log(`request_id: ${requestId || "unknown"}`);
}
