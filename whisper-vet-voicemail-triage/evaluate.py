"""Test suite for the triage note: is it safe to hand to a nurse?

A triage note fails quietly: a rabbit that stopped eating filed as "routine", a
callback number with one digit wrong. This suite feeds each transcript that
main.py produced back through the triage step and lets an LLM judge check three
assertions against the transcript:

  1. the urgency matches what the transcript describes,
  2. the callback number is exactly the one the caller gave, and
  3. the pet and owner details match, with nothing invented.

Run `uv run main.py` first: it caches each voicemail's transcript in out/.
Each `opik.run_tests` call becomes an experiment in Opik, with a pass/fail
verdict per item and per assertion.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

EXAMPLE_DIR = Path(__file__).resolve().parent
OUT_DIR = EXAMPLE_DIR / "out"
PROJECT_NAME = "whisper-vet-voicemail-triage"

load_dotenv(EXAMPLE_DIR / ".env")
os.environ["OPIK_PROJECT_NAME"] = PROJECT_NAME
os.environ.pop("OPENAI_BASE_URL", None)

import opik

from main import triage

SUITE_NAME = "whisper-vet-voicemail-triage-suite"

ASSERTIONS = [
    "The urgency level fits what the transcript describes: possible "
    "poisoning, breathing trouble, collapse, or a rabbit that has stopped "
    "eating is an emergency; a stable animal in pain or with a new problem "
    "is same_day; bookings, vaccines, refills, and questions are routine. "
    "A calm or polite tone does not lower the urgency.",
    "The callback number in the note is exactly the number the caller gave "
    "in the transcript. If the caller corrected the number, the corrected "
    "one is used. No digits are invented, dropped, or swapped.",
    "The pet name, the pet species, and the owner name match the transcript, "
    "and the note states nothing the caller did not say (no invented "
    "symptoms, times, or medications).",
]


def task(item: dict) -> dict:
    """Triage one transcript. The judge sees this input and output."""
    note = triage(item["transcript"])
    return {"input": {"transcript": item["transcript"]}, "output": note}


if __name__ == "__main__":
    cached = sorted(OUT_DIR.glob("*.json"))
    if not cached:
        raise SystemExit("No transcripts in out/. Run `uv run main.py` first.")

    client = opik.Opik()
    suite = client.get_or_create_test_suite(
        name=SUITE_NAME,
        project_name=PROJECT_NAME,
        global_assertions=ASSERTIONS,
        # The triage model and the judge are both small LLMs, so a single
        # run is flaky. Each item runs RUNS_PER_ITEM times and must pass
        # PASS_THRESHOLD of them: the noise is absorbed, a real regression
        # (which fails every run) is not.
        global_execution_policy={"runs_per_item": 3, "pass_threshold": 2},
    )

    # Add each voicemail once; re-runs reuse the existing items.
    existing = {item["data"]["voicemail"] for item in suite.get_items()}
    for path in cached:
        record = json.loads(path.read_text())
        if record["voicemail"] not in existing:
            suite.insert(
                [{"data": {"voicemail": record["voicemail"], "transcript": record["transcript"]}}]
            )

    result = opik.run_tests(test_suite=suite, task=task)
    print(f"\nPass rate: {result.pass_rate:.0%}")
    opik.flush_tracker()
