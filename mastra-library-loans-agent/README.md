# mastra-library-loans-agent

**A public-library loans agent on Mastra whose search, renew and hold tool calls land in Opik as real `execute_tool` spans.**

An agent that can call tools is hard to debug from its chat transcript alone. When a member is told "I can't renew that", the cause could be the model's choice of tool, the arguments it invented, or what the tool actually returned, and the reply shows you none of that. This example is a loans assistant for Alder Creek Public Library, a fictional branch, built with [Mastra](https://mastra.ai/) and traced to Opik through Mastra's observability layer and an OpenTelemetry exporter. Every patron request becomes one trace with the full agent loop inside it: the agent run, each step, the model call of that step, and the tool the model decided to run, with the exact arguments and the exact JSON that came back.

## What you'll build

One Mastra `Agent` on `gpt-4o-mini` with three tools over in-memory data loaded from `data/` (so only the LLM call leaves your machine):

- `search_catalog`: keyword search over seven fictional books, returning copies on the shelf and how many patrons are waiting.
- `renew_loan`: renews a loan for 14 days, or refuses with a reason (`hold_queue`, `overdue`, `renewal_limit`, `card_blocked`).
- `place_hold`: puts a member on the waiting list for a book that is checked out, and returns the queue position.

`npm run demo` plays four scripted requests. The third one makes the agent chain three tools on its own:

```
"Renew loan L-8802, The Salt Road. If you can't, put me on the waiting list for Night Ferry to Karsk."
   -> renew_loan   (refused: two patrons are waiting for The Salt Road)
   -> search_catalog   (finds Night Ferry to Karsk = BK-302)
   -> place_hold   (placed, queue position 5)
```

Tracing is configuration, not code: the tools and the agent never mention Opik. `src/mastra.ts` wires Mastra's `OtelExporter` to Opik's OTLP endpoint, and `src/opik-exporter.ts` is a small exporter that patches the few spans fields Opik cannot read from Mastra's output (provider and model for cost, and the trace-level input and output).

## See it in Opik

Open the `mastra-library-loans-agent` project in the workspace you configured. The Traces tab lists four traces, all named `invoke_agent alder-creek-loans-agent`, with Input and Output columns filled with the patron's message and the agent's final answer.

Open the third trace (the one that starts "Member M-2041 again"). It has 24 spans, and the tree reads like the agent's reasoning: `invoke_agent` at the root, then four `agent_step` spans. Each step holds a `chat gpt-4o-mini` span (type `llm`) and, in the first three steps, the tool the model chose (type `tool`):

1. `execute_tool renewLoan`: input `{"member_id": "M-2041", "loan_id": "L-8802"}`, output `{"renewed": false, "reason": "hold_queue", "title": "The Salt Road", "holds_waiting": 2, ...}`.
2. `execute_tool searchCatalog`: input `{"query": "Night Ferry to Karsk"}`, output with `book_id: "BK-302"`, 0 copies available, 4 holds waiting.
3. `execute_tool placeHold`: input `{"member_id": "M-2041", "book_id": "BK-302"}`, output `{"placed": true, "queue_position": 5, ...}`.
4. The last step is a plain `chat` span that writes the answer: "I couldn't renew your loan for The Salt Road ... you're currently in the 5th position."

Notice that the model took the `book_id` for `place_hold` from the `search_catalog` result, not from its own memory. That is the receipt you want when you ask "did the agent make that up?".

Each `llm` span shows its token usage and an estimated cost (about $0.00008 to $0.00014 per call). Across the whole run there are 4 traces, 60 spans (6 tool spans, 10 llm spans), about 5,500 tokens and roughly $0.001 in total. The other traces are shorter: the search and the successful renewal (`L-8801`, `renewed: true`) are one tool step plus one answer step (12 spans each), and the overdue renewal for member M-3377 is a single `renewLoan` call returning `reason: "overdue"` (12 spans).

Two details worth knowing when you click around. Mastra names tool spans after the key in the `tools` object, so you see `execute_tool renewLoan`, not `renew_loan`. And Opik shows the trace Input and Output as small objects keyed `gen_ai.prompt` and `gen_ai.completion`, because that is the attribute Opik maps them from.

## Run it yourself

1. `cp .env.example .env`, then fill in `OPENAI_API_KEY`, `OPIK_API_KEY` and `OPIK_WORKSPACE` (leave `OPIK_URL_OVERRIDE` as is for Opik Cloud, remove it for a local Opik).
2. `npm install` (needs Node 22.13 or newer; no `.npmrc` is required, the install has no peer conflicts).
3. `npm run demo` (about 15 seconds, well under one cent of OpenAI usage).
4. Open the `mastra-library-loans-agent` project in Opik and click the third trace.
5. Optional: `npm run tree` prints the same span trees in your terminal using the Opik TypeScript SDK, with tool arguments, results, tokens and cost.

## Poke around

- Delete the sentence "Never tell a member a renewal is impossible until renew_loan has said so" from the instructions in `src/agent.ts` and rerun. In my own earlier runs without that sentence, the overdue request (request 4) was sometimes answered with no `execute_tool` span at all: the model refuses from the patron's own words. A trace with no tool span is an ungrounded answer, and now you can filter for it.
- Make the policy bite: in `data/members.json` set `renewals_used` to 2 on loan `L-8801` and watch the second request come back with `reason: "renewal_limit"` in the tool span.
- Change request 3 to ask for a hold on a book with copies on the shelf (for example BK-410) and see `place_hold` refuse with `copy_available`, and the agent tell the member to just borrow it.
- Drop `maxSteps` to 1 in `src/demo.ts`. The trace shrinks to one LLM call that stops after choosing a tool, a cheap way to see what the step loop is buying you.
- Remove the `OpikSpanExporter` from `src/mastra.ts` (use the `provider.custom` config only) and compare: the `llm` spans lose their cost, and the trace Output column goes empty.

## How it's put together

- `src/library.ts`: loads the catalog and member ledger from `data/` into memory.
- `src/tools.ts`: the three Mastra tools, `search_catalog`, `renew_loan`, `place_hold`.
- `src/agent.ts`: the Alder Creek loans agent, its instructions, model and tools.
- `src/mastra.ts`: the Mastra instance and the Opik wiring (the only agent-side file that knows tracing exists).
- `src/opik-exporter.ts`: OTLP exporter that fixes provider, model, trace input and trace output before spans leave the process.
- `src/demo.ts`: loads env vars, runs the four scripted requests, flushes the exporter with `mastra.shutdown()`.
- `src/tree.ts`: reads the traces back through the Opik SDK and prints the span trees.
- `data/catalog.json`, `data/members.json`: the fictional books, members and loans.
- `.env.example`: every variable the example needs.
