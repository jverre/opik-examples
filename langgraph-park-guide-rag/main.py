"""Entry point: a few traced questions, then two experiments (k=3 vs k=1)."""

import opik

from park_rag.config import PROJECT_NAME
from park_rag.evaluation import get_dataset, run_experiment
from park_rag.graph import build_graph

DEMO_QUESTIONS = [
    "How much does a car pay to enter the park?",
    "Can I bring my dog on the Granite Crown trail?",
    "Can I rent a kayak on Opal Lake?",  # not in the guide
]


def main() -> None:
    app, tracer = build_graph(k=3)
    for question in DEMO_QUESTIONS:
        result = app.invoke({"question": question})
        print(f"Q: {question}\nA: {result['answer']}\n")
    tracer.flush()

    dataset = get_dataset()
    run_experiment(dataset, k=3, name="park-guide-k3")
    run_experiment(dataset, k=1, name="park-guide-k1")

    opik.flush_tracker()
    print(f"\nOpen the '{PROJECT_NAME}' project in Opik to see the traces.")


if __name__ == "__main__":
    main()
