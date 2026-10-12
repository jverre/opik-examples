import { randomBytes } from "node:crypto";
import { createInterface } from "node:readline/promises";
import { Opik } from "opik";
import { Concierge, MODEL } from "./concierge.js";

// The Opik project is the folder name, set explicitly so traces never land elsewhere.
const PROJECT = "openai-ts-hotel-concierge";
const client = new Opik({ projectName: PROJECT });

const CONVERSATIONS: Record<string, string[]> = {
  "dune-cottage-booking": [
    "Hi! We're two adults and a dog looking for a room for the weekend of 17 July. What do you have?",
    "The Dune Cottage sounds right. What does the dog cost, and what are check-in and check-out times?",
    "Perfect. Can we get a table for 2 at the Pilot House on Friday 2026-07-17 around 19:00?",
  ],
  "late-arrival-and-extras": [
    "We land late on Saturday. Is breakfast included in the Harbor View Double, and when does it end?",
    "Is there parking? And can you arrange pet-sitting for a parrot during our stay?",
    "OK. Last one: how do we get to Cormorant Island?",
  ],
};

async function runDemo(): Promise<void> {
  const lastTrace: Record<string, string> = {};
  const turnsByTrace = new Map<string, string>();

  for (const [threadId, turns] of Object.entries(CONVERSATIONS)) {
    console.log(`\n=== Conversation: ${threadId} ===`);
    const concierge = new Concierge(client, threadId);
    for (const [i, guestMessage] of turns.entries()) {
      console.log(`\nGuest: ${guestMessage}`);
      console.log(`Concierge: ${await concierge.ask(guestMessage)}`);
      turnsByTrace.set(concierge.traceIds[i]!, `${threadId} turn ${i + 1}`);
    }
    lastTrace[threadId] = concierge.traceIds.at(-1)!;
  }

  // Guest feedback arrives after the conversation. Make sure the traces exist first.
  await client.flush();
  client.logTracesFeedbackScores([
    {
      id: lastTrace["dune-cottage-booking"]!,
      name: "guest-satisfaction",
      value: 1.0,
      reason: "Guest clicked thumbs-up after the table was confirmed.",
    },
    {
      id: lastTrace["late-arrival-and-extras"]!,
      name: "guest-satisfaction",
      value: 0.0,
      reason: "Guest wanted pet-sitting arranged and got a handoff to the front desk.",
    },
  ]);
  await client.flush();
  console.log("\nLogged guest-satisfaction: 1.0 (dune-cottage-booking), 0.0 (late-arrival-and-extras)");

  await printCostPerTurn(turnsByTrace);
}

/** Read the spans back and show what each turn cost. Cost is computed server-side, so poll briefly. */
async function printCostPerTurn(turnsByTrace: Map<string, string>): Promise<void> {
  type Row = { llmCalls: number; tokens: number; cost: number; priced: number };
  let rows = new Map<string, Row>();
  for (let attempt = 0; attempt < 10; attempt++) {
    // opik-openai logs its spans with type "general" (model, usage and cost are still attached), so filter by name.
    const spans = await client.searchSpans({ projectName: PROJECT, filterString: 'name = "concierge-llm"', maxResults: 200 });
    rows = new Map();
    for (const s of spans) {
      const label = s.traceId ? turnsByTrace.get(s.traceId) : undefined;
      if (!label) continue;
      const row = rows.get(label) ?? { llmCalls: 0, tokens: 0, cost: 0, priced: 0 };
      row.llmCalls += 1;
      row.tokens += s.usage?.["total_tokens"] ?? 0;
      if (s.totalEstimatedCost != null) {
        row.cost += s.totalEstimatedCost;
        row.priced += 1;
      }
      rows.set(label, row);
    }
    const complete = rows.size === turnsByTrace.size && [...rows.values()].every((r) => r.priced === r.llmCalls);
    if (complete) break;
    await new Promise((r) => setTimeout(r, 3000));
  }

  console.log(`\nCost per turn (${MODEL}, read back from Opik):`);
  let total = 0;
  for (const label of [...turnsByTrace.values()]) {
    const r = rows.get(label);
    if (!r) continue;
    total += r.cost;
    console.log(`  ${label.padEnd(34)} ${r.llmCalls} llm call(s)  ${String(r.tokens).padStart(5)} tokens  $${r.cost.toFixed(6)}`);
  }
  console.log(`  ${"total".padEnd(34)} $${total.toFixed(6)}`);
}

async function runInteractive(): Promise<void> {
  const concierge = new Concierge(client, `interactive-${randomBytes(4).toString("hex")}`);
  const rl = createInterface({ input: process.stdin, output: process.stdout });
  console.log(`Driftwood Pier concierge (thread ${concierge.threadId}). Ctrl+C or empty line to quit.`);
  for (;;) {
    const line = (await rl.question("\nYou: ")).trim();
    if (!line) break;
    console.log(`Concierge: ${await concierge.ask(line)}`);
  }
  rl.close();
}

try {
  if (process.argv.includes("--interactive")) await runInteractive();
  else await runDemo();
} finally {
  await client.flush();
}
