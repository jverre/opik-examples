import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { MemoryVectorStore } from "@langchain/classic/vectorstores/memory";
import type { Document } from "@langchain/core/documents";
import { StringOutputParser } from "@langchain/core/output_parsers";
import { ChatPromptTemplate } from "@langchain/core/prompts";
import { RunnableLambda, RunnablePassthrough, RunnableSequence } from "@langchain/core/runnables";
import { ChatOllama, OllamaEmbeddings } from "@langchain/ollama";
import { CHAT_MODEL, EMBED_MODEL, OLLAMA_URL } from "./config.js";

const DOCS_DIR = fileURLToPath(new URL("../docs/", import.meta.url));

/** One chunk per "##" section: each chunk is about one rule, and stays small. */
function loadChunks(): string[] {
  const chunks: string[] = [];
  for (const file of readdirSync(DOCS_DIR).filter((f) => f.endsWith(".md")).sort()) {
    const [title, ...sections] = readFileSync(join(DOCS_DIR, file), "utf8").split("\n## ");
    for (const section of sections) {
      chunks.push(`${title!.trim()}\n\n## ${section.trim()}`);
    }
  }
  return chunks;
}

export async function buildChain() {
  const embeddings = new OllamaEmbeddings({ model: EMBED_MODEL, baseUrl: OLLAMA_URL });
  const store = await MemoryVectorStore.fromTexts(loadChunks(), [], embeddings);
  const retriever = store.asRetriever({ k: 2 });

  // The retriever is named so its span reads "search_handbook" in Opik, and
  // the formatter is a named step so the chain stays easy to read in the tree.
  const searchHandbook = retriever
    .withConfig({ runName: "search_handbook" })
    .pipe(
      RunnableLambda.from((docs: Document[]) =>
        docs.map((d) => d.pageContent).join("\n\n---\n\n"),
      ).withConfig({ runName: "format_sections" }),
    );

  const llm = new ChatOllama({
    model: CHAT_MODEL,
    baseUrl: OLLAMA_URL,
    temperature: 0,
    numPredict: 200, // cap the answer; this is a CPU-bound demo
  });

  const prompt = ChatPromptTemplate.fromMessages([
    [
      "system",
      "You are the Foxglove Hollow Brew Club's handbook assistant. Answer the " +
        "question using only the handbook excerpts below. If the excerpts do " +
        "not cover it, say so. Answer in at most three sentences.\n\n{context}",
    ],
    ["human", "{question}"],
  ]);

  const chain = RunnableSequence.from<string, string>([
    { context: searchHandbook, question: new RunnablePassthrough<string>() },
    prompt,
    llm,
    new StringOutputParser(),
  ]);
  // The run name becomes the trace name in Opik.
  return chain.withConfig({ runName: "ask_the_handbook" });
}
