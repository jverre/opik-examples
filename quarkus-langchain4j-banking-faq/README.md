# quarkus-langchain4j-banking-faq

*A credit-union FAQ bot on Quarkus LangChain4j, traced into Opik over plain OpenTelemetry, with the prompt and the answer on every span.*

A member asks "Can I buy Bitcoin through Larkspur?" and the bot says it does not know. Was that the right call, or did retrieval hand the model the wrong pages? In a RAG app you cannot tell from the answer alone. You have to see the exact prompt the model received. Quarkus LangChain4j emits OpenTelemetry spans out of the box, and Opik ingests OTLP directly, so there is no Opik SDK in this project: a few lines of `application.properties` send every request to Opik. One catch, and the reason this example exists: by default the LLM spans carry model name and token counts but **not** the prompt or the completion. Two properties fix that.

## What you'll build

A Quarkus 3.40 service for Larkspur Credit Union, a fictional member-owned bank. `GET /ask?q=...` goes to a LangChain4j AI service (`FaqAssistant`) that answers with `gpt-4o-mini`. At startup the `easy-rag` extension reads five FAQ files from `src/main/resources/faq/` (accounts and fees, cards and fraud, loans, savings and certificates, digital banking), splits them into chunks, embeds them with `text-embedding-3-small` into an in-memory store, and for every question retrieves the top 3 chunks into the prompt. One small tool, `branchHours`, lets the model look up branch opening hours. The system prompt says: answer only from the excerpts, otherwise send the member to member services.

`./run.sh` builds the app, starts it on port 4261, asks five scripted questions over HTTP (card theft, auto loan APR, branch hours, overdraft fees, and one the FAQ cannot answer), then stops the app. No Opik code anywhere: the OTLP endpoint and the three headers (`Authorization`, `Comet-Workspace`, `projectName`) are built from environment variables in `application.properties`.

## See it in Opik

Open the `quarkus-langchain4j-banking-faq` project and the Traces tab. After a run you will see six traces: five named `GET /ask` (one per question) and one named `POST /embeddings`, which is the startup indexing of the FAQ files.

Open any `GET /ask` trace. The tree has the HTTP server span `GET /ask` at the root (the question appears only as `url.query` in its input, and the trace has no output of its own, because Quarkus records an HTTP span, not your business data). Under it sits `langchain4j.aiservices.FaqAssistant.answer`, then a `POST /embeddings` span (embedding the question for retrieval), then a `completion gpt-4o-mini` span of type llm, with `POST /chat/completions` beside it for the raw HTTP call. The llm span is where the value is. Its input holds `gen_ai.prompt`: the system prompt, the member's question, and "Answer using the following information:" followed by the retrieved FAQ chunks, about 3,400 characters in the Bitcoin case. Its output holds `gen_ai.completion`. Opik shows the model (`gpt-4o-mini-2024-07-18`), the provider (openai), token usage, and an estimated cost. In my run each question used 880 to 965 tokens and cost about $0.00014 to $0.00018 per completion, roughly $0.0009 for all six llm spans.

Two traces are worth comparing. The card-theft question retrieves the cards-and-fraud chunk and the answer quotes the 1-800-555-0142 line and the $15 expedited fee straight from it. The Bitcoin question retrieves the digital-banking and accounts chunks, which contain nothing about crypto, and the completion is "I do not know... call member services at 1-800-555-0177". The prompt on the llm span is the proof that the refusal was correct: the right chunk was never in it. The branch-hours trace is the one with 8 spans: two llm spans (the model asks for the tool, then answers), and a `langchain4j.tools.branchHours` span of type tool with arguments `{"branch": "downtown"}` and the result string.

## Run it yourself

1. Prerequisites: Java 21 or newer (tested on Java 25; the code compiles for release 21) and Maven 3.9+.
2. `cp .env.example .env` and fill in `OPENAI_API_KEY`, `OPIK_API_KEY` and `OPIK_WORKSPACE` (or export them in your shell).
3. `./run.sh`. First build downloads dependencies; after that the whole demo takes about 40 seconds and well under a cent.
4. Open the `quarkus-langchain4j-banking-faq` project in Opik and click the newest `GET /ask` trace.
5. To play with the service yourself: `./run.sh serve`, then `curl --get --data-urlencode "q=What is the Zelle limit?" http://localhost:4261/ask`.

## Poke around

- Set `quarkus.langchain4j.tracing.include-prompt=false` and `include-completion=false` in `application.properties`, rerun, and open an llm span. Model, token usage and cost are still there, but the input and output are empty. This is the difference between knowing a call happened and knowing why it answered that way.
- Ask something the FAQ half covers, like `q=Does Larkspur do mortgages?`. The loans file says Larkspur refers members to a partner. Check whether the retrieved chunk is in the prompt before you decide whether the answer is right.
- Change `quarkus.langchain4j.easy-rag.max-results` from 3 to 1 and ask the overdraft question again. Watch the prompt on the llm span shrink to one chunk.
- Running Opik locally? Set `OPIK_OTEL_ENDPOINT=http://localhost:5173/api/v1/private/otel` and nothing else changes.

## How it's put together

- `pom.xml` — Quarkus 3.40.1 with its LangChain4j BOM: `quarkus-rest-jackson`, `quarkus-langchain4j-openai`, `quarkus-langchain4j-easy-rag`, `quarkus-opentelemetry`. No Opik dependency.
- `src/main/resources/application.properties` — model settings, easy-rag chunking, the OTLP endpoint and headers (from env vars), and the `include-prompt` / `include-completion` switches.
- `src/main/resources/faq/` — five fictional Larkspur FAQ documents, the corpus.
- `src/main/java/org/larkspur/faq/FaqAssistant.java` — the AI service: system prompt plus the question.
- `src/main/java/org/larkspur/faq/BranchTools.java` — the `branchHours` tool.
- `src/main/java/org/larkspur/faq/AskResource.java` — the `GET /ask` endpoint.
- `run.sh` — build, start, ask five questions, stop.

Notes: the HTTP server and OpenAI client spans come from Quarkus's own instrumentation and show up as general spans next to the llm and tool spans. I could not switch the HTTP-client spans off with `quarkus.otel.instrument.rest-client=false`, so they stay.

---

Part of the Opik examples · built with [Opik](https://github.com/comet-ml/opik)
