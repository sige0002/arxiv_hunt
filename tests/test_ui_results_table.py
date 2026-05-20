"""Tests for citation byte helpers and tag diff parsing."""

from __future__ import annotations

from arxiv_hunt.bibtex import paper_to_bibtex, paper_to_ris
from ui.components.results_table import (
    _papers_to_bibtex_bytes,
    _papers_to_ris_bytes,
    _parse_tag_input,
)


class TestCitationBytes:
    def test_bibtex_bytes_match_concatenated_per_paper_output(self, sample_papers):
        expected = "\n\n".join(paper_to_bibtex(p) for p in sample_papers).encode("utf-8")
        assert _papers_to_bibtex_bytes(sample_papers) == expected

    def test_ris_bytes_match_concatenated_per_paper_output(self, sample_papers):
        expected = "\n\n".join(paper_to_ris(p) for p in sample_papers).encode("utf-8")
        assert _papers_to_ris_bytes(sample_papers) == expected

    def test_bibtex_bytes_is_utf8_decodable(self, sample_papers):
        # Ensure output round-trips through UTF-8.
        _papers_to_bibtex_bytes(sample_papers).decode("utf-8")

    def test_single_paper_bibtex_bytes_has_no_trailing_separator(self, sample_paper):
        b = _papers_to_bibtex_bytes([sample_paper])
        assert not b.endswith(b"\n\n")


class TestParseTagInput:
    def test_simple_comma_separated(self):
        assert _parse_tag_input("llm, to-read") == {"llm", "to-read"}

    def test_strips_surrounding_whitespace(self):
        assert _parse_tag_input("  a , b  ,c") == {"a", "b", "c"}

    def test_empty_segments_are_dropped(self):
        assert _parse_tag_input(",, llm,, , ") == {"llm"}

    def test_empty_input_yields_empty_set(self):
        assert _parse_tag_input("") == set()

    def test_duplicate_tags_collapse(self):
        assert _parse_tag_input("a, a, A") == {"a", "A"}
