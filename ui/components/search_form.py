"""Search form component for arxiv_hunt."""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from arxiv_hunt.client import ArxivClient
from arxiv_hunt.config import (
    ARXIV_CATEGORIES,
    MAX_QUERY_LENGTH,
    MAX_RESULTS_LIMIT,
    SEARCH_PRESETS,
    SHELL_META_CHARS,
)
from arxiv_hunt.csv_io import cleanup_old_archives, save_papers_to_csv
from ui.session import get_db


def _validate_input(query: str, author: str, categories: list[str]) -> str | None:
    """Validate the search inputs.

    Returns:
        An error message string if validation fails, or None if valid.
    """
    has_query = bool(query and query.strip())
    has_author = bool(author and author.strip())

    if not has_query and not has_author:
        return (
            "Please provide a query or author — categories alone produce zero "
            "results on arXiv."
        )
    for label, value in [("Query", query), ("Author", author)]:
        if not value:
            continue
        if len(value) > MAX_QUERY_LENGTH:
            return f"{label} is too long ({len(value)} chars). Maximum is {MAX_QUERY_LENGTH}."
        found_meta = [ch for ch in value if ch in SHELL_META_CHARS]
        if found_meta:
            chars_display = " ".join(repr(ch) for ch in sorted(set(found_meta)))
            return f"{label} contains disallowed characters: {chars_display}"
    return None


def render_search_form() -> None:
    """Render the search form and handle search execution."""
    st.header("Search arXiv Papers")

    # --- Preset buttons (outside the form so they trigger rerun) ---
    preset_cols = st.columns(len(SEARCH_PRESETS))
    for col, (preset_name, preset_values) in zip(preset_cols, SEARCH_PRESETS.items()):
        with col:
            if st.button(preset_name, use_container_width=True):
                # Inject directly into widget keys so the form retains the values
                st.session_state["_q"] = preset_values["query"]
                st.session_state["_cat"] = [
                    f"{c} - {ARXIV_CATEGORIES[c]}"
                    for c in preset_values["categories"]
                    if c in ARXIV_CATEGORIES
                ]
                st.rerun()

    # --- Search form ---
    with st.form("search_form"):
        query = st.text_input(
            "Search query",
            key="_q",
            max_chars=MAX_QUERY_LENGTH,
            placeholder="e.g. transformer attention mechanism",
            help=f"Max {MAX_QUERY_LENGTH} characters. Shell metacharacters are not allowed.",
        )

        author = st.text_input(
            "Author",
            key="_author",
            max_chars=MAX_QUERY_LENGTH,
            placeholder="e.g. Yann LeCun",
            help="Filter by author name.",
        )

        author_operator = st.radio(
            "Combine query & author with",
            options=["AND", "OR"],
            index=0,
            horizontal=True,
        )

        col_start, col_end, col_max = st.columns(3)
        with col_start:
            start_date = st.date_input(
                "Start date",
                value=date.today() - timedelta(days=7),
                max_value=date.today(),
                help="Include papers published on or after this date.",
            )
        with col_end:
            end_date = st.date_input(
                "End date",
                value=date.today(),
                max_value=date.today(),
                help="Include papers published on or before this date.",
            )
        with col_max:
            max_results = st.number_input(
                "Max results",
                min_value=1,
                max_value=MAX_RESULTS_LIMIT,
                value=10,
                step=1,
                help=f"Maximum number of results (up to {MAX_RESULTS_LIMIT}).",
            )

        # Build category options for multiselect
        category_display = [
            f"{code} - {name}" for code, name in ARXIV_CATEGORIES.items()
        ]

        selected_categories = st.multiselect(
            "Categories",
            key="_cat",
            options=category_display,
            help="Select one or more categories. Leave empty for all categories.",
        )

        submitted = st.form_submit_button("Search", type="primary")

    if submitted:
        # Parse selected categories
        categories: list[str] = [
            item.split(" - ")[0] for item in selected_categories
        ]

        # Validate inputs
        error = _validate_input(query, author, categories)
        if error:
            st.error(error)
            return

        if start_date > end_date:
            st.error("Start date must be on or before end date.")
            return

        # Execute search
        with st.spinner("Searching arXiv..."):
            try:
                client = ArxivClient()
                papers = client.search(
                    query.strip(),
                    max_results=int(max_results),
                    days=None,
                    start_date=start_date,
                    end_date=end_date,
                    categories=categories or None,
                    author=author.strip() or None,
                    author_operator=author_operator,
                )
            except Exception as exc:
                st.error(f"Search failed: {exc}")
                return

        if not papers:
            st.warning("No papers found matching your query.")
            st.session_state.pop("papers", None)
            st.session_state.pop("search_query", None)
            return

        # Save to CSV and clean up old archives
        search_label = query.strip() or author.strip() or ",".join(categories)
        try:
            results_path, archive_path = save_papers_to_csv(papers, search_label)
            cleanup_old_archives()
        except Exception as exc:
            st.error(f"Failed to save CSV: {exc}")
            return

        # Persist to local DB (upsert + record search history).
        search_params = {
            "query": query.strip(),
            "author": author.strip(),
            "author_operator": author_operator,
            "categories": categories,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "max_results": int(max_results),
        }
        try:
            get_db().save_search(search_label, search_params, papers)
        except Exception as exc:
            st.warning(f"Search succeeded but failed to record in DB: {exc}")

        # Store in session state
        st.session_state["papers"] = papers
        st.session_state["search_query"] = search_label
        st.session_state["results_csv_path"] = str(results_path)

        st.success(f"Found {len(papers)} paper(s). CSV saved to `{results_path.name}`.")
