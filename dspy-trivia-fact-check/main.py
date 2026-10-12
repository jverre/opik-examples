"""A DSPy fact-checker that compiles itself a house verdict format, measured in Opik.

The program checks trivia claims about a fictional natural-science almanac
(data/reference_corpus.md). The team's house format for a ruling is
"<VERDICT> | ref: <ID or none> | <one-sentence reason>", for example
"FALSE | ref: GEO-1 | The ridge was raised by volcanic uplift." That
convention is never stated in the signature; it lives only in worked
examples, which is exactly what DSPy compilation finds and bakes in.

The script runs the same Opik test suite twice: with the raw ChainOfThought
program, then after BootstrapFewShot picks demos from a trainset. Every DSPy
call is traced through OpikCallback.
"""

import json
import os
import pathlib
import re

PROJECT_NAME = "dspy-trivia-fact-check"
os.environ["OPIK_PROJECT_NAME"] = PROJECT_NAME

import dotenv
import dspy
import opik
from opik.integrations.dspy.callback import OpikCallback

dotenv.load_dotenv()

DATA = pathlib.Path(__file__).parent / "data"
MODEL = "openai/gpt-4o-mini"
CORPUS = (DATA / "reference_corpus.md").read_text()
CLAIMS = json.loads((DATA / "claims.json").read_text())

# One line wires DSPy to Opik: every module call becomes a trace, with the
# ChainOfThought module, its Predict step and the LM call nested inside it.
lm = dspy.LM(MODEL, cache=False)
dspy.configure(lm=lm, callbacks=[OpikCallback(project_name=PROJECT_NAME, log_graph=True)])


# --- The DSPy program ------------------------------------------------------

class FactCheck(dspy.Signature):
    """Fact-check the claim against the reference corpus."""

    corpus: str = dspy.InputField(desc="the reference corpus, entries tagged [ID]")
    claim: str = dspy.InputField()
    ruling: str = dspy.OutputField()


# What the signature does NOT say: the three allowed verdicts, the "ref:"
# citation, or the one-line shape. The raw program only knows "fact-check the
# claim"; the house format has to come from compiled demos.
program = dspy.ChainOfThought(FactCheck)


# --- Trainset and compile-time metric --------------------------------------

trainset = [
    dspy.Example(
        corpus=CORPUS, claim=c["claim"], ruling=c["ruling"],
        verdict=c["verdict"], ref=c["ref"], key=c["key"],
    ).with_inputs("corpus", "claim")
    for c in CLAIMS["train"]
]

RULING = re.compile(r"^(TRUE|FALSE|UNVERIFIABLE) \| ref: ([A-Z]+-\d+|none) \| (\S.*)$")


def house_ruling(example: dspy.Example, prediction, trace=None) -> bool:
    """Right shape, right verdict, right citation, reason mentions the key fact.

    Purely programmatic, so compiling spends no judge tokens.
    """
    match = RULING.match(prediction.ruling.strip())
    if not match:
        return False
    verdict, ref, reason = match.groups()
    return (verdict == example.verdict and ref == example.ref
            and example.key.lower() in reason.lower())


# --- The test suite: eight held-out claims ---------------------------------

# None of these claims appear in the trainset, so the compiled program cannot
# have memorized them; the demos must transfer. Each item also pins the
# expected verdict, so a wrong ruling fails even when the format is right.
GLOBAL_ASSERTIONS = [
    "The ruling has exactly the form '<VERDICT> | ref: <ID or none> | <reason>', "
    "where VERDICT is one of TRUE, FALSE or UNVERIFIABLE, written in capitals as "
    "the first word, and the three parts are separated by ' | '",
    "The ref is a single corpus entry id such as GEO-1 when the verdict is TRUE or "
    "FALSE, and the word none when the verdict is UNVERIFIABLE, and the ruling cites "
    "the corpus entry that actually covers the claim",
    "The reason is one short sentence and the ruling has no text before the verdict "
    "or after the reason",
]


def item_assertion(c: dict) -> str:
    """The item-level check: the ruling must reach the right verdict and cite the right entry."""
    cited = "cites the entry " + c["ref"] if c["ref"] != "none" else "cites no entry (ref: none)"
    return f"The verdict is {c['verdict']} and the ruling {cited}"


def make_task(prog: dspy.Module):
    """Wrap a DSPy program as a run_tests task."""

    def task(item: dict) -> dict:
        prediction = prog(corpus=CORPUS, claim=item["claim"])
        return {"input": {"claim": item["claim"]}, "output": prediction.ruling}

    return task


def main() -> None:
    client = opik.Opik()

    # 1. Tracing demo: one claim through the uncompiled program.
    claim = "Glimmerfen moss glows in the dark because of bacteria."
    print(f"Claim: {claim}")
    print(f"Ruling (uncompiled): {program(corpus=CORPUS, claim=claim).ruling}\n")

    # 2. The suite. Every item runs 3 times and must pass at least 2 of them,
    # which absorbs the judge's and the model's run-to-run noise.
    suite = client.get_or_create_test_suite(
        name="dspy-trivia-fact-check-suite",
        project_name=PROJECT_NAME,
        global_assertions=GLOBAL_ASSERTIONS,
        global_execution_policy={"runs_per_item": 3, "pass_threshold": 2},
    )
    suite.insert([
        {"data": {"claim": c["claim"], "expected_verdict": c["verdict"], "expected_ref": c["ref"]},
         "assertions": [item_assertion(c)]}
        for c in CLAIMS["test"]
    ])

    # 3. Baseline: the suite against the UNCOMPILED program.
    print("Running the suite against the uncompiled program...")
    uncompiled = opik.run_tests(
        test_suite=suite,
        task=make_task(program),
        experiment_name="dspy-uncompiled",
        experiment_config={"program": "ChainOfThought(FactCheck)", "compiled": False, "model": MODEL},
        worker_threads=4,
        generate_report=False,
    )

    # 4. Compile. BootstrapFewShot runs a teacher over the trainset, keeps the
    # attempts that pass the metric, reasoning included, and bakes up to four
    # of them into the prompt as demos.
    print("\nCompiling with BootstrapFewShot...")
    optimizer = dspy.BootstrapFewShot(
        metric=house_ruling,
        max_bootstrapped_demos=4,
        max_labeled_demos=8,
        max_rounds=1,
    )
    compiled_program = optimizer.compile(program, trainset=trainset)

    # 5. The same suite, same assertions, against the COMPILED program.
    print("\nRunning the suite against the compiled program...")
    compiled = opik.run_tests(
        test_suite=suite,
        task=make_task(compiled_program),
        experiment_name="dspy-compiled",
        experiment_config={"program": "ChainOfThought(FactCheck)", "compiled": True,
                           "optimizer": "BootstrapFewShot", "model": MODEL},
        worker_threads=4,
        generate_report=False,
    )

    # 6. Before and after.
    print("\n=== Uncompiled vs compiled ===")
    for name, result in [("uncompiled", uncompiled), ("compiled  ", compiled)]:
        print(f"{name}: {result.pass_rate:.0%} pass rate "
              f"({result.items_passed}/{result.items_total} items passed)")
    if compiled.experiment_url:
        print(f"\nView the runs: {compiled.experiment_url}")

    opik.flush_tracker()


if __name__ == "__main__":
    main()
