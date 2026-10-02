import "dotenv/config";

const apiKey = process.env.KITTENML_API_KEY;
if (!apiKey) {
  throw new Error("Copy .env.example to .env and add KITTENML_API_KEY before running.");
}

const baseURL = (process.env.KITTENML_BASE_URL || "https://api.kittenml.com/v1").replace(/\/$/, "");
let builtIn = [];
const custom = [];
const shared = new Map();
let after = null;
let catalog;
let requestId = "unknown";
do {
  // Built-in and shared voices come back on every page; limit and after
  // page only your custom voices.
  const url = new URL(`${baseURL}/voices`);
  url.searchParams.set("model", "kitten-tts-2-latest");
  url.searchParams.set("limit", "100");
  if (after) url.searchParams.set("after", after);
  const response = await fetch(url, {
    headers: { Authorization: `Bearer ${apiKey}` },
  });
  if (!response.ok) {
    throw new Error(`Voice list failed (${response.status}): ${await response.text()}`);
  }
  // Keep x-request-id with your application logs for support correlation.
  requestId = response.headers.get("x-request-id") || "unknown";
  catalog = await response.json();
  if (!builtIn.length) {
    builtIn = catalog.data.filter((voice) => voice.type === "built_in");
  }
  custom.push(...catalog.data.filter((voice) => voice.type === "custom"));
  for (const voice of catalog.data.filter((entry) => entry.type === "public")) {
    shared.set(voice.id, voice);
  }
  after = catalog.has_more ? catalog.last_custom_id : null;
} while (after);

const languages = catalog.languages.map((row) => row.code);
console.log(`model: ${catalog.model}`);
console.log(`languages: ${languages.join(", ")}`);
// Pass a built-in voice's id as the request's voice value; its name is the title.
console.log(`built-in voices: ${builtIn.length}`);
for (const voice of builtIn) {
  console.log(`- ${voice.id} "${voice.name}" [${voice.language}]`);
}
// Pass a custom voice as {"id": "voice_..."}; its name is only a display label.
console.log(`custom voices: ${custom.length}`);
for (const voice of custom) {
  console.log(`- ${voice.id} "${voice.name}" [${voice.language}]`);
}
// Shared voices are ones KittenML makes available to every organization.
// Pass them like custom voices, as {"id": "voice_..."}.
console.log(`shared voices: ${shared.size}`);
for (const voice of shared.values()) {
  console.log(`- ${voice.id} "${voice.name}" [${voice.language}]`);
}
if (catalog.public_voices_unavailable) {
  console.log("note: shared voices could not be read this time; retry to see them.");
}
console.log(`request_id: ${requestId}`);
