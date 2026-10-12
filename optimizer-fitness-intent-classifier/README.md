# optimizer-fitness-intent-classifier

*An optimizer rewrites a first-draft intent classifier prompt, and a held-out set checks that the gain is real.*

Most prompts are improved the same way: someone squints at a few bad outputs, edits the wording, eyeballs two or three replies, and declares it better. There is no score, no record of what was tried, and no way to tell a real gain from luck. Prompt optimization replaces that loop with a measured one: a labeled dataset, a metric, and an algorithm that proposes candidate prompts and keeps what scores higher. This example hands a deliberately plain intent classifier for a fictional fitness app to Opik's `MetaPromptOptimizer` with a small fixed budget, plots the score across every trial, and then scores the baseline and the winner on messages the optimizer never saw.

## What you'll build

One script that routes in-app messages for Stridewell, a fictional fitness coaching app, into five intents: `log_workout`, `change_plan`, `injury_concern`, `billing`, `sync_issue`. The starting prompt names the intents but never says "answer with only the label", so gpt-4o-mini replies "The intent of the message is: change_plan." and exact-match accuracy is 0.00. Many messages are also deliberately two-intent ("Charged twice for Plus and the watch sync is also broken"), and the labels follow house rules the prompt does not know (see the docstring in `messages.py`).

The script uploads two datasets, 20 train messages and 10 validation messages, and runs the optimizer on train only:

```
baseline prompt -> score on 20 train messages -> reasoning model proposes 4 candidates per round
      -> keep the best -> repeat (at most 8 trials)
      -> score baseline and winner on the 10 validation messages
      -> save the winner to the prompt library as version 2
```

The classifier is gpt-4o-mini at temperature 0, the reasoning model is gpt-4.1-mini, and the whole run takes about a minute and a half and costs about one cent.

## See it in Opik

Open the run link the script prints at the end (it is pinned to the project, because `get_run_link()` opens in whatever project the UI last had active and can look empty). It lands on the **Optimization runs** view for `optimizer-fitness-intent-classifier-train` in the project `optimizer-fitness-intent-classifier`. You will see the score chart: the baseline at 0.00, then eight trials. In the run that this README describes the trials scored 0.70, 0.65, 0.65, 0.60, 0.75, 0.70, 0.65 and 0.60, so the best was 0.75 at trial 5. Click any point to read the exact prompt it evaluated and its per-message results. The drop from 0.00 to 0.70 is the optimizer discovering the output contract ("respond ONLY with the exact intent label"); everything after that is the search fumbling for the two-intent rules, and the flat, noisy plateau is the honest picture of that.

The optimizer did not learn the house rules. Its winner still misses about a quarter of the train messages, and the misses are two-intent messages: it sometimes answers with two labels ("log_workout, sync_issue") or picks the wrong one (a cancellation request that mentions a torn calf comes back as `billing`, where the house rule says pain wins). That is a real limit worth seeing: an optimizer fixes what the scores and a handful of examples make visible. It will not invent a business rule that 20 messages only hint at.

Open the **Experiments** tab next. Besides the trial experiments there are two more on the `-validation` dataset, tagged `baseline` and `winner`: 0.00 and 0.70. These 10 messages never reached the optimizer, so 0.70 is a fair estimate of how the winner behaves on new traffic. They are deliberately kept out of the run's trial chart. With 10 messages one miss moves the score by 0.1, so treat it as a sanity check, not a benchmark.

Open the **Prompts** library and find `optimizer-fitness-intent-classifier-prompt`. Version 1 is the baseline, version 2 is the winner, and the diff is the lesson: the optimizer wrote down the output contract the baseline left implicit.

The **Traces** tab of the project holds 202 traces: 200 `evaluation_task` traces (one per message per scored prompt, each with an `llm` span for the gpt-4o-mini call with token usage and cost, and an `intent_accuracy` feedback score of 0 or 1) and 2 `optimization_algorithm` traces from the reasoning model. Filter the feedback score to 0 and read the baseline's sentence-shaped answers next to the labels it should have given.

## Run it yourself

1. `cp .env.example .env` and add your OpenAI key and Opik credentials (or export them in your shell).
2. `uv sync`
3. `uv run main.py` (about 90 seconds, about one cent). Your exact scores will differ a little: the optimizer's search follows the failures it happens to see.
4. Follow the "optimization run" link the script prints, then check the Experiments and Prompts tabs.

## Poke around

- Open the worst trial (0.60) and read its prompt. Seeing what did not work teaches more than the winner.
- Paste the priority rule from the `messages.py` docstring into `BASELINE_SYSTEM` and re-run: a quick check outside Opik put that prompt at 16 of 20 on train and 9 of 10 on validation with no optimization at all. Optimization finds wording, you still supply the policy.
- Set `MAX_TRIALS = 3` and see how much of the gain survives. Almost all of it comes from the first trial.
- Add five `billing` messages to `TRAIN` in `messages.py` and see whether the optimizer starts to quote them in the prompt as examples (and whether validation agrees that this helps).

## How it's put together

- `main.py`: dataset upload, the exact-match metric, the baseline prompt, the bounded optimizer run, the score-curve printout, the held-out validation check, and the prompt-library save.
- `messages.py`: 30 labeled messages (20 train, 10 validation) and the house rules behind the labels.
- `pyproject.toml`: pins `opik==2.2.96` and `opik-optimizer==3.2.0` (Python 3.12 or 3.13).
- `.env.example`: the keys the run needs.

## Notes from building this

- The optimizer evaluates validation experiments under its current optimization id, which would put them in the run's trial chart. `main.py` clears `optimizer.current_optimization_id` before the held-out scoring to avoid that. It is an internal attribute, so it may change in a later release.
- `main.py` does not pass `validation_dataset=` to the optimizer: when you do, `MetaPromptOptimizer` ranks its candidates on that set, so it would no longer be unseen. The held-out check is done by hand with `optimizer.evaluate_prompt` instead.
- `result.llm_cost_total` came back empty, so the cost above is the sum of `total_estimated_cost` over the project's `llm` spans.
- The optimizer sometimes pastes the `{message}` placeholder into the system prompt (as in the winner here). It still works because the user turn also carries the message, and `main.py` converts `{message}` to the library's `{{message}}` when saving.
