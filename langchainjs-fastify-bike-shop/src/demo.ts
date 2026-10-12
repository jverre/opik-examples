/**
 * Autonomous demo: start the Fastify server, play scripted visitor sessions
 * against POST /chat over HTTP, flush the traces to Opik, stop the server.
 */
import { buildServer, flushOpik, PROJECT_NAME } from "./server.js";

const PORT = Number(process.env.PORT ?? 4201);

// Each key is a sessionId, so each becomes one thread in Opik.
const CONVERSATIONS: Record<string, string[]> = {
  "visitor-flat-and-tuneup": [
    "Hi! My rear tire went flat on the way to work. How much to fix it?",
    "Could you also do a basic tune-up while it's there? What would the total be?",
    "Great. I'll drop it off Sunday morning, is that okay?",
  ],
  "visitor-ebike-brakes": [
    "My e-bike's brakes feel spongy. Do you work on those?",
    "It's hydraulic. And the motor cuts out sometimes too, can you fix that?",
    "OK, so what would you charge to look at the motor and bleed the brakes?",
  ],
  // A visitor on a brand-new tab: a fresh sessionId, so the bot has no memory.
  "visitor-new-tab": ["So the total is still $83 like you told me earlier, right?"],
};

async function chat(sessionId: string, message: string): Promise<string> {
  const response = await fetch(`http://127.0.0.1:${PORT}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sessionId, message }),
  });
  if (!response.ok) {
    throw new Error(`POST /chat failed: ${response.status} ${await response.text()}`);
  }
  const { reply } = (await response.json()) as { reply: string };
  return reply;
}

async function main() {
  const app = buildServer();
  await app.listen({ port: PORT, host: "127.0.0.1" });
  console.log(`Demo server up on http://127.0.0.1:${PORT}`);

  try {
    for (const [sessionId, turns] of Object.entries(CONVERSATIONS)) {
      console.log(`\n=== Session: ${sessionId} ===`);
      for (const message of turns) {
        console.log(`\nVisitor: ${message}`);
        console.log(`Bot:     ${await chat(sessionId, message)}`);
      }
    }
    await flushOpik();
  } finally {
    await app.close();
  }

  console.log(
    `\nDone. Open the "${PROJECT_NAME}" project in Opik: three threads, seven traces.`,
  );
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
