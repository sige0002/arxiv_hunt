"""Output formatters for arxiv_hunt."""
from __future__ import annotations

import json

from arxiv_hunt.models import Paper


def papers_to_json(papers: list[Paper]) -> list[dict[str, str]]:
    """Convert papers to a list of dictionaries."""
    return [p.to_csv_row() for p in papers]


def papers_to_json_str(
    papers: list[Paper],
    *,
    indent: int | None = 2,
) -> str:
    """Convert papers to a JSON string."""
    data = papers_to_json(papers)
    return json.dumps(data, ensure_ascii=False, indent=indent)
