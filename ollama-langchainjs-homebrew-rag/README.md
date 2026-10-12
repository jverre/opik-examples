# ollama-langchainjs-homebrew-rag

*A homebrew-club RAG bot that runs entirely on your laptop, with every step visible in Opik.*

Some documents should never go to a model API, and some teams simply have no API budget. The fix is open-weight models running locally, but small local models get things wrong more often than frontier ones, so you need to see the pipeline more clearly, not less. This example answers questions about the fictional Foxglove Hollow Brew Club handbook with TypeScript, LangChain.js and Ollama running in Docker. No OpenAI or Anthropic key is involved, and the only data that leaves your machine is the trace sent to Opik.

## What you'll build

A question-answering chain over four short handbook sheets in `docs/` (mashing, fermentation, bottling, club rules). Each `##` section becomes one chunk. `nomic-embed-text` embeds the chunks into an in-memory vector store, and `llama3.2:1b` answers from the two best matches. Both models are served by one Ollama container that `docker-compose.yml` defines. The chain is plain LangChain.js (retriever, prompt, `ChatOllama`), and `opik-langchain`'s `OpikCallbackHandler` is passed as a callback, so each of the three demo questions becomes one Opik trace.

## See it in Opik

Open the `ollama-langchainjs-homebrew-rag` project on Opik Cloud. The Traces tab has three traces named `ask_the_handbook`, each tagged `ollama` and `rag`, each with 9 spans. Open one and you will see the chain tree: `RunnableSequence` and `RunnableMap` at the top, then a `search_handbook` span (type `tool`), a `format_sections` span, a `ChatPromptTemplate` span, a `ChatOllama` span (type `llm`) and a `StrOutputParser` span.

The span to read first is `search_handbook`. Its input is the question, and its output is the two sections the vector store fetched. For "What temperature should I mash the Hollow Amber at, and for how long?" it fetched "Mash temperature" and "Water volumes". The `ChatOllama` span then shows the assembled prompt and the answer: "the Hollow Amber should be mashed at 64 C for 60 minutes". The handbook says 67 C. The 64 C figure belongs to a different beer, the Pale Lantern, and sits in the same retrieved section. So retrieval did its job and the 1B model mixed up two numbers. The other two traces fail differently. For the priming question, "Priming sugar" was fetched, but the model garbled 120 g into "3 g in 250 ml". For the yeast question, "Pitching yeast" was fetched, but the answer never gives the wort temperature limit. In all three the fix is different (a bigger model, a clearer chunk, a stricter prompt), and the `search_handbook` span is what tells you which one you need.

The `ChatOllama` span shows `llama3.2:1b` as its model and `ollama` as its provider, where a hosted model's name would normally be. Its usage and cost columns are empty. That is expected: the LangChain.js Ollama path does not report token counts to Opik, so this example is about tracing, not cost. In the final run the model calls took 2 to 7 seconds each on a laptop CPU, and retrieval took under 0.1 seconds.

About the retriever: in the Python version of this idea, `OpikTracer` drops LangChain retriever runs, and the fix is to wrap retrieval in a named function span. In TypeScript with `opik-langchain` 2.2.96 that gap does not exist. A retriever placed directly in the chain is logged as a `tool` span without any workaround. The only thing this example does is rename it with `.withConfig({ runName: "search_handbook" })`, because the default name is the unhelpful `VectorStoreRetriever`.

## Run it yourself

You need Node 20+, Docker running, and about 1.6 GB of disk for the models. The first `setup` downloads them into a named Docker volume, and later runs skip the download. Ollama is mapped to host port 11535.

1. `npm install`. A `.npmrc` sets `legacy-peer-deps=true` because `opik-langchain@2.2.96` declares a peer range of `opik@^1.8.75`, which excludes `opik@2.x`.
2. `cp .env.example .env` and fill in `OPIK_API_KEY` and `OPIK_WORKSPACE`. There is no model-provider key to add. (Or export those variables in your shell.)
3. `npm run setup` starts the Ollama container and pulls `llama3.2:1b` and `nomic-embed-text`.
4. `npm run demo` answers the three questions and flushes the traces.
5. Open the `ollama-langchainjs-homebrew-rag` project in Opik and click the newest trace.
6. When you are done, `npm run stop` (same as `docker compose down`) stops the container. The models stay in the volume. Run `docker compose down -v` to delete them too.

## Poke around

- Add a question the handbook does not cover ("Can I brew a mead here?") to `QUESTIONS` in `src/demo.ts`. Check `search_handbook` to see what got fetched anyway, then see whether a 1B model obeys the "say so" instruction.
- Change the mash temperature in `docs/01-mashing.md` from 67 C to 65 C and re-run. The answer should follow your edit, and the trace shows it came from the retrieved section, not from model memory.
- Swap `CHAT_MODEL` in `src/config.ts` for `llama3.2:3b` (pull it with `docker exec ollama-langchainjs-homebrew-rag ollama pull llama3.2:3b`) and compare the two traces side by side. Same retrieval, different answers.
- Remove the `.withConfig({ runName: "search_handbook" })` call in `src/rag.ts` and see the retriever span fall back to `VectorStoreRetriever`.
- Point `OPIK_URL_OVERRIDE` at a self-hosted Opik to keep the traces on your machine too.

## How it's put together

- `src/demo.ts` - starts Ollama if needed, runs the three questions with the Opik callback, flushes.
- `src/rag.ts` - loads and chunks `docs/`, builds the vector store and the traced chain.
- `src/setup.ts` - starts the container and pulls the models (`npm run setup`).
- `src/config.ts` - project name, Ollama URL, model names; also drops provider keys from the process env.
- `docker-compose.yml` - the Ollama service with its own named volume.
- `docs/` - four fictional handbook sheets; the RAG corpus.
- `.env.example` - the Opik keys; deliberately no provider key.
- `.npmrc` - `legacy-peer-deps` for the stale `opik-langchain` peer range.

One typing quirk: `opik-langchain@2.2.96` declares the handler's `tags` option as the empty tuple `[]`, so `src/demo.ts` casts the tag list to compile. It works at runtime.
