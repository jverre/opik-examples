<div align="center">

# Opik Examples

*27 small, runnable LLM apps. Each one teaches one Opik feature, and each one was run and checked in Opik.*

![Examples](https://img.shields.io/badge/examples-27-success?style=flat)
![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat&logo=python&logoColor=white)
![TypeScript](https://img.shields.io/badge/typescript-node%2020%2B-3178C6?style=flat&logo=typescript&logoColor=white)
[![Powered by Opik](https://img.shields.io/badge/powered%20by-Opik-2f54eb?style=flat)](https://github.com/comet-ml/opik)
![license](https://img.shields.io/badge/license-Apache%202.0-blue?style=flat)

**[The examples](#the-examples) · [Running an example](#running-an-example) · [What's inside](#whats-inside-each-example) · [License](#license)**

</div>

---

Every folder here is a complete, runnable app that teaches one [Opik](https://github.com/comet-ml/opik) lesson: threads, test suites, experiments, prompt versions, attachments, cost per agent, OpenTelemetry ingestion, and more. Every example ships its own fictional data, so the only network calls go to the model provider and to Opik. Every example was run end to end, and its traces, spans, and other artifacts were confirmed in Opik through the SDK before its README was written. The numbers in each README come from that run, honest failures included. There are no screenshots; each README tells you in words what to open in Opik and what you will see.

## The examples

| Example | Integration | Language | What it shows | Highlights |
|---|---|---|---|---|
| [openai-ts-hotel-concierge](openai-ts-hotel-concierge/) | OpenAI SDK + `opik-openai` | TypeScript | A seaside-hotel concierge whose logs read as conversations | Threads, cost per turn, `guest-satisfaction` feedback 1.0 vs 0.0 |
| [anthropic-museum-guide-citations](anthropic-museum-guide-citations/) | Anthropic SDK | Python | A museum guide that must quote the curator's notes verbatim | Test suite with citation assertions: strict prompt 100%, warm prompt 85.7% |
| [pydantic-ai-calendar-extraction](pydantic-ai-calendar-extraction/) | Pydantic AI (OTel) | Python | Typed calendar events from messy emails, as a CLI package | OTel tracing; the suite catches invented values: strict 100%, eager 43% |
| [langgraph-park-guide-rag](langgraph-park-guide-rag/) | LangChain + LangGraph | Python | RAG over a national-park visitor guide, split into modules | Retrieve/generate spans, `Hallucination` + `ContextPrecision` experiments at k=3 and k=1 |
| [openai-agents-insurance-claims](openai-agents-insurance-claims/) | OpenAI Agents SDK | Python | A claims desk where triage hands off to auto, home, and pet specialists | Handoff + tool spans, a re-route back through triage, threads via `group_id` |
| [crewai-product-launch](crewai-product-launch/) | CrewAI | Python | A three-agent crew writes a product-launch plan | One trace per kickoff, tokens and dollar cost per agent |
| [litellm-changelog-router](litellm-changelog-router/) | LiteLLM | Python | The same commit lists routed to OpenAI and Anthropic, as a CLI package | Per-model cost and latency table: Haiku 6.9x the cost of gpt-4o-mini |
| [prompt-library-podcast-titles](prompt-library-podcast-titles/) | Opik SDK (no framework) | Python | A podcast episode-title prompt managed in the prompt library | Immutable versions with diffs, suite 0% on v1 and 100% on v2 |
| [vercel-ai-sveltekit-plant-care](vercel-ai-sveltekit-plant-care/) | Vercel AI SDK + SvelteKit | TypeScript | A streaming houseplant-care assistant | Streaming spans, threads, a live online-evaluation rule set up from code |
| [langchainjs-fastify-bike-shop](langchainjs-fastify-bike-shop/) | LangChain.js + Fastify | TypeScript | A bike-repair shop's website chat | Threads that render as clean transcripts |
| [mastra-library-loans-agent](mastra-library-loans-agent/) | Mastra (OTel) | TypeScript | A public-library loans agent with catalog, renew, and hold tools | Agent-loop trees with real tool calls; a custom exporter fills trace I/O and cost |
| [temporal-py-talk-review](temporal-py-talk-review/) | Temporal Python SDK (OTel) | Python | A durable conference-talk review workflow with a flaky activity | One trace across two OS processes, the failed attempt visible with its error |
| [openai-image-boardgame-cards](openai-image-boardgame-cards/) | OpenAI SDK + `opik-openai` | TypeScript | Board-game card art from managed prompt briefs | PNG attachments, prompt v1 to v2 diff, `art-only` guardrail score |
| [llamaindex-lab-sop-qa](llamaindex-lab-sop-qa/) | LlamaIndex | Python | Q&A over generated laboratory SOP PDFs, as a CLI package | Retrieve + synthesize spans; a suite whose assertions name the failing step |
| [langgraph-wildlife-survey-team](langgraph-wildlife-survey-team/) | LangGraph | Python | Planner, looping field researchers, and a writer produce a wildlife survey | One deep trace with the loop in the agent-graph view, cost per agent |
| [smolagents-solar-farm-analyst](smolagents-solar-farm-analyst/) | smolagents (OpenInference) | Python | A CodeAgent audits a solar-farm output CSV with planted anomalies | Generated pandas code and execution logs in spans; one anomaly honestly missed |
| [whisper-vet-voicemail-triage](whisper-vet-voicemail-triage/) | OpenAI TTS + Whisper | Python | Vet-clinic voicemails to transcripts to triage notes | Playable MP3 on every trace; suite with `execution_policy`, a real mishearing at 80% |
| [openai-vision-nutrition-labels](openai-vision-nutrition-labels/) | OpenAI vision | Python | Typed fields from rendered nutrition labels, as a CLI package | Label images as attachments; suite 83% with an honest failure on a rotated label |
| [optimizer-fitness-intent-classifier](optimizer-fitness-intent-classifier/) | Opik Agent Optimizer | Python | A fitness-app intent classifier prompt, optimized against a dataset | Score curve 0.00 to 0.75 in 8 trials, winner saved as prompt v2 |
| [dspy-trivia-fact-check](dspy-trivia-fact-check/) | DSPy | Python | A fact-check program that compiles its own few-shot prompt | Same suite, uncompiled 0% vs compiled 100% |
| [voltagent-restaurant-reservations](voltagent-restaurant-reservations/) | VoltAgent (OTel) | TypeScript | A bistro reservation assistant with booking tools | The same request with the `gen_ai.*` mapper off and on: no cost vs cost |
| [beeai-facility-maintenance-agent](beeai-facility-maintenance-agent/) | BeeAI (OpenInference) | TypeScript | A facility-maintenance triage ReAct agent | Iteration, LLM, and tool spans from OpenInference instrumentation |
| [python-sdk-manual-translation-qa](python-sdk-manual-translation-qa/) | Opik Python SDK (no framework) | Python | A translation QA pipeline traced entirely by hand | Manual spans, hand-recorded usage, two feedback scores, a flush demo |
| [quarkus-langchain4j-banking-faq](quarkus-langchain4j-banking-faq/) | Quarkus LangChain4j (OTLP) | Java | A credit-union FAQ bot with RAG and a branch-hours tool | OTel from the JVM with prompt and completion on spans, usage and cost |
| [ollama-langchainjs-homebrew-rag](ollama-langchainjs-homebrew-rag/) | LangChain.js + Ollama | TypeScript | Fully local RAG over a homebrewing handbook | Tracing with zero cloud LLM calls; right retrieval, wrong 1B-model answers |
| [n8n-grant-screening](n8n-grant-screening/) | n8n + n8n-observability | low-code | An arts-foundation grant screening workflow | Zero-code tracing via hooks, workflow imported through the n8n API |
| [dify-student-housing-assistant](dify-student-housing-assistant/) | Dify (native integration) | low-code | A university housing-office assistant built with no app code | Opik tracing switched on through Dify's API; threads from the conversation id |

## Running an example

You need an Opik to send traces to. Use [Opik Cloud](https://www.comet.com/opik), or start a local one:

```bash
git clone https://github.com/comet-ml/opik.git && cd opik && ./opik.sh   # UI at http://localhost:5173
```

For a local Opik, set `OPIK_URL_OVERRIDE=http://localhost:5173/api` and `OPIK_WORKSPACE=default`, and leave `OPIK_API_KEY` empty.

Then every example follows the same four steps:

1. Clone the repo and `cd` into the example's folder.
2. `cp .env.example .env` and add your keys (the repo-root `.env.example` lists every variable used anywhere).
3. Install: `uv sync` for Python, `npm install` for TypeScript, nothing extra for Java or the Docker-based examples.
4. Run the command in the example's README: usually `uv run main.py` or `npm run demo`, `./run.sh` for Java, and `./setup.sh && ./demo.sh` for n8n and Dify.

Each example logs to its own Opik project, named after its folder. After a run, open that project in Opik, and the README tells you exactly what to look at.

## What's inside each example

Every folder has the same anatomy:

- The app itself: `main.py`, a small package with a CLI, `src/` for TypeScript, or a Maven project for Java. It is kept small enough to read in one sitting.
- `README.md`: the problem, what you build, what to open in Opik and what you will see there, how to run it, and a few experiments to try.
- `.env.example`: every variable the example reads, with a comment and a link to where to get it.
- `pyproject.toml` or `package.json` (with `package-lock.json`), with the Opik packages pinned to an exact version.

Some examples add a `data/`, `docs/`, or `guide/` folder with the fictional corpus they use, so everything runs offline except the LLM calls. Examples that make images, audio, or PDFs generate them at run time; no large binaries are committed.

## License

[Apache 2.0](LICENSE).

---

<sub>Inspired by Opik's [examples](https://github.com/comet-ml/opik) and [documentation](https://www.comet.com/docs/opik/).</sub>
