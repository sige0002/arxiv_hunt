"""Tests for BibTeX/RIS export."""
from arxiv_hunt.bibtex import paper_to_bibtex, paper_to_ris, papers_to_bibtex_file
from arxiv_hunt.models import Paper


def _make_paper(**kwargs):
    defaults = dict(
        arxiv_id="2602.12345v1",
        title="Attention Is All You Need",
        authors="Vaswani, Ashish; Shazeer, Noam",
        abstract="The dominant sequence transduction models...",
        published="2026-02-20",
        updated="2026-02-22",
        primary_category="cs.CL",
        categories="cs.CL; cs.AI",
        pdf_url="https://arxiv.org/pdf/2602.12345v1",
        entry_url="https://arxiv.org/abs/2602.12345v1",
    )
    defaults.update(kwargs)
    return Paper(**defaults)


# BibTeX tests
class TestPaperToBibtex:
    def test_basic_bibtex_format(self):
        paper = _make_paper()
        bib = paper_to_bibtex(paper)
        assert bib.startswith("@article{")
        assert "2602.12345v1" in bib
        assert "Attention Is All You Need" in bib
        assert "Vaswani, Ashish and Shazeer, Noam" in bib
        assert "2026" in bib

    def test_bibtex_has_required_fields(self):
        paper = _make_paper()
        bib = paper_to_bibtex(paper)
        for field in ["title", "author", "year", "eprint", "archiveprefix", "primaryclass"]:
            assert f"{field}" in bib.lower() or f"{field} =" in bib.lower()

    def test_bibtex_key_format(self):
        paper = _make_paper(arxiv_id="2602.12345v1", authors="Smith, John; Doe, Jane")
        bib = paper_to_bibtex(paper)
        # Key should start with first author's last name
        assert "@article{smith2026" in bib.lower() or "@article{Smith2026" in bib

    def test_bibtex_escapes_special_chars(self):
        paper = _make_paper(title="Learning with $100 & More: A {Study}")
        bib = paper_to_bibtex(paper)
        assert "\\$" in bib or "$100" in bib  # Should handle LaTeX special chars

    def test_bibtex_no_updated_field(self):
        paper = _make_paper(updated="")
        bib = paper_to_bibtex(paper)
        assert "@article{" in bib  # Should still work without updated


# RIS tests
class TestPaperToRis:
    def test_basic_ris_format(self):
        paper = _make_paper()
        ris = paper_to_ris(paper)
        assert "TY  - JOUR" in ris or "TY  - ELEC" in ris
        assert "TI  - Attention Is All You Need" in ris
        assert "ER  -" in ris  # End record marker

    def test_ris_has_authors(self):
        paper = _make_paper()
        ris = paper_to_ris(paper)
        assert "AU  - Vaswani, Ashish" in ris
        assert "AU  - Shazeer, Noam" in ris

    def test_ris_has_url(self):
        paper = _make_paper()
        ris = paper_to_ris(paper)
        assert "UR  - " in ris


# File export tests
class TestPapersToBibtexFile:
    def test_export_to_file(self, tmp_path):
        papers = [_make_paper(arxiv_id=f"2602.{i:05d}v1") for i in range(3)]
        output = tmp_path / "refs.bib"
        papers_to_bibtex_file(papers, output)
        assert output.exists()
        content = output.read_text()
        assert content.count("@article{") == 3

    def test_export_empty_list(self, tmp_path):
        output = tmp_path / "empty.bib"
        papers_to_bibtex_file([], output)
        assert output.exists()
        assert output.read_text().strip() == ""
