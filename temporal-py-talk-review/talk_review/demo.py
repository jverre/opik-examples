"""Self-contained demo: starts a local Temporal dev server, spawns the worker as
a separate OS process, runs two talk reviews as the client, and shuts down."""

import asyncio
import json
import signal
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment

from .models import Review, Submission
from .settings import OPIK_PROJECT_NAME, TASK_QUEUE, require_env
from .tracing import setup_tracing, tracing_interceptor
from .workflows import ReviewTalk

PORT = 7400
ADDRESS = f"127.0.0.1:{PORT}"
SUBMISSIONS = Path(__file__).resolve().parent.parent / "data" / "submissions.json"


def start_worker() -> subprocess.Popen:
    env = {"TEMPORAL_ADDRESS": ADDRESS}
    import os

    proc = subprocess.Popen(
        [sys.executable, "-m", "talk_review.worker"],
        env={**os.environ, **env},
        stdout=subprocess.PIPE,
        text=True,
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        print(f"[worker] {line}", end="")
        if "WORKER_READY" in line:
            return proc
    raise RuntimeError(f"Worker exited early with code {proc.wait()}")


async def review_all() -> None:
    provider = setup_tracing("talk-review-client")
    tracer = trace.get_tracer("talk-review-client")

    print("Starting local Temporal dev server (downloads on first run)...")
    async with await WorkflowEnvironment.start_local(port=PORT, ui=False) as env:
        print(f"Temporal dev server ready on {ADDRESS}")
        worker = start_worker()
        client = await Client.connect(ADDRESS, interceptors=[tracing_interceptor()])
        try:
            for raw in json.loads(SUBMISSIONS.read_text()):
                sub = Submission(**raw)
                print(f"\n=== {sub.talk_id}: {sub.title}")
                # Root span per talk. The interceptor's StartWorkflow span nests
                # under it and the worker's spans nest under that: one trace.
                with tracer.start_as_current_span(f"review:{sub.talk_id}") as span:
                    span.set_attribute("input.value", json.dumps(asdict(sub)))
                    try:
                        review: Review = await client.execute_workflow(
                            ReviewTalk.run, sub, id=f"review-{sub.talk_id}", task_queue=TASK_QUEUE
                        )
                    except Exception as err:
                        span.set_status(Status(StatusCode.ERROR, str(err)))
                        raise
                    span.set_attribute("output.value", json.dumps(asdict(review)))
                    span.set_status(Status(StatusCode.OK))
                a = review.availability
                print(f"Speaker available: {a.available} ({a.note})")
                print(f"Recommendation: {review.recommendation}")
                print(f"Review: {review.review_text}")
        finally:
            print("\nShutting down...")
            worker.send_signal(signal.SIGINT)  # worker drains, then flushes its spans
            worker.wait()
            provider.shutdown()  # flush the client's spans too
    print(f'Done. Open the "{OPIK_PROJECT_NAME}" project in Opik.')


def main() -> None:
    require_env("OPENAI_API_KEY")
    asyncio.run(review_all())


if __name__ == "__main__":
    main()
