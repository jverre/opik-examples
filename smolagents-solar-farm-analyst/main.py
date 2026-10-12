"""A smolagents analyst for a solar farm, traced to Opik over OpenTelemetry.

A CodeAgent on gpt-4o-mini answers questions about a fictional solar farm's
daily output CSV by writing pandas code and running it locally. The CSV has
three planted anomalies (a dead inverter, a stuck meter, a slow decline), so
there is something concrete to find. Every step is exported to Opik as
OpenTelemetry spans by openinference's SmolagentsInstrumentor: the model call
that wrote the code, and the tool call that executed it.
"""

import configparser
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_NAME = "smolagents-solar-farm-analyst"
CSV_PATH = Path(__file__).parent / "data" / "solar_output.csv"

load_dotenv(Path(__file__).parent / ".env")


def configure_opik_otel() -> None:
    """Point the OTLP exporter at Opik. Keys come from the environment or
    ~/.opik.config (written by `opik configure`); nothing is hardcoded."""
    config = configparser.ConfigParser()
    config.read(Path.home() / ".opik.config")

    def setting(env: str, key: str) -> str:
        return os.getenv(env) or config.get("opik", key)

    api_key = setting("OPIK_API_KEY", "api_key")
    workspace = setting("OPIK_WORKSPACE", "workspace")
    base_url = os.getenv("OPIK_URL_OVERRIDE", "https://www.comet.com/opik/api").rstrip("/")

    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = f"{base_url}/v1/private/otel"
    os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = (
        f"Authorization={api_key},Comet-Workspace={workspace},projectName={PROJECT_NAME}"
    )


configure_opik_otel()

# --- Instrumentation: the documented smolagents <> Opik pattern ---------------

from openinference.instrumentation.smolagents import SmolagentsInstrumentor  # noqa: E402
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter  # noqa: E402
from opentelemetry.sdk.trace import TracerProvider  # noqa: E402
from opentelemetry.sdk.trace.export import SimpleSpanProcessor  # noqa: E402

trace_provider = TracerProvider()
trace_provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter()))
SmolagentsInstrumentor().instrument(tracer_provider=trace_provider)

# --- The agent -----------------------------------------------------------------

from smolagents import CodeAgent, OpenAIServerModel  # noqa: E402

model = OpenAIServerModel(model_id="gpt-4o-mini")

# The agent answers by writing Python. smolagents' local executor only lets that
# code import what you authorize: here, pandas on top of the safe defaults.
agent = CodeAgent(
    tools=[],
    model=model,
    additional_authorized_imports=["pandas"],
    max_steps=6,
)

BRIEFING = f"""\
You are a performance analyst for Larkmoor Ridge Solar, a fictional farm with
six inverters (INV-01 to INV-06), each on a 250 kWp array.
The daily output for 1 March to 29 May 2026 is the CSV file at: {CSV_PATH}

Columns: date (YYYY-MM-DD), inverter_id, energy_kwh (the inverter's daily
output), irradiance_kwh_m2 (daily sunshine at the site, the same for every
inverter on a given day), fault_code (blank when the inverter logged no
fault), fault_minutes.

Load it with pandas and answer with concrete numbers from the data. Give your
final answer as two or three plain sentences, not as a raw Python object.
"""

QUESTIONS = [
    "Did any inverter produce zero energy on a day when the others were "
    "producing? If so, which one, on which dates, and what fault code (if any) "
    "was logged?",
    "Look for an inverter whose daily energy_kwh barely changes for a long "
    "stretch even though irradiance_kwh_m2 changes a lot. Which inverter, which "
    "dates, and what value does it report?",
    "Compute each inverter's specific yield (energy_kwh divided by "
    "irradiance_kwh_m2) for 10 May to 29 May. Does one inverter lag the others "
    "by a consistent margin, and by roughly what percentage versus the median "
    "of the other five?",
]


def main() -> None:
    for i, question in enumerate(QUESTIONS, 1):
        print(f"\n{'=' * 72}\nQuestion {i}: {question}\n{'=' * 72}")
        answer = agent.run(BRIEFING + "\nQuestion: " + question)
        print(f"\nAnswer {i}: {answer}")

    # Shut the provider down so the last spans are exported before exit.
    trace_provider.shutdown()
    print(f"\nDone. Open the '{PROJECT_NAME}' project in Opik: one trace per question.")


if __name__ == "__main__":
    main()
