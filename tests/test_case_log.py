"""Tests for the SQLite feedback/case log."""

import sqlite3

import pytest

from core.case_log import (
    SCHEMA_VERSION,
    VALID_OUTCOMES,
    init_case_log,
    list_feedback_events,
    record_feedback,
    record_outcome,
    set_before_image_ref,
)


def test_record_feedback_creates_sqlite_case_log(tmp_path):
    db_path = tmp_path / "case_log.sqlite3"

    feedback_id = record_feedback(
        str(db_path),
        rating="up",
        question="Quand semer le mil ?",
        answer="Après les pluies régulières.",
        created_at="2026-07-03T10:00:00+00:00",
    )

    assert feedback_id == 1
    rows = list_feedback_events(str(db_path))
    assert rows == [
        {
            "id": 1,
            "created_at": "2026-07-03T10:00:00+00:00",
            "rating": "up",
            "question": "Quand semer le mil ?",
            "answer": "Après les pluies régulières.",
            "outcome": None,
            "outcome_at": None,
            "before_image_ref": None,
            "after_image_ref": None,
        }
    ]

    with sqlite3.connect(db_path) as conn:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
    assert version == SCHEMA_VERSION


def test_record_feedback_rejects_invalid_rating(tmp_path):
    with pytest.raises(ValueError, match="rating"):
        record_feedback(
            str(tmp_path / "case_log.sqlite3"),
            rating="maybe",
            question="Q",
            answer="A",
        )


def test_list_feedback_events_returns_empty_for_missing_db(tmp_path):
    assert list_feedback_events(str(tmp_path / "missing.sqlite3")) == []


def test_record_outcome_updates_feedback_row(tmp_path):
    db_path = str(tmp_path / "case_log.sqlite3")
    feedback_id = record_feedback(
        db_path,
        rating="up",
        question="Quand semer le mil ?",
        answer="Après les pluies régulières.",
    )

    updated = record_outcome(
        db_path,
        feedback_id=feedback_id,
        outcome="applied_improved",
    )

    assert updated is True
    rows = list_feedback_events(db_path)
    assert len(rows) == 1
    assert rows[0]["outcome"] == "applied_improved"
    assert rows[0]["outcome_at"] is not None


def test_record_outcome_returns_false_for_missing_row(tmp_path):
    db_path = str(tmp_path / "case_log.sqlite3")
    init_case_log(db_path)

    updated = record_outcome(
        db_path,
        feedback_id=9999,
        outcome="not_applied",
    )

    assert updated is False


def test_record_outcome_rejects_invalid_outcome(tmp_path):
    db_path = str(tmp_path / "case_log.sqlite3")
    record_feedback(db_path, rating="down", question="Q", answer="A")

    with pytest.raises(ValueError, match="outcome"):
        record_outcome(db_path, feedback_id=1, outcome="maybe_later")


def test_migration_adds_outcome_columns_idempotently(tmp_path):
    """Create a v1 database, then call init_case_log to apply migration."""
    db_path = str(tmp_path / "case_log.sqlite3")

    # Create a v1 schema manually (without outcome columns).
    with sqlite3.connect(db_path) as conn:
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
        conn.execute("PRAGMA user_version = 1")
        conn.execute(
            "INSERT INTO feedback_events (created_at, rating, question, answer) "
            "VALUES ('2026-01-01T00:00:00+00:00', 'up', 'Q', 'A')"
        )

    # Apply migration by calling init_case_log (should add columns).
    init_case_log(db_path)

    # Verify columns exist and old data is intact.
    rows = list_feedback_events(db_path)
    assert len(rows) == 1
    assert rows[0]["outcome"] is None
    assert rows[0]["outcome_at"] is None
    assert rows[0]["rating"] == "up"

    # Calling init_case_log again should be idempotent.
    init_case_log(db_path)
    assert len(list_feedback_events(db_path)) == 1

    # Verify version was bumped.
    with sqlite3.connect(db_path) as conn:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
    assert version == SCHEMA_VERSION


def test_list_feedback_events_includes_outcome_columns(tmp_path):
    db_path = str(tmp_path / "case_log.sqlite3")
    record_feedback(db_path, rating="down", question="Q", answer="A")
    record_outcome(db_path, feedback_id=1, outcome="applied_worse")

    rows = list_feedback_events(db_path)
    assert len(rows) == 1
    assert rows[0]["outcome"] == "applied_worse"
    assert rows[0]["outcome_at"] is not None


def test_valid_outcomes_contains_expected_values():
    assert VALID_OUTCOMES == {
        "applied_improved",
        "applied_unchanged",
        "applied_worse",
        "not_applied",
        "not_sure",
    }


def test_before_and_after_image_refs_are_stored(tmp_path):
    db_path = str(tmp_path / "case_log.sqlite3")
    feedback_id = record_feedback(
        db_path,
        rating="up",
        question="Photo feuille",
        answer="Dépistage prudent.",
        before_image_ref="data/feedback_images/fb_1_before.jpg",
    )
    assert set_before_image_ref(
        db_path,
        feedback_id=feedback_id,
        before_image_ref="data/feedback_images/fb_1_before.jpg",
    )
    assert record_outcome(
        db_path,
        feedback_id=feedback_id,
        outcome="applied_improved",
        after_image_ref="data/feedback_images/fb_1_after.jpg",
    )
    row = list_feedback_events(db_path)[0]
    assert row["before_image_ref"] == "data/feedback_images/fb_1_before.jpg"
    assert row["after_image_ref"] == "data/feedback_images/fb_1_after.jpg"
    assert row["outcome"] == "applied_improved"


def test_migration_adds_image_ref_columns(tmp_path):
    db_path = str(tmp_path / "case_log.sqlite3")
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE feedback_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                rating TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                outcome TEXT,
                outcome_at TEXT
            )
            """
        )
        conn.execute("PRAGMA user_version = 2")
        conn.execute(
            "INSERT INTO feedback_events (created_at, rating, question, answer) "
            "VALUES ('2026-01-01T00:00:00+00:00', 'up', 'Q', 'A')"
        )
    init_case_log(db_path)
    row = list_feedback_events(db_path)[0]
    assert "before_image_ref" in row
    assert "after_image_ref" in row
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
