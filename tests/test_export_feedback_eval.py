"""Tests for feedback evaluation export."""

from types import SimpleNamespace

from core.case_log import record_evidence, record_feedback, record_outcome
from scripts.evaluate_rag import load_feedback_eval_cases
from scripts.export_feedback_eval import main


def test_export_feedback_eval_writes_csv(tmp_path):
    db = tmp_path / "case_log.sqlite3"
    out = tmp_path / "out.csv"
    ledger_created_at = record_evidence(
        str(db),
        question_hash_value="salted-hash",
        decisions=[SimpleNamespace(
            chunk_id="chunk-1",
            source_title="Guide mil",
            score=0.42,
            kept=True,
            demoted_reason="",
        )],
    )
    fid = record_feedback(
        str(db),
        rating="up",
        question="Q",
        answer="A",
        before_image_ref=str(tmp_path / "missing_before.jpg"),
        crop_id="mil",
        place_id="kaya",
        answer_path="rag",
        question_hash_value="salted-hash",
        ledger_created_at=ledger_created_at,
    )
    record_outcome(
        str(db),
        feedback_id=fid,
        outcome="applied_improved",
        after_image_ref=str(tmp_path / "missing_after.jpg"),
    )

    code = main(["--db", str(db), "--output", str(out)])
    assert code == 0
    text = out.read_text(encoding="utf-8")
    assert "before_image_ref" in text
    assert "after_image_exists" in text
    assert "applied_improved" in text
    assert "evidence_ledger" in text
    assert "chunk-1" in text
    assert "Guide mil" in text
    assert "kaya" in text
    assert "False" in text
    privacy = out.parent / "FEEDBACK_EVAL_PRIVACY.md"
    assert privacy.is_file()
    assert "consent" in privacy.read_text(encoding="utf-8").lower()


def test_export_feedback_eval_jsonl(tmp_path):
    db = tmp_path / "case_log.sqlite3"
    out = tmp_path / "out.jsonl"
    record_feedback(str(db), rating="down", question="Quand semer le mil ?", answer="A")
    code = main(["--db", str(db), "--output", str(out), "--format", "jsonl"])
    assert code == 0
    lines = [line for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 1
    assert "Quand semer le mil" in lines[0]


def test_load_feedback_eval_cases_from_export(tmp_path):
    db = tmp_path / "case_log.sqlite3"
    out = tmp_path / "out.csv"
    record_feedback(
        str(db),
        rating="up",
        question="Comment stocker le niébé ?",
        answer="Réponse test",
    )
    record_feedback(str(db), rating="up", question="x", answer="too short question skip")
    assert main(["--db", str(db), "--output", str(out), "--no-privacy-note"]) == 0
    cases = load_feedback_eval_cases(str(out), limit=5)
    assert len(cases) == 1
    assert cases[0].category == "Feedback"
    assert cases[0].data["messageText"] == "Comment stocker le niébé ?"
