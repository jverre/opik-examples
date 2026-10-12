// Mastra instance with Opik observability. Tracing is configuration only:
// Mastra's Observability layer records agent runs, LLM calls and tool
// executions, and the OtelExporter ships them to Opik's OTLP endpoint.
// https://www.comet.com/docs/opik/integrations/mastra
import { Mastra } from "@mastra/core/mastra";
import { Observability } from "@mastra/observability";
import { OtelExporter } from "@mastra/otel-exporter";
import { PinoLogger } from "@mastra/loggers";
import { LibSQLStore } from "@mastra/libsql";
import { OpikSpanExporter } from "./opik-exporter.ts";
import { loansAgent } from "./agent.ts";

export const PROJECT_NAME = process.env.OPIK_PROJECT_NAME ?? "mastra-library-loans-agent";

const opikBase = (process.env.OPIK_URL_OVERRIDE ?? "https://www.comet.com/opik/api").replace(/\/+$/, "");

const otlpEndpoint = `${opikBase}/v1/private/otel/v1/traces`;
const headers = {
  Authorization: process.env.OPIK_API_KEY!,
  "Comet-Workspace": process.env.OPIK_WORKSPACE!,
  projectName: PROJECT_NAME,
};

export const mastra = new Mastra({
  agents: { loansAgent },
  storage: new LibSQLStore({ id: "memory-store", url: ":memory:" }),
  logger: new PinoLogger({ name: "Mastra", level: "warn" }),
  observability: new Observability({
    configs: {
      default: {
        serviceName: "mastra-library-loans-agent",
        exporters: [
          new OtelExporter({
            provider: { custom: { endpoint: otlpEndpoint, protocol: "http/json", headers } },
            exporter: new OpikSpanExporter({ url: otlpEndpoint, headers }),
          }),
        ],
      },
    },
  }),
});
