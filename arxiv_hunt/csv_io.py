"""CSV I/O utilities for arxiv_hunt."""

from __future__ import annotations

import csv
import logging
import re
from datetime import datetime
from pathlib import Path

from arxiv_hunt.config import CSV_COLUMNS, CSV_OUTPUT_DIR, RESULTS_CSV_FILENAME
from arxiv_hunt.models import Paper

logger = logging.getLogger(__name__)

# Characters that could trigger formula injection in spreadsheets
_CSV_INJECTION_PREFIXES = ("=", "+", "-", "@")


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use as a filename.

    Removes path traversal characters and shell-unsafe characters.
    """
    # Remove path separators and traversal
    name = name.replace("..", "")
    name = name.replace("/", "_")
    name = name.replace("\\", "_")
    # Remove null bytes
    name = name.replace("\x00", "")
    # Replace any remaining non-alphanumeric chars (except dash, underscore, dot)
    name = re.sub(r"[^\w\-.]", "_", name)
    # Collapse multiple underscores
    name = re.sub(r"_+", "_", name)
    # Strip leading/trailing underscores and dots
    name = name.strip("_.")
    # Limit length
    if len(name) > 200:
        name = name[:200]
    return name or "unnamed"


def _sanitize_cell(value: str) -> str:
    """Prevent CSV injection by escaping dangerous cell prefixes."""
    if value and value[0] in _CSV_INJECTION_PREFIXES:
        return "'" + value
    return value


def save_papers_to_csv(
    papers: list[Paper],
    query: str,
    output_dir: Path | None = None,
    *,
    sanitize_cells: bool = True,
) -> tuple[Path, Path]:
    """Save papers to CSV files.

    Creates two files:
    - results.csv (always overwritten with latest results)
    - {query}_{timestamp}.csv (archive copy)

    Args:
        papers: List of Paper objects to save.
        query: The search query (used in archive filename).
        output_dir: Output directory (defaults to CSV_OUTPUT_DIR).
        sanitize_cells: If True, escape cells that start with formula characters.

    Returns:
        Tuple of (results_path, archive_path).
    """
    output_dir = output_dir or CSV_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    results_path = output_dir / RESULTS_CSV_FILENAME

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_query = sanitize_filename(query)
    archive_filename = f"{safe_query}_{timestamp}.csv"
    archive_path = output_dir / archive_filename

    rows = []
    for paper in papers:
        row = paper.to_csv_row()
        if sanitize_cells:
            row = {k: _sanitize_cell(v) for k, v in row.items()}
        rows.append(row)

    for path in (results_path, archive_path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        logger.info("Saved %d papers to %s", len(papers), path)

    return results_path, archive_path


MAX_ARCHIVES = 5


def list_recent_archives(output_dir: Path | None = None) -> list[Path]:
    """Return archive CSVs sorted by modification time (newest first)."""
    output_dir = output_dir or CSV_OUTPUT_DIR
    if not output_dir.is_dir():
        return []
    return sorted(
        (p for p in output_dir.glob("*.csv") if p.name != RESULTS_CSV_FILENAME),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def cleanup_old_archives(output_dir: Path | None = None, *, keep: int = MAX_ARCHIVES) -> None:
    """Delete archive CSVs exceeding *keep* count (oldest first)."""
    archives = list_recent_archives(output_dir)
    for old in archives[keep:]:
        old.unlink()
        logger.info("Deleted old archive: %s", old.name)


def load_papers_from_csv(csv_path: Path) -> list[Paper]:
    """Load papers from a CSV file.

    Args:
        csv_path: Path to the CSV file.

    Returns:
        List of Paper objects.
    """
    papers: list[Paper] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Strip CSV injection prefix if present
            cleaned = {}
            for k, v in row.items():
                if v and v.startswith("'") and len(v) > 1 and v[1] in _CSV_INJECTION_PREFIXES:
                    v = v[1:]
                cleaned[k] = v
            papers.append(Paper(**{k: cleaned.get(k, "") for k in CSV_COLUMNS}))
    logger.info("Loaded %d papers from %s", len(papers), csv_path)
    return papers
