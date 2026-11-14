import "dotenv/config";

// GET /v1/voices accepts one value for each of these filters.
const filterNames = ["language", "use_case", "tone", "gender", "pitch", "accent", "perceived_age"];
// With no arguments, search like the docs example: calm English audiobook voices.
const defaultFilters = { language: "en", use_case: "audiobook", tone: "calm" };

const apiKey = process.env.KITTENML_API_KEY;
if (!apiKey) {
  throw new Error("Copy .env.example to .env and add KITTENML_API_KEY before running.");
}

// Read filters such as gender=female from the command line.
let filters = {};
for (const argument of process.argv.slice(2)) {
  const [name, ...rest] = argument.split("=");
  const value = rest.join("=");
  if (!filterNames.includes(name) || !value) {
    throw new Error(`Pass filters as name=value, with a name from: ${filterNames.join(", ")}`);
  }
  filters[name] = value;
}
if (!Object.keys(filters).length) filters = defaultFilters;

const baseURL = (process.env.KITTENML_BASE_URL || "https://api.kittenml.com/v1").replace(/\/$/, "");
const publicVoices = new Map();
const saved = [];
let after = null;
let catalog;
let requestId = "unknown";
do {
  // include_metadata adds each voice's description and listening tags.
  // Filters combine with AND, with or without include_metadata.
  const url = new URL(`${baseURL}/voices`);
  url.searchParams.set("model", "kitten-tts-2-latest");
  url.searchParams.set("include_metadata", "true");
  url.searchParams.set("limit", "100");
  for (const [name, value] of Object.entries(filters)) url.searchParams.set(name, value);
  if (after) url.searchParams.set("after", after);
  const response = await fetch(url, {
    headers: { Authorization: `Bearer ${apiKey}` },
  });
  if (!response.ok) {
    // An unknown filter value returns 400 with param naming the filter.
    throw new Error(`Voice list failed (${response.status}): ${await response.text()}`);
  }
  // Keep x-request-id with your application logs for support correlation.
  requestId = response.headers.get("x-request-id") || "unknown";
  catalog = await response.json();
  for (const voice of catalog.data) {
    if (voice.type === "custom") {
      saved.push(voice);
    } else {
      // Public voices match on every page; keep each one once.
      publicVoices.set(voice.id, voice);
    }
  }
  after = catalog.has_more ? catalog.last_custom_id : null;
} while (after);

const summary = Object.entries(filters).map(([name, value]) => `${name}=${value}`);
console.log(`filters: ${summary.join(" ")}`);
// Send a public voice's id as the voice string, for example "voice": "otis_en".
console.log(`public voices: ${publicVoices.size}`);
for (const voice of publicVoices.values()) {
  console.log(`- ${voice.id} "${voice.name}" [${voice.language}]`);
  // metadata is null for a voice with no published metadata yet.
  if (voice.metadata?.description) console.log(`  ${voice.metadata.description}`);
}
// Saved voices have no metadata, so any filter other than language leaves
// them out. Send one as an object, "voice": {"id": "voice_..."}.
console.log(`saved voices: ${saved.length}`);
for (const voice of saved) {
  console.log(`- ${voice.id} "${voice.name}" [${voice.language}]`);
}
if (catalog.public_voices_unavailable) {
  console.log("note: the public voices could not be read this time; retry to see them.");
}
// metadata_filters lists the values each filter accepts; language takes any
// code from languages.
console.log("accepted filter values:");
for (const [name, values] of Object.entries(catalog.metadata_filters || {})) {
  console.log(`  ${name}: ${values.join(", ")}`);
}
console.log(`request_id: ${requestId}`);
