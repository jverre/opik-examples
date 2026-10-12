import OpenAI from "openai";
import type { ChatCompletionMessageParam } from "openai/resources/chat/completions";
import { Opik } from "opik";
import { trackOpenAI } from "opik-openai";
import { SYSTEM_PROMPT, TOOLS, checkRestaurantTable } from "./hotel.js";

export const MODEL = "gpt-4o-mini";

/** One instance per guest conversation. Keeps the message history as memory. */
export class Concierge {
  private messages: ChatCompletionMessageParam[] = [{ role: "system", content: SYSTEM_PROMPT }];
  private openai = new OpenAI();
  /** Opik trace id of every turn, in order. */
  readonly traceIds: string[] = [];

  constructor(
    private client: Opik,
    readonly threadId: string,
  ) {}

  async ask(guestMessage: string): Promise<string> {
    // One trace per turn. Every trace of a conversation shares the same threadId,
    // which is what the Threads tab groups on.
    const trace = this.client.trace({
      name: "concierge-turn",
      threadId: this.threadId,
      input: { message: guestMessage },
    });
    this.traceIds.push(trace.data.id);

    // Passing the trace as `parent` nests every OpenAI call under it as an llm span.
    const openai = trackOpenAI(this.openai, {
      client: this.client,
      parent: trace,
      generationName: "concierge-llm",
    });

    this.messages.push({ role: "user", content: guestMessage });
    let reply = "";
    for (let step = 0; step < 4; step++) {
      const completion = await openai.chat.completions.create({
        model: MODEL,
        messages: this.messages,
        tools: TOOLS,
      });
      const message = completion.choices[0]!.message;
      this.messages.push(message);

      if (!message.tool_calls?.length) {
        reply = message.content ?? "";
        break;
      }
      for (const call of message.tool_calls) {
        if (call.type !== "function") continue;
        const args = JSON.parse(call.function.arguments) as { date: string; party_size: number };
        const span = trace.span({ name: call.function.name, type: "tool", input: args });
        const result = checkRestaurantTable(args);
        span.update({ output: result });
        span.end();
        this.messages.push({ role: "tool", tool_call_id: call.id, content: JSON.stringify(result) });
      }
    }

    trace.update({ output: { reply } });
    trace.end();
    return reply;
  }
}
