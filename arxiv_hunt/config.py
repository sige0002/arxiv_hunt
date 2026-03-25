"""Configuration constants for arxiv_hunt."""

from __future__ import annotations

from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Output directories
CSV_OUTPUT_DIR = PROJECT_ROOT / "data" / "csv"
EXCEL_OUTPUT_DIR = PROJECT_ROOT / "data" / "excel"
PDF_OUTPUT_DIR = PROJECT_ROOT / "data" / "pdf"

# arXiv API settings
ARXIV_RATE_LIMIT_SECONDS = 3.0
DEFAULT_MAX_RESULTS = 10
DEFAULT_DAYS = 7

# CSV settings
RESULTS_CSV_FILENAME = "results.csv"

CSV_COLUMNS = [
    "arxiv_id",
    "title",
    "authors",
    "published",
    "updated",
    "primary_category",
    "categories",
    "pdf_url",
    "entry_url",
    "abstract",
]

# Excel additional columns
EXCEL_EXTRA_COLUMNS = [
    "abstract_translated",
    "relevance_score",
]

# arXiv categories (subset for UI)
ARXIV_CATEGORIES = {
    "cs.AI": "Artificial Intelligence",
    "cs.CL": "Computation and Language",
    "cs.CV": "Computer Vision",
    "cs.LG": "Machine Learning",
    "cs.RO": "Robotics",
    "cs.NE": "Neural and Evolutionary Computing",
    "cs.IR": "Information Retrieval",
    "cs.SE": "Software Engineering",
    "stat.ML": "Machine Learning (stat)",
    "eess.AS": "Audio and Speech Processing",
    "eess.IV": "Image and Video Processing",
    "math.OC": "Optimization and Control",
    "q-bio.QM": "Quantitative Methods (bio)",
    "physics.comp-ph": "Computational Physics",
}

# Search presets for UI
SEARCH_PRESETS: dict[str, dict[str, str | list[str]]] = {
    "LLM/NLP": {
        "query": "large language model",
        "categories": ["cs.CL", "cs.AI", "cs.LG"],
    },
    "Computer Vision": {
        "query": "image recognition OR object detection",
        "categories": ["cs.CV", "eess.IV"],
    },
    "Robotics": {
        "query": "robot learning OR manipulation",
        "categories": ["cs.RO", "cs.AI"],
    },
}

# Validation limits
MAX_QUERY_LENGTH = 500
MAX_RESULTS_LIMIT = 200
SHELL_META_CHARS = set(";|&`$")
