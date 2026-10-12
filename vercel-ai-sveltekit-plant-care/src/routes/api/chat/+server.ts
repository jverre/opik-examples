import { openai } from "@ai-sdk/openai";
import { streamText, convertToModelMessages, type UIMessage } from "ai";
import { OpikExporter } from "opik-vercel";
import { SYSTEM_PROMPT } from "$lib/server/prompt";
import type { RequestHandler } from "./$types";

export const POST: RequestHandler = async ({ request }) => {
  // The client sends the chat id and the full message history on every turn.
  const { id, messages }: { id: string; messages: UIMessage[] } =
    await request.json();

  const result = streamText({
    model: openai("gpt-4o-mini"),
    system: SYSTEM_PROMPT,
    messages: await convertToModelMessages(messages),

    // These two settings are the integration. They turn the call into
    // OpenTelemetry spans for the OpikExporter registered in
    // hooks.server.ts. The chat id rides in runtimeContext and becomes the
    // Opik thread id.
    runtimeContext: { threadId: id, traceName: "plant-care-turn" },
    experimental_telemetry: {
      ...OpikExporter.getSettings({ name: "plant-care-turn" }),
      includeRuntimeContext: { threadId: true, traceName: true },
    },
  });

  return result.toUIMessageStreamResponse();
};
