// SvelteKit runs this file once when the server starts. It is the whole
// Opik integration: an OpikExporter wired into an OpenTelemetry NodeSDK, plus
// the AI SDK's telemetry integration. (AI SDK v7 moved telemetry behind an
// explicit registerTelemetry call; in v4 to v6 the spans were emitted
// automatically.)
import { NodeSDK, tracing } from "@opentelemetry/sdk-node";
import { registerTelemetry } from "ai";
import { OpenTelemetry } from "@ai-sdk/otel";
import { OpikExporter } from "opik-vercel";
import { Opik } from "opik";
import { config } from "dotenv";
import { PROJECT_NAME } from "$lib/project";

// `npm run dev` does not export .env into process.env, so load it here.
// Variables that are already set (for example by the demo) win.
config({ quiet: true });

const exporter = new OpikExporter({
  // Pin the project so every trace lands in one place. The API key,
  // workspace and URL come from the OPIK_* environment variables.
  client: new Opik({ projectName: PROJECT_NAME }),
  tags: ["sveltekit", "streaming"],
});

const sdk = new NodeSDK({
  serviceName: PROJECT_NAME,
  // Export spans after 1s instead of the 5s default so a short-lived server
  // (like the demo's) does not stop with the last reply still queued.
  spanProcessors: [
    new tracing.BatchSpanProcessor(exporter, { scheduledDelayMillis: 1000 }),
  ],
});
sdk.start();

registerTelemetry(
  new OpenTelemetry({
    usage: true, // put token counts on the LLM spans so Opik can price them
    // The endpoint passes a thread id and trace name through runtimeContext.
    // Opik reads them from these span attributes; the thread id is what
    // stitches the turns of one chat into a single Opik thread.
    enrichSpan: ({ runtimeContext }) => {
      const attributes: Record<string, string> = {};
      if (runtimeContext?.threadId != null) {
        attributes["ai.telemetry.metadata.threadId"] = String(
          runtimeContext.threadId,
        );
      }
      if (runtimeContext?.traceName != null) {
        attributes["ai.telemetry.metadata.traceName"] = String(
          runtimeContext.traceName,
        );
      }
      return attributes;
    },
  }),
);

// Flush on shutdown so a final streamed reply is never lost.
for (const signal of ["SIGINT", "SIGTERM"] as const) {
  process.once(signal, () => {
    void sdk.shutdown().finally(() => process.exit(0));
  });
}
