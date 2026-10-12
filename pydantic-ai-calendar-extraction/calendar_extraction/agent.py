"""The Pydantic AI agent, in two prompt flavours, and the traced extraction function."""

from functools import cache
from typing import Any

import opik
from opik import opik_context
from pydantic_ai import Agent

from . import MODEL, PROJECT_NAME
from .models import CalendarEvent, NoEvent

BASE = (
    "You read one email and turn it into a calendar event. The email starts with "
    "headers; resolve relative dates such as 'tomorrow' or 'next Friday' against "
    "its Date header. If the email does not describe a concrete event with a date, "
    "return NoEvent. If it was rescheduled, return the latest time, not the old one."
)

PROMPTS = {
    # Strict: unknown means null.
    "strict": BASE
    + " Fill in every field the email actually states, including a time zone such "
    "as CET or Eastern when one is written. If a field is not stated, leave it null "
    "(or the list empty). Never guess an end time, a time zone, a location or a link.",
    # Eager: a plausible-sounding prompt that quietly asks for invention.
    "eager": BASE
    + " Calendar entries should be complete, so never leave a field empty: if the "
    "email omits an end time assume one hour, assume the sender's time zone, and "
    "pick the most likely venue.",
}


@cache
def get_agent(prompt: str) -> Agent:
    return Agent(
        MODEL,
        name="event_extractor",
        output_type=[CalendarEvent, NoEvent],
        system_prompt=PROMPTS[prompt],
    )


@opik.track(name="extract_event", project_name=PROJECT_NAME)
def extract_event(email: str, prompt: str = "strict") -> dict[str, Any]:
    """One traced extraction: raw email in, CalendarEvent or NoEvent out.

    The Pydantic AI spans (invoke_agent, chat) arrive over OpenTelemetry and are
    merged under this trace by OpikSpanProcessor.
    """
    opik_context.update_current_trace(tags=[f"prompt:{prompt}"], metadata={"prompt": prompt})
    output = get_agent(prompt).run_sync(email).output
    kind = "event" if isinstance(output, CalendarEvent) else "no_event"
    return {"kind": kind, **output.model_dump()}
