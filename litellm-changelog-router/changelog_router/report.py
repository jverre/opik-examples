"""Read the llm spans of a run back from Opik and print a per-model table."""

import time
from dataclasses import dataclass, field

import opik

from changelog_router import PROJECT_NAME


@dataclass
class ModelRow:
    model: str
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost: float = 0.0
    latencies: list[float] = field(default_factory=list)

    @property
    def mean_latency(self) -> float:
        return sum(self.latencies) / len(self.latencies)


def latest_run_id(client: opik.Opik) -> str | None:
    """Return the run id carried by the most recent trace in the project."""
    traces = client.search_traces(project_name=PROJECT_NAME, max_results=50)
    traces.sort(key=lambda t: t.start_time, reverse=True)
    for trace in traces:
        for tag in trace.tags or []:
            if tag.startswith("run:"):
                return tag.removeprefix("run:")
    return None


def collect(client: opik.Opik, run_id: str, expected: int | None = None, wait_s: float = 45) -> list[ModelRow]:
    """Aggregate llm spans per model. Polls briefly because ingestion is async."""
    deadline = time.time() + wait_s
    while True:
        rows: dict[str, ModelRow] = {}
        traces = client.search_traces(
            project_name=PROJECT_NAME, filter_string=f'tags contains "run:{run_id}"', max_results=200
        )
        spans = []
        for trace in traces:
            spans += [
                s
                for s in client.search_spans(project_name=PROJECT_NAME, trace_id=trace.id, max_results=50)
                if s.type == "llm"
            ]
        priced = [s for s in spans if s.total_estimated_cost is not None]
        for s in priced:
            row = rows.setdefault(s.model, ModelRow(model=s.model))
            row.calls += 1
            row.prompt_tokens += (s.usage or {}).get("prompt_tokens", 0)
            row.completion_tokens += (s.usage or {}).get("completion_tokens", 0)
            row.cost += s.total_estimated_cost
            row.latencies.append((s.end_time - s.start_time).total_seconds())
        if expected is None or len(priced) >= expected or time.time() > deadline:
            return sorted(rows.values(), key=lambda r: r.cost)
        time.sleep(3)


def print_table(run_id: str, rows: list[ModelRow]) -> None:
    print(f"\nPer-model comparison for run {run_id} (read back from Opik project '{PROJECT_NAME}')\n")
    header = f"{'Model':<28}{'Calls':>6}{'Prompt tok':>12}{'Compl. tok':>12}{'Cost (USD)':>13}{'Mean latency':>14}{'Max':>8}"
    print(header)
    print("-" * len(header))
    for r in rows:
        print(
            f"{r.model:<28}{r.calls:>6}{r.prompt_tokens:>12}{r.completion_tokens:>12}"
            f"{'$' + format(r.cost, '.6f'):>13}{r.mean_latency:>13.2f}s{max(r.latencies):>7.2f}s"
        )
    if len(rows) >= 2:
        cheap, dear = rows[0], rows[-1]
        print(
            f"\n{dear.model} cost {dear.cost / cheap.cost:.1f}x as much as {cheap.model} "
            f"and its mean latency was {dear.mean_latency / cheap.mean_latency:.1f}x."
        )
