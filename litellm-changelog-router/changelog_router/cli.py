"""Command line entry point: `run` writes the changelogs, `report` compares the models."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

OUT_DIR = Path("out")


def cmd_run(args: argparse.Namespace) -> int:
    from changelog_router import MODELS
    from changelog_router.commits import load_releases
    from changelog_router.router import write_changelog
    from changelog_router.tracing import flush

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    releases = load_releases()
    print(f"run {run_id}: {len(releases)} releases x {len(MODELS)} models")

    for model in MODELS:
        print(f"\n=== {model} ===")
        for release in releases:
            draft = write_changelog(model, release, run_id)
            path = OUT_DIR / model.split("/")[-1] / f"{release.version}.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(draft.text + "\n")
            print(f"  {release.version}: {draft.latency_s:5.2f}s, {len(draft.text.split()):3d} words -> {path}")
    flush()

    if not args.no_report:
        return _report(run_id, expected=len(MODELS) * len(releases))
    print(f"\nrun `python -m changelog_router report --run {run_id}` to compare the models")
    return 0


def _report(run_id: str | None, expected: int | None = None) -> int:
    import opik

    from changelog_router.report import collect, latest_run_id, print_table

    client = opik.Opik()
    run_id = run_id or latest_run_id(client)
    if not run_id:
        print("No run found in Opik yet. Run `python -m changelog_router run` first.")
        return 1
    rows = collect(client, run_id, expected=expected)
    if not rows:
        print(f"No priced llm spans found for run {run_id}.")
        return 1
    print_table(run_id, rows)
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    return _report(args.run)


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="changelog-router", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="write a changelog per release with every model, then print the comparison")
    run.add_argument("--no-report", action="store_true", help="skip the comparison table")
    run.set_defaults(func=cmd_run)

    report = sub.add_parser("report", help="print the per-model cost and latency table for a run")
    report.add_argument("--run", help="run id (default: the latest run in the Opik project)")
    report.set_defaults(func=cmd_report)

    args = parser.parse_args()
    if args.command == "run":
        from changelog_router.tracing import setup_tracing

        setup_tracing()
    else:
        import os

        from changelog_router import PROJECT_NAME

        os.environ["OPIK_PROJECT_NAME"] = PROJECT_NAME
    sys.exit(args.func(args))
