"""Results table component for arxiv_hunt."""

from __future__ import annotations

import csv
import io
import itertools
import tempfile
from pathlib import Path

import streamlit as st

from arxiv_hunt.config import CSV_COLUMNS
from arxiv_hunt.csv_io import _sanitize_cell
from arxiv_hunt.excel_converter import convert_csv_to_excel
from arxiv_hunt.models import Paper


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
    """Generate Excel file content as bytes from papers.

    Writes papers to a temporary CSV, converts to Excel via
    convert_csv_to_excel, and reads back the bytes.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_csv = Path(tmpdir) / "results.csv"
        tmp_xlsx = Path(tmpdir) / "results.xlsx"

        # Write temporary CSV
        with open(tmp_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            for paper in papers:
                writer.writerow(paper.to_csv_row())

        # Convert to Excel
        convert_csv_to_excel(csv_path=tmp_csv, output_path=tmp_xlsx)

        return tmp_xlsx.read_bytes()


def render_results_table() -> None:
    """Render search results grouped by date with download buttons."""
    papers: list[Paper] | None = st.session_state.get("papers")

    if not papers:
        st.info("Run a search to see results here.")
        return

    st.header("Results")
    st.markdown(f"Showing **{len(papers)}** paper(s).")

    # Download buttons at the top
    col1, col2 = st.columns(2)

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

    st.divider()

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

            # Abstract expander
            with st.expander("Abstract"):
                st.markdown(paper.abstract)
                st.caption(
                    f"**Authors:** {paper.authors}  \n"
                    f"**ID:** {paper.arxiv_id}  \n"
                    f"**Categories:** {paper.categories}"
                )

            st.markdown("---")
