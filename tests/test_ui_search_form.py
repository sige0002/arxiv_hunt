"""Tests for the Web UI search form validation."""

from __future__ import annotations

from ui.components.search_form import _validate_input


class TestValidateInput:
    def test_query_and_author_both_empty_with_categories_is_rejected(self):
        err = _validate_input("", "", ["cs.AI", "cs.LG"])
        assert err is not None
        assert "query or author" in err

    def test_query_and_author_both_empty_no_categories_is_rejected(self):
        err = _validate_input("", "", [])
        assert err is not None

    def test_query_only_is_accepted(self):
        assert _validate_input("transformer", "", []) is None

    def test_author_only_is_accepted(self):
        assert _validate_input("", "Yann LeCun", ["cs.LG"]) is None

    def test_query_with_shell_metacharacter_is_rejected(self):
        err = _validate_input("ml; rm -rf /", "", [])
        assert err is not None
        assert "disallowed" in err

    def test_query_over_max_length_is_rejected(self):
        err = _validate_input("a" * 501, "", [])
        assert err is not None
        assert "too long" in err

    def test_whitespace_only_query_is_treated_as_empty(self):
        err = _validate_input("   ", "   ", ["cs.AI"])
        assert err is not None
        assert "query or author" in err
