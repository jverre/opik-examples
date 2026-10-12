/**
 * One-time setup: start the Ollama container and pull both models into its
 * named volume. Safe to re-run; models that are already present are skipped.
 */
import { execFileSync } from "node:child_process";
import { CHAT_MODEL, EMBED_MODEL, OLLAMA_URL } from "./config.js";

async function listModels(): Promise<string[]> {
  const res = await fetch(`${OLLAMA_URL}/api/tags`);
  if (!res.ok) throw new Error(`Ollama /api/tags returned ${res.status}`);
  const body = (await res.json()) as { models: { name: string }[] };
  return body.models.map((m) => m.name);
}

async function waitForOllama(): Promise<void> {
  for (let i = 0; i < 60; i++) {
    try {
      await listModels();
      return;
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
  }
  throw new Error(`Ollama did not become ready on ${OLLAMA_URL}`);
}

async function pull(model: string): Promise<void> {
  console.log(`Pulling ${model} (first run only)...`);
  const res = await fetch(`${OLLAMA_URL}/api/pull`, {
    method: "POST",
    body: JSON.stringify({ model, stream: false }),
  });
  const body = (await res.json()) as { error?: string };
  if (!res.ok || body.error) {
    throw new Error(`Failed to pull ${model}: ${body.error ?? res.status}`);
  }
  console.log(`Pulled ${model}.`);
}

export async function ensureOllama(): Promise<void> {
  execFileSync("docker", ["compose", "up", "-d"], { stdio: "ignore" });
  await waitForOllama();
  const present = await listModels();
  for (const model of [CHAT_MODEL, EMBED_MODEL]) {
    if (present.includes(model) || present.includes(`${model}:latest`)) continue;
    await pull(model);
  }
}

// Run directly (`npm run setup`), not when imported.
if (import.meta.url === `file://${process.argv[1]}`) {
  await ensureOllama();
  console.log(`Ollama is ready on ${OLLAMA_URL} with ${CHAT_MODEL} and ${EMBED_MODEL}.`);
}
