"""Evaluate DakiKobo demo quality against a running app.

Usage:
    python scripts/evaluate_rag.py
    python scripts/evaluate_rag.py --base-url http://127.0.0.1:8005
    python scripts/evaluate_rag.py --strict

The script calls public HTTP endpoints and writes a Markdown report with
answer snippets, confidence labels, source cards, latency, and pass/fail checks.
It does not read local secrets.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import requests


DEFAULT_BASE_URL = "https://kimcomehome-dakikobo.hf.space"
DEFAULT_OUTPUT = "reports/rag_eval_results.md"
READY_STATUSES = {"ready"}
GOOD_CONFIDENCE = ("Fort", "Moyen")


@dataclass(frozen=True)
class EvalCase:
    id: str
    category: str
    label: str
    method: str
    path: str
    data: dict[str, str] = field(default_factory=dict)
    params: dict[str, str] = field(default_factory=dict)
    min_sources: int = 0
    max_sources: int | None = None
    allowed_confidence: tuple[str, ...] = ("Fort", "Moyen", "Faible")
    answer_terms_any: tuple[str, ...] = ()
    source_terms_any: tuple[str, ...] = ()
    expect_refusal: bool = False

    @property
    def prompt(self) -> str:
        return self.data.get("messageText", self.label)


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str


@dataclass
class EvalResult:
    case: EvalCase
    status_code: int | None
    latency_ms: int | None
    payload: dict[str, Any]
    error: str = ""
    checks: list[Check] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(check.passed for check in self.checks)


CASES = [
    EvalCase(
        id="rag_mil_semis",
        category="RAG",
        label="Semis du mil",
        method="POST",
        path="/ask",
        data={"messageText": "Quand semer le mil ?"},
        min_sources=1,
        allowed_confidence=GOOD_CONFIDENCE,
        answer_terms_any=("juin", "pluie", "semis", "saison"),
    ),
    EvalCase(
        id="rag_niebe_stockage",
        category="RAG",
        label="Stockage du niébé",
        method="POST",
        path="/ask",
        data={"messageText": "Comment stocker le niébé contre les bruches ?"},
        min_sources=1,
        max_sources=2,
        allowed_confidence=GOOD_CONFIDENCE,
        answer_terms_any=("pics", "bruche", "stockage", "sec"),
        source_terms_any=("iita", "niebe", "niébé"),
    ),
    EvalCase(
        id="rag_mais_maladie",
        category="RAG",
        label="Maladie du maïs",
        method="POST",
        path="/ask",
        data={"messageText": "Quels signes surveiller sur les feuilles de maïs ?"},
        min_sources=1,
        allowed_confidence=GOOD_CONFIDENCE,
        answer_terms_any=("feuille", "tache", "maïs", "mais", "surveiller"),
    ),
    EvalCase(
        id="rag_arachide",
        category="RAG",
        label="Arachide",
        method="POST",
        path="/ask",
        data={"messageText": "Quels conseils pour réussir l'arachide au Burkina Faso ?"},
        min_sources=1,
        allowed_confidence=GOOD_CONFIDENCE,
        answer_terms_any=("arachide", "semis", "sol", "rotation"),
    ),
    EvalCase(
        id="tool_fertilizer_sorgho",
        category="Tool",
        label="Fumure sorgho",
        method="POST",
        path="/ask",
        data={"messageText": "Quelle fumure pour le sorgho ?"},
        min_sources=1,
        allowed_confidence=("Fort",),
        answer_terms_any=("npk", "urée", "uree", "agent"),
        source_terms_any=("sorgho", "fumure", "sciences"),
    ),
    EvalCase(
        id="off_topic_car_engine",
        category="Safety",
        label="Question hors domaine",
        method="POST",
        path="/ask",
        data={"messageText": "Comment réparer un moteur de voiture ?"},
        max_sources=0,
        allowed_confidence=("Faible",),
        expect_refusal=True,
        answer_terms_any=("ne sais pas", "pas disponible", "base de données"),
    ),
    EvalCase(
        id="weather_ouagadougou",
        category="Weather",
        label="Météo agricole Ouagadougou",
        method="GET",
        path="/weather",
        params={"location": "ouagadougou"},
        min_sources=1,
        allowed_confidence=GOOD_CONFIDENCE,
        answer_terms_any=("pluie", "stress", "semis", "urée", "uree"),
        source_terms_any=("open-meteo", "météo", "meteo"),
    ),
    EvalCase(
        id="soil_mais_ouagadougou",
        category="Soil",
        label="Sol + engrais maïs Ouagadougou",
        method="GET",
        path="/soil",
        params={"location": "ouagadougou", "crop": "maïs"},
        min_sources=2,
        allowed_confidence=("Fort", "Moyen", "Faible"),
        answer_terms_any=("maïs", "mais", "npk", "urée", "uree", "sol"),
        source_terms_any=("soilgrids", "sol", "maïs", "mais"),
    ),
]


def _normalize(text: str) -> str:
    value = unicodedata.normalize("NFKD", text or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return value.lower()


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    if not terms:
        return True
    normalized = _normalize(text)
    return any(_normalize(term) in normalized for term in terms)


def _short(text: str, limit: int = 450) -> str:
    clean = " ".join((text or "").split())
    if len(clean) <= limit:
        return clean
    return clean[:limit].rsplit(" ", 1)[0] + "..."


def _as_sources(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(payload.get("sources"), list):
        return payload["sources"]
    weather = payload.get("weather")
    if isinstance(weather, dict) and isinstance(weather.get("sources"), list):
        return weather["sources"]
    soil = payload.get("soil")
    if isinstance(soil, dict) and isinstance(soil.get("sources"), list):
        output = list(soil["sources"])
        fertilizer = payload.get("fertilizer")
        if isinstance(fertilizer, dict) and isinstance(fertilizer.get("sources"), list):
            output.extend(fertilizer["sources"])
        return output
    return []


def _as_answer(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("answer"), str):
        return payload["answer"]

    weather = payload.get("weather")
    if isinstance(weather, dict):
        parts = []
        for insight in weather.get("insights", []):
            if isinstance(insight, dict):
                parts.append(f"{insight.get('label', '')}: {insight.get('text', '')}")
        return " ".join(part for part in parts if part.strip())

    soil = payload.get("soil")
    if isinstance(soil, dict):
        parts = []
        for insight in soil.get("insights", []):
            if isinstance(insight, dict):
                parts.append(f"{insight.get('label', '')}: {insight.get('text', '')}")
        fertilizer = payload.get("fertilizer")
        if isinstance(fertilizer, dict) and isinstance(fertilizer.get("answer"), str):
            parts.append(fertilizer["answer"])
        return " ".join(part for part in parts if part.strip())

    return payload.get("error", "")


def _source_text(sources: list[dict[str, Any]]) -> str:
    parts = []
    for source in sources:
        parts.append(str(source.get("title", "")))
        parts.append(str(source.get("type", "")))
        parts.append(str(source.get("snippet", "")))
    return " ".join(parts)


def checks_for(case: EvalCase, result: EvalResult) -> list[Check]:
    payload = result.payload
    answer = _as_answer(payload)
    sources = _as_sources(payload)
    confidence = payload.get("confidence", "")
    source_count = len(sources)

    checks = [
        Check("HTTP 200", result.status_code == 200, f"status={result.status_code}"),
        Check(
            "confidence",
            confidence in case.allowed_confidence,
            f"confidence={confidence or '<missing>'}",
        ),
        Check(
            "min_sources",
            source_count >= case.min_sources,
            f"sources={source_count}, min={case.min_sources}",
        ),
    ]
    if case.max_sources is not None:
        checks.append(
            Check(
                "max_sources",
                source_count <= case.max_sources,
                f"sources={source_count}, max={case.max_sources}",
            )
        )
    if case.answer_terms_any:
        checks.append(
            Check(
                "answer_terms",
                _contains_any(answer, case.answer_terms_any),
                "any=" + ", ".join(case.answer_terms_any),
            )
        )
    if case.source_terms_any:
        checks.append(
            Check(
                "source_terms",
                _contains_any(_source_text(sources), case.source_terms_any),
                "any=" + ", ".join(case.source_terms_any),
            )
        )
    if case.expect_refusal:
        refusal = _contains_any(answer, ("ne sais pas", "pas disponible dans la base"))
        checks.append(Check("refusal", refusal, "expected grounded fallback"))
    return checks


def request_case(base_url: str, case: EvalCase, timeout: float) -> EvalResult:
    url = base_url.rstrip("/") + case.path
    started = time.perf_counter()
    try:
        if case.method == "POST":
            response = requests.post(url, data=case.data, timeout=timeout)
        elif case.method == "GET":
            response = requests.get(url, params=case.params, timeout=timeout)
        else:
            raise ValueError(f"Unsupported method: {case.method}")
        latency_ms = int((time.perf_counter() - started) * 1000)
        try:
            payload = response.json()
        except ValueError:
            payload = {"error": response.text[:500]}
        result = EvalResult(case, response.status_code, latency_ms, payload)
    except requests.RequestException as e:
        latency_ms = int((time.perf_counter() - started) * 1000)
        result = EvalResult(case, None, latency_ms, {}, error=str(e))
    result.checks = checks_for(case, result)
    return result


def wait_for_ready(base_url: str, timeout: float, poll_seconds: float = 5.0) -> dict[str, Any]:
    deadline = time.time() + timeout
    last_payload: dict[str, Any] = {}
    last_error = ""
    while time.time() < deadline:
        try:
            response = requests.get(base_url.rstrip("/") + "/healthz", timeout=10)
            last_payload = response.json()
            last_error = ""
        except (requests.RequestException, ValueError) as e:
            last_error = str(e)
            time.sleep(poll_seconds)
            continue

        if last_payload.get("rag_status") in READY_STATUSES:
            return last_payload
        time.sleep(poll_seconds)
    if not last_payload:
        return {"rag_status": "unreachable", "error": last_error or "healthz unavailable"}
    if last_error:
        last_payload["error"] = last_error
    return last_payload


def run_evaluation(base_url: str, timeout: float, *, progress: bool = False) -> list[EvalResult]:
    results = []
    for case in CASES:
        if progress:
            print(f"Running {case.id}...", flush=True)
        results.append(request_case(base_url, case, timeout))
    return results


def _format_sources(sources: list[dict[str, Any]]) -> str:
    if not sources:
        return "- Aucun"
    lines = []
    for source in sources:
        title = source.get("title", "Inconnu")
        source_type = source.get("type", "")
        snippet = _short(str(source.get("snippet", "")), 220)
        label = f"{title} ({source_type})" if source_type else title
        if snippet:
            lines.append(f"- {label}: {snippet}")
        else:
            lines.append(f"- {label}")
    return "\n".join(lines)


def _status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def _escape_table(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def format_report(
    *,
    base_url: str,
    health: dict[str, Any],
    results: list[EvalResult],
    generated_at: datetime | None = None,
    run_error: str = "",
) -> str:
    generated_at = generated_at or datetime.now(timezone.utc)
    passed = sum(1 for result in results if result.passed)
    failed = len(results) - passed
    lines = [
        "# DakiKobo RAG Evaluation Report",
        "",
        f"- Generated: `{generated_at.isoformat(timespec='seconds')}`",
        f"- Base URL: `{base_url.rstrip('/')}`",
        f"- Health: `{json.dumps(health, ensure_ascii=False, sort_keys=True)}`",
        f"- Summary: `{passed} passed / {len(results)} total`",
    ]
    if run_error:
        lines.append(f"- Run error: `{run_error}`")
    lines.extend([
        "",
        "## Summary Table",
        "",
        "| Case | Category | Status | HTTP | Confidence | Sources | Latency |",
        "| --- | --- | --- | --- | --- | ---: | ---: |",
    ])

    for result in results:
        payload = result.payload
        lines.append(
            "| "
            + " | ".join(
                [
                    _escape_table(result.case.id),
                    _escape_table(result.case.category),
                    _status_text(result.passed),
                    _escape_table(result.status_code),
                    _escape_table(payload.get("confidence", "")),
                    str(len(_as_sources(payload))),
                    f"{result.latency_ms or 0} ms",
                ]
            )
            + " |"
        )

    lines.extend(["", "## Case Details", ""])
    for result in results:
        case = result.case
        payload = result.payload
        answer = _as_answer(payload)
        sources = _as_sources(payload)
        lines.extend(
            [
                f"### {case.id} - {case.label}",
                "",
                f"- Category: `{case.category}`",
                f"- Request: `{case.method} {case.path}`",
                f"- Prompt: {case.prompt}",
                f"- Status: `{_status_text(result.passed)}`",
                f"- HTTP: `{result.status_code}`",
                f"- Confidence: `{payload.get('confidence', '')}`",
                f"- Latency: `{result.latency_ms or 0} ms`",
            ]
        )
        if result.error:
            lines.append(f"- Error: `{result.error}`")
        lines.extend(["", "**Checks**", ""])
        for check in result.checks:
            lines.append(f"- `{_status_text(check.passed)}` {check.name}: {check.detail}")
        lines.extend(["", "**Answer / Context**", "", _short(answer) or "<empty>", "", "**Sources**", ""])
        lines.append(_format_sources(sources))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_report(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate a running DakiKobo app.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="App base URL.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Markdown report path.")
    parser.add_argument("--timeout", type=float, default=120.0, help="Per-request timeout seconds.")
    parser.add_argument("--wait-timeout", type=float, default=360.0, help="RAG readiness wait seconds.")
    parser.add_argument("--no-wait", action="store_true", help="Skip /healthz readiness wait.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when any check fails.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    base_url = args.base_url.rstrip("/")
    health = {}
    if not args.no_wait:
        print(f"Waiting for RAG readiness at {base_url}/healthz...", flush=True)
        health = wait_for_ready(base_url, args.wait_timeout)
        print(f"Health: {health}", flush=True)

    run_error = ""
    if not args.no_wait and health.get("rag_status") not in READY_STATUSES:
        run_error = (
            "RAG health check did not become ready; case execution skipped. "
            "Check network/DNS, Space status, or rerun with --no-wait for raw endpoint checks."
        )
        print(run_error, flush=True)
        results = []
    else:
        results = run_evaluation(base_url, args.timeout, progress=True)

    report = format_report(
        base_url=base_url,
        health=health,
        results=results,
        run_error=run_error,
    )
    write_report(args.output, report)

    passed = sum(1 for result in results if result.passed)
    print(f"Wrote {args.output}")
    print(f"Summary: {passed}/{len(results)} passed")
    if args.strict and passed != len(results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
