"""Shared settings. Importing this module sets the Opik project for the process."""

import os
import pathlib

PROJECT_NAME = "langgraph-park-guide-rag"
os.environ["OPIK_PROJECT_NAME"] = PROJECT_NAME

import dotenv

dotenv.load_dotenv()  # optional local .env (OPENAI_API_KEY, OPIK_API_KEY, ...)

GUIDE_DIR = pathlib.Path(__file__).parents[1] / "guide"
EMBEDDING_MODEL = "text-embedding-3-small"
ANSWER_MODEL = "gpt-4o-mini"
DATASET_NAME = f"{PROJECT_NAME}-questions"
