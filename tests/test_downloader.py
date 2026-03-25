"""Tests for PDF download functionality."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
import pytest

from arxiv_hunt.downloader import (
    make_pdf_filename,
    download_paper_pdf,
    download_papers_pdf,
)
from arxiv_hunt.models import Paper


def _make_paper(**kwargs) -> Paper:
    defaults = dict(
        arxiv_id="2602.12345v1",
        title="Attention Is All You Need",
        authors="Vaswani, Ashish; Shazeer, Noam",
        abstract="Test abstract.",
        published="2026-02-20",
        updated="",
        primary_category="cs.CL",
        categories="cs.CL; cs.AI",
        pdf_url="https://arxiv.org/pdf/2602.12345v1",
        entry_url="https://arxiv.org/abs/2602.12345v1",
    )
    defaults.update(kwargs)
    return Paper(**defaults)


class TestMakePdfFilename:
    def test_basic_filename(self):
        paper = _make_paper()
        name = make_pdf_filename(paper)
        assert name.endswith(".pdf")
        assert "2602.12345v1" in name

    def test_filename_includes_first_author(self):
        paper = _make_paper(authors="Smith, John; Doe, Jane")
        name = make_pdf_filename(paper)
        assert "Smith" in name or "smith" in name.lower()

    def test_filename_includes_year(self):
        paper = _make_paper(published="2026-02-20")
        name = make_pdf_filename(paper)
        assert "2026" in name

    def test_filename_sanitized(self):
        paper = _make_paper(title="What/Why: A Study of $100 & More?")
        name = make_pdf_filename(paper)
        assert "/" not in name
        assert "\\" not in name
        assert "?" not in name

    def test_filename_length_limit(self):
        paper = _make_paper(title="A" * 300)
        name = make_pdf_filename(paper)
        assert len(name) <= 255


class TestDownloadPaperPdf:
    @patch("arxiv_hunt.downloader.urllib.request.urlretrieve")
    def test_download_creates_file(self, mock_urlretrieve, tmp_path):
        # Mock urlretrieve to create the file
        def fake_retrieve(url, filename):
            Path(filename).write_bytes(b"%PDF-1.4 fake content")
            return filename, {}
        mock_urlretrieve.side_effect = fake_retrieve

        paper = _make_paper()
        result = download_paper_pdf(paper, output_dir=tmp_path)
        assert result is not None
        assert result.exists()
        assert result.suffix == ".pdf"
        mock_urlretrieve.assert_called_once()

    @patch("arxiv_hunt.downloader.urllib.request.urlretrieve")
    def test_download_skips_existing(self, mock_urlretrieve, tmp_path):
        paper = _make_paper()
        # Pre-create the file
        expected = tmp_path / make_pdf_filename(paper)
        expected.write_bytes(b"%PDF-1.4 existing")

        result = download_paper_pdf(paper, output_dir=tmp_path, skip_existing=True)
        assert result == expected
        mock_urlretrieve.assert_not_called()

    @patch("arxiv_hunt.downloader.urllib.request.urlretrieve")
    def test_download_no_pdf_url(self, mock_urlretrieve, tmp_path):
        paper = _make_paper(pdf_url="")
        result = download_paper_pdf(paper, output_dir=tmp_path)
        assert result is None
        mock_urlretrieve.assert_not_called()

    @patch("arxiv_hunt.downloader.urllib.request.urlretrieve")
    def test_download_network_error(self, mock_urlretrieve, tmp_path):
        mock_urlretrieve.side_effect = OSError("Network error")
        paper = _make_paper()
        result = download_paper_pdf(paper, output_dir=tmp_path)
        assert result is None


class TestDownloadPapersPdf:
    @patch("arxiv_hunt.downloader.urllib.request.urlretrieve")
    def test_bulk_download(self, mock_urlretrieve, tmp_path):
        def fake_retrieve(url, filename):
            Path(filename).write_bytes(b"%PDF-1.4 fake")
            return filename, {}
        mock_urlretrieve.side_effect = fake_retrieve

        papers = [_make_paper(arxiv_id=f"2602.{i:05d}v1") for i in range(3)]
        results = download_papers_pdf(papers, output_dir=tmp_path)
        assert len(results) == 3
        assert all(r is not None and r.exists() for r in results)

    @patch("arxiv_hunt.downloader.urllib.request.urlretrieve")
    def test_bulk_download_empty_list(self, mock_urlretrieve, tmp_path):
        results = download_papers_pdf([], output_dir=tmp_path)
        assert results == []
        mock_urlretrieve.assert_not_called()

    @patch("arxiv_hunt.downloader.urllib.request.urlretrieve")
    def test_bulk_download_partial_failure(self, mock_urlretrieve, tmp_path):
        call_count = 0
        def fake_retrieve(url, filename):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise OSError("Network error")
            Path(filename).write_bytes(b"%PDF-1.4 fake")
            return filename, {}
        mock_urlretrieve.side_effect = fake_retrieve

        papers = [_make_paper(arxiv_id=f"2602.{i:05d}v1") for i in range(3)]
        results = download_papers_pdf(papers, output_dir=tmp_path)
        assert len(results) == 3
        # 1st and 3rd succeed, 2nd fails
        assert results[0] is not None
        assert results[1] is None
        assert results[2] is not None
