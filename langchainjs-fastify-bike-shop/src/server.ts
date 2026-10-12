/**
 * Spoke & Sprocket website chat: a Fastify backend traced with Opik.
 *
 * Every POST /chat call runs one LangChain.js chain invocation. The chain is
 * string in, string out, so the root trace in Opik holds the visitor's
 * sentence and the bot's sentence. The widget's sessionId becomes the Opik
 * threadId, so a visitor's turns read as one conversation in the Threads tab.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import dotenv from "dotenv";
import Fastify from "fastify";
import fastifyStatic from "@fastify/static";
import { ChatOpenAI } from "@langchain/openai";
import {
  ChatPromptTemplate,
  MessagesPlaceholder,
} from "@langchain/core/prompts";
import { StringOutputParser } from "@langchain/core/output_parsers";
import { RunnableLambda, RunnableSequence } from "@langchain/core/runnables";
import type { RunnableConfig } from "@langchain/core/runnables";
import { AIMessage, HumanMessage } from "@langchain/core/messages";
import type { BaseMessage } from "@langchain/core/messages";
import { Opik } from "opik";
import { OpikCallbackHandler } from "opik-langchain";

const here = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(here, "../.env"), quiet: true });

export const PROJECT_NAME = "langchainjs-fastify-bike-shop";

const SHOP_FACTS = readFileSync(path.join(here, "../data/shop.md"), "utf8");

const SYSTEM_PROMPT = `You are the website chat assistant for Spoke & Sprocket
Cycle Works, a bike repair shop. Be friendly, concise and concrete: this is a
small chat widget, so answer in two or three sentences. Use only the shop
facts below. If something is not covered, say you are not sure and suggest
the visitor drops by or asks the workshop team. Do the arithmetic when asked
for a total, and say that parts are extra.

SHOP FACTS
${SHOP_FACTS}`;

// One shared Opik client so every session batches through one connection.
const opikClient = new Opik({ projectName: PROJECT_NAME });

interface Session {
  history: BaseMessage[];
  opikHandler: OpikCallbackHandler;
}
const sessions = new Map<string, Session>();

function getSession(sessionId: string): Session {
  let session = sessions.get(sessionId);
  if (!session) {
    session = {
      history: [],
      // threadId is the whole threads story: same id, same Opik thread.
      opikHandler: new OpikCallbackHandler({
        client: opikClient,
        threadId: sessionId,
      }),
    };
    sessions.set(sessionId, session);
  }
  return session;
}

// The first step takes the visitor's plain string and attaches this session's
// history (the sessionId travels in the invoke config). Everything after is
// prompt -> model -> parser, and the chain's final output is a plain string.
const loadSessionHistory = RunnableLambda.from(
  (message: string, config?: RunnableConfig) => {
    const sessionId = (config?.configurable as { sessionId?: string })
      ?.sessionId;
    const session = sessionId ? sessions.get(sessionId) : undefined;
    if (!session) throw new Error(`Unknown session: ${sessionId}`);
    return { history: session.history, message };
  },
).withConfig({ runName: "load-session-history" });

const prompt = ChatPromptTemplate.fromMessages([
  ["system", SYSTEM_PROMPT],
  new MessagesPlaceholder("history"),
  ["human", "{message}"],
]);
const llm = new ChatOpenAI({ model: "gpt-4o-mini", temperature: 0 });
const chain = RunnableSequence.from([
  loadSessionHistory,
  prompt,
  llm,
  new StringOutputParser(),
]);

interface ChatBody {
  message: string;
  sessionId: string;
}

export function buildServer() {
  const app = Fastify({ logger: false });

  app.register(fastifyStatic, { root: path.join(here, "../public") });

  app.get("/health", async () => ({ ok: true, project: PROJECT_NAME }));

  app.post<{ Body: ChatBody }>(
    "/chat",
    {
      // Fastify validates the body for us and answers 400 before the handler runs.
      schema: {
        body: {
          type: "object",
          required: ["message", "sessionId"],
          properties: {
            message: { type: "string", minLength: 1 },
            sessionId: { type: "string", minLength: 1 },
          },
        },
      },
    },
    async (request, reply) => {
      const { message, sessionId } = request.body;
      try {
        const session = getSession(sessionId);
        const answer = await chain.invoke(message, {
          callbacks: [session.opikHandler],
          runName: "shop-chat-turn",
          configurable: { sessionId },
        });
        session.history.push(new HumanMessage(message), new AIMessage(answer));
        return { reply: answer, sessionId };
      } catch (error) {
        console.error("Chat turn failed:", error);
        return reply
          .code(500)
          .send({ error: "The assistant could not answer. Try again." });
      }
    },
  );

  return app;
}

/** Send any buffered traces to Opik. Called on shutdown and by the demo. */
export async function flushOpik(): Promise<void> {
  await opikClient.flush();
}

// Run the server directly with `npm run dev`.
const isMain =
  process.argv[1] &&
  path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);

if (isMain) {
  const port = Number(process.env.PORT ?? 4200);
  const app = buildServer();
  await app.listen({ port, host: "127.0.0.1" });
  console.log(`Spoke & Sprocket chat: http://localhost:${port}`);
  console.log(`Traces land in the "${PROJECT_NAME}" Opik project.`);
  for (const signal of ["SIGINT", "SIGTERM"] as const) {
    process.on(signal, async () => {
      await app.close();
      await flushOpik(); // don't lose the last turns on Ctrl+C
      process.exit(0);
    });
  }
}
