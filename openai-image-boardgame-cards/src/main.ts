// openai-image-boardgame-cards: a board-game card art generator traced with Opik.
//
// One run does four things:
//   1. Registers the art brief in the Opik prompt library (two versions: v1 plain,
//      v2 with art direction) and prints the diff between them.
//   2. Generates art for two cards with each version using the OpenAI Images API.
//      Each image is one Opik trace, and the PNG is attached to the trace.
//   3. Runs a cheap vision check (gpt-4o-mini) on every image in a guardrail span and
//      logs an `art-only` feedback score: 1 if no stray text and no drawn card frame.
//   4. Saves the PNGs to ./out and prints a table, then flushes to Opik.

import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import OpenAI from "openai";
import { Opik, PromptType, type Prompt } from "opik";
import { trackOpenAI } from "opik-openai";
import {
  BRIEF_V1,
  BRIEF_V2,
  CARDS,
  GAME,
  PROMPT_NAME,
  V2_CHANGE_DESCRIPTION,
} from "./prompts.js";

// Local proxies sometimes override the OpenAI base URL; this example talks to the public API.
delete process.env.OPENAI_BASE_URL;

// Load .env without a dependency. Existing environment variables win.
try {
  process.loadEnvFile(path.resolve(".env"));
} catch {
  // no .env file: keys come from the environment
}

if (!process.env.OPENAI_API_KEY) {
  console.error("OPENAI_API_KEY is not set. Copy .env.example to .env or export it, then re-run.");
  process.exit(1);
}

const PROJECT = process.env.OPIK_PROJECT_NAME ?? "openai-image-boardgame-cards";
const OUT_DIR = "out";
const CHECKER_MODEL = "gpt-4o-mini";

const opik = new Opik({ projectName: PROJECT });
const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

// ---------------------------------------------------------------------------
// 1. The prompt library
// ---------------------------------------------------------------------------

// createPrompt compares against the latest version, so registering v1 again after v2
// exists would create a spurious v3. Register only when the prompt is new.
async function registerBriefVersions(): Promise<{ v1: Prompt; v2: Prompt }> {
  const existing = await opik.getPrompt({ name: PROMPT_NAME });
  if (!existing) {
    const common = { name: PROMPT_NAME, type: PromptType.MUSTACHE, tags: ["board-game", "image-generation"] };
    await opik.createPrompt({ ...common, prompt: BRIEF_V1, changeDescription: "Initial brief: card, subject, mood" });
    await opik.createPrompt({ ...common, prompt: BRIEF_V2, changeDescription: V2_CHANGE_DESCRIPTION });
    console.log(`Registered "${PROMPT_NAME}" in the prompt library (v1 + v2).`);
  } else {
    console.log(`"${PROMPT_NAME}" already in the library, reusing it.`);
  }

  const latest = await opik.getPrompt({ name: PROMPT_NAME });
  if (!latest) throw new Error(`Prompt "${PROMPT_NAME}" not found after registering it.`);

  // Versions come back newest first. getPrompt wants a version number like "v1", not a commit id.
  const versions = await latest.getVersions();
  if (versions.length < 2) throw new Error(`Expected 2 versions of "${PROMPT_NAME}", found ${versions.length}.`);
  const [newest, oldest] = [versions[0]!, versions[versions.length - 1]!];

  console.log("\nDiff between the two brief versions (newest vs oldest):");
  newest.compareTo(oldest);

  const v1 = await opik.getPrompt({ name: PROMPT_NAME, version: "v1" });
  const v2 = await opik.getPrompt({ name: PROMPT_NAME, version: `v${versions.length}` });
  if (!v1 || !v2) throw new Error("Could not load both brief versions by commit.");
  return { v1, v2 };
}

// ---------------------------------------------------------------------------
// 2. Generate one card, check it
// ---------------------------------------------------------------------------

type Card = (typeof CARDS)[number];
type Verdict = { has_text: boolean; has_card_frame: boolean; note: string };

async function checkArt(
  tracedOpenAI: OpenAI,
  parent: ReturnType<Opik["trace"]>,
  b64: string,
): Promise<Verdict> {
  const guard = parent.span({
    name: "art-only-check",
    type: "guardrail",
    input: { rule: "no text, no drawn card frame", model: CHECKER_MODEL },
  });
  const checker = trackOpenAI(tracedOpenAI, { client: opik, parent: guard, generationName: "vision-check" });
  const res = await checker.chat.completions.create({
    model: CHECKER_MODEL,
    temperature: 0,
    response_format: { type: "json_object" },
    messages: [
      {
        role: "system",
        content:
          'You inspect trading-card artwork. Reply with JSON only: {"has_text": boolean, "has_card_frame": boolean, "note": string}. ' +
          "has_text is true if ANY letters, numbers or lettering-like glyphs appear. has_card_frame is true if the image draws its own card border, banner or title bar. note is one short sentence.",
      },
      {
        role: "user",
        content: [
          { type: "text", text: "Inspect this artwork." },
          { type: "image_url", image_url: { url: `data:image/png;base64,${b64}`, detail: "low" } },
        ],
      },
    ],
  });
  const verdict = JSON.parse(res.choices[0]?.message?.content ?? "{}") as Verdict;
  guard.update({ output: verdict });
  guard.end();
  return verdict;
}

async function generateCard(prompt: Prompt, card: Card) {
  const version = prompt.version ?? "unknown";
  const imagePrompt = prompt.format({ game: GAME, ...card });

  const trace = opik.trace({
    name: "generate-card-art",
    input: { card: card.card_name, card_type: card.card_type, image_prompt: imagePrompt },
    tags: [version, card.id],
    metadata: { prompt_name: PROMPT_NAME, prompt_version: version, prompt_id: prompt.id, card: card.card_name },
  });

  const tracked = trackOpenAI(openai, { client: opik, parent: trace, generationName: "images.generate" });
  const result = await tracked.images.generate({
    model: "gpt-image-1-mini",
    prompt: imagePrompt,
    n: 1,
    size: "1024x1024",
    quality: "low",
  });
  const b64 = result.data?.[0]?.b64_json;
  if (!b64) throw new Error("gpt-image-1-mini returned no image data");

  fs.writeFileSync(path.join(OUT_DIR, `${version}-${card.id}.png`), Buffer.from(b64, "base64"));

  // The image goes on the trace as a base64 data URI. The Opik SDK spots it in the output and
  // uploads it as a real attachment, so Opik shows the picture instead of a wall of base64.
  trace.update({
    output: { image: `data:image/png;base64,${b64}`, model: "gpt-image-1-mini", size: "1024x1024" },
  });

  const verdict = await checkArt(openai, trace, b64);
  const clean = !verdict.has_text && !verdict.has_card_frame;
  trace.score({
    name: "art-only",
    value: clean ? 1 : 0,
    reason: `has_text=${verdict.has_text}, has_card_frame=${verdict.has_card_frame}. ${verdict.note}`,
  });
  trace.end();
  return { version, card: card.card_name, verdict, clean };
}

// ---------------------------------------------------------------------------
// 3. The run
// ---------------------------------------------------------------------------

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const { v1, v2 } = await registerBriefVersions();

  const rows: Awaited<ReturnType<typeof generateCard>>[] = [];
  for (const prompt of [v1, v2]) {
    console.log(`\nGenerating with brief ${prompt.version}:`);
    for (const card of CARDS) {
      const row = await generateCard(prompt, card);
      rows.push(row);
      console.log(
        `  ${row.card.padEnd(10)} text=${row.verdict.has_text} frame=${row.verdict.has_card_frame} art-only=${row.clean ? 1 : 0}  ${row.verdict.note}`,
      );
    }
  }

  await opik.flush();
  console.log(
    `\nDone. Open the "${PROJECT}" project in Opik: ${rows.length} traces with the PNG attached, and "${PROMPT_NAME}" in the prompt library. Images are in ./${OUT_DIR}.`,
  );
}

main().catch(async (error) => {
  console.error("Run failed:", error);
  await opik.flush();
  process.exit(1);
});
