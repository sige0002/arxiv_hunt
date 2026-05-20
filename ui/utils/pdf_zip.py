"""Bundle PDFs for a list of papers into an in-memory ZIP."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Iterable

from arxiv_hunt.config import ARXIV_RATE_LIMIT_SECONDS, PDF_OUTPUT_DIR
from arxiv_hunt.downloader import download_papers_pdf
from arxiv_hunt.models import Paper


def papers_to_pdf_zip(
    papers: list[Paper],
    *,
    pdf_dir: Path | None = None,
    rate_limit: float = ARXIV_RATE_LIMIT_SECONDS,
) -> tuple[bytes, dict]:
    """Download every paper's PDF and bundle the results into a ZIP.

    Uses ``download_papers_pdf`` so the shared ``data/pdf/`` cache and the
    arXiv rate-limit policy are honored. Failures (missing pdf_url, HTTP
    errors) skip the offending paper without stopping the batch.

    Returns ``(zip_bytes, summary_dict)``. ``summary_dict`` has keys
    ``ok``, ``failed`` and ``failed_ids``.
    """
    pdf_dir = pdf_dir or PDF_OUTPUT_DIR
    paths = download_papers_pdf(
        papers,
        output_dir=pdf_dir,
        rate_limit=rate_limit,
        skip_existing=True,
    )

    failed_ids: list[str] = []
    ok_count = 0
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for paper, path in zip(papers, paths):
            if path is None:
                failed_ids.append(paper.arxiv_id)
                continue
            try:
                zf.write(path, arcname=Path(path).name)
                ok_count += 1
            except OSError:
                failed_ids.append(paper.arxiv_id)

        failed_count = len(failed_ids)
        summary_lines = [
            f"success={ok_count}",
            f"failed={failed_count}",
            "failed_arxiv_ids=" + ",".join(failed_ids),
        ]
        zf.writestr("summary.txt", "\n".join(summary_lines) + "\n")

    return buffer.getvalue(), {
        "ok": ok_count,
        "failed": failed_count,
        "failed_ids": failed_ids,
    }


__all__: Iterable[str] = ["papers_to_pdf_zip"]
