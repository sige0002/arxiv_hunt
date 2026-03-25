"""PDF download functionality for arxiv_hunt."""
from __future__ import annotations

import logging
import re
import time
import urllib.request
from pathlib import Path

from arxiv_hunt.config import ARXIV_RATE_LIMIT_SECONDS, PDF_OUTPUT_DIR
from arxiv_hunt.models import Paper

logger = logging.getLogger(__name__)


def make_pdf_filename(paper: Paper) -> str:
    """Generate a sanitized PDF filename from paper metadata.

    Format: {first_author_lastname}_{year}_{arxiv_id}.pdf
    """
    # Extract first author's last name
    first_author = paper.authors.split(";")[0].strip()
    if "," in first_author:
        last_name = first_author.split(",")[0].strip()
    elif first_author:
        last_name = first_author.split()[-1]
    else:
        last_name = "unknown"

    # Extract year
    year = paper.published[:4] if paper.published else "unknown"

    # Sanitize arxiv_id (replace path separators)
    arxiv_id = paper.arxiv_id.replace("/", "_").replace(":", "_")

    # Build filename
    raw = f"{last_name}_{year}_{arxiv_id}.pdf"

    # Sanitize: keep only word chars, hyphens, and dots
    raw = re.sub(r'[^\w\-.]', '_', raw)
    raw = re.sub(r'_+', '_', raw)
    raw = raw.strip('_.')

    # Length limit (leave room for .pdf suffix)
    if len(raw) > 250:
        raw = raw[:246] + ".pdf"

    return raw or "paper.pdf"


def download_paper_pdf(
    paper: Paper,
    *,
    output_dir: Path | None = None,
    skip_existing: bool = True,
    rate_limit: float = ARXIV_RATE_LIMIT_SECONDS,
) -> Path | None:
    """Download a single paper's PDF.

    Returns the path to the downloaded file, or None on failure.
    """
    if not paper.pdf_url:
        logger.warning("No PDF URL for %s", paper.arxiv_id)
        return None

    output_dir = output_dir or PDF_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = make_pdf_filename(paper)
    filepath = output_dir / filename

    if skip_existing and filepath.exists():
        logger.info("Skipping existing: %s", filepath)
        return filepath

    try:
        logger.info("Downloading %s -> %s", paper.pdf_url, filepath)
        urllib.request.urlretrieve(paper.pdf_url, str(filepath))
        return filepath
    except Exception:
        logger.exception("Failed to download %s", paper.arxiv_id)
        return None


def download_papers_pdf(
    papers: list[Paper],
    *,
    output_dir: Path | None = None,
    skip_existing: bool = True,
    rate_limit: float = ARXIV_RATE_LIMIT_SECONDS,
) -> list[Path | None]:
    """Download PDFs for multiple papers.

    Returns a list of paths (None for failures) in the same order as input.
    """
    results: list[Path | None] = []
    for i, paper in enumerate(papers):
        result = download_paper_pdf(
            paper, output_dir=output_dir, skip_existing=skip_existing, rate_limit=rate_limit
        )
        results.append(result)
        # Rate limit between downloads (but not after the last one)
        if i < len(papers) - 1 and rate_limit > 0:
            time.sleep(rate_limit)
    return results
