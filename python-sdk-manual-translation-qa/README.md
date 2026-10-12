<div align="center">

# Translation QA, Traced by Hand

**`python-sdk-manual-translation-qa`**

*Translate it, translate it back, and see exactly which step lost the meaning.*

![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat&logo=python&logoColor=white)
[![Opik](https://img.shields.io/badge/opik-2.2.96-2f54eb?style=flat)](https://github.com/comet-ml/opik)
![OpenAI](https://img.shields.io/badge/openai-gpt--4o--mini-412991?style=flat&logo=openai&logoColor=white)
[![uv](https://img.shields.io/badge/setup-uv-DE5FE9?style=flat)](https://docs.astral.sh/uv/)

</div>

---

Most Opik examples attach a wrapper (`track_openai`, a callback, a decorator) and traces appear on their own. That is convenient until the output does not match what you expect, or your pipeline mixes LLM calls with steps no wrapper knows about. This example drops every wrapper. It is a localization QA pipeline for a fictional habit-tracking app, Tidepool: each UI string is language-detected, translated, back-translated without peeking at the original, compared against the original, and given a ship-or-review verdict. Every trace, span and field on the LLM spans (model, provider, token usage) comes from an explicit call to the low-level `opik.Opik()` client that you can point at.

## What you'll build

A script that checks seven canned Tidepool strings (a few are idioms, on purpose). Each becomes one trace:

```
UI string -> client.trace("translation-qa")
  |- detect            general   which language is the source?
  |   '- chat detect-language   llm   gpt-4o-mini, usage recorded by hand
  |- translate         general   source -> target language
  |   '- chat translate          llm
  |- back_translate    general   target -> source, blind to the original
  |   '- chat back-translate     llm
  |- compare           general
  |   |- lexical-similarity     tool  difflib ratio, no LLM
  |   '- chat judge-meaning      llm   0..1 "did the meaning survive?"
  '- verdict          guardrail meaning_score >= 0.85 -> ship, else review
trace feedback scores: back_translation_similarity, lexical_similarity
finally -> client.flush()
```

Two things are the point. First, `chat_json()` in `qa/pipeline.py` is the integration: it opens an `llm` span with the exact messages, calls OpenAI directly, then copies `response.model`, `provider="openai"` and the three token counts onto the span, which is what lets Opik compute the cost. Second, spans are written once, complete, when a step finishes (see "Spans are written once" below), because that is the safe way to use the low-level client.

## See it in Opik

Open the `python-sdk-manual-translation-qa` project in Opik Cloud. The Traces tab shows seven `translation-qa` traces from the demo, plus two `flush-demo-*` traces from the flush experiment. Each translation trace has 10 spans and takes about 3 seconds. Tags show the target language and the verdict (`review` or `ship`), and two feedback score columns, `back_translation_similarity` and `lexical_similarity`, sit next to them.

Sort by `back_translation_similarity` and the story is in the column. In the final run only two strings shipped: the French "Tu as battu ton record, bravo !" to Spanish (meaning 1.0, lexical 0.98) and "Cancel anytime. No strings attached." to Italian (0.9). The other five went to `review`:

- "Tap to log today's water." to German scored 0.7 with a lexical similarity of 0.94. It came back as "Type to log today's water." The words are nearly identical, so a pure string-similarity check would pass it, but the judge caught that "tap" turned into "type". That row is why the LLM judge exists next to the cheap lexical check.
- "Your streak is on fire!" (Japanese, 0.5) and "Skip a day? No sweat, your streak is on ice." (Japanese, 0.4) lost their idioms: "in great condition" and "will be reset".
- The German "Das Wochenziel ist in trockenen Tüchern." to English scored 0.4. The idiom flattened to "The weekly goal is set."
- The Portuguese string to Korean scored 0.8 (tone drift, casual to formal).

Open the `s1` trace (tag `german`) and expand it. `detect` contains a nested `chat detect-language` span, and `compare` contains both `lexical-similarity` (type `tool`, no cost) and `chat judge-meaning`. Click any `chat ...` span: model `gpt-4o-mini-2024-07-18`, provider `openai`, prompt and completion tokens, and a non-null estimated cost (about $0.00002 for the small calls, $0.00005 for the judge). Across all 28 LLM spans the run used 2,959 tokens and cost about $0.0007. The `verdict` span (type `guardrail`) shows the rule that decided: `meaning_score 0.7 < 0.85`. Hover the `back_translation_similarity` score on the trace to read the judge's one-sentence reason.

Scores come from an LLM judge at temperature 0, so they wobble by a tenth or so between runs (the "on fire" string scored 0.4 in one run and 0.5 in another). The verdicts above were stable across the runs made while writing this.

### Spans are written once

The Python SDK logs a warning if you call `span.update()` or `span.end()` right after creating a span: with batching on, the PATCH can race the batched create and lose data. A first version of this example did exactly that and the warning fired on every call. So `qa/pipeline.py` uses a tiny `Step` helper instead. It picks the span id up front, remembers `start_time`, and sends the finished span (input, output, start and end time, usage) in a single `client.span()` call. Parent and child links work because the ids are chosen by us. The trace itself is sent twice with the same id: once at the start (input only, so it is visible immediately) and once at the end with the full payload, which overwrites the first. This is the SDK's own recommended alternative.

### Flush semantics

`client.flush()` blocks until everything queued in memory has been delivered. `qa/flush_demo.py` logs one trace and one span three ways, with no LLM calls:

| Mode | What it does | Result in the final run |
| --- | --- | --- |
| `flush` | log, `client.flush()`, exit | trace arrived |
| `no-flush` | log, then just exit normally | trace arrived |
| `hard-exit` | log, then `os._exit(0)` | trace missing |

The honest finding: the Python client also drains its queue from an `atexit` hook, so a plain script that forgets `flush()` still delivers on a normal exit. What loses data is any exit that skips `atexit`: `os._exit`, a container killed by SIGKILL, a serverless runtime that freezes the process after the handler returns. The `hard-exit` trace never reaches Opik. The demo calls `client.flush()` at the end for that reason, and so should anything that runs in a short-lived worker or reads its own data back right after logging.

## Run it yourself

1. `cp .env.example .env`, then add `OPENAI_API_KEY` and your Opik credentials (or run `opik configure` once and skip the Opik lines).
2. `uv sync`
3. `uv run python -m qa.demo` checks the seven strings and exits (about 25 seconds, under a cent).
4. Open the `python-sdk-manual-translation-qa` project in Opik and expand any `translation-qa` trace.
5. Optional, no OpenAI key needed: `uv run python -m qa.flush_demo flush`, then `no-flush`, then `hard-exit`, wait a few seconds, then `uv run python -m qa.flush_demo check`.

## Poke around

- Delete the `usage={...}` block in `chat_json()` and re-run. The spans still show up, but the token and cost columns go blank. That is the exact field the cost pipeline feeds on, and what you lose when an integration does not report usage. Set `total_cost=` instead to override Opik's price table.
- Raise `SHIP_THRESHOLD` to 0.95 or lower it to 0.5 and re-run. The `verdict` span's `rule` field shows why each string flipped, and the `ship` and `review` tags move with it.
- Add your own strings to `qa/strings.py`, such as a short ambiguous one ("Spring", "Date") or a string where the target language is wrong for the content. Check whether the judge flags it, or whether the back-translation round-trips cleanly and hides the mistake. Back-translation cannot see errors that are symmetric.
- Reintroduce `span.update()` and `span.end()` right after span creation (the pattern in most tutorials) and watch the SDK warning appear. Then swap `os._exit` into `qa/demo.py` right before the flush and see how many traces survive.

## How it's put together

- `qa/pipeline.py` - the whole example: the `Step` helper, `chat_json()` (the hand-rolled LLM span), and `check_string()` (the five steps, the trace, the scores).
- `qa/strings.py` - seven fictional Tidepool UI strings with target languages.
- `qa/demo.py` - runs every string, prints verdicts, and calls `client.flush()`.
- `qa/flush_demo.py` - the flush / no-flush / hard-exit experiment and a `check` command.
- `pyproject.toml` - Python 3.12+, `opik==2.2.96`, `openai`, `python-dotenv`.
- `.env.example` - the keys the example needs.
