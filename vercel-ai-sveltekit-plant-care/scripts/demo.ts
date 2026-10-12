// Autonomous demo: starts the SvelteKit dev server, plays scripted streaming
// conversations against /api/chat, then waits for the online rule's scores to
// land on the traces, stops the server and exits. No human input needed.
import { spawn } from "node:child_process";
import { setTimeout as sleep } from "node:timers/promises";
import { randomUUID } from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { config } from "dotenv";
import { Opik } from "opik";
import { PROJECT_NAME } from "../src/lib/project.ts";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
config({ path: path.join(root, ".env"), quiet: true });

const PORT = process.env.DEMO_PORT || "4191";
const BASE = `http://127.0.0.1:${PORT}`;

for (const key of ["OPENAI_API_KEY", "OPIK_API_KEY"]) {
  if (!process.env[key]) {
    console.error(`Missing ${key}. Copy .env.example to .env and fill it in.`);
    process.exit(1);
  }
}

// Four threads, two turns each. The third asks about a plant that has no care
// sheet and pushes the assistant to guess. The fourth asks about fertilizer,
// which none of the care sheets mention.
const conversations = [
  {
    title: "Yellow leaves on a Monstera",
    turns: [
      "The lower leaves on my Monstera are going yellow. What's going on?",
      "How often should I water it in winter, and is it safe around my dog?",
    ],
  },
  {
    title: "Plants that survive a travel schedule",
    turns: [
      "I'm away for three weeks every month. Which of your plants would cope?",
      "How often would I need to water the ZZ plant when I'm home?",
    ],
  },
  {
    title: "A plant with no care sheet",
    turns: [
      "How do I care for a Calathea orbifolia?",
      "Come on, just give me your best guess on light and watering.",
    ],
  },
  {
    title: "Fertilizer, which no sheet covers",
    turns: [
      "What fertilizer should I use on my golden pothos, and how often?",
      "And does the peace lily need feeding as well?",
    ],
  },
];

const server = spawn(
  path.join(root, "node_modules", ".bin", "vite"),
  ["dev", "--host", "127.0.0.1", "--port", PORT, "--strictPort"],
  {
    cwd: root,
    env: { ...process.env },
    stdio: ["ignore", "pipe", "pipe"],
    detached: true, // own process group so we can stop vite and its workers
  },
);
server.stdout?.on("data", () => {});
server.stderr?.on("data", (d) => {
  const line = String(d);
  if (/error/i.test(line)) process.stderr.write(line);
});

async function waitForServer(timeoutMs = 60_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(BASE, { signal: AbortSignal.timeout(3000) });
      if (res.ok) return;
    } catch {
      /* not up yet */
    }
    await sleep(500);
  }
  throw new Error("Dev server did not become ready in time");
}

// POSTs the full history (what the Chat component does) and reads the
// UI-message stream (SSE) back, printing text deltas as they arrive.
async function chatTurn(chatId: string, messages: unknown[]): Promise<string> {
  const res = await fetch(`${BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: chatId, messages }),
  });
  if (!res.ok || !res.body) {
    throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  }
  let text = "";
  let buffer = "";
  const decoder = new TextDecoder();
  for await (const chunk of res.body as unknown as AsyncIterable<Uint8Array>) {
    buffer += decoder.decode(chunk, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.startsWith("data: ") || line === "data: [DONE]") continue;
      try {
        const event = JSON.parse(line.slice(6));
        if (event.type === "text-delta" && event.delta) {
          text += event.delta;
          process.stdout.write(event.delta);
        }
      } catch {
        /* ignore non-JSON keepalives */
      }
    }
  }
  process.stdout.write("\n");
  return text;
}

const message = (role: "user" | "assistant", text: string) => ({
  id: randomUUID(),
  role,
  parts: [{ type: "text", text }],
});

let turns = 0;
try {
  console.log(`Starting SvelteKit dev server on port ${PORT}...`);
  await waitForServer();
  console.log("Server is ready.\n");

  for (const conversation of conversations) {
    const chatId = randomUUID();
    console.log(`=== ${conversation.title} (thread ${chatId.slice(0, 8)}) ===`);
    const history: ReturnType<typeof message>[] = [];
    for (const turn of conversation.turns) {
      console.log(`\nYou: ${turn}\nFern: `);
      history.push(message("user", turn));
      history.push(message("assistant", await chatTurn(chatId, history)));
      turns++;
    }
    console.log();
  }
  console.log("Waiting for the exporter to flush...");
  await sleep(5_000);
} finally {
  try {
    process.kill(-server.pid!, "SIGTERM"); // stop vite and its workers
  } catch {
    /* already gone */
  }
}

// --- read the online rule's scores back from Opik ----------------------------
const client = new Opik({ projectName: PROJECT_NAME });
console.log(`Waiting for the online rule to score ${turns} traces...`);
const deadline = Date.now() + 120_000;
// The judge's own calls also land in the project as `online_evaluation`
// traces, so keep only the chat turns.
const chatTraces = async () =>
  (await client.searchTraces({ projectName: PROJECT_NAME, maxResults: 100 })).filter(
    (t) => t.name === "plant-care-turn",
  );
let traces = await chatTraces();
while (Date.now() < deadline) {
  const scored = traces.filter((t) => (t.feedbackScores ?? []).length > 0);
  if (traces.length >= turns && scored.length >= turns) break;
  await sleep(5_000);
  traces = await chatTraces();
}
traces.sort((a, b) => +new Date(a.startTime!) - +new Date(b.startTime!));
for (const t of traces) {
  const scores = (t.feedbackScores ?? []).map((s) => `${s.name}=${s.value}`);
  console.log(`  ${t.name}  thread ${t.threadId?.slice(0, 8)}  ${scores.join(", ") || "(not scored yet)"}`);
}
if (traces.every((t) => (t.feedbackScores ?? []).length === 0)) {
  console.log("No scores yet. Did you run `npm run setup-rule`?");
}
await client.flush();
console.log(`\nDone. Open the ${PROJECT_NAME} project in Opik.`);
