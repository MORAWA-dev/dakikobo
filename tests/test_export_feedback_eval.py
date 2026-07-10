"""Tests for feedback evaluation export."""

from core.case_log import record_feedback, record_outcome
from scripts.export_feedback_eval import main


def test_export_feedback_eval_writes_csv(tmp_path):
    db = tmp_path / "case_log.sqlite3"
    out = tmp_path / "out.csv"
    fid = record_feedback(
        str(db),
        rating="up",
        question="Q",
        answer="A",
        before_image_ref=str(tmp_path / "missing_before.jpg"),
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
    assert "False" in text
