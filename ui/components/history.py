"""Search history page component for arxiv_hunt."""

from __future__ import annotations

import re
from datetime import datetime

import streamlit as st

from arxiv_hunt.csv_io import list_recent_archives, load_papers_from_csv
from ui.components.results_table import render_results_table


def _parse_archive_label(name: str) -> tuple[str, str]:
    """Parse archive filename into (query, timestamp).

    'large_language_model_20260226_143012.csv'
      -> ('large language model', '02/26 14:30')
    """
    stem = name.removesuffix(".csv")
    m = re.search(r"_(\d{8}_\d{6})$", stem)
    if not m:
        return stem, ""
    query_part = stem[: m.start()].replace("_", " ")
    try:
        dt = datetime.strptime(m.group(1), "%Y%m%d_%H%M%S")
        ts = dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        ts = m.group(1)
    return query_part, ts


def render_history() -> None:
    """Render the search history page (up to 5 recent archives)."""
    st.header("Search History")

    archives = list_recent_archives()
    if not archives:
        st.info("No search history yet. Run a search first.")
        return

    st.markdown(f"Showing the last **{len(archives)}** search(es).")

    for i, path in enumerate(archives):
        query_label, ts = _parse_archive_label(path.name)

        with st.container(border=True):
            col_info, col_btn = st.columns([4, 1])
            with col_info:
                st.markdown(f"**{query_label}**")
                st.caption(ts)
            with col_btn:
                if st.button("Load", key=f"hist_{i}", use_container_width=True):
                    try:
                        papers = load_papers_from_csv(path)
                        st.session_state["papers"] = papers
                        st.session_state["search_query"] = query_label
                        st.session_state["results_csv_path"] = str(path)
                        st.session_state["_hist_loaded"] = True
                    except Exception as exc:
                        st.error(f"Failed to load: {exc}")

    if st.session_state.pop("_hist_loaded", False):
        st.rerun()

    # Show loaded results inline
    if st.session_state.get("papers"):
        st.markdown("---")
        render_results_table()
