"""Library page — local DB browser (FTS5, tags, search history)."""

from __future__ import annotations

import json

import streamlit as st

from arxiv_hunt.database import PaperDatabase
from arxiv_hunt.models import Paper
from arxiv_hunt.tags import list_papers_by_tag, list_tags
from ui.components.results_table import render_results_table


def _papers_from_history_row(db: PaperDatabase, search_id: int) -> list[Paper]:
    """Reconstruct the ordered Paper list for a recorded search."""
    rows = db.conn.execute(
        """
        SELECT p.* FROM search_results sr
        JOIN papers p ON p.id = sr.paper_id
        WHERE sr.search_id = ?
        ORDER BY sr.rank
        """,
        (search_id,),
    ).fetchall()
    return [db._row_to_paper(r) for r in rows]


def _intersect_papers(groups: list[list[Paper]]) -> list[Paper]:
    """Return papers present in every group, preserved in the first group's order."""
    if not groups:
        return []
    common_ids = set(p.arxiv_id for p in groups[0])
    for group in groups[1:]:
        common_ids &= {p.arxiv_id for p in group}
    seen: set[str] = set()
    out: list[Paper] = []
    for p in groups[0]:
        if p.arxiv_id in common_ids and p.arxiv_id not in seen:
            out.append(p)
            seen.add(p.arxiv_id)
    return out


def render_library_page(db: PaperDatabase) -> None:
    """Render the Library page using the session-scoped PaperDatabase."""
    st.header("Library")
    st.info(
        "Library uses the local database (data/arxiv_hunt.db). "
        "The History page shows the last 5 CSV archive files separately."
    )

    # --- Section 1: Full-text search ---------------------------------
    st.subheader("Full-text search")
    with st.form("library_fts_form"):
        fts_query = st.text_input(
            "Search papers by text",
            key="library_fts_query",
            placeholder="e.g. attention OR transformer",
            help="Matches against the FTS5 mirror of paper titles and abstracts.",
        )
        fts_submit = st.form_submit_button("Search", type="primary")
    if fts_submit and fts_query.strip():
        try:
            hits = db.search_papers(fts_query.strip())
        except Exception as exc:
            st.error(f"FTS5 search failed: {exc}")
            hits = []
        st.session_state["papers"] = hits
        st.session_state["search_query"] = f"FTS: {fts_query.strip()}"
        if not hits:
            st.warning("No matches in the local database.")

    st.markdown("---")

    # --- Section 2: Browse by tag ------------------------------------
    st.subheader("Browse by tag")
    all_tags = list_tags(db)
    if not all_tags:
        st.caption("No tags yet. Add tags from the result cards on the Search page.")
    else:
        selected = st.multiselect(
            "Filter by tag (AND across selections)",
            options=all_tags,
            key="library_tag_filter",
        )
        if selected:
            groups = [list_papers_by_tag(db, name) for name in selected]
            tagged = _intersect_papers(groups)
            st.session_state["papers"] = tagged
            st.session_state["search_query"] = "Tags: " + " ∩ ".join(selected)
            if not tagged:
                st.warning("No papers match the intersection of the chosen tags.")

    st.markdown("---")

    # --- Section 3: Search history (DB) ------------------------------
    st.subheader("Search history (DB)")
    history = db.get_search_history(limit=50)
    if not history:
        st.caption("No search history yet.")
    else:
        for entry in history:
            with st.container(border=True):
                head_col, btn_col = st.columns([5, 1])
                with head_col:
                    st.markdown(
                        f"**{entry['query'] or '(empty)'}** "
                        f"— {entry['result_count']} result(s)"
                    )
                    st.caption(entry["searched_at"])
                    try:
                        params_pretty = json.dumps(
                            entry["params"], ensure_ascii=False, sort_keys=True
                        )
                    except Exception:
                        params_pretty = str(entry["params"])
                    st.caption(params_pretty)
                with btn_col:
                    if st.button(
                        "Load",
                        key=f"lib_hist_load_{entry['id']}",
                        use_container_width=True,
                    ):
                        try:
                            reloaded = _papers_from_history_row(db, int(entry["id"]))
                        except Exception as exc:
                            st.error(f"Failed to load: {exc}")
                            reloaded = []
                        st.session_state["papers"] = reloaded
                        st.session_state["search_query"] = entry["query"]
                        st.session_state["_lib_loaded"] = True

    if st.session_state.pop("_lib_loaded", False):
        st.rerun()

    # --- Render whatever the user selected above ---------------------
    if st.session_state.get("papers"):
        st.markdown("---")
        render_results_table()
