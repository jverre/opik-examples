"""Corpus loader: one chunk per '##' section of each guide chapter."""

from park_rag.config import GUIDE_DIR


def load_chunks() -> list[str]:
    chunks = []
    for path in sorted(GUIDE_DIR.glob("*.md")):
        title, *sections = path.read_text().split("\n## ")
        for section in sections:
            chunks.append(f"{title.strip()}\n\n## {section.strip()}")
    return chunks
