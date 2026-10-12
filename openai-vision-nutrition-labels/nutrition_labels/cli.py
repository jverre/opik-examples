"""Command line entry point: `render`, `extract <image>`, `suite`."""

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv


def cmd_render(args: argparse.Namespace) -> int:
    from nutrition_labels.render import LABELS, render_all

    paths = render_all()
    for label, path in zip(LABELS, paths):
        print(f"  {path}  ({label.kind})")
    print(f"\nRendered {len(paths)} labels. Images stay in out/, which is git-ignored.")
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    import opik

    from nutrition_labels.extract import extract_label
    from nutrition_labels.render import get_label

    path = Path(args.image)
    if not path.exists():
        print(f"{path} not found. Run `uv run nutrition-labels render` first.")
        return 1
    facts = extract_label(path, tags=["cli"])
    print(json.dumps(facts.model_dump(), indent=2))
    label = get_label(args.image)
    if label:
        diffs = {k: (facts.model_dump()[k], v) for k, v in label.truth.items() if facts.model_dump()[k] != v}
        print("\nmatches the generated truth" if not diffs else f"\ndiffers from truth (got, expected): {diffs}")
    opik.flush_tracker()
    return 0


def cmd_suite(args: argparse.Namespace) -> int:
    from nutrition_labels.render import LABELS, render_all
    from nutrition_labels.suite import EXECUTION_POLICY, run_suite

    if not all(label.path.exists() for label in LABELS):
        render_all()
    print(f"Running the test suite: {len(LABELS)} labels x {EXECUTION_POLICY['runs_per_item']} runs...\n")
    result = run_suite()

    print(f"Pass rate: {result.pass_rate:.0%} ({result.items_passed}/{result.items_total} labels)")
    for item_result in sorted(result.item_results.values(), key=lambda r: r.test_results[0].test_case.task_output["input"]["label"]):
        case = item_result.test_results[0].test_case.task_output["input"]
        status = "PASS" if item_result.passed else "FAIL"
        print(f"  [{status}] {case['label']:<18} {case['difficulty']:<6} runs passed: {item_result.runs_passed}/{item_result.runs_total}")
        # Show why a run failed: the judge's reason for each failed assertion.
        for run in item_result.test_results:
            for score in run.score_results:
                if score.value not in (True, 1):
                    print(f"         run {run.trial_id}: {score.name[:70]} -> {(score.reason or '')[:160]}")
    print(f"\nExperiment: {result.experiment_name} ({result.experiment_url})")
    return 0


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="nutrition-labels", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("render", help="draw the six label images into out/labels/").set_defaults(func=cmd_render)
    extract = sub.add_parser("extract", help="read one label image and print the typed fields")
    extract.add_argument("image", help="path to a label PNG")
    extract.set_defaults(func=cmd_extract)
    sub.add_parser("suite", help="run the Opik test suite over all six labels").set_defaults(func=cmd_suite)
    args = parser.parse_args()
    sys.exit(args.func(args))
