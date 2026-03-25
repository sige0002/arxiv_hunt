"""BibTeX and RIS export for arXiv papers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from arxiv_hunt.models import Paper


def _escape_bibtex(text: str) -> str:
    """Escape special LaTeX/BibTeX characters in text."""
    # Order matters: escape backslash first, then others
    replacements = [
        ("&", r"\&"),
        ("%", r"\%"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("$", r"\$"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _make_bibtex_key(paper: Paper) -> str:
    """Generate a BibTeX citation key from a paper.

    Format: {first_author_lastname}{year}{id_suffix}
    Example: vaswani2026_2602.12345v1
    """
    # Extract first author's last name
    first_author = paper.authors.split(";")[0].strip()
    # Handle "Last, First" format
    if "," in first_author:
        last_name = first_author.split(",")[0].strip()
    else:
        # Handle "First Last" format
        parts = first_author.split()
        last_name = parts[-1] if parts else "unknown"

    # Extract year from published date
    year = paper.published[:4] if paper.published else "0000"

    # Clean the last name for use as a key (remove non-alphanumeric)
    last_name_clean = re.sub(r"[^a-zA-Z]", "", last_name).lower()

    # Create a short suffix from arxiv_id
    arxiv_suffix = paper.arxiv_id.replace(".", "").replace("/", "_")

    return f"{last_name_clean}{year}_{arxiv_suffix}"


def paper_to_bibtex(paper: Paper) -> str:
    """Convert a Paper to a BibTeX entry string.

    Args:
        paper: The Paper dataclass instance to convert.

    Returns:
        A formatted BibTeX entry string.
    """
    key = _make_bibtex_key(paper)

    # Convert semicolon-separated authors to BibTeX "and" format
    authors_list = [a.strip() for a in paper.authors.split(";") if a.strip()]
    authors_bib = " and ".join(authors_list)

    # Extract year and month
    year = paper.published[:4] if paper.published else ""
    month_num = paper.published[5:7] if len(paper.published) >= 7 else ""
    month_names = {
        "01": "jan", "02": "feb", "03": "mar", "04": "apr",
        "05": "may", "06": "jun", "07": "jul", "08": "aug",
        "09": "sep", "10": "oct", "11": "nov", "12": "dec",
    }
    month = month_names.get(month_num, "")

    # Build fields
    fields = []
    fields.append(f"  title = {{{_escape_bibtex(paper.title)}}}")
    fields.append(f"  author = {{{authors_bib}}}")
    fields.append(f"  year = {{{year}}}")
    if month:
        fields.append(f"  month = {month}")
    fields.append(f"  eprint = {{{paper.arxiv_id}}}")
    fields.append(f"  archiveprefix = {{arXiv}}")
    fields.append(f"  primaryclass = {{{paper.primary_category}}}")
    fields.append(f"  abstract = {{{_escape_bibtex(paper.abstract)}}}")
    if paper.entry_url:
        fields.append(f"  url = {{{paper.entry_url}}}")

    fields_str = ",\n".join(fields)
    return f"@article{{{key},\n{fields_str}\n}}"


def paper_to_ris(paper: Paper) -> str:
    """Convert a Paper to an RIS entry string.

    Args:
        paper: The Paper dataclass instance to convert.

    Returns:
        A formatted RIS entry string.
    """
    lines = []
    lines.append("TY  - ELEC")
    lines.append(f"TI  - {paper.title}")

    # Add individual author lines
    authors_list = [a.strip() for a in paper.authors.split(";") if a.strip()]
    for author in authors_list:
        lines.append(f"AU  - {author}")

    lines.append(f"AB  - {paper.abstract}")

    # Date in RIS format (YYYY/MM/DD)
    if paper.published:
        da = paper.published.replace("-", "/")
        lines.append(f"DA  - {da}")

    # Year
    if paper.published:
        lines.append(f"PY  - {paper.published[:4]}")

    # URL
    if paper.entry_url:
        lines.append(f"UR  - {paper.entry_url}")
    elif paper.pdf_url:
        lines.append(f"UR  - {paper.pdf_url}")

    # arXiv ID
    lines.append(f"AN  - {paper.arxiv_id}")

    # Keywords / categories
    if paper.categories:
        for cat in paper.categories.split(";"):
            cat = cat.strip()
            if cat:
                lines.append(f"KW  - {cat}")

    lines.append("ER  -")
    return "\n".join(lines)


def papers_to_bibtex_file(papers: list[Paper], output_path: Path | str) -> Path:
    """Export multiple papers to a .bib file.

    Args:
        papers: List of Paper instances to export.
        output_path: Path for the output .bib file.

    Returns:
        The Path of the written file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    entries = [paper_to_bibtex(p) for p in papers]
    content = "\n\n".join(entries)

    output_path.write_text(content, encoding="utf-8")
    return output_path


def papers_to_ris_file(papers: list[Paper], output_path: Path | str) -> Path:
    """Export multiple papers to a .ris file.

    Args:
        papers: List of Paper instances to export.
        output_path: Path for the output .ris file.

    Returns:
        The Path of the written file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    entries = [paper_to_ris(p) for p in papers]
    content = "\n\n".join(entries)

    output_path.write_text(content, encoding="utf-8")
    return output_path
