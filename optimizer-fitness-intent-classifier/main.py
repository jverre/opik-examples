"""Optimize a fitness-app intent classifier's prompt with the Opik Agent Optimizer.

The starting point is a hand-written first-draft prompt. The MetaPromptOptimizer
scores it on 20 TRAIN messages, reasons about the misses, and proposes better
prompts within a small fixed budget (gpt-4o-mini everywhere). Then the baseline
and the winner are both scored on 10 VALIDATION messages the optimizer never
saw. The score curve across trials, the held-out check, and the winning prompt
(saved to the Opik prompt library as version 2) all land in Opik.
"""

import os
import pathlib

PROJECT_NAME = "optimizer-fitness-intent-classifier"
os.environ["OPIK_PROJECT_NAME"] = PROJECT_NAME  # before importing opik

import dotenv

dotenv.load_dotenv(pathlib.Path(__file__).parent / ".env")

import opik
from opik_optimizer import ChatPrompt, MetaPromptOptimizer

from messages import INTENTS, TRAIN, VALIDATION

MODEL = "openai/gpt-4o-mini"  # LiteLLM naming; the classifier being optimized
REASONING_MODEL = "openai/gpt-4.1-mini"  # proposes the candidate prompts
TRAIN_DATASET = f"{PROJECT_NAME}-train"
VALIDATION_DATASET = f"{PROJECT_NAME}-validation"
LIBRARY_PROMPT_NAME = f"{PROJECT_NAME}-prompt"
MAX_TRIALS = 8  # candidate prompts the optimizer may evaluate: the budget cap

# ---------------------------------------------------------------- datasets ---
# Re-inserting identical rows is safe: Opik deduplicates, so re-runs reuse the
# datasets instead of growing them.
client = opik.Opik()


def make_dataset(name: str, rows: list[tuple[str, str]], description: str):
    dataset = client.get_or_create_dataset(name=name, description=description)
    dataset.insert([{"message": text, "intent": label} for text, label in rows])
    return dataset


train = make_dataset(
    TRAIN_DATASET, TRAIN, "20 labeled Stridewell messages the optimizer climbs against"
)
validation = make_dataset(
    VALIDATION_DATASET, VALIDATION, "10 held-out messages, scored only after optimizing"
)


# ------------------------------------------------------------------ metric ---
def intent_accuracy(dataset_item: dict, llm_output: str) -> float:
    """Exact match: 1.0 if the whole answer is the intent label, else 0.0.

    The normalization is minimal on purpose (lowercase, strip quotes and
    punctuation), so "log_workout." passes but "The intent is log_workout"
    does not. The output contract is part of what the optimizer must learn.
    """
    answer = llm_output.strip().lower().strip(".!\"'` *")
    return 1.0 if answer == dataset_item["intent"] else 0.0


# --------------------------------------------------------- baseline prompt ---
# A first draft like many real ones: it names the intents but never says to
# answer with only the label, and it knows none of the house rules for messages
# that touch two intents (pain plus a cancellation, a failed sync plus a run to
# log, "plan" meaning subscription or training).
BASELINE_SYSTEM = f"""\
You triage in-app messages for Stridewell, a fitness coaching app.
Work out what the user wants. The possible intents are: {", ".join(INTENTS)}.
Tell us which intent the message is."""

prompt = ChatPrompt(
    name="intent-classifier",
    system=BASELINE_SYSTEM,
    user="{message}",  # filled from the dataset's "message" column
    model=MODEL,
    model_parameters={"temperature": 0},  # keep scoring noise low
)

# Version 1 in the prompt library is the baseline, saved before optimizing so
# the library tells the whole story: v1 first draft, v2 optimized.
client.create_chat_prompt(
    name=LIBRARY_PROMPT_NAME,
    messages=[
        {"role": "system", "content": BASELINE_SYSTEM},
        {"role": "user", "content": "{{message}}"},
    ],
    change_description="Baseline hand-written prompt (pre-optimization)",
    project_name=PROJECT_NAME,
)

# ---------------------------------------------------------------- optimize ---
optimizer = MetaPromptOptimizer(
    model=REASONING_MODEL,  # the model that reasons about why the prompt fails
    num_task_examples=10,  # labeled examples shown to the reasoning model
    task_context_columns=["message", "intent"],
    prompts_per_round=4,
    seed=42,
    verbose=1,
)

result = optimizer.optimize_prompt(
    prompt=prompt,
    dataset=train,
    metric=intent_accuracy,
    n_samples=len(TRAIN),  # score every training message on every trial
    max_trials=MAX_TRIALS,
    project_name=PROJECT_NAME,
)

initial = result.initial_score if result.initial_score is not None else 0.0
best = result.score

# ------------------------------------------------------------- score curve ---
print()
print("=" * 64)
print(f"score curve on TRAIN ({len(TRAIN)} messages), one row per trial")
print("-" * 64)
curve = [("baseline", initial)]
trials = [
    t
    for round_state in result.history
    for t in round_state.get("trials", [])
    if t.get("candidate_id") != "baseline"
]
for trial in sorted(trials, key=lambda t: t.get("timestamp", "")):  # chronological
    curve.append((f"trial {len(curve)}", trial.get("score")))
for label, score in curve:
    shown = f"{score:.3f}" if isinstance(score, (int, float)) else "n/a"
    bar = "#" * round((score or 0) * 40) if isinstance(score, (int, float)) else ""
    print(f"{label:<10} {shown}  {bar}")

# ----------------------------------------------- held-out validation check ---
# The optimizer only ever saw TRAIN. Scoring both prompts on messages it never
# saw tells you whether the gain generalizes or was fit to the training set.
winner = result.prompt


def held_out(p: ChatPrompt, tag: str) -> float:
    # The optimizer tags every evaluation with its optimization id. Clear it so
    # these two validation experiments stay out of the run's trial chart.
    optimizer.current_optimization_id = None
    return optimizer.evaluate_prompt(
        prompt=p,
        dataset=validation,
        metric=intent_accuracy,
        n_samples=len(VALIDATION),
        experiment_config={"split": "validation", "prompt": tag},
        verbose=0,
    )


val_baseline = held_out(prompt, "baseline")
val_winner = held_out(winner, "winner")

cost = result.llm_cost_total
print("=" * 64)
print(f"TRAIN       baseline {initial:.3f} -> best {best:.3f}  ({best - initial:+.3f})")
print(
    f"VALIDATION  baseline {val_baseline:.3f} -> winner {val_winner:.3f}  "
    f"({val_winner - val_baseline:+.3f})"
)
print(f"trials completed  : {result.details.get('trials_completed')}  (budget: {MAX_TRIALS})")
print(f"optimizer llm cost: {'$%.4f' % cost if cost is not None else 'unavailable'}")

# get_run_link() goes through a session redirect that keeps whatever project
# you last looked at as the page context, so the run can look empty. The
# direct, project-scoped URL always shows the score history:
opt_info = client.rest_client.optimizations.get_optimization_by_id(
    result.optimization_id
)
ui_base = client.config.url_override.rstrip("/").removesuffix("/api")
print(
    "optimization run  : "
    f"{ui_base}/{client.config.workspace}/projects/{opt_info.project_id}"
    f"/optimizations/{result.optimization_id}"
)
print("=" * 64)

# -------------------------------------------------- save the winning prompt ---
# Only a real train improvement earns version 2.
if best > initial:
    messages = result.prompt.get_messages()
    # The optimizer uses {message}; the library's mustache format uses {{message}}.
    for message in messages:
        message["content"] = message["content"].replace("{message}", "{{message}}")
    client.create_chat_prompt(
        name=LIBRARY_PROMPT_NAME,
        messages=messages,
        change_description=(
            f"MetaPromptOptimizer winner: train {initial:.3f} -> {best:.3f}, "
            f"validation {val_baseline:.3f} -> {val_winner:.3f}"
        ),
        project_name=PROJECT_NAME,
    )
    print(f"\nSaved the winning prompt to the library as '{LIBRARY_PROMPT_NAME}'.")
    print("\nWinning system prompt:\n")
    print(messages[0]["content"])
else:
    print("\nNo improvement over the baseline: the library keeps only v1.")

opik.flush_tracker()
