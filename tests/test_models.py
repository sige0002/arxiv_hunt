"""Tests for arxiv_hunt.models module."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import Mock

from arxiv_hunt.config import CSV_COLUMNS
from arxiv_hunt.models import Paper


class TestFromArxivResult:
    """Tests for Paper.from_arxiv_result."""

    def test_from_arxiv_result_basic(self, mock_arxiv_result: Mock) -> None:
        """All fields should be correctly mapped from arxiv.Result."""
        paper = Paper.from_arxiv_result(mock_arxiv_result)

        assert paper.arxiv_id == "2602.12345v1"
        assert paper.title == "Test Paper Title With Newline"
        assert paper.authors == "Author One; Author Two"
        assert paper.abstract == "Test abstract with newline"
        assert paper.published == "2026-02-20"
        assert paper.updated == "2026-02-22"
        assert paper.primary_category == "cs.CL"
        assert paper.categories == "cs.CL; cs.AI"
        assert paper.pdf_url == "https://arxiv.org/pdf/2602.12345v1"
        assert paper.entry_url == "https://arxiv.org/abs/2602.12345v1"

    def test_from_arxiv_result_newline_removal(self, mock_arxiv_result: Mock) -> None:
        """Newlines in title and abstract should be replaced with spaces."""
        paper = Paper.from_arxiv_result(mock_arxiv_result)

        assert "\n" not in paper.title
        assert "\n" not in paper.abstract
        assert "Title With" in paper.title
        assert "abstract with" in paper.abstract

    def test_from_arxiv_result_no_updated(self, mock_arxiv_result: Mock) -> None:
        """When updated is None, updated field should be empty string."""
        mock_arxiv_result.updated = None
        paper = Paper.from_arxiv_result(mock_arxiv_result)

        assert paper.updated == ""

    def test_from_arxiv_result_no_pdf_url(self, mock_arxiv_result: Mock) -> None:
        """When pdf_url is None, pdf_url field should be empty string."""
        mock_arxiv_result.pdf_url = None
        paper = Paper.from_arxiv_result(mock_arxiv_result)

        assert paper.pdf_url == ""


class TestToCsvRow:
    """Tests for Paper.to_csv_row."""

    def test_to_csv_row_keys(self, sample_paper: Paper) -> None:
        """CSV row keys should match CSV_COLUMNS."""
        row = sample_paper.to_csv_row()
        assert set(row.keys()) == set(CSV_COLUMNS)

    def test_to_csv_row_values(self, sample_paper: Paper) -> None:
        """CSV row values should match Paper fields."""
        row = sample_paper.to_csv_row()

        assert row["arxiv_id"] == "2602.12345v1"
        assert row["title"] == "Test Paper Title With Newline"
        assert row["authors"] == "Author One; Author Two"
        assert row["abstract"] == "Test abstract with newline"
        assert row["published"] == "2026-02-20"
        assert row["updated"] == "2026-02-22"
        assert row["primary_category"] == "cs.CL"
        assert row["categories"] == "cs.CL; cs.AI"
        assert row["pdf_url"] == "https://arxiv.org/pdf/2602.12345v1"
        assert row["entry_url"] == "https://arxiv.org/abs/2602.12345v1"
