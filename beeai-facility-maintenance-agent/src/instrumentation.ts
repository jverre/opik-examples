// Wires BeeAI to Opik. This is the only file that knows tracing exists.
//
// BeeAI emits OpenInference spans through @arizeai/openinference-instrumentation-beeai;
// a standard OTLP/HTTP exporter ships them to Opik's OpenTelemetry endpoint. Auth and
// routing (workspace + project) travel as plain HTTP headers, with no Opik SDK involved.
import { NodeSDK } from "@opentelemetry/sdk-node";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-http";
import { BeeAIInstrumentation } from "@arizeai/openinference-instrumentation-beeai";
import * as beeaiFramework from "beeai-framework";

export const PROJECT_NAME = "beeai-facility-maintenance-agent";

const workspace = process.env.OPIK_WORKSPACE ?? process.env.OPIK_WORKSPACE_NAME ?? "default";

// Opik Cloud by default; OPIK_URL_OVERRIDE (e.g. http://localhost:5173/api)
// redirects the same traces to a self-hosted instance.
const opikApiBase = (process.env.OPIK_URL_OVERRIDE ?? "https://www.comet.com/opik/api").replace(
  /\/+$/,
  "",
);

const beeAIInstrumentation = new BeeAIInstrumentation();

const sdk = new NodeSDK({
  traceExporter: new OTLPTraceExporter({
    url: `${opikApiBase}/v1/private/otel/v1/traces`,
    headers: {
      Authorization: process.env.OPIK_API_KEY ?? "",
      "Comet-Workspace": workspace,
      projectName: PROJECT_NAME,
    },
  }),
  instrumentations: [beeAIInstrumentation],
});
sdk.start();

// tsx loads beeai-framework before the instrumentation's module hook can see it,
// so patch the already-imported module explicitly (the documented step).
beeAIInstrumentation.manuallyInstrument(beeaiFramework);

/** Flush pending spans and stop the exporter. Call once, right before exit. */
export async function shutdownTracing(): Promise<void> {
  await sdk.shutdown();
}
