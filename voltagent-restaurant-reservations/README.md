# voltagent-restaurant-reservations

*A VoltAgent booking assistant for a fictional bistro, where the same request is traced twice to show what a `gen_ai.*` attribute mapper buys you in Opik.*

A reservation agent is easy to demo and hard to audit: the guest sees "Your table is booked, ID ML-1051", and the only evidence of what actually happened is in the tool calls. This example is a booking assistant for Maison Lanterne, a 14-table bistro open Thursday to Sunday, built with [VoltAgent](https://voltagent.dev/) and traced to Opik over plain OpenTelemetry. VoltAgent exports OTel spans out of the box, but it names its attributes in its own vocabulary, and Opik reads the `gen_ai.*` semantic conventions. Without a mapping the traces arrive, but as untyped spans with no model, no token usage and no cost. The demo sends one request twice, once with the mapper off and once with it on, so you can see the difference in the same project.

## What you'll build

One VoltAgent `Agent` on `gpt-4o-mini` with three tools over an in-memory booking book (`src/bistro.ts`): `check_availability` lists free slots for a party and date, `book_table` books the smallest free table that fits, and `cancel_booking` cancels by booking id plus the name on it. Nothing but the LLM call leaves your machine.

Tracing lives in one file, `src/observability.ts`. It plugs a `MappingSpanProcessor` in front of a `BatchSpanProcessor` and an OTLP exporter aimed at Opik's OTel endpoint (with the `projectName` header set). The processor rewrites each span just before export:

| Span | What VoltAgent emits | What the mapper writes |
| --- | --- | --- |
| `llm` | `llm.model`, `llm.usage.prompt_tokens`, `llm.usage.completion_tokens`, `llm.usage.total_tokens`, `llm.messages` | `gen_ai.request.model`, `gen_ai.provider.name` (VoltAgent has none on this span), `gen_ai.usage.prompt_tokens`, `gen_ai.usage.completion_tokens`, `gen_ai.usage.total_tokens`, and `input` as `{"messages": [...]}` |
| `tool` | `tool.name`, `input` (the call arguments), `output` | `gen_ai.tool.call.arguments` (this is what makes Opik type the span as a tool); `output` is left alone |
| agent root | `input`, `output`, plus `agent.*`, `entity.*`, `ai.model.*` bookkeeping | nothing promoted; the bookkeeping moves to `opik.metadata.*` |

Opik sends every attribute it does not recognise to the span input, so the mapper also moves the leftover VoltAgent attributes to `opik.metadata.<name>` (nothing is dropped, they just stop burying the input).

`npm run demo` plays five scripted guest requests:

1. "Do you have a table for 4 this Friday around 7:30pm?" with the mapper **off**.
2. The same sentence with the mapper **on**.
3. "Can you book Saturday at 8:30pm for two, under the name Ines Moreau?" (chains `check_availability`, then `book_table`).
4. "Please cancel my reservation ML-1050. It's under Hugo Bernard." (`cancel_booking`).
5. "Can I get a table for 9 on Saturday at 8pm?" (the tool refuses and the agent sends the guest to the phone).

## See it in Opik

Open the `voltagent-restaurant-reservations` project in Opik Cloud. It holds 5 traces, all named `lanterne-reservations`, and each has an agent root span, one `llm:generateText` span and one `tool.execution:<name>` span per tool call (4 spans for the booking trace, 3 for the others). Sort by oldest first.

- **Trace 1 (mapper off).** The Friday-for-four request. The trace has no token usage and no cost, and all three spans show type `general`, including `llm:generateText` and `tool.execution:check_availability`. Open any span and the input is a wall of VoltAgent attributes (`operation.id`, `entity.id`, `span.type: "llm"`, `llm.usage.prompt_tokens`, a serialized Zod schema under `tool.parameters`). The data is all there, but Opik does not know what any of it means. Metadata carries `gen_ai_mapping: off`.
- **Trace 2 (mapper on, same sentence).** Now `llm:generateText` is an `llm` span with model `gpt-4o-mini`, provider `openai`, 600 prompt and 53 completion tokens (653 total) and an estimated cost of $0.0001218, and the trace rolls those up. The `tool.execution:check_availability` span is typed `tool`, its input is just `{"gen_ai.tool.call.arguments": {"date": "2026-11-13", "party_size": 4, "around_time": "19:30"}}` and its output is the slot list, with `19:30` marked `available: false`. The LLM span input is `{"messages": [...]}`, the system prompt plus the guest message, instead of the attribute pile. The trace input and output are the guest's sentence and the agent's reply, and the leftover VoltAgent attributes sit in metadata (`gen_ai_mapping: on`).
- **Trace 3 (booking).** Two `tool` spans: `check_availability` for `2026-11-14`, then `book_table` with the booking `ML-1051` for Ines Moreau at 20:30 as its output. LLM span: 688 prompt, 49 completion tokens, $0.0001326.
- **Trace 4 (cancel).** The `cancel_booking` span shows `{"booking_id": "ML-1050", "name": "Hugo Bernard"}` going in and the cancelled booking coming out.
- **Trace 5 (party of 9).** The `check_availability` output is `{"error": "We seat parties of 1 to 6 online. Larger groups should call the restaurant."}`. That is the reason for the agent's reply, and it is only visible in the tool span.

Across the four mapped traces the total estimated cost is about $0.0005. In the project's trace list, trace 1 has no usage or cost to show; traces 2 to 5 do.

Two honest limits. VoltAgent puts the model's final text on the agent root span, not the `llm` span, so the `llm:generateText` span has an input but no output in Opik. And there is one `llm` span per request even when the agent calls two tools: its usage is the whole request, not one number per model step.

## Run it yourself

1. `cd voltagent-restaurant-reservations && cp .env.example .env`, then fill in `OPENAI_API_KEY`, `OPIK_API_KEY` and `OPIK_WORKSPACE_NAME` (add `OPIK_URL_OVERRIDE` if you self-host Opik).
2. `npm install`
3. `npm run demo` (about 16 seconds; the five requests cost roughly $0.0006 of OpenAI usage).
4. Open the `voltagent-restaurant-reservations` project in Opik and compare the first two traces.

Optional: `npm run typecheck` runs `tsc --noEmit`. VoltAgent prints an AI SDK warning about system messages in the prompt on every call; the demo filters that single message because VoltAgent does not expose the option that acknowledges it.

## Poke around

- Flip the demo's mapper off for every request (set `mapped: false` on each entry in `src/demo.ts`) and look at the project's cost and token columns: they go blank.
- In `mapLlmSpan`, delete the `gen_ai.provider.name` line and re-run, then check whether the `llm` span still gets a cost. Opik prices a span from model, provider and usage together, so this shows which of the three the cost depends on.
- Make Friday 19:30 free again by removing one booking from the seed list in `src/bistro.ts`, and watch the `check_availability` output in the tool span flip from `available: false` to `true`.
- Change the model in `src/agent.ts` to `openai/gpt-4.1-mini` and re-run: the mapper picks up the new `llm.model` value and the cost per trace changes.

## How it's put together

- `src/bistro.ts` - the fictional bistro: 14 tables, eight evening slots, a seeded book and the availability, booking and cancellation logic.
- `src/tools.ts` - the three VoltAgent tools wrapping `bistro.ts`.
- `src/agent.ts` - the reservation agent: instructions, model and tools.
- `src/observability.ts` - the OTLP exporter aimed at Opik plus the `gen_ai.*` mapping span processor (the only file that knows tracing exists).
- `src/demo.ts` - loads env vars, runs the five scripted requests (flipping the mapper for the first), flushes the exporter.
- `.env.example` - every key the example needs.
