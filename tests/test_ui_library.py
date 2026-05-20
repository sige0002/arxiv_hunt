"""Tests for the Library page helper functions (DB-backed, headless)."""

from __future__ import annotations

from arxiv_hunt.database import PaperDatabase
from arxiv_hunt.models import Paper
from arxiv_hunt.tags import tag_paper
from ui.components.library import _intersect_papers, _papers_from_history_row


def _mk_paper(arxiv_id: str, title: str = "T", abstract: str = "A") -> Paper:
    return Paper(
        arxiv_id=arxiv_id,
        title=title,
        authors="A One",
        abstract=abstract,
        published="2026-05-12",
        updated="",
        primary_category="cs.AI",
        categories="cs.AI",
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
        entry_url=f"https://arxiv.org/abs/{arxiv_id}",
    )


class TestFTS5SearchViaLibrary:
    def test_fts5_returns_only_matching_papers(self, tmp_path):
        db = PaperDatabase(tmp_path / "lib.db")
        db.upsert_paper(_mk_paper("2605.0001", title="Attention is All You Need"))
        db.upsert_paper(_mk_paper("2605.0002", title="Convolutional Networks"))

        hits = db.search_papers("Attention")
        ids = [p.arxiv_id for p in hits]
        assert ids == ["2605.0001"]

        zero = db.search_papers("Nonexistent")
        assert zero == []


class TestTagIntersection:
    def test_intersect_two_tag_groups(self, tmp_path):
        db = PaperDatabase(tmp_path / "lib.db")
        p1 = _mk_paper("2605.0001")
        p2 = _mk_paper("2605.0002")
        db.upsert_paper(p1)
        db.upsert_paper(p2)
        tag_paper(db, p1.arxiv_id, "llm")
        tag_paper(db, p2.arxiv_id, "llm")
        tag_paper(db, p2.arxiv_id, "to-read")

        from arxiv_hunt.tags import list_papers_by_tag

        groups = [
            list_papers_by_tag(db, "llm"),
            list_papers_by_tag(db, "to-read"),
        ]
        result = _intersect_papers(groups)
        assert [p.arxiv_id for p in result] == ["2605.0002"]

    def test_intersect_with_disjoint_groups_is_empty(self):
        p1 = _mk_paper("a")
        p2 = _mk_paper("b")
        assert _intersect_papers([[p1], [p2]]) == []

    def test_intersect_empty_input_is_empty(self):
        assert _intersect_papers([]) == []


class TestLoadHistoricalSearch:
    def test_papers_from_history_row_preserves_rank_order(self, tmp_path):
        db = PaperDatabase(tmp_path / "lib.db")
        papers = [_mk_paper(f"260{i}.{i:04d}") for i in range(3)]
        for p in papers:
            db.upsert_paper(p)
        sid = db.save_search("transformer", {"max_results": 3}, papers)

        reloaded = _papers_from_history_row(db, sid)
        assert [p.arxiv_id for p in reloaded] == [p.arxiv_id for p in papers]
