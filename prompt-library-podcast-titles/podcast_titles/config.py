"""Names and settings shared by every module.

Importing this module first pins the Opik project, so no trace can land in
whatever default project the machine happens to be configured with.
"""

import os
import pathlib
from functools import lru_cache

import dotenv

PROJECT_NAME = "prompt-library-podcast-titles"
os.environ["OPIK_PROJECT_NAME"] = PROJECT_NAME

dotenv.load_dotenv()

import opik  # noqa: E402  (must come after the project is pinned)

PROMPT_NAME = "prompt-library-podcast-titles-episode-title"
SUITE_NAME = "prompt-library-podcast-titles-suite"
TITLE_MODEL = "gpt-4o-mini"
EPISODES_FILE = pathlib.Path(__file__).parents[1] / "data" / "episodes.json"


@lru_cache
def opik_client() -> opik.Opik:
    return opik.Opik(project_name=PROJECT_NAME)
