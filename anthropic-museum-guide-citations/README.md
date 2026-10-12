<div align="center">

# Museum Guide That Quotes the Curator

**`anthropic-museum-guide-citations`**

*A museum guide must quote the curator's notes word for word. A test suite checks every quote, and every question gets a pass or a fail.*

![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat&logo=python&logoColor=white)
![Anthropic SDK](https://img.shields.io/badge/anthropic-0.122%2B-191919?style=flat&logo=anthropic&logoColor=white)
[![Opik](https://img.shields.io/badge/Opik-2.2.96-2f54eb?style=flat)](https://github.com/comet-ml/opik)
[![uv](https://img.shields.io/badge/setup-uv-DE5FE9?style=flat&logo=uv&logoColor=white)](https://docs.astral.sh/uv/)

**[What you'll build](#what-youll-build) · [See it in Opik](#see-it-in-opik) · [Run it](#run-it-yourself) · [Poke around](#poke-around)**

</div>

---

A museum guide that "quotes the curator" has a quiet failure mode: the quote that
is almost right. The wording is smoothed, a clause is dropped, and a careful
"there is no truth in the story" becomes a confident "the story was invented".
Nobody notices until a visitor repeats it to the curator. This example builds a
Claude guide for one gallery of a fictional maritime museum, makes it cite the
curator's notes inside `<quote>` tags, and turns "are the quotes real?" into an
Opik test suite with plain-English assertions and a pass or fail for every question.

## What you'll build

A guide for Gallery 3 of the fictional Saltmarsh Maritime Museum ("The Wreck of the
Marigold"), answering from `data/curator_notes.md`. Claude Haiku 4.5 runs through the
Anthropic SDK wrapped with `track_anthropic`. Two system prompts compete:

- `warm-v1` asks for a friendly guide and says to "tidy the wording" of excerpts.
- `strict-v2` requires `<quote>` excerpts copied character for character, and says
  to admit when the notes do not cover a question.

Both prompts are saved in Opik's prompt library. One test suite of seven visitor
questions holds the quality bar as plain English, with no metric classes:

- every excerpt inside `<quote>` tags appears verbatim in the curator's notes,
- the excerpts genuinely support the claims in the answer,
- the answer addresses the question without adding facts the notes do not contain.

Three questions add their own assertions: the bell's crack must be blamed on a
casting flaw (not the rocks), the figurehead must be "attributed to" its carver, and a
question the notes cannot answer (the ship's tonnage) must get an honest "I don't have
that". The judge is Claude too, and each item is judged 3 times and passes on 2 of 3,
because a judge is an LLM and an LLM is not deterministic.

## See it in Opik

Open the **`anthropic-museum-guide-citations`** project. One run of the script leaves
42 traces (7 questions x 3 runs x 2 prompts), all named `evaluation_task`. Open any
one: the tree holds `task`, then `guide_answer` (your function), then
`anthropic_messages_create`, an `llm` span with `claude-haiku-4-5-20251001`, about
1,900 prompt tokens and a cost near $0.0034. Beside it sit the judge's own spans
(`llm_judge`, with an `anthropic_messages_parse` `llm` span). The project holds 84 `llm`
spans with usage and cost, about $0.21 in total.

Now open **Test suites** and pick `anthropic-museum-guide-citations`. It has 7 items,
3 global assertions, and per-item assertions on 3 of them. Open its **Experiments**: there are
two runs, `warm-v1-...` and `strict-v2-...`, each linked to its prompt version
(`museum-guide-warm-v1`, `museum-guide-strict-v2`). In my run `strict-v2` passed
**7 of 7** items (100%). `warm-v1` passed **6 of 7** (86%): it failed "Is it true the
figurehead is cursed?". The judge's reason on that row says the guide quoted
"The tale that the figurehead is cursed was invented by a 1950s ghost-walk company",
while the notes actually read "There is no truth in the story that the figurehead is
cursed; that tale was invented by a 1950s ghost-walk company". Same meaning, but the
quote was edited, so the verbatim assertion failed. It also flagged embellishments
("beautifully carved", "talented") as facts the notes never state.

Look at the individual runs behind each item too. `warm-v1` had 7 failed assertion
checks across its 21 runs (a verbatim failure on the photography, figurehead, and
carver questions, plus "adds facts" failures on several others), but the 2-of-3 policy
let most items through. `strict-v2` had none. Open a failing row to jump to the trace
with the exact prompt and answer that produced it. Run it again and the exact
failures will differ; the pattern (warm leaks, strict holds) is what to look for.

## Run it yourself

1. `cp .env.example .env` and fill in `ANTHROPIC_API_KEY`, `OPIK_API_KEY` and
   `OPIK_WORKSPACE` (or run `opik configure`).
2. `uv sync`
3. `uv run main.py` (about 1.5 minutes, around $0.20). Pass a variant name to run one:
   `uv run main.py strict-v2`.
4. Open the `anthropic-museum-guide-citations` project in Opik, then its test suite
   and the newest runs.

## Poke around

- Add a trap question the notes cannot answer ("Who paid for the restoration?") with
  the assertion "The response says the notes do not cover this". See what `warm-v1` does
  when there is nothing to quote.
- Raise the bar: change `global_execution_policy` to `{"runs_per_item": 3,
  "pass_threshold": 3}`. Flaky items that squeaked by now fail.
- Add the assertion "The response never describes the crack as damage from the rocks"
  to the bell item and watch which prompt trips it.
- Edit `strict-v2` (drop "Never fix, shorten or reword") and re-run it. Opik saves a
  new prompt version, and you can compare the two runs side by side.

## How it's put together

- `main.py` - the guide function, both prompt variants, the test suite with its assertions, and the `opik.run_tests()` calls.
- `data/curator_notes.md` - the fictional curator's notes the guide answers from.
- `pyproject.toml` - dependencies (`opik==2.2.96`, `anthropic`, `python-dotenv`).
- `.env.example` - the keys you need.

---

Part of [Opik examples](../README.md) · built with [Opik](https://github.com/comet-ml/opik) · ⭐ [star Opik](https://github.com/comet-ml/opik) if this example helped
