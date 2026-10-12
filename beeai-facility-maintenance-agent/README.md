# beeai-facility-maintenance-agent

*A BeeAI ReAct agent that triages office maintenance requests, and the Opik trace that shows when it files one at the wrong priority.*

ReAct agents decide their next move by writing it down: a thought, a tool call, another thought, until they commit to an answer. [BeeAI](https://beeai.dev/) gives you that loop in TypeScript, then hides it behind one `agent.run()` call. When a dispatcher bot files "person stuck in the elevator" as `high` instead of `emergency`, you need to know whether the model misread the request, passed the wrong argument to a tool, or ignored what a tool returned. This example is a dispatcher for the Larkspur Office Campus, a fictional three-building site. BeeAI emits OpenInference spans, so every iteration, model call and tool call reaches Opik over plain OpenTelemetry, with no Opik SDK in the code.

## What you'll build

One BeeAI `ReActAgent` on `gpt-4o-mini` with three tools over local JSON (`data/`):

- `lookup_asset` matches the requester's words ("roof unit", "kitchen sink") to a registered asset with building, trade and warranty.
- `lookup_technician` returns the on-call technician, hours and SLA for a trade.
- `create_work_order` files the order (in memory) with asset, assignee, priority and a summary.

The agent is told to call them in that order and to use `emergency` for gas, fire, flooding or anyone trapped. `npm run demo` sends four scripted requests: a dripping sink (routine), a gas smell (emergency), a stuck elevator with a visitor inside (should be emergency, and the assignee is an outside vendor), and a stuck thermostat that matches nothing in the asset register. Tracing lives in one file, `src/instrumentation.ts`: a `NodeSDK` with BeeAI's OpenInference instrumentation and an OTLP exporter aimed at Opik, with auth and project routing as HTTP headers.

## See it in Opik

Open the `beeai-facility-maintenance-agent` project. The Traces tab holds four traces named `beeai-framework-main`, one per request, each about 4 to 6 seconds long and each with 57 spans.

Expand the first trace. The root `beeai-framework-main` span holds the whole `agent.run()` call, and under it sit four `iteration-N` spans. Iteration 1 contains a `backend.openai.chat.*` group (type `llm`, model `gpt-4o-mini`) followed by `tool.dynamic.lookupAsset.*` spans. Iteration 2 is the same pattern with `lookupTechnician`, iteration 3 with `createWorkOrder`, and iteration 4 is the final model call that writes the answer. Each tool has `start`, `success` and `finish` spans. The `success` span is the useful one: its input shows `tool.parameters` (for example `{'query': 'sink kitchenette second floor'}`) and its output shows the JSON the tool returned, here asset `PLB-B3-12` in Building 3.

The elevator trace (third) is the one worth opening. The request says a visitor is stuck inside, and the prompt says anyone trapped is an `emergency`. In the final run the `createWorkOrder` success span shows `priority: 'high'`, filed as `WO-4103` to `Otterbeck Lifts dispatch`. The lookups were correct (asset `ELV-B1-01`, vendor technician, 2 hour SLA), so the trace tells you this is a prompt-following problem at the last step, not a bad lookup. The gas trace, by contrast, shows `priority: 'emergency'`. Because the model is not deterministic, your run may file the elevator order differently; that is itself the point of looking at the tool arguments.

The fourth trace (thermostat) shows `lookupAsset` returning `found: false` with the list of known assets. The agent then files `asset_id: 'UNKNOWN'` to `Ines Okafor` (Climate Systems), and the work order comes back with status `needs_asset_confirmation`.

What Opik does and does not show for this integration, from the final run:

- Span types are `llm` for the model-call events and `general` for everything else. Tool spans are typed `general`, not `tool`; you recognize them by the `tool.dynamic.<name>.*` names.
- Token usage lands on the `llm` spans of iterations 1 and 4 (for example 1,281 and 1,727 total tokens in the first trace) and rolls up to the trace, which reads 3,008. The two middle model calls carry no usage, so the trace total undercounts.
- No cost appears. The OpenInference spans carry no provider field Opik can price, so `total_estimated_cost` is empty on every span.
- Each `iteration` also contains many small `agent.react.*` event spans (`update`, `partialUpdate`, `toolStart`), which is why a four-step run has 57 spans.

## Run it yourself

1. `cp .env.example .env` and fill in `OPENAI_API_KEY`, `OPIK_API_KEY` and `OPIK_WORKSPACE`.
2. `npm install`
3. `npm run demo` (about 25 seconds and about one cent of `gpt-4o-mini`)
4. Open the `beeai-facility-maintenance-agent` project in Opik and click the newest trace.

`beeai-framework` is pinned to 0.1.13 because the OpenInference instrumentation only supports that version. The code needs Node 20 or newer.

## Poke around

- Reword the elevator request to "someone is trapped in the elevator" and run again. Compare the `createWorkOrder` priority across runs, then add "stuck means emergency" to the instructions in `src/agent.ts` and check the tool span.
- Drop `maxIterations` to 2 in `src/agent.ts`. The loop should be cut off before a work order is filed, so look for a trace that ends without any `createWorkOrder` spans (untested here).
- Add an asset to `data/assets.json` for the east wing thermostat and rerun request 4. The `lookupAsset` output flips from `found: false` to a match and the work order status becomes `assigned`.
- Point the exporter at a self-hosted Opik by setting `OPIK_URL_OVERRIDE=http://localhost:5173/api` in `.env`.

## How it's put together

- `src/instrumentation.ts`: the OTel `NodeSDK`, BeeAI's OpenInference instrumentation, and the OTLP exporter aimed at Opik (the only file that knows tracing exists).
- `src/tools.ts`: the three tools and their Zod input schemas.
- `src/agent.ts`: the dispatcher instructions and the `ReActAgent` on `gpt-4o-mini`.
- `src/demo.ts`: loads env vars, runs the four scripted requests, flushes the exporter.
- `data/assets.json`, `data/technicians.json`: the fictional asset register and on-call roster.
- `.env.example`: every key the example needs.
