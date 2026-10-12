"""Q&A over generated laboratory SOP PDFs, traced with Opik."""

import os
from pathlib import Path

PROJECT_NAME = "llamaindex-lab-sop-qa"
SOP_DIR = Path(__file__).parent.parent / "data" / "sops"

# Set before opik is imported anywhere, so every trace lands in this project.
os.environ["OPIK_PROJECT_NAME"] = PROJECT_NAME
