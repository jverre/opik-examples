# Insurance Claims Triage with Handoffs

**`openai-agents-insurance-claims`**

*One front desk, three specialists: see which agent decided what, and which tool call decided the payout.*

A claims desk fails in a quiet way: the customer is told "covered" or "not covered" and nobody can say which agent made the call, from which policy line, on what tool result. A branch that falls on a car in a garage is the classic case, because both the auto and the home policy list "falling object", and the answer depends on who gets the claim. This example is a small claims desk on the OpenAI Agents SDK. A triage agent hands claims to an auto, home, or pet specialist. Each specialist assesses coverage against a fictional policy file, asks the customer to confirm, then files the claim. With one line of Opik setup, every turn becomes a trace where handoffs, agent turns, tool calls, and one input guardrail are laid out as a tree, and each conversation becomes a thread.

## What you'll build

Four agents on `gpt-4o-mini`: a **Triage Agent** that only routes, plus **Auto**, **Home**, and **Pet Claims Agents**. Each specialist owns one assess tool (`assess_auto_claim`, `assess_home_claim`, `assess_pet_claim`) and a shared `file_claim`. Specialists can also hand a claim back to triage, which is what makes a mid-conversation re-route possible. The tools read `data/policies.json` (three fictional policyholders), so no insurance API and no extra keys are needed. A rule-based input guardrail on the triage agent refuses requests to backdate cover.

Tracing is the documented one-liner, `set_trace_processors([OpikTracingProcessor()])`. Each scripted conversation runs its turns inside `trace(group_id=...)`, and Opik uses the `group_id` as the thread id. Follow-up turns resume with whichever agent answered last, so a thread mixes turns that start at triage with turns that skip it. The demo plays five conversations (eight turns) with no human input.

```
claim -> Triage Agent (guardrail) -> handoff -> Auto/Home/Pet agent -> assess tool -> "confirm?"
confirm -> same specialist -> file_claim -> claim number
```

## See it in Opik

Open the `openai-agents-insurance-claims` project. The Traces tab holds 8 traces, all named `Claims desk`, and the Threads tab holds 5 threads: `fender-bender-...`, `branch-on-the-car-...` (3 turns), `biscuit-teeth-...`, `kitchen-leak-...`, and `backdate-...`. The suffix is random per run.

Open the first trace of the `branch-on-the-car` thread and expand it. Under `Task`, the `Triage Agent` span holds a `no_backdating` span, one `Response` LLM span, and a `Handoff`. Then the `Auto Claims Agent` span holds an `assess_auto_claim` tool span. Click it: the model chose `{"policy_id":"POL-7001","incident_type":"falling_object","estimated_cost_usd":3200}` and the tool returned `{"covered": true, "deductible_usd": 500, "estimated_payout_usd": 2700.0}`. The branch landed on a car in the driveway, so auto paid.

Now open the second trace of that thread, where the customer says the car was inside the garage and asks for a home claim. The tree now reads `Auto Claims Agent`, `Handoff`, `Triage Agent`, `Handoff`, `Home Claims Agent`: the auto specialist handed the claim back to triage, which handed it to the home specialist. Its `assess_home_claim` span returns `deductible_usd: 1000, estimated_payout_usd: 2200.0`. Same $3,200 repair, same peril, a $500 lower payout, because the line changed. The third trace is a bare `Home Claims Agent` turn that calls `file_claim` and returns `CLM-0ABAE1` (the claim number differs on every run). That whole story is in one thread, in order.

The denials are just as readable. In `biscuit-teeth` the `assess_pet_claim` span returns `{"covered": false, "reason": "'dental disease' is a pre-existing condition"}` and the agent never calls `file_claim`. In `kitchen-leak` the `assess_home_claim` span returns "water_damage is not in the covered perils ['fire', 'storm', 'theft']". The LLM span after each tool call shows how the model phrased the denial, so you can check that the wording matches the tool result.

The `backdate` trace is the guardrail case: a single `Triage Agent` span with a `no_backdating` span, no LLM call at all, and no input or output on the trace. The run raises `InputGuardrailTripwireTriggered`, the demo prints `matched: ['backdate', 'before i bought']`, and nothing is spent. In Opik 2.2.96 the guardrail span is logged with type `tool`, not `guardrail`, and its input and output are empty. The tripwire result only shows in your console.

Cost: every `Response` span is typed `llm` with the model `gpt-4o-mini-2024-07-18`, token usage, and an estimated cost between about $0.00004 (a routing call) and $0.00014 (a filing call). Turns cost $0.0002 to $0.0004 each, and the whole demo costs under $0.002. The trace list's cost column shows the re-route turn (Auto, triage, Home, three LLM calls) at about $0.00039, roughly double a plain filing turn.

## Run it yourself

1. `cp .env.example .env` and fill in `OPENAI_API_KEY`, `OPIK_API_KEY`, and `OPIK_WORKSPACE`.
2. `uv sync`
3. `uv run main.py` (about 25 seconds)
4. Open the `openai-agents-insurance-claims` project in Opik, then the Traces and Threads tabs.

The project name is set in `main.py`, so traces land there regardless of your default project. Model output varies a little between runs, so your numbers and wording may differ from the ones above.

## Poke around

- Change the branch claim to a driveway claim for `POL-7003` (auto only, no `falling_object` cover) and watch the assess span return `covered: false`. Then try `POL-7001` with "tree fell on the shed" and see which specialist triage picks when neither line is obvious.
- Remove `"falling_object"` from the home policy in `data/policies.json` and replay the `branch-on-the-car` conversation. The re-route will still happen, but the home assess span will deny it, and the thread shows how the customer got there.
- Delete the sentence "never say you are transferring them" from `COMMON` in `main.py`. With gpt-4o-mini, a specialist can echo the handoff message ("I've transferred you...") instead of working, which costs the customer a turn. In the trace the specialist's first `Response` span has no tool call after it, and that is how you spot it.
- Add a fourth specialist (a `Travel Claims Agent` with its own assess tool) and confirm the new handoff shows up in the trace with no tracing changes.

## How it's put together

- `main.py` is the whole app: tools, the guardrail, four agents, and the scripted conversations with thread grouping.
- `data/policies.json` holds three fictional policyholders with auto, home, and pet cover, deductibles, covered perils, and pre-existing conditions.
- `pyproject.toml` pins `opik==2.2.96` and requires Python 3.12 or 3.13.
- `.env.example` lists the keys the example needs.
