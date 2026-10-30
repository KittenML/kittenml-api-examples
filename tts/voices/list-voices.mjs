import "dotenv/config";

const apiKey = process.env.KITTENML_API_KEY;
if (!apiKey) {
  throw new Error("Copy .env.example to .env and add KITTENML_API_KEY before running.");
}

const baseURL = (process.env.KITTENML_BASE_URL || "https://api.kittenml.com/v1").replace(/\/$/, "");
const publicVoices = new Map();
const saved = [];
let after = null;
let catalog;
let requestId = "unknown";
do {
  // The public voices come back on every page; limit and after page only
  // your saved voices.
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
  for (const voice of catalog.data) {
    if (voice.type === "custom") {
      saved.push(voice);
    } else {
      // Every other voice (type "public") is selected by its id string.
      publicVoices.set(voice.id, voice);
    }
  }
  after = catalog.has_more ? catalog.last_custom_id : null;
} while (after);

const languages = catalog.languages.map((row) => row.code);
console.log(`model: ${catalog.model}`);
console.log(`languages: ${languages.join(", ")}`);
// Public voices are the ones KittenML makes available to every organization.
// Send the id as the voice string, for example "voice": "frank_en".
console.log(`public voices: ${publicVoices.size} (send the id as the voice string)`);
for (const voice of publicVoices.values()) {
  console.log(`- ${voice.id} "${voice.name}" [${voice.language}]`);
}
// Saved voices are your organization's own. Send one as an object,
// "voice": {"id": "voice_..."}; its name is only a display label.
console.log(`saved voices: ${saved.length} (send as {"id": "voice_..."})`);
for (const voice of saved) {
  console.log(`- ${voice.id} "${voice.name}" [${voice.language}]`);
}
if (catalog.public_voices_unavailable) {
  console.log("note: the public voices could not be read this time; retry to see them.");
}
console.log(`request_id: ${requestId}`);
