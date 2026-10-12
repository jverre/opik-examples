"""The three activities: two LLM calls and one deliberately flaky lookup."""

import json

from openai import AsyncOpenAI
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from temporalio import activity

from .models import AbstractAnalysis, Availability, Submission
from .settings import MODEL

_openai = AsyncOpenAI()
_tracer = trace.get_tracer("talk-review-activities")


async def _traced_chat(name: str, messages: list[dict], *, json_mode: bool = False) -> str:
    """One chat completion inside an OTel span that Opik renders as an `llm` span.

    TracingInterceptor makes the activity span current, so this span nests under
    the activity, which nests under the workflow, which nests under the client's
    StartWorkflow span. The gen_ai.* attributes are what Opik reads for the model
    name and token usage.
    """
    with _tracer.start_as_current_span(name) as span:
        response = await _openai.chat.completions.create(
            model=MODEL,
            messages=messages,
            **({"response_format": {"type": "json_object"}} if json_mode else {}),
        )
        content = response.choices[0].message.content or ""
        usage = response.usage
        span.set_attributes(
            {
                "gen_ai.operation.name": "chat",
                "gen_ai.system": "openai",
                "gen_ai.provider.name": "openai",
                "gen_ai.request.model": MODEL,
                "gen_ai.response.model": response.model,
                "input.value": json.dumps({"messages": messages}),
                "output.value": content,
            }
        )
        if usage:
            span.set_attributes(
                {
                    "gen_ai.usage.input_tokens": usage.prompt_tokens,
                    "gen_ai.usage.output_tokens": usage.completion_tokens,
                    "gen_ai.usage.prompt_tokens": usage.prompt_tokens,
                    "gen_ai.usage.completion_tokens": usage.completion_tokens,
                }
            )
        span.set_status(Status(StatusCode.OK))
        return content


# --- Activity 1: read the abstract like a program-committee member ----------


@activity.defn
async def analyze_abstract(sub: Submission) -> AbstractAnalysis:
    content = await _traced_chat(
        "analyze-abstract",
        [
            {
                "role": "system",
                "content": (
                    "You are a program-committee reviewer for a software engineering "
                    "conference. Read the abstract and reply with JSON: "
                    '{"level": "beginner"|"intermediate"|"advanced", '
                    '"concrete_claims": [string], "red_flags": [string], "summary": string}. '
                    "concrete_claims are specific, checkable facts or numbers the speaker "
                    "promises. red_flags are vague buzzwords, clickbait, or missing substance. "
                    "Use empty lists when there are none."
                ),
            },
            {"role": "user", "content": f"Title: {sub.title}\n\nAbstract: {sub.abstract}"},
        ],
        json_mode=True,
    )
    return AbstractAnalysis(**json.loads(content))


# --- Activity 2: speaker availability (canned calendar, flaky on purpose) ---

CALENDAR = {
    "Ingrid Halvorsen": {"2026-11-05": (True, "Free all day; arriving the evening before.")},
    "Rafael Quenby": {"2026-11-05": (False, "Already keynoting another event in Lisbon that day.")},
}


@activity.defn
async def check_speaker_availability(sub: Submission) -> Availability:
    # The planted failure: the calendar service drops the connection on the
    # first attempt of every call. Temporal retries by policy; both attempts show
    # up as separate RunActivity spans in the same Opik trace.
    if activity.info().attempt == 1:
        raise ConnectionError(
            "speaker-calendar service unavailable: connection reset (transient, succeeds on retry)"
        )
    available, note = CALENDAR.get(sub.speaker, {}).get(
        sub.conference_date, (True, "No conflicts on file.")
    )
    return Availability(speaker=sub.speaker, date=sub.conference_date, available=available, note=note)


# --- Activity 3: write the review ---------------------------------------------


@activity.defn
async def write_review(
    sub: Submission, analysis: AbstractAnalysis, availability: Availability
) -> dict:
    content = await _traced_chat(
        "write-review",
        [
            {
                "role": "system",
                "content": (
                    "You write the final program-committee note for a conference talk. "
                    'Reply with JSON: {"recommendation": "accept"|"waitlist"|"decline", '
                    '"review_text": string}. review_text is under 90 words, addressed to the '
                    "committee, and must mention the speaker's availability. Decline talks "
                    "whose abstract is all red flags; waitlist good talks whose speaker is "
                    "unavailable; accept good talks with an available speaker."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "title": sub.title,
                        "speaker": sub.speaker,
                        "analysis": analysis.__dict__,
                        "availability": availability.__dict__,
                    }
                ),
            },
        ],
        json_mode=True,
    )
    return json.loads(content)
