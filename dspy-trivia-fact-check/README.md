<div align="center">

# DSPy Trivia Fact-Check

**`dspy-trivia-fact-check`**

*The same eight claims, the same test suite: the raw program passes 0 of 8, the compiled one passes 8 of 8.*

![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat&logo=python&logoColor=white)
![DSPy](https://img.shields.io/badge/DSPy-3.4.0-8B0000?style=flat)
[![Opik](https://img.shields.io/badge/Opik-2.2.96-2f54eb?style=flat)](https://github.com/comet-ml/opik)
[![uv](https://img.shields.io/badge/setup-uv-DE5FE9?style=flat&logo=uv&logoColor=white)](https://docs.astral.sh/uv/)

**[What you'll build](#what-youll-build) · [See it in Opik](#see-it-in-opik) · [Run it](#run-it-yourself) · [Poke around](#poke-around) · [How it's put together](#how-its-put-together)**

</div>

---

A fact-checker that answers correctly is not the same as one that answers in a form something downstream can use. Here the checker rules on trivia claims about a made-up science almanac, and the team wants every ruling as `VERDICT | ref: ID | reason`, for example `FALSE | ref: GEO-1 | The Karrow Ridge was raised by volcanic uplift.` Nothing in the program's instructions says so. The raw model knows the answers and says `False` or `The claim is false.`, which a parser cannot use and a reader cannot audit. DSPy's `BootstrapFewShot` finds the convention from a few worked rulings and bakes it into the prompt. Opik runs one test suite against both versions, so the improvement is a number, and the demos that caused it are visible in the trace.

## What you'll build

A single script, `main.py`, with a `dspy.ChainOfThought` program on `gpt-4o-mini`. It gets a twelve-entry offline reference corpus (`data/reference_corpus.md`, the fictional "Halden Almanac") and one claim, and returns a ruling. The signature says only "Fact-check the claim against the reference corpus": it never names the three verdicts (`TRUE`, `FALSE`, `UNVERIFIABLE`), the `ref:` citation, or the one-line shape.

An Opik test suite holds eight held-out claims (three TRUE, three FALSE, two UNVERIFIABLE). Three global assertions check the format and the citation, and each item adds an assertion for the expected verdict and the corpus entry it must cite. The suite runs every item 3 times and requires 2 passes. The script runs it once on the raw program, compiles with `BootstrapFewShot` against nine answered claims (a purely programmatic metric, so compiling spends no judge tokens), then runs the identical suite on the compiled program. One `OpikCallback` traces every DSPy call.

```
raw program ──────► suite run "dspy-uncompiled"   0 / 8 items pass
      │ BootstrapFewShot (4 bootstrapped + 4 labeled demos from 9 claims)
compiled program ─► suite run "dspy-compiled"    8 / 8 items pass
```

## See it in Opik

Open the `dspy-trivia-fact-check` project. The Traces tab holds 53 traces from one run: 48 named `evaluation_task` (2 runs of the suite x 8 claims x 3 repeats) and 5 named `ChainOfThought` (your one-off demo question plus the 4 teacher attempts that `BootstrapFewShot` kept as demos). Open an `evaluation_task` trace. The tree shows `task` at the top, then `ChainOfThought`, then `Predict`, then `LM: openai - gpt-4o-mini` as the actual model call with its tokens and cost. That is the DSPy module graph, nested the way the program is built. Next to it is a `metrics_calculation` span with the judge's `llm_judge` span and its `completion` call, which shows what the assertions cost.

Now compare the two kinds of trace. In an uncompiled trace the `LM` span input is about 770 prompt tokens: the corpus, the claim, and no examples. In a compiled trace it is about 4,730 prompt tokens, because the prompt now carries eight worked rulings, four of them with the reasoning the teacher wrote. The compiled prompt is not a pickle file or a hidden artifact. It is right there, and you can diff it against the version before it.

Open the Experiments page. Two experiments, `dspy-uncompiled` and `dspy-compiled`, both on the dataset `dspy-trivia-fact-check-suite`, each with 24 samples (8 items x 3 repeats). In the verified run, the pass rate was 0% for the uncompiled run and 100% for the compiled one. Open an uncompiled item and look at the outputs: `False`, `The claim is true.`, `Insufficient evidence to confirm or deny the claim.` The model was often right, but the format and citation assertions failed on all 24 runs, and the UNVERIFIABLE items ran into the same wall (the model wrote prose like "Insufficient information", never the word `UNVERIFIABLE`). In the compiled run the same claims give `FALSE | ref: GEO-2 | Lake Orrin never freezes due to hot springs feeding it from below.` and `UNVERIFIABLE | ref: none | The corpus does not mention the lifespan of Tidewater crabs.` All three global assertions pass 24 of 24. Nothing in the signature changed.

One caveat on reading this honestly. The assertions are checked by an LLM judge, and the model samples at the default temperature, so a re-run can land an item lower. That is what the 3-runs, 2-to-pass policy is for. Expect the uncompiled side at 0% every time and the compiled side at or near 100%; one item missing is 88%.

The last lines of the console output of the verified run:

```
=== Uncompiled vs compiled ===
uncompiled: 0% pass rate (0/8 items passed)
compiled  : 100% pass rate (8/8 items passed)
```

## Run it yourself

1. `cp .env.example .env`, then fill in `OPENAI_API_KEY` and your Opik settings (`OPIK_API_KEY`, `OPIK_WORKSPACE`), or run `opik configure` once.
2. `uv sync`
3. `uv run main.py`
4. Open the `dspy-trivia-fact-check` project in Opik, then its Experiments tab.

A full run takes about two minutes and costs about three cents on `gpt-4o-mini`, judge calls included.

## Poke around

- Remove the `ref: none` convention for UNVERIFIABLE from the trainset (give every demo a real entry id) and recompile. The format assertion still passes on TRUE and FALSE, but watch what the two UNVERIFIABLE items do.
- Set `max_bootstrapped_demos=1` and `max_labeled_demos=1`. One demo is enough to teach the shape, but see whether it is enough to teach the `none` ref.
- In the trainset, put the two UNVERIFIABLE claims last. The optimizer stops collecting demos after four passing attempts, so the compiled program may never see one, and the verdict falls back to `UNKNOWN`. Order matters.
- Open a `ChainOfThought` trace with no suite around it: those are the teacher attempts the demos were harvested from, reasoning included.

## How it's put together

- `main.py`: the signature, the program, the trainset and the compile metric, the test suite, and the uncompiled-then-compiled runs.
- `data/reference_corpus.md`: the twelve fictional almanac entries the checker reads, each tagged `[ID]`.
- `data/claims.json`: nine answered training claims and the eight held-out test claims with their expected verdict and citation.
- `pyproject.toml`: pins `opik==2.2.96` and `dspy==3.4.0`.
- `.env.example`: the keys you need.
