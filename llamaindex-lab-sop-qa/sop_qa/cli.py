"""Command line: build-pdfs, ask, suite, demo."""

import argparse
import logging
import sys

import dotenv

dotenv.load_dotenv()

for _noisy in ("httpx", "LiteLLM", "litellm", "openai"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

from . import PROJECT_NAME  # noqa: E402  (sets OPIK_PROJECT_NAME before opik loads)

DEMO_QUESTIONS = [
    "How closely do the tubes have to be balanced in the R-12 rotor?",
    "A tube cracked mid-spin and liquid leaked into the centrifuge. What do I do, "
    "and how long before I can open the lid?",
    "What is the policy for working alone in the lab at night?",
]


def _print_answer(result) -> None:
    print(f"Q: {result.question}")
    print(f"A: {result.answer}")
    print("   retrieved: " + ", ".join(f"{e['source'].removesuffix('.pdf')} ({e['score']})" for e in result.excerpts))
    print()


def cmd_build_pdfs(_args) -> None:
    from .pdfs import build_pdfs

    for path in build_pdfs():
        print(f"wrote {path}")


def cmd_ask(args) -> None:
    import opik

    from .engine import ask, build_engine, enable_tracing

    enable_tracing()  # before build_engine: the engine captures the callback manager when created
    engine = build_engine(top_k=args.top_k)
    for question in args.questions:
        _print_answer(ask(engine, question))
    opik.flush_tracker()


def cmd_suite(args) -> None:
    import opik

    from .engine import build_engine, enable_tracing
    from .suite import run_suite

    enable_tracing()
    engine = build_engine(top_k=args.top_k)
    run_suite(engine, top_k=args.top_k, runs_per_item=args.runs)
    opik.flush_tracker()


def cmd_demo(args) -> None:
    import opik

    from .engine import ask, build_engine, enable_tracing
    from .suite import run_suite

    print("== build-pdfs ==")
    cmd_build_pdfs(args)
    enable_tracing()  # before build_engine: the engine captures the callback manager when created
    engine = build_engine(top_k=3)
    print("\n== ask (top-k 3) ==")
    for question in DEMO_QUESTIONS:
        _print_answer(ask(engine, question))
    # The same suite twice, so the two experiments can be compared in Opik:
    # top-k 1 starves the retrieve step, top-k 3 is the baseline.
    for top_k in (1, 3):
        print(f"== suite, top-k {top_k} ==")
        run_suite(build_engine(top_k=top_k), top_k=top_k, runs_per_item=args.runs)
        print()
    opik.flush_tracker()


def main() -> None:
    parser = argparse.ArgumentParser(prog="sop-qa", description=f"Lab SOP Q&A (Opik project: {PROJECT_NAME})")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("build-pdfs", help="generate the SOP PDFs into data/sops/").set_defaults(func=cmd_build_pdfs)

    p = sub.add_parser("ask", help="answer one or more questions")
    p.add_argument("questions", nargs="+")
    p.add_argument("--top-k", type=int, default=3, help="chunks retrieved per question (default 3)")
    p.set_defaults(func=cmd_ask)

    p = sub.add_parser("suite", help="run the step-level Opik test suite")
    p.add_argument("--top-k", type=int, default=3)
    p.add_argument("--runs", type=int, default=3, help="runs per item; an item passes if 2 of N pass")
    p.set_defaults(func=cmd_suite)

    p = sub.add_parser("demo", help="build-pdfs, ask three questions, then run the suite at top-k 1 and 3")
    p.add_argument("--runs", type=int, default=3)
    p.set_defaults(func=cmd_demo)

    args = parser.parse_args()
    args.func(args)
    sys.exit(0)
