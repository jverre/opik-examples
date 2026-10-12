"""The test suite: one item per episode, three plain-language assertions."""

import opik

from podcast_titles.config import (
    PROJECT_NAME,
    PROMPT_NAME,
    SUITE_NAME,
    TITLE_MODEL,
    opik_client,
)
from podcast_titles.writer import load_episodes, write_title

# The quality bar every title must clear. An LLM judge checks each assertion
# against the episode brief and the title the app produced.
ASSERTIONS = [
    "The title is 60 characters or fewer (use the length_in_characters field)",
    "The title contains the guest's full name exactly as written in the episode brief",
    "The title is plain and specific: no emoji, no exclamation marks, no words "
    "in ALL CAPS, and no clickbait phrasing",
]

# Models are flaky; judges are too. Run each episode three times and require
# two clean passes, so one unlucky sample does not flip an item.
EXECUTION_POLICY = {"runs_per_item": 3, "pass_threshold": 2}


def get_suite() -> opik.TestSuite:
    suite = opik_client().get_or_create_test_suite(
        name=SUITE_NAME,
        description="Episode title rules for the Second Draft podcast.",
        project_name=PROJECT_NAME,
        global_assertions=ASSERTIONS,
        global_execution_policy=EXECUTION_POLICY,
    )
    # insert() skips items that already exist, so re-running is safe.
    suite.insert([{"data": {"episode": ep}} for ep in load_episodes()])
    return suite


def make_task(version: str):
    """Build a run_tests task that titles every episode with one prompt version."""

    def task(item: dict) -> dict:
        episode = item["episode"]
        title = write_title(episode, version=version)
        return {
            "input": {"guest": episode["guest"], "notes": episode["notes"]},
            # The judge cannot count characters reliably, so hand it the count.
            "output": {"title": title, "length_in_characters": len(title)},
        }

    return task


def run_version(suite: opik.TestSuite, version: str):
    prompt = opik_client().get_prompt(
        name=PROMPT_NAME, version=version, project_name=PROJECT_NAME
    )
    if prompt is None:
        raise SystemExit(
            f"Prompt version {version} not found. "
            f"Run `podcast-titles push --version {version}` first."
        )
    return opik.run_tests(
        test_suite=suite,
        task=make_task(version),
        experiment_name=f"prompt-library-podcast-titles-{version}",
        experiment_config={
            "prompt_version": version,
            "prompt_commit": prompt.commit,
            "model": TITLE_MODEL,
        },
        prompts=[prompt],
        worker_threads=6,
        generate_report=False,
        verbose=1,
    )
