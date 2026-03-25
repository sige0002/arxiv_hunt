"""Scheduled watch/patrol for new arXiv papers."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from arxiv_hunt.client import ArxivClient
from arxiv_hunt.models import Paper

logger = logging.getLogger(__name__)


@dataclass
class WatchEntry:
    """A single watch/patrol configuration entry."""

    name: str
    query: str
    categories: list[str] = field(default_factory=list)
    days: int = 1
    max_results: int = 20


@dataclass
class WatchConfig:
    """Configuration for scheduled watches."""

    watches: list[WatchEntry]
    slack_webhook_url: str | None = None


def load_watch_config(config_path: Path) -> WatchConfig:
    """Load watch configuration from a YAML file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Watch config not found: {config_path}")

    with open(config_path, encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)

    watches: list[WatchEntry] = []
    for entry in data.get("watches", []):
        watches.append(
            WatchEntry(
                name=entry["name"],
                query=entry.get("query", ""),
                categories=entry.get("categories", []),
                days=entry.get("days", 1),
                max_results=entry.get("max_results", 20),
            )
        )

    return WatchConfig(
        watches=watches,
        slack_webhook_url=data.get("slack_webhook_url"),
    )


def run_watch(config: WatchConfig) -> dict[str, list[Paper]]:
    """Execute all watches and return results keyed by watch name."""
    client = ArxivClient()
    results: dict[str, list[Paper]] = {}

    for watch in config.watches:
        logger.info("Running watch: %s (query=%r)", watch.name, watch.query)
        papers = client.search(
            query=watch.query,
            max_results=watch.max_results,
            days=watch.days,
            categories=watch.categories or None,
        )
        results[watch.name] = papers
        logger.info("Watch '%s': found %d papers", watch.name, len(papers))

    return results


def format_slack_message(watch_name: str, papers: list[Paper]) -> str:
    """Format papers as a Slack message."""
    if not papers:
        return f"*{watch_name}*: 新着論文なし (0件)"

    lines = [f"*{watch_name}*: {len(papers)}件の新着論文"]
    for paper in papers[:10]:  # Limit to 10 for Slack
        lines.append(
            f"  - <{paper.entry_url}|{paper.title}>"
            f" [{paper.primary_category}] ({paper.arxiv_id})"
        )

    if len(papers) > 10:
        lines.append(f"  ... 他{len(papers) - 10}件")

    return "\n".join(lines)
