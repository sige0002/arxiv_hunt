"""Tests for arxiv_hunt.csv_io module."""

from __future__ import annotations

import time
from pathlib import Path

from arxiv_hunt.csv_io import (
    _sanitize_cell,
    cleanup_old_archives,
    list_recent_archives,
    load_papers_from_csv,
    sanitize_filename,
    save_papers_to_csv,
)
from arxiv_hunt.models import Paper


# ---------------------------------------------------------------------------
# sanitize_filename tests
# ---------------------------------------------------------------------------

class TestSanitizeFilename:
    """Tests for sanitize_filename."""

    def test_sanitize_filename_basic(self) -> None:
        """Normal alphanumeric strings should pass through with minimal changes."""
        assert sanitize_filename("hello_world") == "hello_world"

    def test_sanitize_filename_path_traversal(self) -> None:
        """Path traversal characters '..' and '/' should be removed."""
        result = sanitize_filename("../../etc/passwd")
        assert ".." not in result
        assert "/" not in result

    def test_sanitize_filename_null_bytes(self) -> None:
        """Null bytes should be removed."""
        result = sanitize_filename("file\x00name")
        assert "\x00" not in result

    def test_sanitize_filename_empty(self) -> None:
        """Empty string should return 'unnamed'."""
        assert sanitize_filename("") == "unnamed"

    def test_sanitize_filename_long(self) -> None:
        """Filenames longer than 200 characters should be truncated."""
        long_name = "a" * 300
        result = sanitize_filename(long_name)
        assert len(result) <= 200


# ---------------------------------------------------------------------------
# _sanitize_cell tests
# ---------------------------------------------------------------------------

class TestSanitizeCell:
    """Tests for _sanitize_cell."""

    def test_sanitize_cell_equals(self) -> None:
        """Cells starting with '=' should be escaped with a leading apostrophe."""
        assert _sanitize_cell("=SUM(A1)") == "'=SUM(A1)"

    def test_sanitize_cell_plus(self) -> None:
        """Cells starting with '+' should be escaped with a leading apostrophe."""
        assert _sanitize_cell("+cmd") == "'+cmd"

    def test_sanitize_cell_minus(self) -> None:
        """Cells starting with '-' should be escaped with a leading apostrophe."""
        assert _sanitize_cell("-cmd") == "'-cmd"

    def test_sanitize_cell_at(self) -> None:
        """Cells starting with '@' should be escaped with a leading apostrophe."""
        assert _sanitize_cell("@SUM(A1)") == "'@SUM(A1)"

    def test_sanitize_cell_safe(self) -> None:
        """Safe cells should be returned unchanged."""
        assert _sanitize_cell("Hello World") == "Hello World"
        assert _sanitize_cell("") == ""


# ---------------------------------------------------------------------------
# save / load roundtrip tests
# ---------------------------------------------------------------------------

class TestSaveAndLoad:
    """Tests for save_papers_to_csv and load_papers_from_csv."""

    def test_save_and_load_roundtrip(
        self, sample_papers: list[Paper], tmp_csv_dir: Path
    ) -> None:
        """Papers saved to CSV should be loadable and match the originals."""
        results_path, _archive_path = save_papers_to_csv(
            sample_papers, "test query", output_dir=tmp_csv_dir
        )

        loaded = load_papers_from_csv(results_path)
        assert len(loaded) == len(sample_papers)

        for original, loaded_paper in zip(sample_papers, loaded):
            assert original.arxiv_id == loaded_paper.arxiv_id
            assert original.title == loaded_paper.title
            assert original.authors == loaded_paper.authors
            assert original.abstract == loaded_paper.abstract

    def test_save_creates_two_files(
        self, sample_papers: list[Paper], tmp_csv_dir: Path
    ) -> None:
        """save_papers_to_csv should create both results.csv and an archive file."""
        results_path, archive_path = save_papers_to_csv(
            sample_papers, "test query", output_dir=tmp_csv_dir
        )

        assert results_path.exists()
        assert archive_path.exists()
        assert results_path.name == "results.csv"
        assert archive_path.name != "results.csv"


# ---------------------------------------------------------------------------
# archive management tests
# ---------------------------------------------------------------------------

class TestArchiveManagement:
    """Tests for list_recent_archives and cleanup_old_archives."""

    def test_cleanup_old_archives(
        self, sample_papers: list[Paper], tmp_csv_dir: Path
    ) -> None:
        """cleanup_old_archives with keep=2 should delete older archives."""
        # Create 4 archive files with distinct timestamps
        for i in range(4):
            save_papers_to_csv(
                sample_papers, f"query_{i}", output_dir=tmp_csv_dir
            )
            # Small sleep to ensure distinct mtime ordering
            time.sleep(0.05)

        archives_before = list_recent_archives(tmp_csv_dir)
        assert len(archives_before) == 4

        cleanup_old_archives(tmp_csv_dir, keep=2)

        archives_after = list_recent_archives(tmp_csv_dir)
        assert len(archives_after) == 2

    def test_list_recent_archives_order(
        self, sample_papers: list[Paper], tmp_csv_dir: Path
    ) -> None:
        """list_recent_archives should return archives newest first."""
        paths = []
        for i in range(3):
            _, archive_path = save_papers_to_csv(
                sample_papers, f"query_{i}", output_dir=tmp_csv_dir
            )
            paths.append(archive_path)
            time.sleep(0.05)

        archives = list_recent_archives(tmp_csv_dir)

        # Newest first: last created should be first in list
        assert archives[0].name == paths[-1].name
        assert archives[-1].name == paths[0].name
