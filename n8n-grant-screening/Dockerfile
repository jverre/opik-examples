# n8n with the Opik OpenTelemetry hooks baked in.
#
# n8n-observability plugs into n8n's lifecycle through EXTERNAL_HOOK_FILES and
# exports one OTel span per workflow execution and per node run. No node is
# added to the workflow and no code is written. The OTLP endpoint and headers
# that point at Opik are set in docker-compose.yml.
FROM n8nio/n8n:2.42.7

USER root
RUN npm install -g n8n-observability@1.0.3

ENV EXTERNAL_HOOK_FILES=/usr/local/lib/node_modules/n8n-observability/dist/hooks.cjs

USER node
