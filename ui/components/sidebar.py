"""Sidebar navigation component for arxiv_hunt."""

from __future__ import annotations

import streamlit as st

PAGES = ["Search", "History", "Library", "Excel Convert"]


def render_sidebar() -> str:
    """Render the sidebar with page navigation.

    Returns:
        The name of the selected page.
    """
    with st.sidebar:
        st.title("arxiv_hunt")
        st.markdown("---")
        selected_page = st.radio(
            "Navigation",
            options=PAGES,
            index=0,
            key="nav_page",
        )
        st.markdown("---")
        st.caption("Search arXiv papers and export to Excel.")

    return selected_page
