"""Write an episode title with a prompt version fetched from the library."""

import json

from openai import OpenAI
from opik import opik_context, track
from opik.integrations.openai import track_openai

from podcast_titles.config import (
    EPISODES_FILE,
    PROJECT_NAME,
    PROMPT_NAME,
    TITLE_MODEL,
    opik_client,
)

# Every call made through this client is logged to Opik as an llm span.
_openai = track_openai(OpenAI(), project_name=PROJECT_NAME)


def load_episodes() -> list[dict]:
    return json.loads(EPISODES_FILE.read_text())


def episode_brief(episode: dict) -> str:
    return (
        f"Guest: {episode['guest']}, {episode['role']}\n"
        f"Episode notes: {episode['notes']}"
    )


@track(name="write_title", project_name=PROJECT_NAME)
def write_title(episode: dict, version: str | None = None) -> str:
    """Title one episode with the named prompt version (latest if None).

    The prompt is fetched from the library on every call, so publishing a new
    version changes the app's behaviour without a deploy. The version and
    commit that actually ran are recorded in the trace metadata.
    """
    prompt = opik_client().get_prompt(
        name=PROMPT_NAME, version=version, project_name=PROJECT_NAME
    )
    if prompt is None:
        raise SystemExit(
            f"Prompt '{PROMPT_NAME}' (version={version or 'latest'}) not found. "
            "Run `podcast-titles push --version v1` first."
        )
    opik_context.update_current_trace(
        metadata={
            "prompt_name": prompt.name,
            "prompt_version": prompt.version,
            "prompt_commit": prompt.commit,
            "episode_id": episode["id"],
        }
    )
    response = _openai.chat.completions.create(
        model=TITLE_MODEL,
        messages=[
            {"role": "system", "content": prompt.prompt},
            {"role": "user", "content": episode_brief(episode)},
        ],
    )
    return response.choices[0].message.content.strip().strip('"')
