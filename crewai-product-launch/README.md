<div align="center">

# Launch Plan Crew, Costed Per Agent

**`crewai-product-launch`**

*Three CrewAI agents write one launch plan. One Opik trace shows what each agent cost.*

![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat&logo=python&logoColor=white)
![CrewAI](https://img.shields.io/badge/crewai-1.15%2B-FF5A50?style=flat&logo=crewai&logoColor=white)
[![Opik](https://img.shields.io/badge/Opik-2.2%2B-2f54eb?style=flat)](https://github.com/comet-ml/opik)
[![uv](https://img.shields.io/badge/setup-uv-DE5FE9?style=flat&logo=uv&logoColor=white)](https://docs.astral.sh/uv/)

**[What you'll build](#what-youll-build) · [See it in Opik](#see-it-in-opik) · [Run it](#run-it-yourself) · [Poke around](#poke-around)**

</div>

---

A crew of agents hands you one finished document, and the document hides its own bill. You cannot tell which agent wrote which part, how much context each one was fed, or which one used most of the tokens. This example is a three-agent CrewAI crew that writes a 90-day launch plan for Fernwick Glide, a fictional folding electric scooter. A single call to `track_crewai` turns each `kickoff` into one Opik trace in which every task, agent and LLM call is a span, with token usage and an estimated dollar cost on each LLM call. A short script then rolls those spans up into a cost table per agent.

## What you'll build

A market analyst, a messaging strategist and a launch planner, run as a sequential CrewAI crew on `gpt-4o-mini`. The analyst works from a fictional launch file, `data/product_brief.md`, instead of a search tool, so the run is offline, needs only an OpenAI key, and takes about 20 seconds. Each task feeds the next: analysis, then positioning, then a 90-day plan with a budget split. `track_crewai(project_name=..., crew=crew)` is the only Opik call in `main.py`. After the crew finishes, `cost_report.py` reads the new trace back from Opik, walks every LLM span up to its agent span, and prints tokens and dollars per agent.

## See it in Opik

Open the **`crewai-product-launch`** project and the **Traces** tab. After the documented run there is one trace, named `kickoff`, with 49 spans. Its input is the whole launch file and its output is the finished plan. The trace row itself shows the totals for the run: 3,556 tokens and about $0.00094.

Expand the trace. The tree mirrors the crew: a span per task (`Task: Analyze the market`, `Task: Write the positioning`, `Task: Plan the 90-day launch`), inside each one a span named after the agent (`Market Analyst`, `Messaging Strategist`, `Launch Planner`), and inside that the agent's reasoning loop, which ends in one `chat_completion_create` span. Those are the only three spans of type `llm`, and each shows its model (`gpt-4o-mini-2024-07-18`), prompt and completion token counts and its estimated cost. In the run behind this README the three agents came out as:

| agent | prompt tokens | completion tokens | total | cost |
|---|---|---|---|---|
| Market Analyst | 797 | 268 | 1,065 | $0.00028 |
| Messaging Strategist | 443 | 291 | 734 | $0.00024 |
| Launch Planner | 1,414 | 343 | 1,757 | $0.00042 |

The launch planner is the most expensive agent (about 45% of the bill) even though it writes the shortest output, because it reads the analysis, the positioning and the launch file again for its budget numbers. The strategist is the cheapest. The same table is printed at the end of the run by `cost_report.py`, so you can compare the console to the spans.

Open the planner's `chat_completion_create` span to read its exact prompt. You will see why a plan can look confident and still be loose: in this run the table balances to $180,000 only because a $59,500 "contingencies" row fills the gap. Reading the input and output of the span that wrote it is how you catch that.

## Run it yourself

1. `cp .env.example .env` and add your `OPENAI_API_KEY` and Opik credentials (skip the Opik lines if you already ran `opik configure`).
2. `uv sync`
3. `uv run main.py`
4. Open the `crewai-product-launch` project in Opik, open the newest `kickoff` trace and expand it.

The run prints the plan, then the per-agent cost table. One run costs under $0.001.

## Poke around

- Give only the launch planner a bigger model (`llm="gpt-4o"` on that agent) and run again. The new trace shows the planner's cost jump while the other two agents stay put, so you can price a quality upgrade at one step.
- Delete `{launch_file}` from `plan_task` and run again. The planner's prompt gets about 800 tokens shorter, and it no longer has the channel costs in front of it. Compare the two spans and check whether the budget table still uses real prices.
- Edit `data/product_brief.md` (change the budget to $60,000) and re-run. Follow the change from the analyst's span through the positioning to the plan.
- Add a fourth agent, such as a pricing strategist, with its own task and add it to `AGENT_ROLES` in `cost_report.py`. The trace grows a branch and the table gains a row, with no other Opik changes.

## How it's put together

- `main.py` - the crew: three agents, three sequential tasks, the `track_crewai` call, and the flush before the report.
- `cost_report.py` - reads the newest trace from Opik and sums tokens and cost per agent.
- `data/product_brief.md` - the fictional launch file the agents work from.
- `pyproject.toml` - dependencies, with `opik` pinned to 2.2.96.
- `.env.example` - the keys the example needs.
