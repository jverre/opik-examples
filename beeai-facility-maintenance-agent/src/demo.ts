// Runs four scripted maintenance requests through the BeeAI triage agent.
// No input needed, just `npm run demo`. Each request becomes one trace in the
// Opik project "beeai-facility-maintenance-agent".
import { config } from "dotenv";
import { fileURLToPath } from "node:url";

config({ path: fileURLToPath(new URL("../.env", import.meta.url)), quiet: true });

for (const key of ["OPENAI_API_KEY", "OPIK_API_KEY"]) {
  if (!process.env[key]) {
    console.error(`Missing ${key}. Copy .env.example to .env and fill it in.`);
    process.exit(1);
  }
}
if (!process.env.OPIK_WORKSPACE && !process.env.OPIK_WORKSPACE_NAME) {
  console.error("Missing OPIK_WORKSPACE. Copy .env.example to .env and fill it in.");
  process.exit(1);
}

// Some dev machines route OpenAI traffic through a local proxy via this
// variable. The example must talk to the public API, so drop it if present.
delete process.env.OPENAI_BASE_URL;

// Import tracing before the agent so the OTel SDK is running when BeeAI loads,
// and import both only after the env vars above are in place.
const { shutdownTracing, PROJECT_NAME } = await import("./instrumentation.ts");
const { triageRequest } = await import("./agent.ts");

const REQUESTS = [
  // 1. Routine: one asset, one trade, clean three-tool path.
  "The sink in the second floor kitchenette is dripping from underneath. Not urgent, but it is making the cabinet wet.",
  // 2. Safety: should be filed as an emergency and sent to the Campus Safety Desk.
  "There is a strong smell of gas near the cafeteria stove and two people feel dizzy.",
  // 3. Vendor-owned asset: the technician is an outside company, not an employee.
  "The main elevator in Building 1 has been stuck between floors for ten minutes with a visitor inside.",
  // 4. No match in the asset register: watch how the agent copes with found=false.
  "The thermostat in the east wing conference room is stuck at 31 degrees and nobody can sit in there.",
];

for (const [i, request] of REQUESTS.entries()) {
  console.log(`\n=== Request ${i + 1} ===`);
  console.log(`Requester: ${request}`);
  console.log(`Triage:\n${await triageRequest(request)}`);
}

// Flush the OTel exporter so the last spans reach Opik before the process exits.
await shutdownTracing();
console.log(`\nDone. Open the "${PROJECT_NAME}" project in Opik to see the traces.`);
