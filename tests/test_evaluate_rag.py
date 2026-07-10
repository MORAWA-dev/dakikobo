from datetime import datetime, timezone

import requests

from scripts.evaluate_rag import (
    CASES,
    EvalCase,
    EvalResult,
    _as_answer,
    _as_sources,
    checks_for,
    format_report,
    hard_pass_rate,
    has_transport_failure,
    main,
    wait_for_ready,
)


def test_builtin_suite_includes_oaph_and_simple_french():
    ids = {case.id for case in CASES}
    assert "rag_oaph_acronym" in ids
    assert "tool_fertilizer_simple_french" in ids
    oaph = next(case for case in CASES if case.id == "rag_oaph_acronym")
    assert "offensive" in oaph.answer_terms_any
    simple = next(case for case in CASES if case.id == "tool_fertilizer_simple_french")
    assert simple.data.get("simple_french") == "1"


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


def test_keyword_and_confidence_are_advisory_not_hard_failures():
    """LLM wording/confidence may miss exact terms without failing the case."""
    case = EvalCase(
        id="rag_mil_semis",
        category="RAG",
        label="Semis du mil",
        method="POST",
        path="/ask",
        min_sources=1,
        allowed_confidence=("Fort", "Moyen"),
        answer_terms_any=("juin", "pluie"),
        source_terms_any=("calendrier",),
    )
    payload = {
        "answer": "Semez le mil au début de la saison des pluies au Burkina Faso.",
        "confidence": "Faible",  # would hard-fail under the old rules
        "sources": [
            {
                "title": "Guide mil",
                "type": "Base locale",
                "snippet": "Conseils de semis.",
            }
        ],
    }
    result = EvalResult(case, 200, 100, payload)
    result.checks = checks_for(case, result)

    by_name = {check.name: check for check in result.checks}
    assert by_name["confidence"].advisory is True
    assert by_name["confidence"].passed is False
    assert by_name["answer_terms"].advisory is True
    assert by_name["source_terms"].advisory is True
    assert by_name["source_terms"].passed is False
    # Hard structural checks still pass → case is a hard pass.
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

    failed_hard = {
        check.name for check in result.checks if not check.passed and not check.advisory
    }
    assert "min_sources" in failed_hard
    assert result.passed is False


def test_empty_answer_fails_hard_when_sources_expected():
    case = EvalCase(
        id="rag_x",
        category="RAG",
        label="x",
        method="POST",
        path="/ask",
        min_sources=1,
    )
    result = EvalResult(case, 200, 10, {"answer": "   ", "sources": [{"title": "A"}]})
    result.checks = checks_for(case, result)
    failed = {c.name for c in result.checks if not c.passed and not c.advisory}
    assert "non_empty_answer" in failed
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
        min_pass_rate=0.75,
    )

    assert "# DakiKobo RAG Evaluation Report" in report
    assert "## Flakiness note" in report
    assert "advisory" in report.lower()
    assert "1 passed / 1 total" in report
    assert "Sciences et Techniques du Burkina" in report
    assert "`PASS` min_sources" in report


def test_format_report_marks_advisory_failures_as_warn():
    case = EvalCase(
        id="rag_x",
        category="RAG",
        label="x",
        method="POST",
        path="/ask",
        min_sources=1,
        answer_terms_any=("zzzz",),
        allowed_confidence=("Fort",),
    )
    payload = {
        "answer": "Réponse agricole valide avec source.",
        "confidence": "Faible",
        "sources": [{"title": "Doc", "type": "Base locale", "snippet": "x"}],
    }
    result = EvalResult(case, 200, 10, payload)
    result.checks = checks_for(case, result)
    report = format_report(
        base_url="https://example.test",
        health={},
        results=[result],
        generated_at=datetime(2026, 6, 30, tzinfo=timezone.utc),
    )
    assert "`WARN` answer_terms" in report
    assert "`WARN` confidence" in report
    assert result.passed is True


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
    assert "## Flakiness note" in report


def test_hard_pass_rate_and_transport_helpers():
    ok_case = EvalCase(id="a", category="RAG", label="a", method="POST", path="/ask", min_sources=0)
    bad_case = EvalCase(id="b", category="RAG", label="b", method="POST", path="/ask", min_sources=0)
    ok = EvalResult(ok_case, 200, 1, {"answer": "x", "sources": []})
    ok.checks = checks_for(ok_case, ok)
    bad = EvalResult(bad_case, None, 1, {}, error="timeout")
    bad.checks = checks_for(bad_case, bad)
    assert hard_pass_rate([ok, bad]) == 0.5
    assert has_transport_failure([ok, bad]) is True
    assert has_transport_failure([ok]) is False


def test_wait_for_ready_reports_unreachable(monkeypatch):
    def fail_get(*args, **kwargs):
        raise requests.RequestException("dns failed")

    monkeypatch.setattr("scripts.evaluate_rag.requests.get", fail_get)
    monkeypatch.setattr("scripts.evaluate_rag.time.sleep", lambda seconds: None)

    payload = wait_for_ready("https://example.test", timeout=0.01, poll_seconds=0.001)

    assert payload["rag_status"] == "unreachable"
    assert "dns failed" in payload["error"]


def test_main_strict_fails_when_health_is_not_ready(monkeypatch, tmp_path):
    output = tmp_path / "report.md"

    monkeypatch.setattr(
        "scripts.evaluate_rag.wait_for_ready",
        lambda base_url, timeout: {"rag_status": "unreachable", "error": "dns failed"},
    )
    monkeypatch.setattr(
        "scripts.evaluate_rag.run_evaluation",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should skip cases")),
    )

    code = main([
        "--base-url",
        "https://example.test",
        "--output",
        str(output),
        "--strict",
    ])

    assert code == 1
    assert "RAG health check did not become ready" in output.read_text(encoding="utf-8")


def test_main_strict_uses_min_pass_rate_not_keyword_fails(monkeypatch, tmp_path):
    """9/10 hard-pass with keyword WARNs should succeed at min-pass-rate 0.75."""
    output = tmp_path / "report.md"

    def fake_run(base_url, timeout, progress=False, cases=None):
        results = []
        for i in range(9):
            case = EvalCase(
                id=f"ok_{i}",
                category="RAG",
                label="ok",
                method="POST",
                path="/ask",
                min_sources=1,
                answer_terms_any=("zzzz_missing",),
                allowed_confidence=("Fort",),
            )
            payload = {
                "answer": "Réponse agricole correcte pour le mil.",
                "confidence": "Faible",
                "sources": [{"title": "Doc", "type": "Base locale"}],
            }
            result = EvalResult(case, 200, 10, payload)
            result.checks = checks_for(case, result)
            results.append(result)
        # One hard failure (empty sources when required).
        bad_case = EvalCase(
            id="bad",
            category="Soil",
            label="bad",
            method="GET",
            path="/soil",
            min_sources=2,
        )
        bad = EvalResult(bad_case, 502, 100, {"error": "offline", "confidence": "Faible"})
        bad.checks = checks_for(bad_case, bad)
        results.append(bad)
        return results

    monkeypatch.setattr(
        "scripts.evaluate_rag.wait_for_ready",
        lambda base_url, timeout: {"rag_status": "ready"},
    )
    monkeypatch.setattr("scripts.evaluate_rag.run_evaluation", fake_run)

    code = main([
        "--base-url",
        "https://example.test",
        "--output",
        str(output),
        "--strict",
        "--min-pass-rate",
        "0.75",
    ])
    assert code == 0
    text = output.read_text(encoding="utf-8")
    assert "Flakiness note" in text
    assert "9 passed / 10 total" in text


def test_main_strict_fails_when_pass_rate_too_low(monkeypatch, tmp_path):
    output = tmp_path / "report.md"

    def fake_run(base_url, timeout, progress=False, cases=None):
        results = []
        for i in range(10):
            case = EvalCase(
                id=f"bad_{i}",
                category="RAG",
                label="bad",
                method="POST",
                path="/ask",
                min_sources=1,
            )
            result = EvalResult(case, 500, 10, {"error": "down"})
            result.checks = checks_for(case, result)
            results.append(result)
        return results

    monkeypatch.setattr(
        "scripts.evaluate_rag.wait_for_ready",
        lambda base_url, timeout: {"rag_status": "ready"},
    )
    monkeypatch.setattr("scripts.evaluate_rag.run_evaluation", fake_run)

    code = main([
        "--base-url",
        "https://example.test",
        "--output",
        str(output),
        "--strict",
        "--min-pass-rate",
        "0.75",
    ])
    assert code == 1
