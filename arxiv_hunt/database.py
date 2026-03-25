"""SQLite database for storing and querying arXiv papers."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from arxiv_hunt.models import Paper

# Default database location
_DEFAULT_DB_DIR = Path(__file__).resolve().parent.parent / "data"


class PaperDatabase:
    """SQLite-backed storage for arXiv papers with full-text search and tagging."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            _DEFAULT_DB_DIR.mkdir(parents=True, exist_ok=True)
            db_path = _DEFAULT_DB_DIR / "arxiv_hunt.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._create_tables()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _create_tables(self) -> None:
        """Create all required tables if they do not already exist."""
        with self.conn:
            self.conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS papers (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    arxiv_id    TEXT    NOT NULL UNIQUE,
                    title       TEXT    NOT NULL,
                    authors     TEXT    NOT NULL,
                    abstract    TEXT    NOT NULL DEFAULT '',
                    published   TEXT    NOT NULL DEFAULT '',
                    updated     TEXT    NOT NULL DEFAULT '',
                    primary_category TEXT NOT NULL DEFAULT '',
                    categories  TEXT    NOT NULL DEFAULT '',
                    pdf_url     TEXT    NOT NULL DEFAULT '',
                    entry_url   TEXT    NOT NULL DEFAULT '',
                    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS searches (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    query       TEXT    NOT NULL,
                    params      TEXT    NOT NULL DEFAULT '{}',
                    result_count INTEGER NOT NULL DEFAULT 0,
                    searched_at TEXT    NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS search_results (
                    search_id   INTEGER NOT NULL REFERENCES searches(id) ON DELETE CASCADE,
                    paper_id    INTEGER NOT NULL REFERENCES papers(id)   ON DELETE CASCADE,
                    rank        INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (search_id, paper_id)
                );

                CREATE TABLE IF NOT EXISTS tags (
                    id   INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT    NOT NULL UNIQUE
                );

                CREATE TABLE IF NOT EXISTS paper_tags (
                    paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
                    tag_id   INTEGER NOT NULL REFERENCES tags(id)   ON DELETE CASCADE,
                    PRIMARY KEY (paper_id, tag_id)
                );
                """
            )

            # FTS5 virtual table for full-text search on title + abstract
            # Check if the FTS table already exists to avoid errors
            row = self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='papers_fts'"
            ).fetchone()
            if row is None:
                self.conn.execute(
                    """
                    CREATE VIRTUAL TABLE papers_fts USING fts5(
                        title, abstract, content=papers, content_rowid=id
                    )
                    """
                )

            # Triggers to keep FTS index in sync
            self.conn.executescript(
                """
                CREATE TRIGGER IF NOT EXISTS papers_ai AFTER INSERT ON papers BEGIN
                    INSERT INTO papers_fts(rowid, title, abstract)
                    VALUES (new.id, new.title, new.abstract);
                END;

                CREATE TRIGGER IF NOT EXISTS papers_ad AFTER DELETE ON papers BEGIN
                    INSERT INTO papers_fts(papers_fts, rowid, title, abstract)
                    VALUES ('delete', old.id, old.title, old.abstract);
                END;

                CREATE TRIGGER IF NOT EXISTS papers_au AFTER UPDATE ON papers BEGIN
                    INSERT INTO papers_fts(papers_fts, rowid, title, abstract)
                    VALUES ('delete', old.id, old.title, old.abstract);
                    INSERT INTO papers_fts(rowid, title, abstract)
                    VALUES (new.id, new.title, new.abstract);
                END;
                """
            )

    # ------------------------------------------------------------------
    # Paper CRUD
    # ------------------------------------------------------------------

    def upsert_paper(self, paper: Paper) -> int:
        """Insert or update a paper. Returns the paper's database id.

        Deduplication is based on arxiv_id (UNIQUE constraint). If a paper
        with the same arxiv_id already exists, its fields are updated.
        """
        with self.conn:
            # Try to find existing paper first
            row = self.conn.execute(
                "SELECT id FROM papers WHERE arxiv_id = ?", (paper.arxiv_id,)
            ).fetchone()

            if row is not None:
                # Update existing paper
                self.conn.execute(
                    """
                    UPDATE papers SET
                        title = ?, authors = ?, abstract = ?, published = ?,
                        updated = ?, primary_category = ?, categories = ?,
                        pdf_url = ?, entry_url = ?
                    WHERE arxiv_id = ?
                    """,
                    (
                        paper.title, paper.authors, paper.abstract,
                        paper.published, paper.updated, paper.primary_category,
                        paper.categories, paper.pdf_url, paper.entry_url,
                        paper.arxiv_id,
                    ),
                )
                return int(row["id"])
            else:
                # Insert new paper
                cursor = self.conn.execute(
                    """
                    INSERT INTO papers
                        (arxiv_id, title, authors, abstract, published,
                         updated, primary_category, categories, pdf_url, entry_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        paper.arxiv_id, paper.title, paper.authors,
                        paper.abstract, paper.published, paper.updated,
                        paper.primary_category, paper.categories,
                        paper.pdf_url, paper.entry_url,
                    ),
                )
                assert cursor.lastrowid is not None
                return cursor.lastrowid

    def get_paper_by_arxiv_id(self, arxiv_id: str) -> Optional[Paper]:
        """Look up a paper by its arXiv identifier."""
        row = self.conn.execute(
            "SELECT * FROM papers WHERE arxiv_id = ?", (arxiv_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_paper(row)

    def get_all_papers(self) -> list[Paper]:
        """Return every paper in the database."""
        rows = self.conn.execute("SELECT * FROM papers ORDER BY id").fetchall()
        return [self._row_to_paper(r) for r in rows]

    def search_papers(self, query: str) -> list[Paper]:
        """Full-text search over paper titles and abstracts using FTS5."""
        rows = self.conn.execute(
            """
            SELECT p.* FROM papers p
            JOIN papers_fts fts ON p.id = fts.rowid
            WHERE papers_fts MATCH ?
            ORDER BY rank
            """,
            (query,),
        ).fetchall()
        return [self._row_to_paper(r) for r in rows]

    # ------------------------------------------------------------------
    # Search history
    # ------------------------------------------------------------------

    def save_search(
        self, query: str, params: dict, papers: list[Paper]
    ) -> int:
        """Persist a search query and link it to papers found.

        Returns the search id.
        """
        with self.conn:
            # Upsert all papers first
            paper_ids = [self.upsert_paper(p) for p in papers]

            cursor = self.conn.execute(
                """
                INSERT INTO searches (query, params, result_count)
                VALUES (?, ?, ?)
                """,
                (query, json.dumps(params), len(papers)),
            )
            assert cursor.lastrowid is not None
            search_id: int = cursor.lastrowid

            for rank, pid in enumerate(paper_ids):
                self.conn.execute(
                    """
                    INSERT OR IGNORE INTO search_results (search_id, paper_id, rank)
                    VALUES (?, ?, ?)
                    """,
                    (search_id, pid, rank),
                )

        return search_id

    def get_search_history(self, limit: int = 50) -> list[dict]:
        """Return recent searches, most-recent first."""
        rows = self.conn.execute(
            """
            SELECT id, query, params, result_count, searched_at
            FROM searches
            ORDER BY searched_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "query": r["query"],
                "params": json.loads(r["params"]),
                "result_count": r["result_count"],
                "searched_at": r["searched_at"],
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Tags
    # ------------------------------------------------------------------

    def create_tag(self, name: str) -> int:
        """Create a tag (idempotent). Returns the tag id."""
        with self.conn:
            row = self.conn.execute(
                "SELECT id FROM tags WHERE name = ?", (name,)
            ).fetchone()
            if row is not None:
                return int(row["id"])
            cursor = self.conn.execute(
                "INSERT INTO tags (name) VALUES (?)", (name,)
            )
            assert cursor.lastrowid is not None
            return cursor.lastrowid

    def delete_tag(self, name: str) -> None:
        """Delete a tag by name (also removes paper_tags associations)."""
        with self.conn:
            self.conn.execute("DELETE FROM tags WHERE name = ?", (name,))

    def get_all_tags(self) -> list[str]:
        """Return all tag names sorted alphabetically."""
        rows = self.conn.execute(
            "SELECT name FROM tags ORDER BY name"
        ).fetchall()
        return [r["name"] for r in rows]

    def add_tag_to_paper(self, arxiv_id: str, tag_name: str) -> None:
        """Associate a tag with a paper (both must already exist)."""
        with self.conn:
            paper_row = self.conn.execute(
                "SELECT id FROM papers WHERE arxiv_id = ?", (arxiv_id,)
            ).fetchone()
            tag_row = self.conn.execute(
                "SELECT id FROM tags WHERE name = ?", (tag_name,)
            ).fetchone()
            if paper_row is None or tag_row is None:
                return
            self.conn.execute(
                "INSERT OR IGNORE INTO paper_tags (paper_id, tag_id) VALUES (?, ?)",
                (paper_row["id"], tag_row["id"]),
            )

    def remove_tag_from_paper(self, arxiv_id: str, tag_name: str) -> None:
        """Remove a tag association from a paper."""
        with self.conn:
            paper_row = self.conn.execute(
                "SELECT id FROM papers WHERE arxiv_id = ?", (arxiv_id,)
            ).fetchone()
            tag_row = self.conn.execute(
                "SELECT id FROM tags WHERE name = ?", (tag_name,)
            ).fetchone()
            if paper_row is None or tag_row is None:
                return
            self.conn.execute(
                "DELETE FROM paper_tags WHERE paper_id = ? AND tag_id = ?",
                (paper_row["id"], tag_row["id"]),
            )

    def get_tags_for_paper(self, arxiv_id: str) -> list[str]:
        """Return all tag names associated with a paper."""
        rows = self.conn.execute(
            """
            SELECT t.name FROM tags t
            JOIN paper_tags pt ON pt.tag_id = t.id
            JOIN papers p ON p.id = pt.paper_id
            WHERE p.arxiv_id = ?
            ORDER BY t.name
            """,
            (arxiv_id,),
        ).fetchall()
        return [r["name"] for r in rows]

    def get_papers_by_tag(self, tag_name: str) -> list[Paper]:
        """Return all papers associated with a given tag."""
        rows = self.conn.execute(
            """
            SELECT p.* FROM papers p
            JOIN paper_tags pt ON pt.paper_id = p.id
            JOIN tags t ON t.id = pt.tag_id
            WHERE t.name = ?
            ORDER BY p.id
            """,
            (tag_name,),
        ).fetchall()
        return [self._row_to_paper(r) for r in rows]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_paper(row: sqlite3.Row) -> Paper:
        """Convert a database row to a Paper dataclass."""
        return Paper(
            arxiv_id=row["arxiv_id"],
            title=row["title"],
            authors=row["authors"],
            abstract=row["abstract"],
            published=row["published"],
            updated=row["updated"],
            primary_category=row["primary_category"],
            categories=row["categories"],
            pdf_url=row["pdf_url"],
            entry_url=row["entry_url"],
        )

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()

    def __del__(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass
