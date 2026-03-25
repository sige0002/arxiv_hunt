"""Tests for watch/scheduled search and JSON output."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from arxiv_hunt.models import Paper
from arxiv_hunt.formatter import papers_to_json, papers_to_json_str
from arxiv_hunt.watcher import (
    WatchConfig,
    load_watch_config,
    run_watch,
    format_slack_message,
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


# ---- JSON formatter tests ----

class TestPapersToJson:
    def test_returns_list_of_dicts(self):
        papers = [_make_paper(arxiv_id="001"), _make_paper(arxiv_id="002")]
        result = papers_to_json(papers)
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["arxiv_id"] == "001"

    def test_all_fields_present(self):
        paper = _make_paper()
        result = papers_to_json([paper])
        expected_keys = {
            "arxiv_id", "title", "authors", "abstract",
            "published", "updated", "primary_category",
            "categories", "pdf_url", "entry_url",
        }
        assert set(result[0].keys()) == expected_keys

    def test_empty_list(self):
        result = papers_to_json([])
        assert result == []


class TestPapersToJsonStr:
    def test_valid_json_string(self):
        papers = [_make_paper()]
        json_str = papers_to_json_str(papers)
        parsed = json.loads(json_str)
        assert isinstance(parsed, list)
        assert len(parsed) == 1

    def test_pretty_print(self):
        papers = [_make_paper()]
        json_str = papers_to_json_str(papers, indent=2)
        assert "\n" in json_str  # Pretty printed has newlines

    def test_compact(self):
        papers = [_make_paper()]
        json_str = papers_to_json_str(papers, indent=None)
        lines = json_str.strip().split("\n")
        # Compact JSON should be fewer lines
        assert len(lines) <= 2


# ---- Watch config tests ----

class TestWatchConfig:
    def test_load_config_from_yaml(self, tmp_path: Path):
        config_file = tmp_path / "watch.yaml"
        config_file.write_text("""
watches:
  - name: "LLM papers"
    query: "large language model"
    categories: ["cs.CL", "cs.AI"]
    days: 1
    max_results: 20
  - name: "CV papers"
    query: "object detection"
    categories: ["cs.CV"]
    days: 3
    max_results: 10
slack_webhook_url: "https://hooks.slack.com/services/xxx"
""")
        config = load_watch_config(config_file)
        assert len(config.watches) == 2
        assert config.watches[0].name == "LLM papers"
        assert config.watches[0].query == "large language model"
        assert config.watches[0].categories == ["cs.CL", "cs.AI"]
        assert config.watches[0].days == 1
        assert config.watches[0].max_results == 20
        assert config.slack_webhook_url == "https://hooks.slack.com/services/xxx"

    def test_load_config_no_slack(self, tmp_path: Path):
        config_file = tmp_path / "watch.yaml"
        config_file.write_text("""
watches:
  - name: "test"
    query: "test query"
""")
        config = load_watch_config(config_file)
        assert config.slack_webhook_url is None
        assert config.watches[0].days == 1  # default
        assert config.watches[0].max_results == 20  # default

    def test_load_config_missing_file(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_watch_config(tmp_path / "nonexistent.yaml")


# ---- Watch execution tests ----

class TestRunWatch:
    @patch("arxiv_hunt.watcher.ArxivClient")
    def test_run_returns_results(self, MockClient, tmp_path: Path):
        mock_client = MockClient.return_value
        mock_client.search.return_value = [
            _make_paper(arxiv_id="001"),
            _make_paper(arxiv_id="002"),
        ]
        config_file = tmp_path / "watch.yaml"
        config_file.write_text("""
watches:
  - name: "test watch"
    query: "test"
    days: 1
""")
        config = load_watch_config(config_file)
        results = run_watch(config)
        assert "test watch" in results
        assert len(results["test watch"]) == 2

    @patch("arxiv_hunt.watcher.ArxivClient")
    def test_run_multiple_watches(self, MockClient, tmp_path: Path):
        mock_client = MockClient.return_value
        mock_client.search.return_value = [_make_paper()]
        config_file = tmp_path / "watch.yaml"
        config_file.write_text("""
watches:
  - name: "watch1"
    query: "query1"
  - name: "watch2"
    query: "query2"
""")
        config = load_watch_config(config_file)
        results = run_watch(config)
        assert len(results) == 2
        assert "watch1" in results
        assert "watch2" in results


# ---- Slack message tests ----

class TestFormatSlackMessage:
    def test_basic_message(self):
        papers = [_make_paper(title="Great Paper", arxiv_id="001")]
        msg = format_slack_message("LLM Watch", papers)
        assert "LLM Watch" in msg
        assert "Great Paper" in msg
        assert "001" in msg

    def test_empty_results(self):
        msg = format_slack_message("Empty Watch", [])
        assert "Empty Watch" in msg
        assert "0" in msg or "no" in msg.lower() or "なし" in msg

    def test_multiple_papers(self):
        papers = [_make_paper(arxiv_id=f"00{i}") for i in range(5)]
        msg = format_slack_message("Multi", papers)
        assert "5" in msg or "Multi" in msg
