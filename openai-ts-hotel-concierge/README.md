<div align="center">

# Hotel Concierge with Threads and Cost per Turn

**`openai-ts-hotel-concierge`**

*A seaside hotel chatbot whose conversations, per-turn cost and guest feedback all show up in Opik.*

</div>

---

A hotel concierge talks in conversations, but the logs record isolated model calls. A guest asks about a room, then about the dog, then about a dinner table, and in your logs that is three unrelated requests, one of them quietly doing a second model call to run a tool. Which conversation did a call belong to? What did each turn cost, and why does it keep growing? Did the guest leave happy? This example is a small concierge for the Driftwood Pier Hotel (fictional, in Tern Harbor) written in TypeScript on the OpenAI SDK, and it answers all three with `opik-openai` and a few lines of the Opik client.

## What you'll build

A framework-free concierge on the OpenAI TypeScript SDK. Each conversation keeps its message history, and the system prompt is built from `data/hotel.md`, an offline set of hotel facts. The model can call one tool, `check_restaurant_table`, which looks up free tables in a small fictional inventory. Every guest message becomes one Opik trace created with `client.trace({ threadId })`; the OpenAI client is wrapped with `trackOpenAI(openai, { parent: trace })`, so each model call nests under that turn, and tool runs are logged as `tool` spans. `npm run demo` plays two scripted three-turn conversations, logs a `guest-satisfaction` score on the last answer of each after the run, then reads the spans back from Opik and prints what every turn cost.

## See it in Opik

Open the `openai-ts-hotel-concierge` project in Opik.

**Threads tab.** Two threads: `dune-cottage-booking` and `late-arrival-and-extras`, three turns each. Open one and it reads like a chat transcript, guest message on one side and concierge reply on the other, instead of six separate API calls.

**Traces tab.** Six traces, all named `concierge-turn`. Five contain a single `concierge-llm` span. The third turn of `dune-cottage-booking` ("a table for 2 on Friday 2026-07-17 around 19:00") is different. Expand it and you see three spans in order: `concierge-llm`, then a `check_restaurant_table` span of type `tool` (input `{date: "2026-07-17", party_size: 2}`, output with only the 19:30 and 20:30 slots because 19:00 is full), then a second `concierge-llm` span that turns the result into the answer, which offers 19:30. That turn is the only one that made two model calls.

**Cost and tokens.** Every `concierge-llm` span carries model `gpt-4o-mini-2024-07-18`, provider `openai`, token usage, and an estimated cost. In the verified run the first conversation's turns used 519, 619 and 1,454 tokens (the last one is two calls), costing about $0.000100, $0.000124 and $0.000248. The second conversation went 505, 580 and 652 tokens. Prompt tokens climb every turn because each call re-sends the whole history, and a tool turn costs roughly double. The whole run cost about $0.0008. Add the cost column to the trace table and sort by it to find the expensive turns.

**Feedback scores.** The `guest-satisfaction` column shows `1.0` on the last turn of `dune-cottage-booking` (thumbs-up after the table offer) and `0.0` on the last turn of `late-arrival-and-extras`, with the reason text stored on the score. The zero is deliberate: the guest asked for parrot pet-sitting in turn two, and the concierge could only offer to ask the front desk. Filter by `guest-satisfaction < 1` and you land on the conversation to improve.

**One caveat.** `opik-openai` currently logs these spans with type `general` rather than `llm`, so the UI does not show the LLM badge on them, even though model, usage and cost are all present. See "Poke around" if you want to work around it.

## Run it yourself

1. Install dependencies (Node 20+): `npm install`
2. Copy the env file and fill it in: `cp .env.example .env`, then export the variables in your shell (for example `set -a; source .env; set +a`). Opik Cloud needs `OPIK_API_KEY`, `OPIK_WORKSPACE` and `OPIK_URL_OVERRIDE`; the OpenAI key goes in `OPENAI_API_KEY`.
3. Run the demo: `npm run demo`. It takes about 10 seconds and costs under a cent.
4. Open the `openai-ts-hotel-concierge` project in Opik and check the Threads tab.

To chat yourself, run `npm run dev`. Each session becomes a new `interactive-xxxxxxxx` thread.

## Poke around

- Ask for a table on a date missing from the inventory in `src/hotel.ts` (try 2026-07-20) and compare the `tool` span output with how the concierge phrases the answer.
- Ask something `data/hotel.md` does not cover, such as "do you have an EV charger?", and check whether the trace shows the bot admitting it does not know or inventing a policy.
- In `src/main.ts`, flip the `1.0` score to `0.0` or add a third score name, re-run, and sort the Traces tab by that column.
- Change `MODEL` in `src/concierge.ts` to `gpt-4.1-mini` and compare per-turn cost in the printout and in the trace list.

## How it's put together

- `src/main.ts` - the two scripted conversations, the feedback scores logged after the run, the cost-per-turn readback, and the `--interactive` mode.
- `src/concierge.ts` - the `Concierge` class: message history, one `client.trace` per turn with the thread id, `trackOpenAI` with the trace as parent, and the tool loop with its `tool` spans.
- `src/hotel.ts` - the system prompt (built from the facts file), the tool definition and the fictional table inventory.
- `data/hotel.md` - the offline hotel facts the concierge answers from.
- `.npmrc` - `legacy-peer-deps=true`, because `opik-openai@2.2.96` declares a peer range of `opik@^1.8.61` that excludes the `opik@2.2.96` it ships alongside.
- `.env.example` - the keys the example needs.
