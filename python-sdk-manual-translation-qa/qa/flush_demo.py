"""What does client.flush() actually buy you? Send one tiny trace three ways.

    uv run python -m qa.flush_demo flush       # log, flush(), exit normally
    uv run python -m qa.flush_demo no-flush    # log, exit normally, no flush()
    uv run python -m qa.flush_demo hard-exit   # log, os._exit(0): no cleanup, no flush

Then `uv run python -m qa.flush_demo check` lists which of the three arrived.
No LLM calls, no cost, no OpenAI key needed.
"""

from __future__ import annotations

import os
import sys

import opik

PROJECT = "python-sdk-manual-translation-qa"
client = opik.Opik(project_name=PROJECT)


def log_one(mode: str) -> None:
    trace_id = client.trace(name=f"flush-demo-{mode}", input={"mode": mode}, tags=["flush-demo"]).id
    client.span(trace_id=trace_id, name="work", input={"mode": mode}, output={"ok": True})
    print(f"{mode}: logged trace {trace_id}", flush=True)


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "flush"

    if mode == "check":
        found = {t.name for t in client.search_traces(project_name=PROJECT, filter_string='tags contains "flush-demo"')}
        for name in ("flush-demo-flush", "flush-demo-no-flush", "flush-demo-hard-exit"):
            print(f"{name:22} {'ARRIVED' if name in found else 'missing'}")
        return

    log_one(mode)
    if mode == "flush":
        client.flush()  # blocks until the in-memory batch has been delivered
    elif mode == "hard-exit":
        os._exit(0)  # like a SIGKILL'd container or a serverless freeze: no atexit hooks run
    # "no-flush": fall off the end and let the interpreter shut down normally.


if __name__ == "__main__":
    main()
