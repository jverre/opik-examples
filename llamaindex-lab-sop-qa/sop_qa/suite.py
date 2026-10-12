"""A step-level Opik test suite: every item checks retrieval and synthesis separately.

The task output is split by pipeline step:

    {"retrieve": {"excerpts": [...]}, "synthesize": {"answer": "..."}}

and every assertion is prefixed with the step it judges. "RETRIEVE:" assertions
only look at the excerpts, "SYNTHESIZE:" assertions only at the answer. When an
item fails, the prefix of the failing assertion says which step to fix.
"""

from collections import defaultdict
from typing import Any

import opik

from . import PROJECT_NAME
from .engine import ask

GLOBAL_ASSERTIONS = [
    "SYNTHESIZE: the answer contains no time, mass, speed, count or extension that appears "
    "in neither the retrieved excerpts nor the question. Figures repeated from the question "
    "are fine, and an answer that only says the SOPs do not cover it passes this check",
]

# Each item: a question, the SOP clause retrieval must surface, and the fact the answer must state.
ITEMS: list[dict[str, Any]] = [
    {
        "question": "How closely do the tubes have to be balanced in the R-12 rotor?",
        "assertions": [
            "RETRIEVE: the excerpts contain the SOP-204 sentence giving the R-12 balancing tolerance (0.1 g)",
            "SYNTHESIZE: the answer says the R-12 masses must match within 0.1 g",
        ],
    },
    {
        "question": "How long does the liquid waste autoclave cycle run, and with what cap setting?",
        "assertions": [
            "RETRIEVE: the excerpts contain the SOP-122 sentence giving the liquid cycle length (45 minutes, caps loosened)",
            "SYNTHESIZE: the answer says 45 minutes, with bottle caps loosened",
        ],
    },
    {
        "question": "I knocked over 250 mL of acetone on the bench. Can I clean it up myself?",
        "assertions": [
            "RETRIEVE: the excerpts contain the SOP-310 large-spill clause (100 mL or more is a large spill, call extension 5511)",
            "SYNTHESIZE: the answer says no, to leave the room and call the Safety Desk on extension 5511",
        ],
    },
    {
        "question": "How long should I flush my eyes at the eyewash after a splash?",
        "assertions": [
            "RETRIEVE: the excerpts contain the SOP-310 sentence giving the eyewash flush time (15 minutes)",
            "SYNTHESIZE: the answer says to flush for 15 minutes",
        ],
    },
    {
        "question": "How long can I keep 1 M Tris-HCl pH 8.0 on the shelf at room temperature?",
        "assertions": [
            "RETRIEVE: the excerpts contain the SOP-101 sentence giving the Tris-HCl shelf life (6 months)",
            "SYNTHESIZE: the answer says 6 months",
        ],
    },
    {
        "question": "The minus 80 freezer alarm went off at minus 70. How long can the samples stay before I move them?",
        "assertions": [
            "RETRIEVE: the excerpts contain the SOP-150 alarm response clause (above -70 C for 30 minutes, move to FZ-02)",
            "SYNTHESIZE: the answer says more than 30 minutes above -70 C triggers a move to backup freezer FZ-02",
        ],
    },
    {
        "question": "A tube cracked mid-spin and liquid leaked into the centrifuge. What do I do, "
        "and how long before I can open the lid?",
        "assertions": [
            "RETRIEVE: the excerpts contain the SOP-204 tube failure clause (lid closed for 30 minutes)",
            "RETRIEVE: the excerpts include text taken from the SOP-310 chemical spill document itself (small spills, large spills or biological spills), not merely a mention of SOP-310 inside another SOP",
            "SYNTHESIZE: the answer says to keep the lid closed for 30 minutes and notify the Lab Safety Officer",
        ],
    },
    {
        "question": "What is the policy for working alone in the lab at night?",
        "assertions": [
            "SYNTHESIZE: the answer says the SOPs do not cover this question, and gives no working-alone rule",
        ],
    },
]


def _step_of(score_name: str) -> str:
    name = score_name.upper()
    for step in ("RETRIEVE", "SYNTHESIZE"):
        if step in name[:40]:
            return step.lower()
    return "other"


def run_suite(engine, top_k: int, runs_per_item: int = 3) -> Any:
    """Insert the items (deduplicated on re-runs) and run one experiment."""
    client = opik.Opik(project_name=PROJECT_NAME)
    suite = client.get_or_create_test_suite(
        name=PROJECT_NAME,
        description="Lab SOP Q&A, judged separately on the retrieve and synthesize steps",
        project_name=PROJECT_NAME,
        global_assertions=GLOBAL_ASSERTIONS,
        # An LLM judge is noisy: run every item N times and require 2 passes.
        global_execution_policy={"runs_per_item": runs_per_item, "pass_threshold": 2},
    )
    suite.insert([{"data": {"question": i["question"]}, "assertions": i["assertions"]} for i in ITEMS])

    def task(item: dict[str, Any]) -> dict[str, Any]:
        result = ask(engine, item["question"])
        return {
            "input": item,
            "output": {
                "retrieve": {"excerpts": result.excerpts},
                "synthesize": {"answer": result.answer},
            },
        }

    result = opik.run_tests(
        test_suite=suite,
        task=task,
        experiment_name=f"sop-qa-top-k-{top_k}",
        experiment_config={"top_k": top_k, "answer_model": "gpt-4o-mini", "chunk_size": 160},
        worker_threads=4,
        verbose=0,
        generate_report=False,
    )
    _report(result)
    return result


def _report(result: Any) -> None:
    print(f"Pass rate: {result.pass_rate:.0%} ({result.items_passed}/{result.items_total} items passed)")
    per_step: dict[str, list[float]] = defaultdict(list)
    for item_result in result.item_results.values():
        question = item_result.test_results[0].test_case.task_output["input"]["question"]
        print(f"  [{'PASS' if item_result.passed else 'FAIL'}] {question}")
        failures: dict[str, list[str]] = defaultdict(list)
        for run in item_result.test_results:
            for score in run.score_results:
                per_step[_step_of(score.name)].append(float(score.value))
                if score.scoring_failed or score.value != 1:
                    failures[score.name].append(score.reason or "")
        if not item_result.passed:
            runs = len(item_result.test_results)
            for name, reasons in failures.items():
                print(f"         failed {len(reasons)}/{runs} runs ({_step_of(name)}): {name[:110]}")
                print(f"         judge: {reasons[0][:200]}")
    print("Assertion pass rate by step (all runs):")
    for step, values in sorted(per_step.items()):
        print(f"  {step:<11} {sum(values) / len(values):.0%} of {len(values)} checks")
    if result.experiment_url:
        print(f"View the run: {result.experiment_url}")
