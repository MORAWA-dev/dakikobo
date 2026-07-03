"""SQLite persistence for feedback and future field-case evaluation data."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone


SCHEMA_VERSION = 1


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_parent_dir(db_path: str) -> None:
    directory = os.path.dirname(db_path)
    if directory:
        os.makedirs(directory, exist_ok=True)


def _connect(db_path: str) -> sqlite3.Connection:
    _ensure_parent_dir(db_path)
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_case_log(db_path: str) -> None:
    """Create the case-log database schema if needed."""
    with _connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                rating TEXT NOT NULL CHECK (rating IN ('up', 'down')),
                question TEXT NOT NULL,
                answer TEXT NOT NULL
            )
            """
        )
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


def record_feedback(
    db_path: str,
    *,
    rating: str,
    question: str,
    answer: str,
    created_at: str | None = None,
) -> int:
    """Persist one answer rating and return its row id."""
    if rating not in {"up", "down"}:
        raise ValueError("rating must be 'up' or 'down'")

    init_case_log(db_path)
    with _connect(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO feedback_events (created_at, rating, question, answer)
            VALUES (?, ?, ?, ?)
            """,
            (created_at or _now_iso(), rating, question or "", answer or ""),
        )
        return int(cursor.lastrowid)


def list_feedback_events(db_path: str) -> list[dict]:
    """Return feedback rows for tests, exports, and future evaluation tooling."""
    if not os.path.isfile(db_path):
        return []
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, created_at, rating, question, answer
            FROM feedback_events
            ORDER BY id
            """
        ).fetchall()
    return [dict(row) for row in rows]
