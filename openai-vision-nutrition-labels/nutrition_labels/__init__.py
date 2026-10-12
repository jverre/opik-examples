"""Fictional nutrition-label images, read by GPT-4o-mini vision and traced in Opik."""

import os

PROJECT_NAME = "openai-vision-nutrition-labels"
MODEL = "gpt-4o-mini"

# Pin the Opik project before anything creates an Opik client, so no trace can
# land in a default project from ~/.opik.config.
os.environ["OPIK_PROJECT_NAME"] = PROJECT_NAME
