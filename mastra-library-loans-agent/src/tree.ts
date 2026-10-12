// Prints the agent-loop span tree of every trace in the Opik project, using the
// Opik TypeScript SDK's REST client. Useful to confirm what landed without
// opening the UI: tool spans with real args/results, llm spans with usage and cost.
import { config } from "dotenv";
import { fileURLToPath } from "node:url";
import { Opik } from "opik";

config({ path: fileURLToPath(new URL("../.env", import.meta.url)), quiet: true });

const project = process.env.OPIK_PROJECT_NAME ?? "mastra-library-loans-agent";
const client = new Opik({ projectName: project });

const short = (v: unknown, n = 90) => {
  const s = typeof v === "string" ? v : JSON.stringify(v ?? "");
  return s.length > n ? `${s.slice(0, n)}...` : s;
};

const traces = (await client.api.traces.getTracesByProject({ projectName: project, size: 50 })).content ?? [];
console.log(`project: ${project} | traces: ${traces.length}`);

for (const trace of [...traces].reverse()) {
  const spans = (await client.api.spans.getSpansByProject({ projectName: project, traceId: trace.id, size: 200 })).content ?? [];
  const byId = new Map(spans.map((s) => [s.id, s]));
  const keep = (n?: string) => ["invoke_agent", "agent_step", "chat", "execute_tool"].some((p) => (n ?? "").startsWith(p));
  const kept = spans.filter((s) => keep(s.name));
  // Hide Mastra helper spans (model_chunk, processor_run, ...): attach each kept span to its nearest kept ancestor.
  const keptParent = (s: (typeof spans)[number]): string | undefined => {
    let p = s.parentSpanId ? byId.get(s.parentSpanId) : undefined;
    while (p && !keep(p.name)) p = p.parentSpanId ? byId.get(p.parentSpanId) : undefined;
    return p?.id;
  };
  const children = (id?: string) =>
    kept.filter((s) => keptParent(s) === id).sort((a, b) => +new Date(a.startTime) - +new Date(b.startTime));
  console.log(`\ntrace ${trace.id}`);
  console.log(`  input : ${short(trace.input)}`);
  console.log(`  output: ${short(trace.output)}`);
  const print = (id: string | undefined, depth: number) => {
    for (const s of children(id)) {
      const extra =
        s.type === "tool" ? ` args=${short(s.input)} result=${short(s.output)}` :
        s.type === "llm" ? ` tokens=${s.usage?.total_tokens} cost=$${s.totalEstimatedCost ?? "none"}` : "";
      console.log(`  ${"  ".repeat(depth)}${s.name} [${s.type}]${extra}`);
      print(s.id, depth + 1);
    }
  };
  print(undefined, 0);
}
await client.flush();
