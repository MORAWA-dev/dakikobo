"""Tests for the SQLite feedback/case log."""

import sqlite3

import pytest

from core.case_log import SCHEMA_VERSION, list_feedback_events, record_feedback


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
