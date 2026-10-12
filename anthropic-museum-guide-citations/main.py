"""A museum guide that must quote the curator's notes, checked by an Opik test suite.

Two guide prompts answer the same visitor questions:

  * "warm-v1"   asks for a friendly guide and lets it "tidy up" quotes.
  * "strict-v2" demands <quote> excerpts copied character for character.

Both are registered in Opik's prompt library, run against one test suite whose
assertions are plain English, and land as two runs you can compare per item.
"""

import os
import pathlib
import sys

PROJECT_NAME = "anthropic-museum-guide-citations"
# Set before importing opik so every trace lands in this project.
os.environ["OPIK_PROJECT_NAME"] = PROJECT_NAME
# Talk to the real Anthropic API, not a local proxy.
os.environ.pop("ANTHROPIC_BASE_URL", None)

import anthropic
import dotenv
import opik
from opik.integrations.anthropic import track_anthropic

dotenv.load_dotenv()

MODEL = "claude-haiku-4-5-20251001"
NOTES = (pathlib.Path(__file__).parent / "data" / "curator_notes.md").read_text()

# Every call made with this client is logged to Opik as an `llm` span with
# model, token usage and estimated cost.
client = track_anthropic(anthropic.Anthropic(), project_name=PROJECT_NAME)

# ---------------------------------------------------------------- prompts

PROMPT_TEXTS = {
    "warm-v1": (
        "You are a friendly guide at the Saltmarsh Maritime Museum. Answer the "
        "visitor's question using the curator's notes below. Be warm and "
        "conversational. Back up your answer with short excerpts from the notes "
        "in <quote>...</quote> tags, and feel free to tidy the wording of an "
        "excerpt so it reads smoothly aloud.\n\n<curator_notes>\n{{notes}}\n</curator_notes>"
    ),
    "strict-v2": (
        "You are a guide at the Saltmarsh Maritime Museum. Answer only from the "
        "curator's notes below. If the notes do not cover the question, say you "
        "do not have that information and suggest the front desk.\n\n"
        "Rules:\n"
        "- Every factual claim must be backed by an excerpt from the notes "
        "wrapped in <quote>...</quote> tags, copied character for character: "
        "same words, spelling and punctuation. Never fix, shorten or reword "
        "inside the tags.\n"
        "- Keep answers short: the answer first, then the quote(s).\n\n"
        "<curator_notes>\n{{notes}}\n</curator_notes>"
    ),
}


@opik.track(name="guide_answer", project_name=PROJECT_NAME)
def guide_answer(question: str, prompt: opik.Prompt) -> str:
    """Answer one visitor question with the given (versioned) guide prompt."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=700,
        system=prompt.format(notes=NOTES),
        messages=[{"role": "user", "content": question}],
    )
    return response.content[0].text


# ------------------------------------------------------------- test suite

# The quality bar, in plain English. An LLM judge checks each assertion
# against each item's input and the guide's output.
GLOBAL_ASSERTIONS = [
    "Every excerpt inside <quote> tags appears verbatim, character for "
    "character, in the curator's notes provided as context",
    "The quoted excerpts genuinely support the factual claims in the answer",
    "The response answers the visitor's question without adding facts that "
    "are absent from the curator's notes",
]

ITEMS = [
    {"question": "Why is the ship's bell cracked? Was it the rocks?"},
    {"question": "Who carved the figurehead?"},
    {"question": "Is it true the figurehead is cursed?"},
    {"question": "How many of the crew survived, and what happened to the captain?"},
    {"question": "I'd like to take photos. Is that allowed, and when does Gallery 3 close?"},
    {"question": "Can I read Davy Lowther's letter to his sister Hannah?"},
    {"question": "What was the Marigold's tonnage?"},
]

# Item-level assertions are checked in addition to the global ones.
ITEM_ASSERTIONS = {
    ITEMS[0]["question"]: [
        "The response says the crack came from a casting flaw and that the "
        "bell was already cracked before the ship sailed",
    ],
    ITEMS[1]["question"]: [
        "The response says the figurehead is attributed to Tobias Wren (or the "
        "Harlow Quay yard) and does not state flatly that he carved it",
    ],
    ITEMS[6]["question"]: [
        "The response says the notes do not give this information and does not "
        "state a tonnage figure",
    ],
}


def build_suite() -> opik.TestSuite:
    client_ = opik.Opik(project_name=PROJECT_NAME)
    suite = client_.get_or_create_test_suite(
        name=PROJECT_NAME,
        description="Museum guide must quote the curator's notes verbatim",
        project_name=PROJECT_NAME,
        global_assertions=GLOBAL_ASSERTIONS,
        # The judge is an LLM too. Judge each item 3 times, pass on 2 of 3.
        global_execution_policy={"runs_per_item": 3, "pass_threshold": 2},
    )
    suite.insert(
        [
            {
                # The notes ride along in the item so the judge can check quotes.
                "data": {"question": it["question"], "context": NOTES},
                **({"assertions": ITEM_ASSERTIONS[it["question"]]} if it["question"] in ITEM_ASSERTIONS else {}),
            }
            for it in ITEMS
        ]
    )
    return suite


def run_variant(suite: opik.TestSuite, name: str):
    prompt = opik.Opik(project_name=PROJECT_NAME).create_prompt(
        name=f"museum-guide-{name}", prompt=PROMPT_TEXTS[name]
    )

    def task(item: dict) -> dict:
        return {"input": item, "output": guide_answer(item["question"], prompt)}

    result = opik.run_tests(
        test_suite=suite,
        task=task,
        experiment_name_prefix=name,
        experiment_config={"prompt_variant": name, "model": MODEL},
        prompts=[prompt],
        model=f"anthropic/{MODEL}",
        worker_threads=4,
        verbose=0,
        generate_report=False,
    )
    print(f"\n=== {name}: pass rate {result.pass_rate:.0%} "
          f"({result.items_passed}/{result.items_total} items) ===")
    for item_result in result.item_results.values():
        runs = item_result.test_results
        question = runs[0].test_case.task_output["input"]["question"]
        print(f"  [{'PASS' if item_result.passed else 'FAIL'}] {question}")
        if not item_result.passed:
            seen = set()
            for run in runs:
                for s in run.score_results:
                    if (s.scoring_failed or s.value != 1) and s.name not in seen:
                        seen.add(s.name)
                        print(f"         failed: {s.name}: {s.reason}")
    if result.experiment_url:
        print(f"  run: {result.experiment_url}")
    return result


def main() -> None:
    variants = sys.argv[1:] or ["warm-v1", "strict-v2"]
    suite = build_suite()
    for name in variants:
        run_variant(suite, name)
    opik.flush_tracker()


if __name__ == "__main__":
    main()
