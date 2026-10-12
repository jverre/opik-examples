"""The worker process: runs the workflow code and the activities (including the
OpenAI calls) and exports its spans to Opik with the trace context the client
started. Run it standalone against any Temporal server, or let `demo` spawn it."""

import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from .activities import analyze_abstract, check_speaker_availability, write_review
from .settings import TASK_QUEUE, TEMPORAL_ADDRESS
from .tracing import setup_tracing, tracing_interceptor
from .workflows import ReviewTalk


async def run() -> None:
    provider = setup_tracing("talk-review-worker")
    interceptor = tracing_interceptor()
    client = await Client.connect(TEMPORAL_ADDRESS, interceptors=[interceptor])
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[ReviewTalk],
        activities=[analyze_abstract, check_speaker_availability, write_review],
        # No `interceptors=` here: a Worker automatically picks up the worker-side
        # half of any interceptor already on its Client. Passing the same
        # TracingInterceptor again records every workflow and activity span twice.
    )
    print(f'WORKER_READY on {TEMPORAL_ADDRESS}, task queue "{TASK_QUEUE}"', flush=True)
    try:
        await worker.run()  # until cancelled (SIGINT/SIGTERM)
    finally:
        provider.shutdown()  # flush remaining spans to Opik


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
