<div align="center">

# Lab SOP Q&A, One Step at a Time

**`llamaindex-lab-sop-qa`**

*When a lab assistant gives a wrong answer, a step-level test suite tells you whether retrieval or the model got it wrong.*

![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat&logo=python&logoColor=white)
![LlamaIndex](https://img.shields.io/badge/llama--index-0.14%2B-6a4c93?style=flat)
[![Opik](https://img.shields.io/badge/Opik-2.2%2B-2f54eb?style=flat)](https://github.com/comet-ml/opik)
[![uv](https://img.shields.io/badge/setup-uv-DE5FE9?style=flat&logo=uv&logoColor=white)](https://docs.astral.sh/uv/)

**[What you'll build](#what-youll-build) · [See it in Opik](#see-it-in-opik) · [Run it](#run-it-yourself) · [Poke around](#poke-around)**

</div>

---

Lab SOPs repeat themselves. "30 minutes" is the aerosol wait after a centrifuge failure, the
solid autoclave cycle, and the freezer alarm window; "6 months" is both a buffer shelf life and
an inventory audit interval. A question-answering bot over those documents can return a fluent,
confident, wrong number, and a single pass/fail score on the final answer does not say why.
Did retrieval fetch the wrong SOP, or did it fetch the right sentence and the model still
fumbled it? This example answers five fictional SOPs for the Fennmoor Cell Biology Lab with
LlamaIndex, traces every question with Opik's LlamaIndex integration, and runs a test suite
whose assertions are split by pipeline step, so every failure points at the step to fix.

## What you'll build

A small package with a CLI, `sop-qa`, split into modules:

- `sop-qa build-pdfs` writes five SOP PDFs (reagent prep, centrifuge, spill response,
  autoclave, ultra-low freezer) into `data/sops/` with reportlab. Nothing is committed; the
  PDFs are generated at run time.
- `sop-qa ask "<question>"` indexes the PDFs and answers with `gpt-4o-mini`, printing the
  answer and which SOPs retrieval pulled from.
- `sop-qa suite` runs an Opik test suite of eight questions. Each assertion is prefixed with the
  step it judges: `RETRIEVE:` assertions read only the retrieved excerpts, `SYNTHESIZE:` assertions
  read only the answer. Every item runs 3 times and must pass 2 of 3, because an LLM judge is noisy.
- `sop-qa demo` does all of it: build the PDFs, ask three questions, then run the suite twice,
  once retrieving 1 chunk per question (`top-k 1`) and once retrieving 3 (`top-k 3`), as two
  experiments you can compare.

Tracing is one call, `set_global_handler("opik", ...)`, made before the engine is built.

## See it in Opik

Open the **`llamaindex-lab-sop-qa`** project. The Traces tab holds 51 traces from one `demo` run:
3 `query` traces from the `ask` step, and 48 `evaluation_task` traces from the suite (24 per
experiment, which is 8 questions times 3 runs). Open the `query` trace for "A tube cracked
mid-spin and liquid leaked into the centrifuge...". It has a `retrieve` span (with an `embedding`
span inside it) whose output is the three chunks that came back: SOP-204 twice (scores 0.596 and
0.493) and SOP-310 (0.461). Next to it is a `synthesize` span containing `chunking`,
`templating` (the exact prompt, with the excerpts stitched in) and an `llm` span: `gpt-4o-mini`,
593 tokens, about $0.00011. Across the project all 51 answer-model `llm` spans carry token usage
and an estimated cost (about $0.0036 in total for the answers).

Then open the Experiments tab, where the same suite has run twice:

- **`sop-qa-top-k-3`** passed 7 of 8 items (88%). All 24 retrieve checks passed.
- **`sop-qa-top-k-1`** passed 6 of 8 items (75%). It fails the cracked-tube question 3 of 3 runs
  on a `RETRIEVE:` assertion: the one chunk it fetched is SOP-204, which only says "clean it up as
  described in SOP-310", so the actual spill text never reached the model. Retrieval pass rate
  drops to 88% (21 of 24) while the synthesis rate does not move.

Both experiments share one failure that no retrieval setting fixes. "How long can I keep 1 M
Tris-HCl pH 8.0 on the shelf?" fails 3 of 3 runs at the `SYNTHESIZE:` step in both. The retrieve
assertion passes, because the excerpt contains "Tris-HCl buffer has a shelf life of 6 months",
but the chunker cut the section heading and the "1 M ... pH 8.0" preparation sentence into a
different chunk, and `gpt-4o-mini` answers "The SOPs do not cover it." The step prefix on the
failing assertion tells you not to touch `top_k`; look at chunking or the prompt. In the
Experiments compare view, the failing assertion is named after its step, and the judge's
reason is attached to each run.

The test suite itself (Test suites tab in the project) shows the 8 items, each with its
`RETRIEVE:` and `SYNTHESIZE:` assertions and the execution policy of 3 runs, pass 2.

## Run it yourself

1. `cp .env.example .env` and add `OPENAI_API_KEY` plus your Opik credentials (or run
   `opik configure` once).
2. `uv sync`
3. `uv run sop-qa demo` (about 1.5 minutes, around $0.02 with the default models)
4. Open the `llamaindex-lab-sop-qa` project in Opik and follow the steps above.

Individual commands: `uv run sop-qa build-pdfs`, `uv run sop-qa ask "How long is the eyewash flush?"`,
`uv run sop-qa suite --top-k 3 --runs 3`.

The judge uses Opik's default model, so one OpenAI key covers the app and the judge. Judge
verdicts vary a little between runs; the "pass 2 of 3" policy absorbs most of that, but a
borderline item can still flip between runs of the demo.

## Poke around

- Run `uv run sop-qa ask "What is the policy for working alone in the lab at night?"` and open the
  trace. Retrieval still returns three chunks (scores near 0.39), and the answer should say the
  SOPs do not cover it. The last suite item pins that behavior.
- Fix the Tris-HCl failure and watch only the `SYNTHESIZE:` score move: raise `chunk_size` in
  `engine.py` from 160 to 320, or relax the "say the SOPs do not cover it" line in `QA_TEMPLATE`.
- Change a fact in `pdfs.py` (make the centrifuge wait 20 minutes), delete `data/sops/`, and
  re-run `suite`. The assertions that pin 30 minutes fail, which makes the suite a regression
  test for the documents, not just the code.
- Try `uv run sop-qa suite --top-k 5` and see whether extra chunks help or distract the model.

## How it's put together

- `sop_qa/pdfs.py` generates the five fictional SOP PDFs with reportlab.
- `sop_qa/engine.py` reads, chunks and embeds the PDFs, builds the query engine, and turns on Opik tracing.
- `sop_qa/suite.py` holds the eight items, the step-prefixed assertions, and the per-step report.
- `sop_qa/cli.py` is the `sop-qa` command: `build-pdfs`, `ask`, `suite`, `demo`.
- `sop_qa/__init__.py` sets the project name and the PDF directory.
- `.env.example` lists the keys the example needs.

---

Part of [Opik Integration Examples](../README.md) · built with [Opik](https://github.com/comet-ml/opik) · ⭐ [star Opik](https://github.com/comet-ml/opik) if this example helped
