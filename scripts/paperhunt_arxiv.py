#!/usr/bin/env python3
"""CLI tool for searching arXiv papers and saving results to CSV.

Usage examples:
    python -m arxiv_hunt.scripts.paperhunt_arxiv --query "transformer attention"
    python -m arxiv_hunt.scripts.paperhunt_arxiv --query "LLM reasoning" --days 14 --max 50 --category cs.CL
    python -m arxiv_hunt.scripts.paperhunt_arxiv --query "diffusion models" -v
"""

from __future__ import annotations

import argparse
import logging
import sys

from arxiv_hunt.config import (
    ARXIV_CATEGORIES,
    DEFAULT_DAYS,
    DEFAULT_MAX_RESULTS,
    MAX_QUERY_LENGTH,
    SHELL_META_CHARS,
)
from arxiv_hunt.client import ArxivClient
from arxiv_hunt.csv_io import save_papers_to_csv

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="paperhunt_arxiv",
        description="Search arXiv for recent papers and save results to CSV.",
    )
    parser.add_argument(
        "--query",
        required=True,
        help="arXiv search query string (e.g. 'transformer attention mechanism').",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_DAYS,
        help=f"Number of days to look back (default: {DEFAULT_DAYS}).",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=DEFAULT_MAX_RESULTS,
        dest="max_results",
        help=f"Maximum number of results to return (default: {DEFAULT_MAX_RESULTS}).",
    )
    parser.add_argument(
        "--category",
        default=None,
        choices=sorted(ARXIV_CATEGORIES.keys()),
        help="Optional arXiv category filter (e.g. cs.AI, cs.CL).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser


def validate_query(query: str) -> None:
    """Validate the search query for safety and length.

    Raises:
        SystemExit: If the query is invalid.
    """
    if not query.strip():
        logger.error("Query must not be empty.")
        sys.exit(1)

    if len(query) > MAX_QUERY_LENGTH:
        logger.error(
            "Query too long (%d chars). Maximum allowed: %d.",
            len(query),
            MAX_QUERY_LENGTH,
        )
        sys.exit(1)

    dangerous_chars = SHELL_META_CHARS.intersection(query)
    if dangerous_chars:
        logger.error(
            "Query contains disallowed characters: %s",
            ", ".join(sorted(dangerous_chars)),
        )
        sys.exit(1)


def main(argv: list[str] | None = None) -> None:
    """Main entry point for the paperhunt_arxiv CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.info("paperhunt_arxiv starting")
    logger.debug(
        "Parameters: query=%r, days=%d, max_results=%d, category=%s",
        args.query,
        args.days,
        args.max_results,
        args.category,
    )

    # Validate inputs
    validate_query(args.query)

    if args.days < 1:
        logger.error("--days must be at least 1.")
        sys.exit(1)

    if args.max_results < 1:
        logger.error("--max must be at least 1.")
        sys.exit(1)

    # Search arXiv
    try:
        client = ArxivClient()
        papers = client.search(
            args.query,
            max_results=args.max_results,
            days=args.days,
            category=args.category,
        )
    except Exception:
        logger.exception("Failed to search arXiv.")
        sys.exit(1)

    if not papers:
        logger.warning("No papers found matching the query.")
        print("No papers found.")
        return

    # Save results to CSV
    try:
        results_path, archive_path = save_papers_to_csv(papers, args.query)
    except Exception:
        logger.exception("Failed to save results to CSV.")
        sys.exit(1)

    # Print summary
    print(f"\nFound {len(papers)} paper(s):\n")
    for i, paper in enumerate(papers, start=1):
        print(f"  {i}. [{paper.arxiv_id}] {paper.title}")
        print(f"     Published: {paper.published} | Category: {paper.primary_category}")
        if args.verbose:
            print(f"     Authors: {paper.authors}")
            print(f"     URL: {paper.entry_url}")
        print()

    print(f"Results saved to: {results_path}")
    print(f"Archive saved to: {archive_path}")


if __name__ == "__main__":
    main()
