"""OpenTelemetry setup shared by the client process and the worker process.

Opik's documented Temporal pattern: put Temporal's `TracingInterceptor` on the
client and on the worker, and point an OTLP exporter at Opik's OpenTelemetry
endpoint in *both* processes. The interceptor carries the trace context through
Temporal's own headers, so spans from the two processes join into one trace.
"""

import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from temporalio.contrib.opentelemetry import TracingInterceptor

from .settings import OPIK_PROJECT_NAME, require_env


def setup_tracing(service_name: str) -> TracerProvider:
    base = os.environ.get("OPIK_URL_OVERRIDE", "https://www.comet.com/opik/api").rstrip("/")
    exporter = OTLPSpanExporter(
        endpoint=f"{base}/v1/private/otel/v1/traces",
        headers={
            "Authorization": require_env("OPIK_API_KEY"),
            "Comet-Workspace": require_env("OPIK_WORKSPACE"),
            "projectName": OPIK_PROJECT_NAME,
        },
    )
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return provider


def tracing_interceptor() -> TracingInterceptor:
    return TracingInterceptor()
