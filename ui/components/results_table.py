"""Results table component for arxiv_hunt."""

from __future__ import annotations

import csv
import io
import itertools
import tempfile
from pathlib import Path

import streamlit as st

from arxiv_hunt.bibtex import paper_to_bibtex, paper_to_ris
from arxiv_hunt.config import ARXIV_RATE_LIMIT_SECONDS, CSV_COLUMNS
from arxiv_hunt.csv_io import _sanitize_cell
from arxiv_hunt.excel_converter import convert_csv_to_excel
from arxiv_hunt.models import Paper
from arxiv_hunt.tags import tag_paper, untag_paper
from ui.session import get_db
from ui.utils.pdf_zip import papers_to_pdf_zip


def _generate_csv_bytes(papers: list[Paper]) -> bytes:
    """Generate CSV file content as bytes from papers.

    Applies CSV injection sanitization to all cell values.
    """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    for paper in papers:
        row = {k: _sanitize_cell(v) for k, v in paper.to_csv_row().items()}
        writer.writerow(row)
    return output.getvalue().encode("utf-8")


def _generate_excel_bytes(papers: list[Paper]) -> bytes:
    """Generate Excel file content as bytes from papers."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_csv = Path(tmpdir) / "results.csv"
        tmp_xlsx = Path(tmpdir) / "results.xlsx"

        with open(tmp_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            for paper in papers:
                writer.writerow(paper.to_csv_row())

        convert_csv_to_excel(csv_path=tmp_csv, output_path=tmp_xlsx)

        return tmp_xlsx.read_bytes()


def _papers_to_bibtex_bytes(papers: list[Paper]) -> bytes:
    """Return UTF-8 bytes of all papers concatenated as BibTeX entries."""
    return "\n\n".join(paper_to_bibtex(p) for p in papers).encode("utf-8")


def _papers_to_ris_bytes(papers: list[Paper]) -> bytes:
    """Return UTF-8 bytes of all papers concatenated as RIS entries."""
    return "\n\n".join(paper_to_ris(p) for p in papers).encode("utf-8")


def _parse_tag_input(value: str) -> set[str]:
    """Parse a comma-separated tag input into a set of stripped non-empty names."""
    return {part.strip() for part in value.split(",") if part.strip()}


def _sync_tags(arxiv_id: str, prev_tags: set[str], new_tags: set[str]) -> None:
    """Diff the previous and new tag sets and propagate changes to the DB."""
    db = get_db()
    for added in new_tags - prev_tags:
        try:
            tag_paper(db, arxiv_id, added)
        except Exception as exc:
            st.warning(f"Failed to add tag '{added}': {exc}")
    for removed in prev_tags - new_tags:
        try:
            untag_paper(db, arxiv_id, removed)
        except Exception as exc:
            st.warning(f"Failed to remove tag '{removed}': {exc}")


def render_results_table() -> None:
    """Render search results grouped by date with download buttons."""
    papers: list[Paper] | None = st.session_state.get("papers")

    if not papers:
        st.info("Run a search to see results here.")
        return

    st.header("Results")
    st.markdown(f"Showing **{len(papers)}** paper(s).")

    # Download buttons at the top
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        csv_bytes = _generate_csv_bytes(papers)
        st.download_button(
            label="Download CSV",
            data=csv_bytes,
            file_name="arxiv_results.csv",
            mime="text/csv",
            key="download_csv",
        )

    with col2:
        try:
            excel_bytes = _generate_excel_bytes(papers)
            st.download_button(
                label="Download Excel",
                data=excel_bytes,
                file_name="arxiv_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_excel",
            )
        except Exception as exc:
            st.error(f"Failed to generate Excel file: {exc}")

    with col3:
        st.download_button(
            label="Download BibTeX",
            data=_papers_to_bibtex_bytes(papers),
            file_name="arxiv_results.bib",
            mime="application/x-bibtex",
            key="download_bibtex",
        )

    with col4:
        st.download_button(
            label="Download RIS",
            data=_papers_to_ris_bytes(papers),
            file_name="arxiv_results.ris",
            mime="application/x-research-info-systems",
            key="download_ris",
        )

    with col5:
        if st.button("Build PDF ZIP", key="build_pdf_zip"):
            n = len(papers)
            est = int(n * ARXIV_RATE_LIMIT_SECONDS)
            with st.spinner(
                f"Downloading {n} PDFs (~{est}s if uncached)…"
            ):
                zip_bytes, summary = papers_to_pdf_zip(papers)
            st.session_state["_pdf_zip_bytes"] = zip_bytes
            st.session_state["_pdf_zip_summary"] = summary

        if "_pdf_zip_bytes" in st.session_state:
            summary = st.session_state.get("_pdf_zip_summary", {})
            ok = summary.get("ok", 0)
            failed = summary.get("failed", 0)
            st.info(f"PDF ZIP ready — success={ok}, failed={failed}")
            st.download_button(
                label="Download PDFs (ZIP)",
                data=st.session_state["_pdf_zip_bytes"],
                file_name="arxiv_results_pdfs.zip",
                mime="application/zip",
                key="download_pdf_zip",
            )

    st.divider()

    db = get_db()

    # Group papers by published date
    sorted_papers = sorted(papers, key=lambda p: p.published, reverse=True)
    for date, group in itertools.groupby(sorted_papers, key=lambda p: p.published):
        st.subheader(date)

        for paper in group:
            # Title with category badge + authors
            badge = f"`{paper.primary_category}`"
            st.markdown(f"**{paper.title}** {badge}")
            st.caption(paper.authors)

            # Action buttons
            btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 4])
            with btn_col1:
                st.link_button("PDF", url=paper.pdf_url, use_container_width=True)
            with btn_col2:
                st.link_button("arXiv Page", url=paper.entry_url, use_container_width=True)

            # Tag input — read current tags from DB and present comma-separated.
            try:
                current_tags = sorted(db.get_tags_for_paper(paper.arxiv_id))
            except Exception:
                current_tags = []
            prev_key = f"tags_prev_{paper.arxiv_id}"
            widget_key = f"tags_{paper.arxiv_id}"
            if prev_key not in st.session_state:
                st.session_state[prev_key] = set(current_tags)
            new_value = st.text_input(
                "Tags (comma-separated)",
                value=", ".join(current_tags),
                key=widget_key,
                help="Press Enter to save. Tags are persisted in data/arxiv_hunt.db.",
            )
            parsed = _parse_tag_input(new_value)
            prev = st.session_state[prev_key]
            if parsed != prev:
                _sync_tags(paper.arxiv_id, prev, parsed)
                st.session_state[prev_key] = parsed

            # Abstract expander
            with st.expander("Abstract"):
                st.markdown(paper.abstract)
                st.caption(
                    f"**Authors:** {paper.authors}  \n"
                    f"**ID:** {paper.arxiv_id}  \n"
                    f"**Categories:** {paper.categories}"
                )

            st.markdown("---")
