"""Tests for the PDF-ZIP bundling helper."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from ui.utils import pdf_zip as pdf_zip_module
from ui.utils.pdf_zip import papers_to_pdf_zip


def test_zip_contains_downloaded_pdfs_and_summary(tmp_path, monkeypatch, sample_papers):
    # Materialize two fake PDFs in a fake download directory.
    a = tmp_path / "paperA.pdf"
    b = tmp_path / "paperB.pdf"
    a.write_bytes(b"FAKE-A")
    b.write_bytes(b"FAKE-B")

    # Stub download_papers_pdf — first paper succeeds, second fails.
    def fake_download(papers, *, output_dir=None, rate_limit=None, skip_existing=True):
        return [a, None]

    # Re-target the symbol imported into the pdf_zip module.
    monkeypatch.setattr(pdf_zip_module, "download_papers_pdf", fake_download)

    zip_bytes, summary = papers_to_pdf_zip(sample_papers[:2])

    assert summary["ok"] == 1
    assert summary["failed"] == 1
    assert summary["failed_ids"] == [sample_papers[1].arxiv_id]

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = sorted(zf.namelist())
        assert "paperA.pdf" in names
        assert "summary.txt" in names
        # No member for the failed paper.
        assert "paperB.pdf" not in names

        text = zf.read("summary.txt").decode("utf-8")
        assert "success=1" in text
        assert "failed=1" in text
        assert sample_papers[1].arxiv_id in text


def test_empty_input_returns_zip_with_only_summary(monkeypatch):
    def fake_download(papers, *, output_dir=None, rate_limit=None, skip_existing=True):
        return []

    monkeypatch.setattr(pdf_zip_module, "download_papers_pdf", fake_download)

    zip_bytes, summary = papers_to_pdf_zip([])

    assert summary == {"ok": 0, "failed": 0, "failed_ids": []}
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        assert zf.namelist() == ["summary.txt"]
