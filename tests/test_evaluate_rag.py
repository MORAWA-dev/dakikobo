from datetime import datetime, timezone

import requests

from scripts.evaluate_rag import (
    EvalCase,
    EvalResult,
    _as_answer,
    _as_sources,
    checks_for,
    format_report,
    wait_for_ready,
)


def test_checks_pass_for_cited_niebe_payload():
    case = EvalCase(
        id="rag_niebe_stockage",
        category="RAG",
        label="Stockage du niébé",
        method="POST",
        path="/ask",
        data={"messageText": "Comment stocker le niébé contre les bruches ?"},
        min_sources=1,
        max_sources=2,
        allowed_confidence=("Fort", "Moyen"),
        answer_terms_any=("pics", "bruche"),
        source_terms_any=("iita", "niebe"),
    )
    payload = {
        "answer": "Utilisez des sacs PICS contre les bruches.",
        "confidence": "Fort",
        "sources": [
            {
                "title": "IITA 2018 - Production du niebe",
                "type": "Base locale",
                "snippet": "Stockage hermétique du niébé.",
            }
        ],
    }
    result = EvalResult(case, 200, 1200, payload)

    result.checks = checks_for(case, result)

    assert result.passed is True


def test_checks_fail_when_required_sources_are_missing():
    case = EvalCase(
        id="rag_mil_semis",
        category="RAG",
        label="Semis du mil",
        method="POST",
        path="/ask",
        min_sources=1,
        allowed_confidence=("Fort", "Moyen"),
    )
    payload = {
        "answer": "Réponse sans source.",
        "confidence": "Faible",
        "sources": [],
    }
    result = EvalResult(case, 200, 100, payload)

    result.checks = checks_for(case, result)

    failed = {check.name for check in result.checks if not check.passed}
    assert "min_sources" in failed
    assert "confidence" in failed
    assert result.passed is False


def test_weather_payload_extracts_sources_and_context_text():
    payload = {
        "confidence": "Moyen",
        "weather": {
            "insights": [
                {"label": "Pluie utile", "text": "Surveillez l'humidité du sol."},
                {"label": "Urée", "text": "Évitez l'urée avant forte pluie."},
            ],
            "sources": [{"title": "Open-Meteo Forecast API", "type": "Météo"}],
        },
    }

    assert "Surveillez" in _as_answer(payload)
    assert _as_sources(payload)[0]["title"] == "Open-Meteo Forecast API"


def test_format_report_contains_summary_checks_and_sources():
    case = EvalCase(
        id="tool_fertilizer_sorgho",
        category="Tool",
        label="Fumure sorgho",
        method="POST",
        path="/ask",
        min_sources=1,
    )
    payload = {
        "answer": "Dose NPK puis urée.",
        "confidence": "Fort",
        "sources": [{"title": "Sciences et Techniques du Burkina", "type": "Outil engrais"}],
    }
    result = EvalResult(case, 200, 250, payload)
    result.checks = checks_for(case, result)

    report = format_report(
        base_url="https://example.test",
        health={"rag_status": "ready"},
        results=[result],
        generated_at=datetime(2026, 6, 30, tzinfo=timezone.utc),
    )

    assert "# DakiKobo RAG Evaluation Report" in report
    assert "1 passed / 1 total" in report
    assert "Sciences et Techniques du Burkina" in report
    assert "`PASS` min_sources" in report


def test_format_report_can_record_run_error_without_cases():
    report = format_report(
        base_url="https://example.test",
        health={"rag_status": "unreachable", "error": "dns failed"},
        results=[],
        generated_at=datetime(2026, 6, 30, tzinfo=timezone.utc),
        run_error="health check failed",
    )

    assert "0 passed / 0 total" in report
    assert "health check failed" in report
    assert "rag_status" in report


def test_wait_for_ready_reports_unreachable(monkeypatch):
    def fail_get(*args, **kwargs):
        raise requests.RequestException("dns failed")

    monkeypatch.setattr("scripts.evaluate_rag.requests.get", fail_get)
    monkeypatch.setattr("scripts.evaluate_rag.time.sleep", lambda seconds: None)

    payload = wait_for_ready("https://example.test", timeout=0.01, poll_seconds=0.001)

    assert payload["rag_status"] == "unreachable"
    assert "dns failed" in payload["error"]
