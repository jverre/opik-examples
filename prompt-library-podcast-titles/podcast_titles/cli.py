"""Command line: push a prompt version, list versions, run the test suite."""

import argparse
import difflib

from podcast_titles.config import PROJECT_NAME, PROMPT_NAME, opik, opik_client
from podcast_titles.prompts import CHANGES, TEXTS
from podcast_titles.suite import get_suite, run_version
from podcast_titles.writer import load_episodes, write_title


def cmd_push(args: argparse.Namespace) -> None:
    prompt = opik_client().create_prompt(
        name=PROMPT_NAME,
        prompt=TEXTS[args.version],
        project_name=PROJECT_NAME,
        change_description=CHANGES[args.version],
    )
    print(f"Pushed {args.version}: {PROMPT_NAME} version {prompt.version} "
          f"(commit {prompt.commit})")


def cmd_versions(_: argparse.Namespace) -> None:
    history = opik_client().get_prompt_history(
        name=PROMPT_NAME, project_name=PROJECT_NAME
    )
    # History comes newest first; show it oldest first.
    history = sorted(history, key=lambda p: int(p.version.lstrip("v")))
    for p in history:
        print(f"{p.version}  commit {p.commit}")
    if len(history) >= 2:
        old, new = history[-2], history[-1]
        print(f"\nDiff {old.version} -> {new.version}:")
        for line in difflib.unified_diff(
            old.prompt.splitlines(), new.prompt.splitlines(), lineterm="", n=0
        ):
            if not line.startswith(("---", "+++", "@@")):
                print(line)


def cmd_title(args: argparse.Namespace) -> None:
    for episode in load_episodes()[:3]:
        print(f"{episode['guest']}: {write_title(episode, version=args.version)}")


def cmd_test(args: argparse.Namespace) -> None:
    suite = get_suite()
    results = {v: run_version(suite, v) for v in args.versions}
    print("\n=== Prompt version comparison ===")
    for version, result in results.items():
        print(
            f"{version}: {result.pass_rate:.0%} pass rate "
            f"({result.items_passed}/{result.items_total} episodes passed)"
        )
    last = results[args.versions[-1]]
    if last.experiment_url:
        print(f"\nView the runs: {last.experiment_url}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="podcast-titles", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    push = sub.add_parser("push", help="publish a prompt version to the library")
    push.add_argument("--version", choices=sorted(TEXTS), required=True)
    push.set_defaults(func=cmd_push)

    sub.add_parser("versions", help="list prompt versions and diff the last two") \
        .set_defaults(func=cmd_versions)

    title = sub.add_parser("title", help="title the first three episodes")
    title.add_argument("--version", default=None, help="v1, v2 (default: latest)")
    title.set_defaults(func=cmd_title)

    test = sub.add_parser("test", help="run the test suite against prompt versions")
    test.add_argument("--versions", nargs="+", default=["v1", "v2"])
    test.set_defaults(func=cmd_test)

    args = parser.parse_args()
    args.func(args)
    opik.flush_tracker()


if __name__ == "__main__":
    main()
