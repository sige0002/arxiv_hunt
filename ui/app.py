"""Main Streamlit application for arxiv_hunt."""

from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from ui.components.sidebar import render_sidebar
from ui.components.search_form import render_search_form
from ui.components.results_table import render_results_table
from ui.components.history import render_history
from ui.components.library import render_library_page
from ui.session import get_db
from arxiv_hunt.excel_converter import convert_csv_to_excel

# ---------------------------------------------------------------------------
# Page configuration (must be the first Streamlit command)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="arxiv_hunt",
    layout="wide",
)

# Initialize the per-session PaperDatabase eagerly so all pages share it.
get_db()

# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------
selected_page = render_sidebar()

# ---------------------------------------------------------------------------
# Page routing
# ---------------------------------------------------------------------------

if selected_page == "Search":
    render_search_form()
    st.markdown("---")
    render_results_table()

elif selected_page == "History":
    render_history()

elif selected_page == "Library":
    render_library_page(get_db())

elif selected_page == "Excel Convert":
    st.header("Convert CSV to Excel")
    st.markdown(
        "Upload a CSV file (e.g. one exported from the Search page) to convert "
        "it to an Excel workbook with TRANSLATE formulas."
    )

    uploaded_file = st.file_uploader(
        "Upload CSV file",
        type=["csv"],
        key="excel_csv_upload",
    )

    target_lang = st.selectbox(
        "Target language for translation formula",
        options=["ja", "zh", "ko", "de", "fr", "es", "pt", "ru", "ar"],
        index=0,
        help="Language code used in the Excel TRANSLATE formula.",
        key="excel_target_lang",
    )

    convert_clicked = st.button("Convert to Excel", type="primary")

    if convert_clicked:
        if uploaded_file is None:
            st.error("Please upload a CSV file first.")
        else:
            with st.spinner("Converting..."):
                try:
                    with tempfile.TemporaryDirectory() as tmpdir:
                        # Save uploaded CSV to temp location
                        tmp_csv = Path(tmpdir) / "uploaded.csv"
                        tmp_csv.write_bytes(uploaded_file.getvalue())

                        # Convert
                        tmp_xlsx = Path(tmpdir) / "converted.xlsx"
                        convert_csv_to_excel(
                            csv_path=tmp_csv,
                            output_path=tmp_xlsx,
                            target_lang=target_lang,
                        )

                        excel_bytes = tmp_xlsx.read_bytes()

                    st.success("Conversion complete!")
                    st.download_button(
                        label="Download Excel",
                        data=excel_bytes,
                        file_name="arxiv_results.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="excel_convert_download",
                    )
                except Exception as exc:
                    st.error(f"Conversion failed: {exc}")
