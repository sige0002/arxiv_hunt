"""Tests for SQLite database."""
import sqlite3
from arxiv_hunt.database import PaperDatabase
from arxiv_hunt.models import Paper


def _make_paper(**kwargs):
    defaults = dict(
        arxiv_id="2602.12345v1",
        title="Test Paper",
        authors="Author One; Author Two",
        abstract="Test abstract for the paper.",
        published="2026-02-20",
        updated="2026-02-22",
        primary_category="cs.CL",
        categories="cs.CL; cs.AI",
        pdf_url="https://arxiv.org/pdf/2602.12345v1",
        entry_url="https://arxiv.org/abs/2602.12345v1",
    )
    defaults.update(kwargs)
    return Paper(**defaults)


class TestPaperDatabase:
    def test_init_creates_tables(self, tmp_path):
        db = PaperDatabase(tmp_path / "test.db")
        # Verify tables exist
        conn = sqlite3.connect(tmp_path / "test.db")
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()
        assert "papers" in tables
        assert "searches" in tables
        assert "search_results" in tables
        assert "tags" in tables
        assert "paper_tags" in tables

    def test_upsert_paper(self, tmp_path):
        db = PaperDatabase(tmp_path / "test.db")
        paper = _make_paper()
        paper_id = db.upsert_paper(paper)
        assert paper_id > 0

    def test_upsert_paper_deduplicates(self, tmp_path):
        db = PaperDatabase(tmp_path / "test.db")
        paper = _make_paper()
        id1 = db.upsert_paper(paper)
        id2 = db.upsert_paper(paper)
        assert id1 == id2

    def test_get_paper_by_arxiv_id(self, tmp_path):
        db = PaperDatabase(tmp_path / "test.db")
        paper = _make_paper(title="My Special Paper")
        db.upsert_paper(paper)
        result = db.get_paper_by_arxiv_id("2602.12345v1")
        assert result is not None
        assert result.title == "My Special Paper"

    def test_get_paper_not_found(self, tmp_path):
        db = PaperDatabase(tmp_path / "test.db")
        result = db.get_paper_by_arxiv_id("nonexistent")
        assert result is None

    def test_save_search(self, tmp_path):
        db = PaperDatabase(tmp_path / "test.db")
        papers = [_make_paper(arxiv_id=f"2602.{i:05d}v1") for i in range(3)]
        search_id = db.save_search("test query", {"max_results": 10}, papers)
        assert search_id > 0

    def test_get_search_history(self, tmp_path):
        db = PaperDatabase(tmp_path / "test.db")
        papers = [_make_paper()]
        db.save_search("query1", {}, papers)
        db.save_search("query2", {}, papers)
        history = db.get_search_history(limit=10)
        assert len(history) == 2
        # Most recent first
        assert history[0]["query"] == "query2"

    def test_search_papers_fulltext(self, tmp_path):
        db = PaperDatabase(tmp_path / "test.db")
        db.upsert_paper(_make_paper(arxiv_id="001", title="Deep Learning for NLP"))
        db.upsert_paper(_make_paper(arxiv_id="002", title="Computer Vision Survey"))
        results = db.search_papers("NLP")
        assert len(results) == 1
        assert results[0].title == "Deep Learning for NLP"

    def test_all_papers(self, tmp_path):
        db = PaperDatabase(tmp_path / "test.db")
        db.upsert_paper(_make_paper(arxiv_id="001"))
        db.upsert_paper(_make_paper(arxiv_id="002"))
        all_papers = db.get_all_papers()
        assert len(all_papers) == 2

    # Tag tests
    def test_create_tag(self, tmp_path):
        db = PaperDatabase(tmp_path / "test.db")
        tag_id = db.create_tag("important")
        assert tag_id > 0

    def test_create_duplicate_tag(self, tmp_path):
        db = PaperDatabase(tmp_path / "test.db")
        id1 = db.create_tag("important")
        id2 = db.create_tag("important")
        assert id1 == id2

    def test_add_tag_to_paper(self, tmp_path):
        db = PaperDatabase(tmp_path / "test.db")
        paper = _make_paper()
        db.upsert_paper(paper)
        db.create_tag("survey")
        db.add_tag_to_paper("2602.12345v1", "survey")
        tags = db.get_tags_for_paper("2602.12345v1")
        assert "survey" in tags

    def test_remove_tag_from_paper(self, tmp_path):
        db = PaperDatabase(tmp_path / "test.db")
        paper = _make_paper()
        db.upsert_paper(paper)
        db.create_tag("survey")
        db.add_tag_to_paper("2602.12345v1", "survey")
        db.remove_tag_from_paper("2602.12345v1", "survey")
        tags = db.get_tags_for_paper("2602.12345v1")
        assert "survey" not in tags

    def test_get_papers_by_tag(self, tmp_path):
        db = PaperDatabase(tmp_path / "test.db")
        db.upsert_paper(_make_paper(arxiv_id="001"))
        db.upsert_paper(_make_paper(arxiv_id="002"))
        db.create_tag("reading")
        db.add_tag_to_paper("001", "reading")
        papers = db.get_papers_by_tag("reading")
        assert len(papers) == 1
        assert papers[0].arxiv_id == "001"

    def test_get_all_tags(self, tmp_path):
        db = PaperDatabase(tmp_path / "test.db")
        db.create_tag("important")
        db.create_tag("survey")
        db.create_tag("baseline")
        tags = db.get_all_tags()
        assert set(tags) == {"important", "survey", "baseline"}

    def test_delete_tag(self, tmp_path):
        db = PaperDatabase(tmp_path / "test.db")
        db.create_tag("temp")
        db.delete_tag("temp")
        tags = db.get_all_tags()
        assert "temp" not in tags
