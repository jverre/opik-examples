from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from .activities import analyze_abstract, check_speaker_availability, write_review
    from .models import Review, Submission


@workflow.defn
class ReviewTalk:
    @workflow.run
    async def run(self, sub: Submission) -> Review:
        analysis = await workflow.execute_activity(
            analyze_abstract, sub, start_to_close_timeout=timedelta(seconds=60)
        )
        availability = await workflow.execute_activity(
            check_speaker_availability,
            sub,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=1), backoff_coefficient=2.0, maximum_attempts=5
            ),
        )
        # Durable timer: stands in for waiting on the committee's review window.
        # It survives a worker restart without re-running the LLM call above.
        await workflow.sleep(timedelta(seconds=2))
        verdict = await workflow.execute_activity(
            write_review,
            args=[sub, analysis, availability],
            start_to_close_timeout=timedelta(seconds=60),
        )
        return Review(
            talk_id=sub.talk_id,
            analysis=analysis,
            availability=availability,
            recommendation=verdict["recommendation"],
            review_text=verdict["review_text"],
        )
