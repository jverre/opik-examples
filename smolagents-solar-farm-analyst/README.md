# smolagents-solar-farm-analyst

*A code-writing agent audits a solar farm, and the trace shows exactly where its pandas went wrong.*

Python 3.12+ · smolagents 1.26.0 · OpenInference + OTLP into Opik · gpt-4o-mini

When an agent answers by writing and running code, the answer arrives as a number with no visible reasoning behind it. If the code measured the wrong thing, the number still looks like a computation. This example puts a smolagents `CodeAgent` in front of a fictional solar farm's output file and asks it three audit questions. The CSV has three planted problems, and in the real run the agent finds two and misses one. Opik shows the generated pandas and the execution log for every step, so you can see which kind of answer you got and why.

## What you'll build

A `CodeAgent` on `gpt-4o-mini` pointed at `data/solar_output.csv`: 90 days (1 March to 29 May 2026) of daily kWh for six inverters at the fictional Larkmoor Ridge Solar, with site irradiance and fault codes, 540 rows. Three anomalies are planted by `make_data.py`:

1. INV-04 produces 0 kWh for six days (14 to 19 April) and logs ground-fault code `GF-17`.
2. INV-02 reports exactly 412.5 kWh for twelve days (20 April to 1 May) while irradiance swings between 3 and 7. A stuck meter, with no fault code.
3. INV-06 loses about 12% of its yield from 10 May onward. No fault code either.

The agent gets three questions, one per anomaly, each phrased without naming the culprit. For each it loops through smolagents' think, code, observe cycle: the model writes a pandas snippet, a local executor runs it (only `pandas` is authorized as an extra import), and the printed output feeds the next step. Tracing is the documented smolagents integration: `SmolagentsInstrumentor` from OpenInference plus an OTLP exporter aimed at Opik's OpenTelemetry endpoint. There are no decorators in the agent code.

## See it in Opik

Open the `smolagents-solar-farm-analyst` project in Opik. The Traces tab holds three traces named `CodeAgent.run`, one per question.

- **Question 1, the dead inverter (8.0 s, 2 steps).** Open the trace. `Step 1` has an output that starts `Execution logs:` and lists INV-04 on 2026-04-14 through 04-19 with fault code `GF-17`. The agent's answer matches the planted anomaly exactly.
- **Question 3, the lagging inverter (11.0 s, 3 steps).** `Step 2`'s execution log is a table of median specific yield per inverter, with INV-06 at 177.3 against 200.3 to 209.2 for the rest, followed by a "lagging inverters" table: INV-06 at 13.58%, INV-01 at 2.25%, INV-05 at 2.38%. The final answer repeats those numbers. The planted drop is 12%; the agent measures against the fleet median, and the small gaps for INV-01 and INV-05 are natural unit-to-unit spread that it reports as lag too.
- **Question 2, the stuck meter (24.8 s, 6 steps), which the agent got wrong.** This is the trace to open. The agent answered that INV-06 shows "relatively stable" output, which is false. Click through the `OpenAIModel.generate` spans in order and read the `Thought:` and `<code>` block in each output. `Step 2` filters for inverters whose standard deviation is under 50 and the log is `Empty DataFrame`. `Step 4` falls back to the standard deviation of daily energy over all 90 days, where INV-06 scores lowest (314.5 kWh). That metric is wrong for the question, because a stuck stretch of twelve days barely moves a 90-day standard deviation, and the agent never looks at INV-02 or at 20 April to 1 May. After six steps it hits `max_steps`, and a seventh `OpenAIModel.generate` span writes the answer from what it has. You can find the exact step where the approach went wrong, which a final sentence alone would never tell you.

Where things live: the generated code is in each `OpenAIModel.generate` span's output (the `content` field, thought followed by `<code>`), and the execution log is in the matching `Step N` span's output. The model span's input holds the full message history, so you can watch the prompt grow. Q2's seven model calls take 2,196 prompt tokens on the first call and 5,122 on the sixth.

Honest caveats from this run:

- **Cost does not appear.** The OpenInference spans arrive with model `gpt-4o-mini` and prompt, completion and total token counts, but Opik shows no estimated cost for them over OTLP. Token counts are there; dollars are not.
- **Trace usage is doubled.** The root `CodeAgent.run` span is typed `llm` and carries the agent's total token usage, so the trace-level total counts every token twice. Q2 shows 52,252 prompt tokens at trace level, but its seven model calls sum to 26,126.
- **Real spend is tiny.** The whole run uses about 40,000 prompt and 2,500 completion tokens, well under a cent or two at gpt-4o-mini prices.

## Run it yourself

1. `cd smolagents-solar-farm-analyst && cp .env.example .env`, then add `OPENAI_API_KEY`. Opik credentials come from `OPIK_API_KEY` and `OPIK_WORKSPACE` in `.env`, or from `~/.opik.config` after `opik configure`. Self-hosted Opik: set `OPIK_URL_OVERRIDE` to your API URL.
2. `uv sync`
3. `uv run main.py` (about 45 seconds; the dependencies are pinned and `requires-python` is capped below 3.14 because some of them lack wheels there)
4. Open the `smolagents-solar-farm-analyst` project in Opik. One trace per question, newest on top.

Agents are not deterministic, so expect different wording and step counts. Question 2 is the one most likely to go wrong, and sometimes it goes right.

## Poke around

- Rerun a few times and compare the Q2 traces. When the agent finds INV-02, look at which step turned to a run-length or `diff() == 0` check; when it misses, look for the step that chose a summary statistic over the whole period.
- Give the agent the answer's shape: change Q2 to "find any inverter reporting the same energy_kwh value on five or more consecutive days". It should succeed in two or three steps, and the trace will show the groupby on consecutive runs.
- Regenerate the data after editing the dates in `make_data.py` (`python make_data.py`), move the stuck-meter window, and see whether the agent still finds the right dates.
- Remove `"pandas"` from `additional_authorized_imports` and rerun. The executor blocks the import, and the failed step is visible in the trace as the agent tries to cope without it.

## How it's put together

- `main.py`: OTLP setup from env vars, the instrumented `CodeAgent`, the briefing, three questions.
- `make_data.py`: deterministic generator for the CSV and the three planted anomalies.
- `data/solar_output.csv`: 540 rows, 6 inverters by 90 days.
- `.env.example`: the keys the example needs.
- `pyproject.toml`: pinned dependencies, Python 3.12 or 3.13.
