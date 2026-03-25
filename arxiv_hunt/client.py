"""arXiv API client for arxiv_hunt."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

import arxiv

from arxiv_hunt.config import ARXIV_RATE_LIMIT_SECONDS, DEFAULT_DAYS, DEFAULT_MAX_RESULTS
from arxiv_hunt.models import Paper

logger = logging.getLogger(__name__)


class ArxivClient:
    """Client for searching arXiv papers."""

    def __init__(self, rate_limit: float = ARXIV_RATE_LIMIT_SECONDS) -> None:
        self.rate_limit = rate_limit

    def search(
        self,
        query: str,
        *,
        max_results: int = DEFAULT_MAX_RESULTS,
        days: int | None = DEFAULT_DAYS,
        start_date: date | None = None,
        end_date: date | None = None,
        category: str | None = None,
        categories: list[str] | None = None,
        author: str | None = None,
        author_operator: str = "AND",
    ) -> list[Paper]:
        """Search arXiv for papers matching the query.

        Args:
            query: arXiv search query string.
            max_results: Maximum number of results to return.
            days: If set, only return papers published within this many days.
                  Ignored when start_date/end_date are provided.
            start_date: If set, only return papers published on or after this date.
            end_date: If set, only return papers published on or before this date.
            category: If set, filter to this arXiv category (single).
            categories: If set, filter to these arXiv categories (multiple, OR-joined).
            author: If set, add author filter to the query.
            author_operator: How to combine query and author filter ("AND" or "OR").

        Returns:
            List of Paper objects.
        """
        parts: list[str] = []

        if query and query.strip():
            parts.append(f"({query})")

        if author and author.strip():
            parts.append(f'au:"{author.strip()}"')

        if parts:
            op = f" {author_operator.upper()} "
            search_query = op.join(parts)
        else:
            search_query = query

        # Category filter: prefer categories (plural) over category (singular)
        cat_filter: str | None = None
        if categories:
            cat_filter = " OR ".join(f"cat:{c}" for c in categories)
        elif category:
            cat_filter = f"cat:{category}"

        if cat_filter:
            search_query = f"({cat_filter}) AND ({search_query})"

        logger.info("Searching arXiv: query=%r, max_results=%d, days=%s", search_query, max_results, days)

        search = arxiv.Search(
            query=search_query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )

        client = arxiv.Client(
            page_size=min(max_results, 100),
            delay_seconds=self.rate_limit,
        )

        # Date filtering: prefer explicit start_date/end_date over days
        dt_start: datetime | None = None
        dt_end: datetime | None = None

        if start_date is not None or end_date is not None:
            if start_date is not None:
                dt_start = datetime(start_date.year, start_date.month, start_date.day, tzinfo=timezone.utc)
            if end_date is not None:
                dt_end = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59, tzinfo=timezone.utc)
            logger.info("Date filter: %s to %s",
                        dt_start.strftime("%Y-%m-%d") if dt_start else "–",
                        dt_end.strftime("%Y-%m-%d") if dt_end else "–")
        elif days is not None:
            dt_start = datetime.now(timezone.utc) - timedelta(days=days)
            logger.info("Date filter: papers after %s", dt_start.strftime("%Y-%m-%d"))

        papers: list[Paper] = []
        for result in client.results(search):
            if dt_start and result.published < dt_start:
                logger.debug("Skipping %s (published %s, before start)", result.get_short_id(), result.published)
                continue
            if dt_end and result.published > dt_end:
                logger.debug("Skipping %s (published %s, after end)", result.get_short_id(), result.published)
                continue

            paper = Paper.from_arxiv_result(result)
            papers.append(paper)
            logger.debug("Found: [%s] %s", paper.arxiv_id, paper.title[:80])

        logger.info("Found %d papers", len(papers))
        return papers
