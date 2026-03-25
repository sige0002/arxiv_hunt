"""Data models for arxiv_hunt."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import arxiv


@dataclass
class Paper:
    """Represents an arXiv paper."""

    arxiv_id: str
    title: str
    authors: str
    abstract: str
    published: str
    updated: str
    primary_category: str
    categories: str
    pdf_url: str
    entry_url: str

    @classmethod
    def from_arxiv_result(cls, result: arxiv.Result) -> Paper:
        """Create a Paper from an arxiv.Result object."""
        return cls(
            arxiv_id=result.get_short_id(),
            title=result.title.replace("\n", " ").strip(),
            authors="; ".join(a.name for a in result.authors),
            abstract=result.summary.replace("\n", " ").strip(),
            published=result.published.strftime("%Y-%m-%d"),
            updated=result.updated.strftime("%Y-%m-%d") if result.updated else "",
            primary_category=result.primary_category,
            categories="; ".join(result.categories),
            pdf_url=result.pdf_url or "",
            entry_url=result.entry_id,
        )

    def to_csv_row(self) -> dict[str, str]:
        """Return a dict suitable for csv.DictWriter."""
        return {
            "arxiv_id": self.arxiv_id,
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract,
            "published": self.published,
            "updated": self.updated,
            "primary_category": self.primary_category,
            "categories": self.categories,
            "pdf_url": self.pdf_url,
            "entry_url": self.entry_url,
        }
