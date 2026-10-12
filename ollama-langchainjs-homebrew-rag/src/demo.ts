/**
 * Three questions about the Foxglove Hollow Brew Club handbook, answered
 * entirely on this machine and traced to Opik with opik-langchain.
 */
import { PROJECT_NAME } from "./config.js"; // must come first: sets the Opik project
import { Opik } from "opik";
import { OpikCallbackHandler } from "opik-langchain";
import { ensureOllama } from "./setup.js";
import { buildChain } from "./rag.js";

const QUESTIONS = [
  "What temperature should I mash the Hollow Amber at, and for how long?",
  "How much sugar do I need to prime a whole 20-litre batch?",
  "What do I have to do before I can pitch the yeast, and how warm can the wort be?",
];

await ensureOllama();
const chain = await buildChain();

const client = new Opik({ projectName: PROJECT_NAME });
// opik-langchain 2.2.96 types `tags` as the empty tuple `[]`, so a real tag
// list needs a cast to compile. It works fine at runtime.
const tags = ["ollama", "rag"] as unknown as [];
const handler = new OpikCallbackHandler({ client, tags });

for (const question of QUESTIONS) {
  // One invoke is one trace. The handler is passed per call, as a callback.
  const answer = await chain.invoke(question, { callbacks: [handler] });
  console.log(`Q: ${question}\nA: ${answer}\n`);
}

await handler.flushAsync();
await client.flush();
console.log(`Done. Open the "${PROJECT_NAME}" project in Opik: three traces, no cloud LLM calls.`);
