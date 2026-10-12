# langgraph-wildlife-survey-team

A planner, four looping field researchers and a writer produce a wildlife survey report, and one Opik trace shows the loop and what each agent cost.

When a team of agents writes a bad report, the mistake could be in the plan, in any one research pass, or in the write-up, and the report text alone does not say which. This example is a three-agent LangGraph team for Marrow Fen Reserve, a fictional nature reserve. It works from an offline corpus of fictional field notes. Traced with Opik, one run is one deep trace in which every agent pass is a span, the research loop is drawn in the agent graph view, and every agent's cost is a number you can read off the spans.

## What you'll build

- A `planner` that uses structured output to split one question ("Which species should get protection priority next season?") into exactly four sub-questions.
- A `field_researcher` that answers one sub-question per pass from the top three matching sections of five field-note files in `data/` (north fen transects, kestrel ridge raptor watch, Cold Spring Creek, trail cameras, survey protocols). Search is a small rarity-weighted keyword match, so there is no web and no vector store.
- A conditional edge (`route_research`) that loops the researcher until every sub-question has a finding, then hands off to the `writer`, which composes a survey report with a ranked priority list and next-season actions.
- All three agents run `gpt-4o-mini`. The compiled graph is wrapped once with `track_langgraph` and an `OpikTracer`, so every invocation is logged automatically with the graph structure attached.
- `costs.py`, which reads the finished trace back from Opik and prints tokens and cost per agent.

```
planner --> field_researcher --+
                ^              |  more sub-questions? loop
                +--------------+  all answered? --> writer --> report
```

## See it in Opik

Open the `langgraph-wildlife-survey-team` project (Traces tab). After one run it holds one trace, named `LangGraph`, tagged `wildlife-survey`, which took about 17 seconds. The trace has 18 spans: 6 of type `llm` (all `ChatOpenAI`, model `gpt-4o-mini-2024-07-18`) and 12 of type `general`. The `general` spans are one `planner`, four `field_researcher` passes, one `writer`, four `route_research` spans (the conditional edge firing after each pass), and the `RunnableSequence` and `RunnableLambda` spans LangChain adds around the planner's structured output.

Open the trace and look at the agent graph panel: it draws `planner`, `field_researcher` and `writer`, with the arrow from `field_researcher` back to itself that is the loop. The trace's metadata carries the `_opik_graph_definition` that makes this view possible. The tree beneath it shows the loop as four sibling `field_researcher` spans. Each one has the full `question`, `sub_questions` and `findings` state as input, and its own `ChatOpenAI` child with the exact excerpts it was given and its answer. In this run the planner asked, for example, about "population trends of bird species observed in the north fen transects", the first researcher pass answered it from `north-fen-transects.md` (wren down from 7.8 to 4.1 per 10 km), and the writer put the Ember-throated wren first in its priority list.

Every `llm` span carries token usage and an estimated cost, so the bill splits by agent. In this run:

| Agent | Passes | Tokens | Cost |
| --- | --- | --- | --- |
| `planner` | 1 | 337 | $0.00010 |
| `field_researcher` | 4 | 2,921 | $0.00097 |
| `writer` | 1 | 2,068 | $0.00059 |
| total | 6 | 5,326 | $0.00167 |

The four researcher passes cost between $0.000195 and $0.000296 each, and the writer is the single most expensive call ($0.00059) because it reads all four findings. The number to watch as the team grows is the researcher line: every extra sub-question from the planner buys one more full pass. `main.py` prints this same table at the end by reading the spans back from Opik, so the README numbers and the terminal agree.

Honest caveats: the planner's sub-questions drive everything, and one question (the fourth, about data reliability and budget) is answered mostly from the protocols file, so the report mentions the budget limit only loosely. The exact wording, counts and cost vary a little from run to run.

## Run it yourself

1. `cp .env.example .env` and add `OPENAI_API_KEY`, `OPIK_API_KEY` and `OPIK_WORKSPACE` (or run `opik configure` and export only the OpenAI key).
2. `uv sync`
3. `uv run main.py` (about 25 seconds and about $0.002 of `gpt-4o-mini`)
4. Open the `langgraph-wildlife-survey-team` project in Opik and click the `LangGraph` trace.

## Poke around

- Change `QUESTION` in `main.py` to something the notes barely cover ("Should the reserve reintroduce beavers?") and read the `field_researcher` outputs: they say what the notes do not cover, and the report inherits that caution.
- Change "exactly 4 sub-questions" to "exactly 2" in `SurveyPlan` and the planner prompt, rerun, and compare: two researcher passes instead of four, and the researcher cost line halves.
- Edit `data/north-fen-transects.md` to say the wren count rose to 9.0 per 10 km, rerun, and follow that number from the first researcher pass into the writer's priority list.
- Change `k=3` in `search_notes` to `k=1` and see which findings lose their supporting section.

## How it's put together

- `main.py` - corpus search, the three agents, the graph, the tracing, and the run.
- `costs.py` - reads the trace back from Opik and prints tokens and cost per agent.
- `data/` - five fictional Marrow Fen Reserve field-note files; the offline corpus.
- `pyproject.toml` - dependencies, with `opik` pinned to 2.2.96.
- `.env.example` - the keys the example needs.
