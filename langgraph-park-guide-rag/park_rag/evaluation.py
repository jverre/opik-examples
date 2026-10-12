"""Dataset + experiments: Hallucination and ContextPrecision over the guide."""

import opik
from opik.evaluation import evaluate
from opik.evaluation.metrics import ContextPrecision, Hallucination

from park_rag.config import DATASET_NAME
from park_rag.graph import build_graph

DATASET_ITEMS = [
    {"question": "How much does a car pay to enter the park?",
     "expected_output": "A private vehicle pays $30 for a 7-day pass."},
    {"question": "When does Ridgeline Drive close for winter?",
     "expected_output": "Ridgeline Drive is closed to vehicles from November 1 to May 15."},
    {"question": "Can I bring my dog on the Moss Falls trail?",
     "expected_output": "No. Dogs are not allowed on Moss Falls; they are only allowed "
                        "on the Fernbank Loop and paved roads, on a leash of 6 feet or less."},
    {"question": "Which campground has flush toilets and what does it cost?",
     "expected_output": "Birchwater Campground has flush toilets and costs $28 per night."},
    {"question": "What do I need to camp in the backcountry, and how many people can be in my group?",
     "expected_output": "A free backcountry permit from the Cedar Gate Visitor Center; "
                        "groups are limited to six people."},
    {"question": "Which hikes are open to bicycles and which are not?",
     "expected_output": "Bicycles are allowed on paved roads and Cedar Gate Road, but never "
                        "on hiking trails."},
    {"question": "Are drones allowed at Opal Lake?",
     "expected_output": "No. Drones are prohibited everywhere in the park."},
    {"question": "Can I rent a kayak on Opal Lake?",
     "expected_output": "The guide does not say."},
]


def get_dataset() -> opik.Dataset:
    dataset = opik.Opik().get_or_create_dataset(name=DATASET_NAME)
    dataset.insert(DATASET_ITEMS)  # deduplicated on re-runs
    return dataset


def run_experiment(dataset: opik.Dataset, k: int, name: str) -> dict[str, float]:
    app, tracer = build_graph(k)

    def task(item: dict) -> dict:
        result = app.invoke({"question": item["question"]})
        return {"output": result["answer"], "context": result["context"]}

    evaluation = evaluate(
        dataset=dataset,
        task=task,
        scoring_metrics=[Hallucination(), ContextPrecision()],
        scoring_key_mapping={"input": "question"},
        experiment_name=name,
        experiment_config={"k": k, "answer_model": "gpt-4o-mini"},
        task_threads=4,
    )
    tracer.flush()
    scores = evaluation.aggregate_evaluation_scores().aggregated_scores
    print(f"\n{name} (k={k}), mean over {len(evaluation.test_results)} questions:")
    for metric, stats in scores.items():
        print(f"  {metric}: {stats.mean:.2f}")
    if evaluation.experiment_url:
        print(f"  {evaluation.experiment_url}")
    return {m: s.mean for m, s in scores.items()}
