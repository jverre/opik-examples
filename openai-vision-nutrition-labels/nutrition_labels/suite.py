"""The Opik test suite: format rules for every label, expected values per label."""

from typing import Any

import opik

from nutrition_labels import PROJECT_NAME
from nutrition_labels.extract import extract_label
from nutrition_labels.render import LABELS, get_label

SUITE_NAME = PROJECT_NAME
EXPERIMENT_NAME = f"{PROJECT_NAME}-gpt-4o-mini"

# Judged from the output alone, for every label.
GLOBAL_ASSERTIONS = [
    "The output has all eight fields (product_name, serving_size_g, calories, total_fat_g, "
    "total_carbs_g, protein_g, sodium_mg, allergens) and every numeric field is a plain number",
    "allergens is a list of short lowercase allergen names, not a sentence",
    "The values look like one serving of a packaged food: calories are kilocalories "
    "(not kilojoules) and no number is negative",
]

# Three runs per label, two must pass: a vision model is not deterministic, and one
# lucky read should not hide a label it usually gets wrong.
EXECUTION_POLICY = {"runs_per_item": 3, "pass_threshold": 2}


def build_items() -> list[dict[str, Any]]:
    # The data names the image only. Expected values live in the assertions, so the
    # judge compares the output against them instead of reading answers from the input.
    return [
        {"data": {"label": label.slug, "difficulty": "hard" if label.hard else "clean"}, "assertions": label.assertions()}
        for label in LABELS
    ]


def task(item: dict[str, Any]) -> dict[str, Any]:
    label = get_label(item["label"])
    facts = extract_label(label.path, tags=["suite", label.slug])
    return {"input": item, "output": facts.model_dump()}


def run_suite():
    missing = [label.path for label in LABELS if not label.path.exists()]
    if missing:
        raise SystemExit("Label images missing. Run `uv run nutrition-labels render` first.")

    client = opik.Opik()
    suite = client.get_or_create_test_suite(
        name=SUITE_NAME,
        project_name=PROJECT_NAME,
        global_assertions=GLOBAL_ASSERTIONS,
        global_execution_policy=EXECUTION_POLICY,
    )
    suite.insert(build_items())  # identical items are deduplicated on re-runs

    result = opik.run_tests(
        test_suite=suite,
        task=task,
        experiment_name=EXPERIMENT_NAME,
        worker_threads=3,
        generate_report=False,
    )
    client.flush()
    return result
