"""Send the same changelog request to any model through LiteLLM."""

import time
from dataclasses import dataclass

import litellm
import opik
from opik import opik_context

from changelog_router import PROJECT_NAME
from changelog_router.commits import Release

SYSTEM_PROMPT = """You write release notes for an open-source project.
Turn the raw commit list into a changelog entry in Markdown:
- Start with a one-sentence summary of the release.
- Group entries under "Breaking changes" (only if any), "Added", "Fixed" and "Improved".
- Skip dependency bumps, CI, merge commits and pure refactors unless users are affected.
- Write for users, not for the team: no commit hashes, no author names.
- Never invent features that are not in the commit list.
Keep it under 250 words."""


@dataclass
class Draft:
    model: str
    version: str
    text: str
    latency_s: float


@opik.track(name="write_changelog", project_name=PROJECT_NAME)
def write_changelog(model: str, release: Release, run_id: str) -> Draft:
    """One routed call. The surrounding trace is tagged with the model and run.

    LiteLLM runs inside @opik.track, so the current span data is handed to the
    OpikLogger callback via metadata. Without it the llm span would land in a
    separate, orphaned trace instead of under this one.
    """
    short_name = model.split("/")[-1]
    opik_context.update_current_trace(
        tags=[short_name, f"run:{run_id}", release.version],
        metadata={"model": model, "release": release.version, "run_id": run_id},
    )

    start = time.perf_counter()
    response = litellm.completion(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Product: {release.product} ({release.description})\n"
                    f"Release: {release.version}, {release.date}\n\n"
                    f"Commits:\n{release.commit_lines()}"
                ),
            },
        ],
        max_tokens=700,
        temperature=0.2,
        metadata={
            "opik": {
                "current_span_data": opik_context.get_current_span_data(),
                "tags": [short_name],
            }
        },
    )
    latency = time.perf_counter() - start
    return Draft(
        model=model,
        version=release.version,
        text=response.choices[0].message.content.strip(),
        latency_s=latency,
    )
