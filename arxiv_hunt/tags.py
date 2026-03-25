"""Tag management helper functions for arxiv_hunt."""
from __future__ import annotations

from arxiv_hunt.database import PaperDatabase
from arxiv_hunt.models import Paper


def tag_paper(db: PaperDatabase, arxiv_id: str, tag_name: str) -> None:
    """Add a tag to a paper. Creates the tag if it doesn't exist."""
    db.create_tag(tag_name)
    db.add_tag_to_paper(arxiv_id, tag_name)


def untag_paper(db: PaperDatabase, arxiv_id: str, tag_name: str) -> None:
    """Remove a tag from a paper."""
    db.remove_tag_from_paper(arxiv_id, tag_name)


def list_tags(db: PaperDatabase) -> list[str]:
    """Return all tags sorted alphabetically."""
    return db.get_all_tags()


def list_papers_by_tag(db: PaperDatabase, tag_name: str) -> list[Paper]:
    """Return all papers with a given tag."""
    return db.get_papers_by_tag(tag_name)


def bulk_tag_papers(db: PaperDatabase, arxiv_ids: list[str], tag_name: str) -> None:
    """Add a tag to multiple papers at once."""
    db.create_tag(tag_name)
    for arxiv_id in arxiv_ids:
        db.add_tag_to_paper(arxiv_id, tag_name)
