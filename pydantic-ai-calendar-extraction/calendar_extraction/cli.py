"""Command line: `extract <file>` for one email, `suite` for the Opik test suite."""

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from .agent import PROMPTS


def cmd_extract(args: argparse.Namespace) -> None:
    from .agent import extract_event

    for path in args.files:
        email = sys.stdin.read() if path == "-" else Path(path).read_text()
        print(f"{path}")
        print(json.dumps(extract_event(email, args.prompt), indent=2))


def cmd_suite(args: argparse.Namespace) -> None:
    import opik

    from .suite import run_suite

    result = run_suite(args.prompt, args.runs)
    print(f"\nPass rate ({args.prompt} prompt): {result.pass_rate:.0%} "
          f"({result.items_passed}/{result.items_total} emails)")
    for item_result in result.item_results.values():
        runs = item_result.test_results
        file = runs[0].test_case.task_output["input"]["file"]
        status = "PASS" if item_result.passed else "FAIL"
        print(f"  [{status}] {file}  ({item_result.runs_passed}/{item_result.runs_total} runs passed)")
    # Why did the failing emails fail? Show the first failed assertion of one failed run.
    for item in result.to_report_dict()["items"]:
        if item["passed"]:
            continue
        run = next(r for r in item["runs"] if not r["passed"])
        bad = next(a for a in run["assertions"] if not a["passed"])
        print(f"\n{run['input']['file']}: {json.dumps(run['output'])}")
        print(f"  failed: {bad['name']}\n  judge:  {bad.get('reason', '')}")
    print(f"\nExperiment: {result.experiment_name} ({result.experiment_url})")
    opik.flush_tracker()


def main() -> None:
    load_dotenv(Path(__file__).parent.parent / ".env")
    parser = argparse.ArgumentParser(prog="calendar-extraction", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("extract", help="extract an event from one or more email files ('-' = stdin)")
    p.add_argument("files", nargs="+")
    p.add_argument("--prompt", choices=PROMPTS, default="strict")
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("suite", help="run the Opik test suite against the agent")
    p.add_argument("--prompt", choices=PROMPTS, default="strict")
    p.add_argument("--runs", type=int, default=3, help="runs per email (default 3)")
    p.set_defaults(func=cmd_suite)

    args = parser.parse_args()

    from . import tracing

    tracing.setup_tracing()
    try:
        args.func(args)
    finally:
        import opik

        opik.flush_tracker()
        tracing.flush()


if __name__ == "__main__":
    main()
