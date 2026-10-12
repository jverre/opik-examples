<div align="center">

# Calendar Extraction, Caught Inventing

**`pydantic-ai-calendar-extraction`**

*The calendar entry looks complete. A test suite shows which parts the model made up.*

![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat&logo=python&logoColor=white)
![Pydantic AI](https://img.shields.io/badge/pydantic--ai-2.31%2B-E92063?style=flat&logo=pydantic&logoColor=white)
[![Opik](https://img.shields.io/badge/Opik-2.2%2B-2f54eb?style=flat)](https://github.com/comet-ml/opik)
[![uv](https://img.shields.io/badge/setup-uv-DE5FE9?style=flat&logo=uv&logoColor=white)](https://docs.astral.sh/uv/)

**[What you'll build](#what-youll-build) · [See it in Opik](#see-it-in-opik) · [Run it](#run-it-yourself) · [Poke around](#poke-around)**

</div>

---

Turning an email into a calendar event is a job LLMs do well, and it hides a trap:
an entry with an end time, a time zone and a venue looks finished whether the email
said those things or the model filled the gaps. "Vendor call tomorrow at 3pm" can
become a one-hour meeting in UTC at "Virtual Meeting", and nothing in the output
tells you which parts were guesses. This example is a small command line tool built
on Pydantic AI that extracts a typed `CalendarEvent` from seven messy fictional
emails. Opik traces every extraction over OpenTelemetry, and a test suite of
plain-language assertions catches the invented values.

## What you'll build

A CLI with two subcommands, split into small modules:

- `extract <file>` runs the agent on one or more emails and prints the typed result.
- `suite` runs the whole corpus through an Opik test suite and prints a pass rate.

The agent is a Pydantic AI `Agent` on `gpt-4o-mini` whose output type is a union,
`CalendarEvent | NoEvent`, so a vague "coffee sometime next week?" can be answered
with a typed "there is no event here" instead of a made-up date. `CalendarEvent` has
nine fields, most of them optional: title, date, start and end time, all-day flag,
time zone, location, meeting link and attendees. The agent has two system prompts.
The `strict` prompt says that unstated fields are null. The `eager` prompt sounds
reasonable ("calendar entries should be complete, so never leave a field empty") and
quietly asks the model to invent. Pass `--prompt eager` to use it.

Tracing uses Pydantic AI's documented path, not decorators on the model call:
logfire instruments the agent, and Opik's `OpikSpanProcessor` ships the
OpenTelemetry spans to Opik's OTLP endpoint. One `@opik.track` function,
`extract_event`, wraps each call so the OTel spans nest into a single trace.

The suite has seven items, one per email in `data/emails/`: a clean invite, a
"tomorrow at 3pm" with nothing else, an all-day offsite with the venue still TBD, a
reschedule buried in a quoted thread, a dinner with a Lisbon signature but no time
zone, a vague coffee request, and a call with a dial-in, a Teams link and an
attendee who is out. Four global assertions state the rules every extraction must
follow (valid shape, every value derivable from the email, nothing invented, ISO
dates and 24-hour times). Each item adds one to four assertions of its own, such as
"the end time, time zone, location and meeting link are all null because the email
gives none of them". An LLM judge checks each assertion. The suite's execution
policy runs every email three times and requires two passes, because judges are noisy.

## See it in Opik

Open the project `pydantic-ai-calendar-extraction` on Opik Cloud.

**Traces.** The `extract` runs from step 3 below appear as traces named
`extract_event`, tagged `prompt:strict`. Expand one: `extract_event` contains
`invoke_agent event_extractor`, which contains `chat gpt-4o-mini` (type `llm`) with
about 550 tokens and an estimated cost of roughly $0.00013. Those inner spans come
from OpenTelemetry, not from decorators in this repo. The input is the raw email. For
`02-vendor-call.txt` the output has `start_time` `15:00` and `end_time`, `timezone`,
`location` and `meeting_link` all `null`.

**Test suite.** Under Test Suites, `pydantic-ai-calendar-extraction` holds seven items
with their global and per-item assertions and a 3-runs, pass-2 execution policy.
Each `suite` command creates an experiment: `calendar-extraction-strict-gpt-4o-mini`
and `calendar-extraction-eager-gpt-4o-mini`, each with 21 runs (7 emails x 3).

**The comparison.** In our verified run `strict` passed 7 of 7 emails (21 of 21 runs)
and `eager` passed 3 of 7. Open the `eager` experiment and read the failed rows:

- The vendor call came back as 15:00 to 16:00, zone `UTC`, location `Virtual Meeting`.
  The email gives none of the three, and the judge says so.
- The dinner got a 21:00 end time, and the venue picked up a ", Lisboa" suffix from the signature.
- The all-day offsite got the zone `GMT`.
- The planning call got a 15:00 end time that was never stated.

The judge's reason is attached to each failed assertion. The coffee email and the
clean invite pass under both prompts, because the model still answers `NoEvent` for
the first and the second states everything. The reschedule email passed 2 of 3 runs,
so it counts as a pass but shows the model wobbling. Results move between runs: an
earlier `eager` run passed 2 of 7, and during development `strict` once dropped to 5
of 7 until a too-literal assertion ("the location is Fjord 2" against a model that
wrote "room Fjord 2 on the second floor") was reworded.

Each experiment also leaves one `evaluation_task` trace per run in the same project.
Inside you find the `extract_event` spans and the judge's `llm_judge` and `completion`
spans, so you can click from a failed assertion to the exact model call
behind it.

## Run it yourself

1. `cp .env.example .env` and set `OPENAI_API_KEY`. Opik credentials come from
   `~/.opik.config` after `opik configure`, or set `OPIK_API_KEY` and
   `OPIK_WORKSPACE` in `.env` (add `OPIK_URL_OVERRIDE` if you self-host).
2. `uv sync`
3. `uv run calendar-extraction extract data/emails/02-vendor-call.txt data/emails/07-planning-call.txt`
4. `uv run calendar-extraction suite`
5. `uv run calendar-extraction suite --prompt eager`
6. Open the `pydantic-ai-calendar-extraction` project in Opik: Traces for the
   extractions, Test Suites for the suite, and Experiments for the two runs (the
   experiment links are printed at the end of steps 4 and 5).

The whole sequence took under two minutes and about two cents in gpt-4o-mini calls
(agent and judge). Each `suite` run prints the pass rate, one line per email with how
many of its 3 runs passed, and for every failing email its output and the judge's reason.

## Poke around

- Run `suite` and `suite --prompt eager` back to back and compare the two experiments
  in Opik. The only difference is one sentence in the system prompt.
- Add your own worst email to `data/emails/`, then add it to `ITEM_ASSERTIONS` in
  `calendar_extraction/suite.py` with one or two plain-language assertions. Inserts are
  deduplicated, so re-runs add only the new item. Rewording an existing assertion
  creates a new item, so delete the old one in the Opik UI.
- Run `suite --runs 1`. With one run per email the pass rate gets noisier, because the
  model and the judge both vary. That is why the default is three runs, pass two.
- Change `MODEL` in `calendar_extraction/__init__.py` to another cheap model and see
  how much it invents under the `eager` prompt.

## How it's put together

- `calendar_extraction/models.py`: the `CalendarEvent` and `NoEvent` Pydantic models.
- `calendar_extraction/agent.py`: the two system prompts, the Pydantic AI agent, and the traced `extract_event` function.
- `calendar_extraction/tracing.py`: logfire plus `OpikSpanProcessor`, with the OTLP endpoint and headers built from environment variables at run time.
- `calendar_extraction/suite.py`: the global and per-email assertions, and `run_suite` (get or create the test suite, insert items, `opik.run_tests`).
- `calendar_extraction/cli.py`: the `extract` and `suite` subcommands.
- `data/emails/`: seven fictional emails with headers, quoted threads and gaps.

---

Part of [Opik Integration Examples](../README.md) · built with [Opik](https://github.com/comet-ml/opik) · ⭐ [star Opik](https://github.com/comet-ml/opik) if this example helped
