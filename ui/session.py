"""Per-session helpers for the Streamlit UI."""

from __future__ import annotations

import streamlit as st

from arxiv_hunt.config import DATABASE_PATH
from arxiv_hunt.database import PaperDatabase


def get_db() -> PaperDatabase:
    """Return the session-scoped PaperDatabase, creating it on first use."""
    db = st.session_state.get("db")
    if db is None:
        db = PaperDatabase(DATABASE_PATH)
        st.session_state["db"] = db
    return db
