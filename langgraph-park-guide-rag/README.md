# langgraph-park-guide-rag

Ask a park visitor guide a question, then open the trace to see which sections were fetched and whether the answer stayed inside them.

Guide-grounded Q&A is easy to get fluent and hard to get right. A model can answer from the wrong passage, ignore the right one, or fill a gap in the guide with something it made up, and the answer text looks the same in every case. This example is a small RAG assistant for Alder Hollow National Park, a fictional park with a four-chapter visitor guide. It is a two-node LangGraph graph (retrieve, then generate) split into small modules and traced with Opik. Every run is a trace that shows what retrieval returned and what the model did with it, and an experiment scores the pipeline for hallucination and retrieval quality at two retrieval depths.

## What you'll build

- `retrieve` looks up the `k` most similar guide sections in an in-memory vector store (`text-embedding-3-small`). The lookup is its own `search_guide` function, wrapped with `@opik.track(type="tool")` so it always appears as a named tool span.
- `generate` answers with `gpt-4o-mini` using only those sections, and says "the guide does not say" when they do not cover the question.
- The compiled graph is wrapped once with `track_langgraph` and an `OpikTracer`, so every invocation is one trace without passing callbacks around.
- `main.py` answers three questions, creates an 8-question Opik dataset, and runs two experiments over it with the `Hallucination` and `ContextPrecision` judges: `park-guide-k3` (3 sections) and `park-guide-k1` (1 section).

## See it in Opik

Open the `langgraph-park-guide-rag` project (Traces tab). After one run it holds 19 traces: 3 named `LangGraph` (the demo questions, tagged `k=3`) and 16 named `evaluation_task` (8 dataset questions times 2 experiments). Click the `LangGraph` trace for "How much does a car pay to enter the park?". The tree has two branches: `retrieve` with a nested `search_guide` span of type tool, whose output is the three guide sections, and `generate` with a nested `ChatOpenAI` span of type llm showing the full prompt, the one-line answer ("A private vehicle pays $30 for a 7-day pass."), 387 tokens, and an estimated cost of about $0.00006. The kayak question is not covered by the guide, and the answer is "The guide does not say.". The `evaluation_task` traces have the judge calls nested inside, and the two scores attached as feedback scores.

Next open Experiments and select the dataset `langgraph-park-guide-rag-questions` (8 items). You will see `park-guide-k3` and `park-guide-k1`, each with a `hallucination_metric` and a `context_precision_metric` column (hallucination: 0 is grounded, 1 is unsupported). In this run, k=3 scored hallucination 0.21 and context precision 0.78, and k=1 scored 0.20 and 0.85. Treat the gap with caution: the judge is an LLM, and eight questions are few. Across three runs while building this example, the same pipeline gave k=3 hallucination between 0.18 and 0.29 and k=1 between 0.14 and 0.28, so only the pattern of higher precision at k=1 held steady. The per-question rows are more useful, and two stood out in every run:

- "Can I bring my dog on the Moss Falls trail?" at k=1: the single retrieved section is `Pets and bikes`, which contains the answer, but the model replied "The guide does not say." and the judges scored hallucination 1.0 and context precision 0.0. Open the trace: the right context was fetched and the generation ignored it, so this is a prompt problem, not a search problem. At k=3 the same question scored hallucination 0.0 and precision 0.6.
- "Are drones allowed at Opal Lake?" at k=3: `Drones and fishing` was the first result, followed by `Emergencies` and `Backcountry camping`, and the row scored hallucination 0.9 and context precision 0.2. At k=1 the same question scored 0.0 and 1.0.

If you run the script again, the experiments are created again with the same names, so the experiment list will show several `park-guide-k3` and `park-guide-k1` runs side by side.

## Run it yourself

1. `cp .env.example .env` and add `OPENAI_API_KEY`, `OPIK_API_KEY` and `OPIK_WORKSPACE` (or run `opik configure` and export only the OpenAI key).
2. `uv sync`
3. `uv run main.py` (about one minute and about $0.03 of gpt-4o-mini and embedding usage)
4. Open the `langgraph-park-guide-rag` project in Opik, then the Experiments page.

## Poke around

- Change `DEMO_QUESTIONS` in `main.py` to ask something the guide covers in two chapters (for example, "Can I fly a drone and fish at Opal Lake?") and check which sections `search_guide` returned.
- Edit `run_experiment(dataset, k=1, ...)` in `main.py` to `k=2` or `k=5` and compare the new run against the others in the experiment view.
- Plant a wrong fact in `guide/visiting.md` (say the vehicle pass costs $45) and rerun: the assistant repeats it with a clean hallucination score, because the metric checks the answer against the retrieved context and not against the truth.
- Tighten or loosen `SYSTEM_PROMPT` in `park_rag/graph.py` and watch how many "the guide does not say" answers change.

## How it's put together

- `main.py` - entry point: three traced questions, then the two experiments.
- `park_rag/config.py` - project name, model names and paths; sets `OPIK_PROJECT_NAME`.
- `park_rag/corpus.py` - corpus loader that splits each chapter into one chunk per `##` section.
- `park_rag/retriever.py` - the in-memory vector store and the tracked `search_guide` tool function.
- `park_rag/graph.py` - the LangGraph retrieve-to-generate graph and its `OpikTracer`.
- `park_rag/evaluation.py` - the dataset, the task function and the `evaluate()` call.
- `guide/` - four short chapters about Alder Hollow National Park; the RAG corpus.
- `.env.example` - the keys the example needs.
