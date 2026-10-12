# vercel-ai-sveltekit-plant-care

*Trace a streaming SvelteKit chat with one OpenTelemetry exporter, then let a live Opik rule grade every reply.*

A streamed reply is not a return value. Tokens leave your server one at a time, so there is no single moment where your code holds "the answer" to log, and every request re-sends the whole conversation, so naive logging gives you duplicates instead of conversations. On top of that, nobody reads traces by hand: you want something to score each reply as it arrives. This example is Fern, the houseplant-care assistant for Fernwick Plant Co. (a fictional shop), built with the Vercel AI SDK in SvelteKit. One `OpikExporter` turns every streamed reply into a complete trace with usage and cost, a thread id groups the turns of one chat, and an online evaluation rule created from code grades each reply with an LLM judge.

## What you'll build

- A SvelteKit app with one page (the `Chat` class from `@ai-sdk/svelte`) and one streaming endpoint, `src/routes/api/chat/+server.ts`. The endpoint calls `streamText` with `gpt-4o-mini` and answers only from six fictional care sheets in `data/care-sheets.json`, which are pasted into the system prompt.
- The whole Opik integration in `src/hooks.server.ts`: an `OpikExporter` (project `vercel-ai-sveltekit-plant-care`) behind an OpenTelemetry `NodeSDK`, plus the AI SDK's `registerTelemetry`. AI SDK v7 needs that explicit `registerTelemetry` call and a `runtimeContext` carrying the chat id; older docs omit both.
- `scripts/setup-rule.ts`, which creates an online evaluation rule on the project through the SDK's REST client: an LLM judge (`gpt-4o-mini`, sampling 1.0) that scores `care_sheet_faithfulness` on every new trace.
- `scripts/demo.ts`, which starts the dev server, plays four scripted conversations (two turns each) against the streaming endpoint, stops the server, and prints the scores the rule attached.

```
browser (Chat) -> POST /api/chat -> streamText(gpt-4o-mini) -> tokens stream back
                                    \-> OTel spans -> OpikExporter -> Opik -> online rule -> feedback score
```

## See it in Opik

Open the `vercel-ai-sveltekit-plant-care` project in Opik. In the Traces tab, the traces named `plant-care-turn` are the chat turns: eight of them in the verified run, one per streamed reply. Open one (the last turn of the fertilizer thread, for example). The trace input is the full message array the model saw, system prompt with the care sheets first, then every earlier turn. The output is the final reply text, assembled after the last token even though it left the server as a stream. The tree has a `step 1` span with a `chat gpt-4o-mini` span of type `llm` inside it. That llm span carries `gpt-4o-mini-2024-07-18` as its model, `openai` as its provider, 568 prompt tokens and 27 completion tokens, and an estimated cost of $0.0001014. Because the history is re-sent on every turn, the second turn of each thread has more prompt tokens than the first. The eight chat turns cost about $0.0008 together.

Open the Threads tab. The thread ids from the `Chat` component turn the eight traces into four threads of two turns: the Monstera with yellow leaves, the plants that survive a travel schedule, the Calathea with no care sheet, and the fertilizer questions that no sheet covers.

Back in Traces, each `plant-care-turn` has a `care_sheet_faithfulness` feedback score, written by the rule `vercel-ai-sveltekit-plant-care-faithfulness`, with the judge's one-sentence reason. In the verified run all eight scored 1: Fern stuck to the sheets, said "I don't have a care sheet for Calathea orbifolia" when asked, and declined to guess even when pushed. The judge's own calls also appear in the same project as `online_evaluation` traces (8 of them in this run, one per chat turn, about $0.0012 in total), so the project holds 16 traces in all; filter on the name `plant-care-turn` when you want only chat. The rule's own page in the project's Online evaluation settings shows its prompt, model and sampling rate.

## Run it yourself

1. `cp .env.example .env` and fill in `OPENAI_API_KEY`, `OPIK_API_KEY` and `OPIK_WORKSPACE`.
2. `npm install`. The repo ships an `.npmrc` with `legacy-peer-deps=true` because `opik-vercel` still declares a peer range of `opik@^1.8.75`.
3. `npm run setup-rule` creates (or replaces) the online evaluation rule. It is idempotent: it deletes any rule with the same name first, so running it twice still leaves exactly one rule.
4. `npm run demo` plays the conversations, waits for the scores and exits (about 20 seconds, including `setup-rule`). Or `npm run dev` and chat yourself at http://localhost:4191.
5. Open the `vercel-ai-sveltekit-plant-care` project in Opik: Traces first, then Threads.

The demo uses port 4191 on purpose: Node's `fetch` refuses to connect to port 4190.

## Poke around

- Delete the "Do not guess" sentence from the system prompt in `src/lib/server/prompt.ts`, rerun `npm run demo`, and watch whether the Calathea and fertilizer threads start scoring 0.
- Open `npm run dev` in two browser tabs. Each tab is its own `Chat` id, so each becomes its own thread.
- Change the model in `+server.ts` to `gpt-4.1-mini` and compare the cost column between runs.
- Edit the judge prompt in `scripts/setup-rule.ts` (for instance, also penalise replies longer than three sentences), rerun `npm run setup-rule`, and send new traffic.

## How it's put together

- `src/hooks.server.ts`: the integration, `OpikExporter` + `NodeSDK` + `registerTelemetry`, loaded once when the server starts.
- `src/routes/api/chat/+server.ts`: the streaming endpoint, `streamText` plus the telemetry settings and the chat id in `runtimeContext`.
- `src/routes/+page.svelte`: the chat page built on the `Chat` class.
- `src/lib/server/prompt.ts`: builds the system prompt from the care sheets.
- `src/lib/project.ts`: the one project name shared by the app and the scripts.
- `data/care-sheets.json`: six fictional care sheets, the whole corpus.
- `scripts/setup-rule.ts`: creates the live online evaluation rule through the REST client.
- `scripts/demo.ts`: starts the server, plays the conversations, reads the scores back, stops the server.
- `.env.example`, `.npmrc`, `svelte.config.js`, `vite.config.ts`, `tsconfig.json`: configuration.
