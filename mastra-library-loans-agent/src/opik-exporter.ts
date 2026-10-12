// A thin OTLP exporter that fixes up Mastra's spans for Opik before they leave
// the process. Mastra's OtelExporter maps cleanly except for a few things that
// matter in the Opik UI, so we patch exactly those:
//   1. provider/model: Mastra reports provider "openai.responses" and the dated
//      model "gpt-4o-mini-2024-07-18"; Opik prices a span only when it sees
//      provider "openai" and a known model name, so cost would be empty.
//   2. trace output: Mastra puts the final answer in mastra.agent_run.output,
//      which Opik does not read, so the trace Output column would be empty
//      (-> gen_ai.completion).
//   3. trace input: same story, mastra.agent_run.input -> gen_ai.prompt.
//   4. noise: Mastra bookkeeping attributes would be dumped into the Input of
//      the root and tool spans, so they are dropped there.
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-http";
import type { ExportResult } from "@opentelemetry/core";
import type { ReadableSpan } from "@opentelemetry/sdk-trace-base";

const DATED_SUFFIX = /-\d{4}-\d{2}-\d{2}$/;

export class OpikSpanExporter extends OTLPTraceExporter {
  override export(spans: ReadableSpan[], resultCallback: (result: ExportResult) => void): void {
    for (const span of spans) patch(span.attributes as Record<string, unknown>);
    super.export(spans, resultCallback);
  }
}

function patch(attrs: Record<string, unknown>): void {
  const op = attrs["gen_ai.operation.name"];

  if (op === "chat") {
    const provider = String(attrs["gen_ai.provider.name"] ?? "");
    if (provider.startsWith("openai")) {
      attrs["gen_ai.provider.name"] = "openai";
      attrs["gen_ai.system"] = "openai";
    }
    const model = attrs["gen_ai.response.model"];
    if (typeof model === "string") attrs["gen_ai.response.model"] = model.replace(DATED_SUFFIX, "");
  }

  if (op === "invoke_agent") {
    // Opik maps gen_ai.prompt / gen_ai.completion to the trace Input / Output.
    const input = attrs["mastra.agent_run.input"];
    if (typeof input === "string") attrs["gen_ai.prompt"] = input;
    const output = attrs["mastra.agent_run.output"];
    if (typeof output === "string") {
      try {
        attrs["gen_ai.completion"] = (JSON.parse(output) as { text?: string }).text ?? output;
      } catch {
        attrs["gen_ai.completion"] = output;
      }
    }
    // The system prompt would otherwise be dumped into the trace Input; keep it as metadata.
    attrs["gen_ai.agent.system_instructions"] = attrs["gen_ai.system_instructions"];
    delete attrs["gen_ai.system_instructions"];
    delete attrs["mastra.agent_run.input"];
    delete attrs["mastra.agent_run.output"];
    dropMastraNoise(attrs);
  }

  // Tool spans keep gen_ai.tool.call.arguments / .result: Opik reads them as the
  // span's Input / Output and uses them to set the span type to "tool".
  if (op === "execute_tool") dropMastraNoise(attrs);
}

// Unmapped attributes land in the span Input in Opik, so drop Mastra bookkeeping.
function dropMastraNoise(attrs: Record<string, unknown>): void {
  for (const key of Object.keys(attrs)) {
    if (key === "mastra.span.type" || key.startsWith("mastra.metadata.")) delete attrs[key];
  }
}
