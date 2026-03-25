"""Tests for tag management functions."""
from __future__ import annotations
from pathlib import Path

import pytest
from arxiv_hunt.database import PaperDatabase
from arxiv_hunt.models import Paper
from arxiv_hunt.tags import (
    tag_paper,
    untag_paper,
    list_tags,
    list_papers_by_tag,
    bulk_tag_papers,
)


def _make_paper(**kwargs) -> Paper:
    defaults = dict(
        arxiv_id="2602.12345v1",
        title="Test Paper",
        authors="Author One; Author Two",
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


@pytest.fixture
def db(tmp_path: Path) -> PaperDatabase:
    database = PaperDatabase(tmp_path / "test.db")
    # Seed with some papers
    database.upsert_paper(_make_paper(arxiv_id="001", title="Paper A"))
    database.upsert_paper(_make_paper(arxiv_id="002", title="Paper B"))
    database.upsert_paper(_make_paper(arxiv_id="003", title="Paper C"))
    return database


class TestTagPaper:
    def test_tag_paper_creates_tag_and_associates(self, db: PaperDatabase):
        tag_paper(db, "001", "important")
        tags = db.get_tags_for_paper("001")
        assert "important" in tags

    def test_tag_paper_idempotent(self, db: PaperDatabase):
        tag_paper(db, "001", "survey")
        tag_paper(db, "001", "survey")  # second call should not error
        tags = db.get_tags_for_paper("001")
        assert tags.count("survey") == 1

    def test_tag_multiple_papers_same_tag(self, db: PaperDatabase):
        tag_paper(db, "001", "reading")
        tag_paper(db, "002", "reading")
        papers = list_papers_by_tag(db, "reading")
        assert len(papers) == 2

    def test_tag_paper_nonexistent_paper(self, db: PaperDatabase):
        # Should not raise, just silently skip
        tag_paper(db, "nonexistent", "test")
        papers = list_papers_by_tag(db, "test")
        assert len(papers) == 0


class TestUntagPaper:
    def test_untag_removes_association(self, db: PaperDatabase):
        tag_paper(db, "001", "survey")
        untag_paper(db, "001", "survey")
        tags = db.get_tags_for_paper("001")
        assert "survey" not in tags

    def test_untag_nonexistent_tag(self, db: PaperDatabase):
        # Should not raise
        untag_paper(db, "001", "nonexistent_tag")

    def test_untag_preserves_other_tags(self, db: PaperDatabase):
        tag_paper(db, "001", "survey")
        tag_paper(db, "001", "important")
        untag_paper(db, "001", "survey")
        tags = db.get_tags_for_paper("001")
        assert "survey" not in tags
        assert "important" in tags


class TestListTags:
    def test_list_all_tags(self, db: PaperDatabase):
        tag_paper(db, "001", "survey")
        tag_paper(db, "002", "baseline")
        tag_paper(db, "003", "important")
        tags = list_tags(db)
        assert set(tags) == {"survey", "baseline", "important"}

    def test_list_tags_empty(self, db: PaperDatabase):
        tags = list_tags(db)
        assert tags == []


class TestListPapersByTag:
    def test_list_papers_with_tag(self, db: PaperDatabase):
        tag_paper(db, "001", "reading")
        tag_paper(db, "003", "reading")
        papers = list_papers_by_tag(db, "reading")
        ids = [p.arxiv_id for p in papers]
        assert "001" in ids
        assert "003" in ids
        assert "002" not in ids

    def test_list_papers_no_results(self, db: PaperDatabase):
        papers = list_papers_by_tag(db, "nonexistent")
        assert papers == []


class TestBulkTagPapers:
    def test_bulk_tag(self, db: PaperDatabase):
        bulk_tag_papers(db, ["001", "002", "003"], "batch-read")
        for aid in ["001", "002", "003"]:
            assert "batch-read" in db.get_tags_for_paper(aid)

    def test_bulk_tag_partial(self, db: PaperDatabase):
        # One paper doesn't exist
        bulk_tag_papers(db, ["001", "nonexistent", "003"], "partial")
        assert "partial" in db.get_tags_for_paper("001")
        assert "partial" in db.get_tags_for_paper("003")
