<div align="center">

# Changelog Router

**`litellm-changelog-router`**

*The same release notes written by two providers, with cost and latency side by side in one Opik table.*

![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat&logo=python&logoColor=white)
![LiteLLM](https://img.shields.io/badge/litellm-1.105-1C7ED6?style=flat)
[![Opik](https://img.shields.io/badge/Opik-2.2.96-2f54eb?style=flat)](https://github.com/comet-ml/opik)
[![uv](https://img.shields.io/badge/setup-uv-DE5FE9?style=flat&logo=uv&logoColor=white)](https://docs.astral.sh/uv/)

**[What you'll build](#what-youll-build) · [See it in Opik](#see-it-in-opik) · [Run it](#run-it-yourself) · [Poke around](#poke-around) · [How it's put together](#how-its-put-together)**

</div>

---

"Would a different model do this job cheaper?" is easy to ask and annoying to answer, because every provider has its own SDK and its own way of reporting tokens and cost. This example answers it for one concrete job: turning a raw commit list into user-facing release notes. A small Python package sends the commits of four fictional releases of `Tidewater`, a made-up Rust job scheduler, to OpenAI's `gpt-4o-mini` and Anthropic's `claude-haiku-4-5` through LiteLLM. Opik records every call with tokens, cost, and latency, and a `report` command reads those numbers back out of Opik into one per-model table.

## What you'll build

A package, `changelog_router/`, with a two-command CLI. `run` loads the commit lists from `data/releases/`, writes a changelog for every release with every model, saves the Markdown under `out/`, and prints the comparison table. `report` prints the same table for any earlier run. Each call is a `write_changelog` function wrapped in `@opik.track`, so a trace has a root `general` span, and LiteLLM's built-in `OpikLogger` callback adds the `llm` span underneath it with usage and estimated cost. Each trace is tagged with the model, the release, and a run id (`run:<timestamp>`), which is how the report finds exactly the calls of one run. The project is `litellm-changelog-router`.

## See it in Opik

Open the `litellm-changelog-router` project and look at the Traces tab. One run gives eight traces, all named `write_changelog`: four for `gpt-4o-mini` and four for `claude-haiku-4-5-20251001`. Each trace has a tag with the model (for example `gpt-4o-mini`), a tag with the release (`v0.8.0` to `v1.0.1`), and a `run:` tag. Expand a trace and you see two spans: the `write_changelog` `general` span, and under it an `llm` span named like `claude-haiku-4-5-20251001_chat.completion_...` with provider `anthropic`, token usage, and an estimated cost. If the `llm` span were detached from the trace, the call would be orphaned; the example passes `current_span_data` to LiteLLM so that it is not.

Add the Estimated cost and Duration columns, filter by the tag `claude-haiku-4-5-20251001` and then `gpt-4o-mini`, and the comparison is right there. In the verified run, the four `gpt-4o-mini` traces cost between $0.00013 and $0.00025 each, and the four Haiku traces between $0.00076 and $0.00178 each. The `v1.0.0` release, the biggest commit list, cost $0.000247 on `gpt-4o-mini` and $0.001779 on Haiku. Duration barely separates them: both finish in about 1.4 to 2.9 seconds.

The `run` command prints the same numbers from the `llm` spans it reads back from Opik. This is the real output of the verified run:

```
Model                        Calls  Prompt tok  Compl. tok   Cost (USD)  Mean latency     Max
---------------------------------------------------------------------------------------------
gpt-4o-mini-2024-07-18           4        1756         905    $0.000806         2.48s   2.73s
claude-haiku-4-5-20251001        4        1984         716    $0.005564         2.19s   2.85s

claude-haiku-4-5-20251001 cost 6.9x as much as gpt-4o-mini-2024-07-18 and its mean latency was 0.9x.
```

Two things are worth noticing. First, the cost gap is a price gap, not a verbosity gap: Haiku wrote fewer completion tokens (716 versus 905) and still cost 6.9x as much, because its per-token price is several times higher. Second, cheap does not mean identical. For `v1.0.0`, Haiku listed the removal of the `/v0` API routes under "Breaking changes", while `gpt-4o-mini` listed it under "Added", and also wrote a link (`docs/guide`) that is not in the commit list. Open the Markdown in `out/` next to the traces to judge whether the price gap is worth it. (Model output varies a little from run to run, so your numbers and wording will differ.)

Note that Opik records the resolved model id, so OpenAI's alias shows up as `gpt-4o-mini-2024-07-18`.

## Run it yourself

1. `cd litellm-changelog-router && cp .env.example .env`, then fill in `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPIK_API_KEY`, and `OPIK_WORKSPACE`.
2. `uv sync`
3. `uv run python -m changelog_router run` (about 30 seconds and under one cent in LLM cost).
4. `uv run python -m changelog_router report` to reprint the table for the latest run, or `report --run <run id>` for an earlier one.
5. Open the `litellm-changelog-router` project in Opik, add the Estimated cost column, and sort by it.

## Poke around

- Add a third model to `MODELS` in `changelog_router/__init__.py` (for example `openai/gpt-4.1-mini`) and re-run. The report table grows a row without any other change.
- Edit the system prompt in `changelog_router/router.py` to ask for "at most 80 words" and compare the completion token columns. Cost per call shrinks, the ratio between models mostly does not.
- Add a release file under `data/releases/` (copy one and change the commits), then compare how each model groups a commit that is both a fix and a breaking change.
- Run `run` twice and open Opik filtered by two different `run:` tags to see how stable latency is between runs, while cost stays almost identical.

## How it's put together

- `changelog_router/__init__.py`: the project name and the list of LiteLLM model strings.
- `changelog_router/commits.py`: loads the release JSON files and formats commits as `git log`-style lines.
- `changelog_router/router.py`: the system prompt and the `@opik.track`ed `write_changelog` call that routes to any model through LiteLLM.
- `changelog_router/tracing.py`: pins the Opik project, registers LiteLLM's `OpikLogger`, and flushes at the end.
- `changelog_router/report.py`: reads `llm` spans of one run back from Opik and prints the per-model table.
- `changelog_router/cli.py`: the `run` and `report` subcommands.
- `data/releases/`: four fictional commit lists, with noise (dependency bumps, merge commits) the model should skip.

---

Part of [Opik Integration Examples](../README.md) · built with [Opik](https://github.com/comet-ml/opik) · ⭐ [star Opik](https://github.com/comet-ml/opik) if this example helped
