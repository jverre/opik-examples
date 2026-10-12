"""Load the fictional Tidewater release commit lists from data/releases."""

import json
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "releases"


@dataclass(frozen=True)
class Release:
    version: str
    date: str
    product: str
    description: str
    commits: list[dict]

    def commit_lines(self) -> str:
        """Render the commits the way `git log --oneline` would show them."""
        return "\n".join(
            f"{c['sha']} {c['type']}({c['scope']}): {c['message']} [{c['author']}]"
            for c in self.commits
        )


def load_releases(data_dir: Path = DATA_DIR) -> list[Release]:
    releases = []
    for path in sorted(data_dir.glob("v*.json")):
        raw = json.loads(path.read_text())
        releases.append(
            Release(
                version=raw["version"],
                date=raw["date"],
                product=raw["product"],
                description=raw["description"],
                commits=raw["commits"],
            )
        )
    return releases
