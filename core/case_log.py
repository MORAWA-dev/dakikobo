"""SQLite field journal and privacy-safe evidence ledger."""

from __future__ import annotations

import os
import sqlite3
import time
from datetime import datetime, timezone
from threading import Lock

from config import FOLLOW_UP_DELAY_DAYS
from core.cache import sqlite_connection


SCHEMA_VERSION = 4
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
VALID_ANSWER_PATHS = frozenset({"rag", "fertilizer", "vision", "cache"})
VALID_DEMOTED_REASONS = frozenset({"", "weak_title", "low_overlap", "score_margin"})


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    info = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row["name"] == column for row in info)


def _migrate_to_v2(conn: sqlite3.Connection) -> None:
    if not _column_exists(conn, "feedback_events", "outcome"):
        conn.execute("ALTER TABLE feedback_events ADD COLUMN outcome TEXT")
    if not _column_exists(conn, "feedback_events", "outcome_at"):
        conn.execute("ALTER TABLE feedback_events ADD COLUMN outcome_at TEXT")


def _migrate_to_v3(conn: sqlite3.Connection) -> None:
    if not _column_exists(conn, "feedback_events", "before_image_ref"):
        conn.execute("ALTER TABLE feedback_events ADD COLUMN before_image_ref TEXT")
    if not _column_exists(conn, "feedback_events", "after_image_ref"):
        conn.execute("ALTER TABLE feedback_events ADD COLUMN after_image_ref TEXT")


def _migrate_to_v4(conn: sqlite3.Connection) -> None:
    additions = {
        "place_id": "TEXT",
        "crop_id": "TEXT",
        "answer_path": "TEXT",
        "follow_up_due_at": "REAL",
    }
    for column, column_type in additions.items():
        if not _column_exists(conn, "feedback_events", column):
            conn.execute(
                f"ALTER TABLE feedback_events ADD COLUMN {column} {column_type}"
            )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS evidence_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feedback_id INTEGER,
            created_at REAL NOT NULL,
            question_hash TEXT NOT NULL,
            chunk_id TEXT NOT NULL,
            source_title TEXT NOT NULL,
            score REAL,
            kept INTEGER NOT NULL,
            demoted_reason TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_evidence_question_created
        ON evidence_ledger(question_hash, created_at)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_evidence_feedback
        ON evidence_ledger(feedback_id)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_feedback_follow_up_due
        ON feedback_events(follow_up_due_at, outcome)
        """
    )


def init_case_log(db_path: str) -> None:
    """Create/apply the additive schema once per process and database path."""
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
        with sqlite_connection(normalized_path) as conn:
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
                    after_image_ref TEXT,
                    place_id TEXT,
                    crop_id TEXT,
                    answer_path TEXT,
                    follow_up_due_at REAL
                )
                """
            )
            _migrate_to_v2(conn)
            _migrate_to_v3(conn)
            _migrate_to_v4(conn)
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
    place_id: str = "",
    crop_id: str = "",
    answer_path: str = "",
    follow_up_due_at: float | None = None,
    question_hash_value: str = "",
    ledger_created_at: float | None = None,
) -> int:
    """Persist one answer rating, link its evidence rows, and return its id."""
    if rating not in {"up", "down"}:
        raise ValueError("rating must be 'up' or 'down'")
    clean_path = (answer_path or "").strip()
    if clean_path and clean_path not in VALID_ANSWER_PATHS:
        raise ValueError("invalid answer_path")
    due_at = (
        float(follow_up_due_at)
        if follow_up_due_at is not None
        else time.time() + (float(FOLLOW_UP_DELAY_DAYS) * 86400)
    )

    init_case_log(db_path)
    with sqlite_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO feedback_events (
                created_at, rating, question, answer, before_image_ref,
                place_id, crop_id, answer_path, follow_up_due_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at or _now_iso(),
                rating,
                question or "",
                answer or "",
                (before_image_ref or "").strip() or None,
                (place_id or "").strip() or None,
                (crop_id or "").strip() or None,
                clean_path or None,
                due_at,
            ),
        )
        feedback_id = int(cursor.lastrowid)
        if question_hash_value and ledger_created_at is not None:
            conn.execute(
                """
                UPDATE evidence_ledger
                SET feedback_id = ?
                WHERE feedback_id IS NULL
                  AND question_hash = ?
                  AND created_at = ?
                """,
                (feedback_id, question_hash_value, float(ledger_created_at)),
            )
        return feedback_id


def record_evidence(
    db_path: str,
    *,
    question_hash_value: str,
    decisions,
    created_at: float | None = None,
) -> float | None:
    """Insert one ledger batch and return its timestamp reference."""
    if not question_hash_value or not decisions:
        return None
    batch_created_at = float(created_at if created_at is not None else time.time())
    rows = []
    for decision in decisions:
        reason = str(getattr(decision, "demoted_reason", "") or "")
        if reason not in VALID_DEMOTED_REASONS:
            raise ValueError("invalid demoted_reason")
        score = getattr(decision, "score", None)
        rows.append((
            None,
            batch_created_at,
            question_hash_value,
            str(getattr(decision, "chunk_id", "")),
            str(getattr(decision, "source_title", "Inconnu")),
            None if score is None else float(score),
            1 if bool(getattr(decision, "kept", False)) else 0,
            reason,
        ))
    init_case_log(db_path)
    with sqlite_connection(db_path) as conn:
        conn.executemany(
            """
            INSERT INTO evidence_ledger (
                feedback_id, created_at, question_hash, chunk_id,
                source_title, score, kept, demoted_reason
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
    return batch_created_at


def clone_latest_evidence(
    db_path: str,
    *,
    question_hash_value: str,
    created_at: float | None = None,
) -> float | None:
    """Clone the latest decision batch for a cache-hit answer."""
    if not os.path.isfile(db_path) or not question_hash_value:
        return None
    init_case_log(db_path)
    batch_created_at = float(created_at if created_at is not None else time.time())
    with sqlite_connection(db_path) as conn:
        latest = conn.execute(
            """
            SELECT MAX(created_at) AS created_at
            FROM evidence_ledger
            WHERE question_hash = ?
            """,
            (question_hash_value,),
        ).fetchone()
        if latest is None or latest["created_at"] is None:
            return None
        conn.execute(
            """
            INSERT INTO evidence_ledger (
                feedback_id, created_at, question_hash, chunk_id,
                source_title, score, kept, demoted_reason
            )
            SELECT NULL, ?, question_hash, chunk_id,
                   source_title, score, kept, demoted_reason
            FROM evidence_ledger
            WHERE question_hash = ? AND created_at = ?
            """,
            (batch_created_at, question_hash_value, float(latest["created_at"])),
        )
    return batch_created_at


def set_before_image_ref(
    db_path: str,
    *,
    feedback_id: int,
    before_image_ref: str,
) -> bool:
    ref = (before_image_ref or "").strip()
    if not ref:
        return False
    init_case_log(db_path)
    with sqlite_connection(db_path) as conn:
        cursor = conn.execute(
            "UPDATE feedback_events SET before_image_ref = ? WHERE id = ?",
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
    if outcome not in VALID_OUTCOMES:
        raise ValueError(f"outcome must be one of {sorted(VALID_OUTCOMES)}")

    init_case_log(db_path)
    with sqlite_connection(db_path) as conn:
        if (after_image_ref or "").strip():
            cursor = conn.execute(
                """
                UPDATE feedback_events
                SET outcome = ?, outcome_at = ?, after_image_ref = ?
                WHERE id = ?
                """,
                (outcome, _now_iso(), after_image_ref.strip(), feedback_id),
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
    if not os.path.isfile(db_path):
        return []
    init_case_log(db_path)
    with sqlite_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, created_at, rating, question, answer,
                   outcome, outcome_at, before_image_ref, after_image_ref,
                   place_id, crop_id, answer_path, follow_up_due_at
            FROM feedback_events
            ORDER BY id
            """
        ).fetchall()
    return [dict(row) for row in rows]


def list_evidence(db_path: str, *, feedback_id: int | None = None) -> list[dict]:
    if not os.path.isfile(db_path):
        return []
    init_case_log(db_path)
    with sqlite_connection(db_path) as conn:
        if feedback_id is None:
            rows = conn.execute("SELECT * FROM evidence_ledger ORDER BY id").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM evidence_ledger WHERE feedback_id = ? ORDER BY id",
                (feedback_id,),
            ).fetchall()
    return [dict(row) for row in rows]


def list_feedback_with_evidence(db_path: str) -> list[dict]:
    """Return feedback rows with linked chunk decisions for private export."""
    feedback_rows = list_feedback_events(db_path)
    evidence_by_feedback: dict[int, list[dict]] = {}
    for row in list_evidence(db_path):
        feedback_id = row.get("feedback_id")
        if feedback_id is not None:
            evidence_by_feedback.setdefault(int(feedback_id), []).append(row)
    return [
        {**row, "evidence": evidence_by_feedback.get(int(row["id"]), [])}
        for row in feedback_rows
    ]


def list_due_followups(db_path: str, *, now: float | None = None) -> list[dict]:
    """Return a privacy-minimized digest of due cases with no outcome."""
    if not os.path.isfile(db_path):
        return []
    init_case_log(db_path)
    due_before = float(now if now is not None else time.time())
    with sqlite_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id AS feedback_id, created_at, place_id, crop_id,
                   answer_path, follow_up_due_at,
                   CASE WHEN before_image_ref IS NULL THEN 0 ELSE 1 END AS has_before_image
            FROM feedback_events
            WHERE outcome IS NULL
              AND follow_up_due_at IS NOT NULL
              AND follow_up_due_at <= ?
            ORDER BY follow_up_due_at, id
            """,
            (due_before,),
        ).fetchall()
    return [dict(row) for row in rows]
