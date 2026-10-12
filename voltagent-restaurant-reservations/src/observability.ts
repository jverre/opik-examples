// VoltAgent -> Opik over plain OpenTelemetry. This is the only file that knows
// tracing exists: no agent or tool code mentions it.
//
// VoltAgent's observability layer is OpenTelemetry underneath, but it names its
// span attributes in its own vocabulary (`llm.usage.prompt_tokens`, `llm.model`,
// `span.type`, `input`). Opik's OTLP endpoint reads the GenAI semantic
// conventions (`gen_ai.*`). Without a mapping the spans still arrive, but as
// untyped general spans: no model, no token usage, no cost.
//
// MappingSpanProcessor sits in front of the exporter and copies VoltAgent's
// attributes to the `gen_ai.*` names Opik understands. It can be switched off
// at runtime (`mapping.enabled = false`) so the demo can show the same request
// traced both ways.
import { VoltAgentObservability } from "@voltagent/core";
import { BatchSpanProcessor } from "@opentelemetry/sdk-trace-base";
import type { Context } from "@opentelemetry/api";
import type { ReadableSpan, Span, SpanProcessor } from "@opentelemetry/sdk-trace-base";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-http";

export const PROJECT_NAME = process.env.OPIK_PROJECT_NAME ?? "voltagent-restaurant-reservations";

// Opik Cloud by default; OPIK_URL_OVERRIDE points at a self-hosted deployment
// (for example http://localhost:5173/api).
const opikBase = (process.env.OPIK_URL_OVERRIDE ?? "https://www.comet.com/opik/api").replace(/\/+$/, "");

export const mapping = { enabled: true };

// Opik's OTLP mapper sends any attribute it does not recognise to the span
// INPUT, which buries the real input under a pile of VoltAgent bookkeeping.
// Attributes under `opik.metadata.` go to span metadata instead, so the mapper
// moves everything it does not promote there (nothing is dropped).
const KEEP = (key: string): boolean =>
  key.startsWith("gen_ai.") || key.startsWith("opik.") || key === "input" || key === "output";

function moveRestToMetadata(attrs: Record<string, unknown>): void {
  for (const key of Object.keys(attrs)) {
    if (KEEP(key)) continue;
    attrs[`opik.metadata.${key}`] = attrs[key];
    delete attrs[key];
  }
}

/** What VoltAgent emits on an `llm` span -> what Opik reads. */
function mapLlmSpan(attrs: Record<string, unknown>): void {
  // llm.model ("gpt-4o-mini") -> gen_ai.request.model. Opik prices a span from
  // model + provider + token counts, so all three have to be present.
  if (attrs["llm.model"]) attrs["gen_ai.request.model"] = attrs["llm.model"];
  // VoltAgent records the provider on the agent span (`ai.model.provider`) but
  // not on the llm span, so the mapper supplies it. This example only uses OpenAI.
  attrs["gen_ai.provider.name"] = "openai";
  // llm.usage.{prompt,completion,total}_tokens -> gen_ai.usage.*
  for (const key of ["prompt_tokens", "completion_tokens", "total_tokens"]) {
    const value = attrs[`llm.usage.${key}`];
    if (value !== undefined) attrs[`gen_ai.usage.${key}`] = value;
  }
  // llm.messages is a JSON array of chat messages. A JSON-object `input`
  // attribute is merged into the span input, so wrapping it as {messages: [...]}
  // gives Opik the chat-prompt shape it renders as a conversation.
  if (typeof attrs["llm.messages"] === "string") {
    attrs["input"] = JSON.stringify({ messages: JSON.parse(attrs["llm.messages"]) });
  }
  moveRestToMetadata(attrs);
}

/** What VoltAgent emits on a `tool` span -> what Opik reads. */
function mapToolSpan(attrs: Record<string, unknown>): void {
  // VoltAgent records the call arguments in `input`. `gen_ai.tool.call.arguments`
  // is the name that makes Opik type the span as a tool call and show the
  // arguments as its input. The result is already in `output`, which Opik reads as-is.
  attrs["gen_ai.tool.call.arguments"] = attrs["input"] ?? "{}";
  delete attrs["input"];
  moveRestToMetadata(attrs);
}

/** The agent's root span: only the guest message and the reply belong in input/output. */
function mapAgentSpan(attrs: Record<string, unknown>): void {
  moveRestToMetadata(attrs);
}

class MappingSpanProcessor implements SpanProcessor {
  constructor(private readonly next: SpanProcessor) {}

  onStart(span: Span, parentContext: Context): void {
    this.next.onStart(span, parentContext);
  }

  onEnd(span: ReadableSpan): void {
    const attrs = span.attributes as Record<string, unknown>;
    // Lands in Opik as span metadata, so the demo's two passes are labelled.
    attrs["opik.metadata.gen_ai_mapping"] = mapping.enabled ? "on" : "off";
    if (mapping.enabled) {
      if (attrs["span.type"] === "llm") mapLlmSpan(attrs);
      else if (attrs["span.type"] === "tool") mapToolSpan(attrs);
      else if (attrs["entity.type"] === "agent") mapAgentSpan(attrs);
    }
    this.next.onEnd(span);
  }

  forceFlush(): Promise<void> {
    return this.next.forceFlush();
  }

  shutdown(): Promise<void> {
    return this.next.shutdown();
  }
}

export const observability = new VoltAgentObservability({
  serviceName: "voltagent-restaurant-reservations",
  spanProcessors: [
    new MappingSpanProcessor(
      new BatchSpanProcessor(
        new OTLPTraceExporter({
          url: `${opikBase}/v1/private/otel/v1/traces`,
          headers: {
            Authorization: process.env.OPIK_API_KEY!,
            "Comet-Workspace": process.env.OPIK_WORKSPACE_NAME ?? process.env.OPIK_WORKSPACE!,
            projectName: PROJECT_NAME,
          },
        })
      )
    ),
  ],
});
