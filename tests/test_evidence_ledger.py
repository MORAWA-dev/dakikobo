"""Phase 4 evidence decisions and SQLite ledger tests (offline only)."""

import json
from pathlib import Path
from types import SimpleNamespace

from core.answer_cache import question_hash
from core.case_log import list_evidence, record_evidence
from core.retrieval import ground_answer


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "retrieval_golden.json"


def _run_case(case: dict):
    docs = [
        SimpleNamespace(
            metadata={"source": item["title"]},
            page_content=item["content"],
        )
        for item in case["documents"]
    ]
    scores = {item["title"]: item["score"] for item in case["documents"]}
    return ground_answer(case["query"], docs, score_lookup=lambda: scores)


def test_offline_golden_set_keeps_stable_citation_decisions():
    """Replay fixture retrievals through policy code: no Flask, Groq, or network."""
    cases = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert {case["name"] for case in cases} == {
        "weak_title",
        "low_overlap",
        "score_margin",
    }
    for case in cases:
        grounded = _run_case(case)
        kept_titles = [
            decision.source_title
            for decision in grounded.evidence_decisions
            if decision.kept
        ]
        demoted = {
            decision.source_title: decision.demoted_reason
            for decision in grounded.evidence_decisions
            if not decision.kept
        }
        assert kept_titles == case["expected"]["kept_titles"], case["name"]
        assert demoted == case["expected"]["demoted"], case["name"]


def test_ledger_records_all_three_demotion_reasons_without_plaintext(tmp_path):
    cases = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    db_path = str(tmp_path / "case_log.sqlite3")
    raw_questions = []
    for index, case in enumerate(cases, start=1):
        raw_questions.append(case["query"])
        grounded = _run_case(case)
        record_evidence(
            db_path,
            question_hash_value=question_hash(case["query"], salt="test-secret"),
            decisions=grounded.evidence_decisions,
            created_at=float(index),
        )

    rows = list_evidence(db_path)
    assert {row["demoted_reason"] for row in rows if not row["kept"]} == {
        "weak_title",
        "low_overlap",
        "score_margin",
    }
    database_bytes = Path(db_path).read_bytes()
    assert all(question.encode("utf-8") not in database_bytes for question in raw_questions)
    assert all(len(row["question_hash"]) == 64 for row in rows)
