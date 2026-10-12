// Plays five scripted guest requests through the Maison Lanterne reservation
// agent. No input needed: `npm run demo`. Every request becomes one trace in
// the Opik project "voltagent-restaurant-reservations".
//
// The first request is sent twice: once with the gen_ai.* attribute mapper
// switched OFF and once with it ON, so the two traces can be compared side by
// side in Opik.
import { config } from "dotenv";
import { fileURLToPath } from "node:url";

config({ path: fileURLToPath(new URL("../.env", import.meta.url)), quiet: true });

// Don't inherit a local LLM proxy from the build machine: talk to OpenAI directly.
delete process.env.OPENAI_BASE_URL;

// VoltAgent puts the system prompt inside the messages array, which makes the
// AI SDK print a security warning on every call. That layout is VoltAgent's and
// the option that acknowledges it is not exposed, so filter that one warning.
const realWarn = console.warn.bind(console);
console.warn = (...args: unknown[]) => {
  if (typeof args[0] === "string" && args[0].includes("System messages in the prompt")) return;
  realWarn(...args);
};

for (const key of ["OPENAI_API_KEY", "OPIK_API_KEY"]) {
  if (!process.env[key]) {
    console.error(`Missing ${key}. Copy .env.example to .env and fill it in.`);
    process.exit(1);
  }
}
if (!process.env.OPIK_WORKSPACE_NAME && !process.env.OPIK_WORKSPACE) {
  console.error("Missing OPIK_WORKSPACE_NAME. Copy .env.example to .env and fill it in.");
  process.exit(1);
}

// Import the agent only after the env vars are loaded: the exporter reads
// them when the observability module initializes.
const { VoltAgent } = await import("@voltagent/core");
const { observability, mapping, PROJECT_NAME } = await import("./observability.ts");
const { reservationAgent } = await import("./agent.ts");

// Registering the agent hands it the Opik-wired observability. No `server`
// option means no HTTP server, so this stays a plain script.
new VoltAgent({ agents: { reservationAgent }, observability });

const FRIDAY_FOUR = "Hi! Do you have a table for 4 this Friday around 7:30pm?";

const REQUESTS: { label: string; mapped: boolean; text: string }[] = [
  // 1 and 2: identical request. Same agent, same tool call, different traces.
  { label: "availability, mapper OFF", mapped: false, text: FRIDAY_FOUR },
  { label: "availability, mapper ON", mapped: true, text: FRIDAY_FOUR },
  // 3: chains check_availability -> book_table.
  {
    label: "book a table",
    mapped: true,
    text: "Can you book Saturday at 8:30pm for two, under the name Ines Moreau?",
  },
  // 4: cancel_booking with a booking id and the matching name.
  {
    label: "cancel a booking",
    mapped: true,
    text: "Please cancel my reservation ML-1050. It's under Hugo Bernard.",
  },
  // 5: a request the book cannot satisfy: the tool result is the reason.
  {
    label: "party too large",
    mapped: true,
    text: "Can I get a table for 9 on Saturday at 8pm?",
  },
];

for (const [i, request] of REQUESTS.entries()) {
  mapping.enabled = request.mapped;
  console.log(`\n=== Request ${i + 1}: ${request.label} ===`);
  console.log(`Guest:     ${request.text}`);
  const result = await reservationAgent.generateText(request.text);
  console.log(`Assistant: ${result.text}`);
}

// Flush the OTel exporter so the last spans reach Opik before the process exits.
await observability.shutdown();
console.log(`\nDone. Open the "${PROJECT_NAME}" project in Opik to see the traces.`);
process.exit(0);
