"""The Opik test suite: rules for every email plus expected values per email."""

from pathlib import Path
from typing import Any

import opik

from . import PROJECT_NAME
from .agent import extract_event

EMAIL_DIR = Path(__file__).parent.parent / "data" / "emails"

# Rules that every extraction must satisfy, written in plain language.
GLOBAL_ASSERTIONS = [
    "The output is either a calendar event with the fields title, date, start_time, "
    "end_time, all_day, timezone, location, meeting_link and attendees, or a "
    "no_event result with a reason",
    "Every non-null value is stated in the email or directly derivable from it, for "
    "example a relative date resolved against the email's Date header. Null fields and "
    "an empty attendees list are fine",
    "No value is invented: an end time, time zone, location or meeting link that the "
    "email never states is null, and attendees the email never names are not listed",
    "Dates look like YYYY-MM-DD and times are 24-hour HH:MM",
]

# Expected values live in the assertions, never in the item data, so the LLM judge
# cannot read the answers off the input.
ITEM_ASSERTIONS: dict[str, list[str]] = {
    "01-product-sync.txt": [
        "The date is 2026-11-04, from 10:00 to 10:45, and the location is Fjord 2 (extra words like 'room' or 'second floor' are fine)",
        "The meeting link is https://meet.harbourline.example/product-sync",
    ],
    "02-vendor-call.txt": [
        "The date is 2026-11-10 and the start time is 15:00, resolved from 'tomorrow at 3pm'",
        "The end time, time zone, location and meeting link are all null because the "
        "email gives none of them ('I'll send a link later' is not a link)",
    ],
    "03-offsite.txt": [
        "The date is 2026-11-20 and all_day is true, with no start or end time",
        "The location is null because the venue is still TBD",
    ],
    "04-design-review-moved.txt": [
        "The date is 2026-11-06 from 11:30 to 12:30, the rescheduled time, not the "
        "quoted Thursday 2pm slot",
        "The location is Atrium B",
    ],
    "05-dinner.txt": [
        "The date is 2026-11-14 and the start time is 20:00",
        "The time zone is null: the sender's signature says Lisboa but the email never "
        "names a time zone",
        "The end time is null, and no guests are invented: the 'kids' are unnamed, so they are not listed",
    ],
    "06-coffee.txt": [
        "The result is no_event, because the email only floats 'maybe Wednesday or "
        "Thursday morning' with no firm date or time",
    ],
    "07-planning-call.txt": [
        "The date is 2026-11-17, the start time is 14:00 and the time zone is Eastern "
        "(ET or EST are fine)",
        "The meeting link is https://teams.example/l/q1-planning",
        "Dana, Olu and Mei are listed as attendees, and Tobias is not",
        "The end time and location are null",
    ],
}


def load_items() -> list[dict[str, Any]]:
    return [
        {"data": {"file": name, "email": (EMAIL_DIR / name).read_text()}, "assertions": rules}
        for name, rules in ITEM_ASSERTIONS.items()
    ]


def run_suite(prompt: str, runs_per_item: int = 3) -> Any:
    """Insert the items (deduplicated on re-runs) and run one experiment."""
    client = opik.Opik(project_name=PROJECT_NAME)
    suite = client.get_or_create_test_suite(
        name=PROJECT_NAME,
        description="Calendar-event extraction from messy emails",
        project_name=PROJECT_NAME,
        global_assertions=GLOBAL_ASSERTIONS,
        # LLM judges are noisy: each email is run 3 times and must pass 2 of 3.
        global_execution_policy={"runs_per_item": runs_per_item, "pass_threshold": 2},
    )
    suite.insert(load_items())

    def task(item: dict[str, Any]) -> dict[str, Any]:
        return {"input": item, "output": extract_event(item["email"], prompt)}

    return opik.run_tests(
        test_suite=suite,
        task=task,
        experiment_name=f"calendar-extraction-{prompt}-gpt-4o-mini",
        experiment_config={"prompt": prompt, "model": "gpt-4o-mini"},
        worker_threads=4,
        verbose=0,
        generate_report=False,
    )
