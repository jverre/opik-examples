"""Environment loading and the constants both processes share."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# A local proxy base URL on the build machine must not leak into the example.
os.environ.pop("OPENAI_BASE_URL", None)

TASK_QUEUE = "talk-reviews"
TEMPORAL_ADDRESS = os.environ.get("TEMPORAL_ADDRESS", "127.0.0.1:7400")
OPIK_PROJECT_NAME = os.environ.get("OPIK_PROJECT_NAME", "temporal-py-talk-review")
MODEL = "gpt-4o-mini"


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing {name}. Copy .env.example to .env and fill it in.")
    return value
