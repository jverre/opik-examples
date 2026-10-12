// Plays four scripted patron requests through the loans agent. Each one becomes
// one Opik trace: invoke_agent -> agent_step -> chat gpt-4o-mini + execute_tool.
import { config } from "dotenv";
import { fileURLToPath } from "node:url";

config({ path: fileURLToPath(new URL("../.env", import.meta.url)), quiet: true });

for (const key of ["OPENAI_API_KEY", "OPIK_API_KEY", "OPIK_WORKSPACE"]) {
  if (!process.env[key]) {
    console.error(`Missing ${key}. Copy .env.example to .env and fill it in.`);
    process.exit(1);
  }
}

// Import Mastra only after the env vars are loaded: the exporter reads them at import time.
const { mastra, PROJECT_NAME } = await import("./mastra.ts");

const REQUESTS = [
  // 1. Plain search: one search_catalog call.
  "Hi, I'm member M-2041. Do you have anything by Odile Brandt on gardening, and is a copy on the shelf?",
  // 2. Renewal that succeeds: one renew_loan call.
  "Member M-2041 here. Please renew my loan L-8801, the lighthouse book.",
  // 3. Renewal refused (hold queue), the agent recovers: renew_loan -> search_catalog -> place_hold.
  "Member M-2041 again. Please renew loan L-8802, The Salt Road. If you can't, I'd like to go on the waiting list for the follow-up, Night Ferry to Karsk.",
  // 4. Overdue loan: renew_loan refuses and the agent has to say no without inventing a workaround.
  "I'm M-3377. Can you renew loan L-9120? I'm a few days late, sorry.",
];

const agent = mastra.getAgent("loansAgent");

for (const [i, request] of REQUESTS.entries()) {
  console.log(`\n=== Request ${i + 1} ===`);
  console.log(`Patron: ${request}`);
  const result = await agent.generate(request, { maxSteps: 6, modelSettings: { temperature: 0 } });
  const tools = result.steps.flatMap((s: any) => (s.toolCalls ?? []).map((c: any) => c.payload?.toolName ?? c.toolName));
  console.log(`Agent:  ${result.text}`);
  console.log(`(tools called: ${tools.join(" -> ") || "none"})`);
}

// Flush the OTel exporter so the last spans reach Opik before the process exits.
await mastra.shutdown();
console.log(`\nDone. Open the "${PROJECT_NAME}" project in Opik to see the traces.`);
