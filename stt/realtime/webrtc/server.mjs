import "dotenv/config";
import path from "node:path";
import { fileURLToPath } from "node:url";
import express from "express";
import OpenAI from "openai";

const apiKey = process.env.KITTENML_API_KEY;
if (!apiKey) throw new Error("Copy .env.example to .env and add your API key before running.");

const MODEL = process.env.KITTENML_MODEL || "kitten-asr-pro-enhanced";
const apiBase = process.env.KITTENML_BASE_URL || "https://api.kittenml.com/v1";
const app = express();
const here = path.dirname(fileURLToPath(import.meta.url));
const client = new OpenAI({
  apiKey,
  baseURL: apiBase,
});

function upstreamErrorDetails(error) {
  // Preserve the upstream status, code, and request ID instead of hiding useful diagnostics.
  const upstream = error?.error && typeof error.error === "object" ? error.error : {};
  const upstreamStatus = Number(error?.status);
  const status = Number.isInteger(upstreamStatus) && upstreamStatus >= 400 && upstreamStatus <= 599
    ? upstreamStatus
    : 502;
  const requestId = error?.requestID || error?.request_id ||
    error?.headers?.get?.("x-request-id") || "unknown";
  const code = upstream.code || error?.code || "realtime_token_error";
  const type = upstream.type || error?.type || "api_error";
  const message = upstream.message ||
    (status < 500 ? error?.message : null) ||
    "Could not create a temporary realtime token.";
  return { status, requestId, code, type, message };
}

app.post("/api/realtime-token", async (_request, response) => {
  try {
    // Mint a five-minute browser credential; never expose the permanent API key.
    const token = await client.realtime.clientSecrets.create({
      expires_after: { anchor: "created_at", seconds: 300 },
      session: {
        type: "transcription",
        model: MODEL,
        audio: { input: {
          format: { type: "audio/pcm", rate: 24_000 },
          transcription: { model: MODEL },
          turn_detection: null,
        }},
      },
    });
    response.json(token);
  } catch (error) {
    const details = upstreamErrorDetails(error);
    console.error(
      `Could not create browser token: status=${details.status} ` +
      `code=${details.code} request_id=${details.requestId}`,
    );
    if (details.requestId !== "unknown") {
      // Mirror the correlation ID in both the header and structured error body.
      response.set("x-request-id", details.requestId);
    }
    response.status(details.status).json({
      error: {
        type: details.type,
        code: details.code,
        message: details.message,
        param: null,
      },
      request_id: details.requestId,
    });
  }
});

app.get("/api/config", (_request, response) => response.json({ apiBase }));

// Serve the browser client only after the protected token route is registered.
app.use(express.static(path.join(here, "public")));
const port = Number(process.env.PORT || 3000);
app.listen(port, "127.0.0.1", () => console.log(`Open http://localhost:${port}`));
