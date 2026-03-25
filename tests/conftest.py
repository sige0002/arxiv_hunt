"""Shared test fixtures for arxiv_hunt."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

import pytest

from arxiv_hunt.models import Paper


@pytest.fixture()
def sample_paper() -> Paper:
    """Return a single Paper instance for testing."""
    return Paper(
        arxiv_id="2602.12345v1",
        title="Test Paper Title With Newline",
        authors="Author One; Author Two",
        abstract="Test abstract with newline",
        published="2026-02-20",
        updated="2026-02-22",
        primary_category="cs.CL",
        categories="cs.CL; cs.AI",
        pdf_url="https://arxiv.org/pdf/2602.12345v1",
        entry_url="https://arxiv.org/abs/2602.12345v1",
    )


@pytest.fixture()
def sample_papers(sample_paper: Paper) -> list[Paper]:
    """Return a list of Paper instances for testing."""
    second = Paper(
        arxiv_id="2602.67890v1",
        title="Second Paper Title",
        authors="Author Three",
        abstract="Second abstract",
        published="2026-02-21",
        updated="",
        primary_category="cs.AI",
        categories="cs.AI",
        pdf_url="https://arxiv.org/pdf/2602.67890v1",
        entry_url="https://arxiv.org/abs/2602.67890v1",
    )
    return [sample_paper, second]


@pytest.fixture()
def mock_arxiv_result() -> Mock:
    """Return a mock arxiv.Result object for testing from_arxiv_result."""
    result = Mock()
    result.get_short_id.return_value = "2602.12345v1"
    result.title = "Test Paper Title\nWith Newline"
    author1 = Mock()
    author1.name = "Author One"
    author2 = Mock()
    author2.name = "Author Two"
    result.authors = [author1, author2]
    result.summary = "Test abstract\nwith newline"
    result.published = datetime(2026, 2, 20, tzinfo=timezone.utc)
    result.updated = datetime(2026, 2, 22, tzinfo=timezone.utc)
    result.primary_category = "cs.CL"
    result.categories = ["cs.CL", "cs.AI"]
    result.pdf_url = "https://arxiv.org/pdf/2602.12345v1"
    result.entry_id = "https://arxiv.org/abs/2602.12345v1"
    return result


@pytest.fixture()
def tmp_csv_dir(tmp_path: Path) -> Path:
    """Return a temporary directory for CSV output."""
    csv_dir = tmp_path / "csv_output"
    csv_dir.mkdir()
    return csv_dir
