"""Send Pydantic AI's OpenTelemetry spans to Opik via logfire."""

import configparser
import os
from pathlib import Path

import logfire
from opik.integrations.otel import OpikSpanProcessor

from . import PROJECT_NAME


def _credentials() -> tuple[str, str]:
    """API key and workspace from the environment, else from ~/.opik.config."""
    config = configparser.ConfigParser()
    config.read(Path.home() / ".opik.config")
    api_key = os.getenv("OPIK_API_KEY") or config.get("opik", "api_key", fallback="")
    workspace = os.getenv("OPIK_WORKSPACE") or config.get("opik", "workspace", fallback="")
    if not api_key or not workspace:
        raise SystemExit("Set OPIK_API_KEY and OPIK_WORKSPACE (or run `opik configure`).")
    return api_key, workspace


def setup_tracing() -> None:
    api_key, workspace = _credentials()
    base = os.getenv("OPIK_URL_OVERRIDE", "https://www.comet.com/opik/api").rstrip("/")
    os.environ["OPIK_PROJECT_NAME"] = PROJECT_NAME
    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = f"{base}/v1/private/otel"
    os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = (
        f"Authorization={api_key},Comet-Workspace={workspace},projectName={PROJECT_NAME}"
    )
    os.environ["OTEL_METRICS_EXPORTER"] = "none"

    # OpikSpanProcessor exports the spans and links them to the surrounding
    # @opik.track trace, so each extraction is ONE trace with the model calls nested.
    logfire.configure(
        send_to_logfire=False, console=False, additional_span_processors=[OpikSpanProcessor()]
    )
    logfire.instrument_pydantic_ai()


def flush() -> None:
    logfire.force_flush()
