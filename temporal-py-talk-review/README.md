# Durable Talk Review on Temporal (Python)

**`temporal-py-talk-review`**

*One trace across two OS processes: the client, the workflow, a failed attempt with its error, and both LLM calls.*

Reviewing conference talk submissions is a slow, flaky pipeline. A model reads each abstract, a calendar service is asked whether the speaker can actually make the date, the committee's review window has to elapse, and then a model writes the verdict. Any step can fail halfway, and the calendar service is the one that does. Temporal solves the reliability half: each step is an activity that is persisted and retried, so a dropped connection never repeats a completed LLM call. But it splits execution across processes, with a client starting the workflow and a worker somewhere else running it, so no single process has seen the whole story. This example wires Temporal's Python OpenTelemetry interceptor to Opik so each review becomes one trace holding the client's spans, the worker's spans, the failed calendar attempt, and the token cost of every model call.

## What you'll build

A `ReviewTalk` workflow with three activities on `gpt-4o-mini`:

1. `analyze_abstract` (LLM) reads a talk abstract and returns its level, its concrete claims, and its red flags.
2. `check_speaker_availability` looks the speaker up in a canned calendar. It raises a `ConnectionError` on its first attempt, on purpose, so Temporal has to retry it.
3. `write_review` (LLM) turns the analysis and the availability into an accept, waitlist, or decline note.

Between steps 2 and 3 the workflow sleeps on a durable 2 second timer, standing in for the committee's review window.

The demo is one command. It starts a local Temporal dev server on port 7400, spawns the worker as a separate OS process, and acts as the client for two fictional submissions in `data/submissions.json`: a solid Postgres migration talk and a buzzword-only observability talk whose speaker is double-booked. Both processes export OTLP spans straight to Opik's OpenTelemetry endpoint, and Temporal's `TracingInterceptor` carries the trace context between them in Temporal's own headers.

```
demo (client process)                    worker (separate process)
  review:TLK-201
    StartWorkflow ──[trace context]──▶  RunWorkflow
                                          analyze_abstract > check_speaker_availability (fails, retried) > write_review
```

## See it in Opik

Open the `temporal-py-talk-review` project in Opik. The Traces tab holds two traces, `review:TLK-201` and `review:TLK-202`, each with 13 spans. Click `review:TLK-201` and expand the tree.

- The root `review:TLK-201` span and `StartWorkflow:ReviewTalk` come from the client process. Everything under `RunWorkflow:ReviewTalk` was exported by the worker process, a different OS process, and still hangs off the same trace.
- Each activity has a `StartActivity:<name>` span (the workflow scheduling it) and a `RunActivity:<name>` span per attempt. `check_speaker_availability` has **two** `RunActivity` spans. The first carries an error, `ConnectionError: speaker-calendar service unavailable: connection reset (transient, succeeds on retry)`, and the second is clean, about one second later (3.364 s vs 2.352 s from the start of the trace in the verified run, matching the 1 second initial retry interval).
- `analyze-abstract` and `write-review` are `llm` spans nested under their `RunActivity` spans, with model `gpt-4o-mini-2024-07-18`, prompt and response in the input and output, and token usage (for example 223 prompt and 134 completion tokens for `analyze-abstract` on TLK-201). Opik turns that into cost: about $0.00011 for the first LLM span and $0.00009 for the second, $0.0002 for the whole trace.
- Open `review:TLK-202` to see the same shape with a different outcome: the model flags the abstract as all red flags and the speaker is double-booked in Lisbon, so the final span's output is a `decline`.

Honest notes on what you will and will not see:

- The failed attempt is an error on the `RunActivity` span, not on the trace. The trace itself is not marked as errored because the workflow succeeded, which is exactly the point of retries. Filter spans on errors to find degrading dependencies.
- Cost works through the OTel `gen_ai.*` attributes set in `activities.py` (`gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`). Without them Opik shows a general span and no cost.
- The workflow's `sleep` timer is not a span. You can see it as the gap between `check_speaker_availability` and `write_review`.
- The worker also logs the activity traceback to stderr when attempt 1 fails. That noise in the demo output is Temporal reporting the planted failure, not a bug.

## Run it yourself

The demo starts its own Temporal dev server (the Python SDK downloads the binary on first run), so you only need Python 3.12+ and `uv`.

1. `cd temporal-py-talk-review && cp .env.example .env` and fill in `OPENAI_API_KEY`, `OPIK_API_KEY`, and `OPIK_WORKSPACE`.
2. `uv run talk-review`
3. Open the `temporal-py-talk-review` project in Opik and click the newest trace.

A full run takes about 20 to 35 seconds and costs well under a cent. To use your own Temporal server instead, start `uv run python -m talk_review.worker` with `TEMPORAL_ADDRESS` set and start `ReviewTalk` on the `talk-reviews` task queue from a client that uses the same `TracingInterceptor`.

## Poke around

- Make the flakiness worse: in `talk_review/activities.py` change `attempt == 1` to `attempt <= 3` and watch four `RunActivity:check_speaker_availability` spans appear, three red and one green, with the backoff gaps visible on the timeline.
- Change the retry policy in `talk_review/workflows.py` (try `backoff_coefficient=4.0`) and measure the gap between attempts on the trace timeline.
- Double-register the interceptor: pass `interceptors=[interceptor]` to `Worker(...)` in `worker.py`. The worker already inherits the client's interceptor, so every workflow and activity span is recorded twice. Seeing 22 spans instead of 13 is a good way to learn how the context propagation works.
- Edit `data/submissions.json`: give a third talk a real abstract but an unavailable speaker, and check the model returns `waitlist` and says why in the `write-review` span.

## How it's put together

- `talk_review/demo.py`: self-contained entry point (`uv run talk-review`): dev server, worker subprocess, two client runs.
- `talk_review/worker.py`: the worker process, which connects with the tracing interceptor and registers the workflow and activities.
- `talk_review/workflows.py`: the durable `ReviewTalk` workflow with the retry policy and the timer.
- `talk_review/activities.py`: the three activities, the OTel-traced OpenAI calls, and the planted transient failure.
- `talk_review/tracing.py`: the OTLP exporter pointed at Opik, shared by both processes.
- `talk_review/models.py`: dataclasses passed between client, workflow, and activities.
- `talk_review/settings.py`: env loading, task queue, and model name.
- `data/submissions.json`: the two fictional talk submissions.
