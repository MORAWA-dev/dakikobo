"""SQLite persistence for feedback and future field-case evaluation data."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from threading import Lock


SCHEMA_VERSION = 3
_CASE_LOG_INITIALIZED = False
_CASE_LOG_INITIALIZED_PATH = ""
_CASE_LOG_INIT_LOCK = Lock()

VALID_OUTCOMES = frozenset({
    "applied_improved",
    "applied_unchanged",
    "applied_worse",
    "not_applied",
    "not_sure",
})


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


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    """Check whether *column* already exists on *table*."""
    info = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row["name"] == column for row in info)


def _migrate_to_v2(conn: sqlite3.Connection) -> None:
    """Add outcome tracking columns (idempotent)."""
    if not _column_exists(conn, "feedback_events", "outcome"):
        conn.execute(
            "ALTER TABLE feedback_events ADD COLUMN outcome TEXT"
        )
    if not _column_exists(conn, "feedback_events", "outcome_at"):
        conn.execute(
            "ALTER TABLE feedback_events ADD COLUMN outcome_at TEXT"
        )


def _migrate_to_v3(conn: sqlite3.Connection) -> None:
    """Add optional before/after image reference columns (idempotent)."""
    if not _column_exists(conn, "feedback_events", "before_image_ref"):
        conn.execute(
            "ALTER TABLE feedback_events ADD COLUMN before_image_ref TEXT"
        )
    if not _column_exists(conn, "feedback_events", "after_image_ref"):
        conn.execute(
            "ALTER TABLE feedback_events ADD COLUMN after_image_ref TEXT"
        )


def init_case_log(db_path: str) -> None:
    """Create/apply the schema once per process for the active database path."""
    global _CASE_LOG_INITIALIZED, _CASE_LOG_INITIALIZED_PATH
    normalized_path = os.path.abspath(db_path)
    if (
        _CASE_LOG_INITIALIZED
        and _CASE_LOG_INITIALIZED_PATH == normalized_path
        and os.path.isfile(normalized_path)
    ):
        return

    with _CASE_LOG_INIT_LOCK:
        if (
            _CASE_LOG_INITIALIZED
            and _CASE_LOG_INITIALIZED_PATH == normalized_path
            and os.path.isfile(normalized_path)
        ):
            return
        with _connect(normalized_path) as conn:
            # Serialize the one-time migration if multiple workers boot together.
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    rating TEXT NOT NULL CHECK (rating IN ('up', 'down')),
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    outcome TEXT,
                    outcome_at TEXT,
                    before_image_ref TEXT,
                    after_image_ref TEXT
                )
                """
            )
            _migrate_to_v2(conn)
            _migrate_to_v3(conn)
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        _CASE_LOG_INITIALIZED = True
        _CASE_LOG_INITIALIZED_PATH = normalized_path


def record_feedback(
    db_path: str,
    *,
    rating: str,
    question: str,
    answer: str,
    created_at: str | None = None,
    before_image_ref: str = "",
) -> int:
    """Persist one answer rating and return its row id."""
    if rating not in {"up", "down"}:
        raise ValueError("rating must be 'up' or 'down'")

    init_case_log(db_path)
    with _connect(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO feedback_events (
                created_at, rating, question, answer, before_image_ref
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                created_at or _now_iso(),
                rating,
                question or "",
                answer or "",
                (before_image_ref or "").strip() or None,
            ),
        )
        return int(cursor.lastrowid)


def set_before_image_ref(
    db_path: str,
    *,
    feedback_id: int,
    before_image_ref: str,
) -> bool:
    """Attach a before-image reference to an existing feedback row."""
    ref = (before_image_ref or "").strip()
    if not ref:
        return False
    init_case_log(db_path)
    with _connect(db_path) as conn:
        cursor = conn.execute(
            """
            UPDATE feedback_events
            SET before_image_ref = ?
            WHERE id = ?
            """,
            (ref, feedback_id),
        )
        return cursor.rowcount > 0


def record_outcome(
    db_path: str,
    *,
    feedback_id: int,
    outcome: str,
    after_image_ref: str = "",
) -> bool:
    """Update a feedback row with a follow-up outcome.

    Returns True when the row was found and updated, False otherwise.
    """
    if outcome not in VALID_OUTCOMES:
        raise ValueError(
            f"outcome must be one of {sorted(VALID_OUTCOMES)}"
        )

    init_case_log(db_path)
    with _connect(db_path) as conn:
        if (after_image_ref or "").strip():
            cursor = conn.execute(
                """
                UPDATE feedback_events
                SET outcome = ?, outcome_at = ?, after_image_ref = ?
                WHERE id = ?
                """,
                (
                    outcome,
                    _now_iso(),
                    after_image_ref.strip(),
                    feedback_id,
                ),
            )
        else:
            cursor = conn.execute(
                """
                UPDATE feedback_events
                SET outcome = ?, outcome_at = ?
                WHERE id = ?
                """,
                (outcome, _now_iso(), feedback_id),
            )
        return cursor.rowcount > 0


def list_feedback_events(db_path: str) -> list[dict]:
    """Return feedback rows for tests, exports, and future evaluation tooling."""
    if not os.path.isfile(db_path):
        return []
    init_case_log(db_path)
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, created_at, rating, question, answer,
                   outcome, outcome_at, before_image_ref, after_image_ref
            FROM feedback_events
            ORDER BY id
            """
        ).fetchall()
    return [dict(row) for row in rows]
