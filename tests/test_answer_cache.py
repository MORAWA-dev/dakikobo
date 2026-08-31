"""Tests for corpus-aware answer caching and the /ask fast path."""

from types import SimpleNamespace

import app as app_module
from core.answer_cache import (
    AnswerCache,
    build_answer_cache_key,
    normalize_question,
    question_hash,
)
from core.query_context import resolve_query_context
from core.ops_metrics import OpsMetricsStore


def _key(**overrides):
    values = {
        "question": "Quand semer le mil ?",
        "crop_id": "mil",
        "growth_stage": "semis",
        "place_id": "ouagadougou",
        "simple_french": False,
        "llm_model": "model-a",
        "manifest_hash_value": "corpus-a",
    }
    values.update(overrides)
    question = values.pop("question")
    return build_answer_cache_key(question, **values)


def test_answer_cache_key_changes_on_locked_components():
    baseline = _key()
    assert _key(question="Quand récolter le mil ?") != baseline
    assert _key(crop_id="sorgho") != baseline
    assert _key(growth_stage="levée") != baseline
    assert _key(place_id="bobo") != baseline
    assert _key(simple_french=True) != baseline
    assert _key(llm_model="model-b") != baseline
    assert _key(manifest_hash_value="corpus-b") != baseline


def test_question_normalization_collapses_case_and_whitespace():
    assert normalize_question("  QUAND   semer\nle MIL ? ") == "quand semer le mil ?"
    assert _key(question="  QUAND   semer\nle MIL ? ") == _key()


def test_answer_cache_value_has_locked_provenance_shape(tmp_path):
    cache = AnswerCache(60, db_path=str(tmp_path / "answers.sqlite3"))
    value = cache.set(
        "key",
        answer="Après des pluies régulières.",
        case={"crop": "mil"},
        sources=[{"title": "Guide mil"}],
        confidence="Moyen",
        retrieved_chunk_ids=["abc123"],
    )

    assert set(value) == {
        "answer",
        "case",
        "sources",
        "confidence",
        "retrieved_chunk_ids",
        "cached_at",
    }
    assert cache.get("key") == value


def test_question_hash_is_salted_and_never_plain_sha256():
    first = question_hash("Quand semer ?", salt="secret-a")
    second = question_hash("Quand semer ?", salt="secret-b")
    assert first != second
    assert len(first) == 64


def test_ask_cache_hit_skips_router_rag_weather_and_tts(monkeypatch, tmp_path):
    query = "Quand semer le mil ?"
    resolved = resolve_query_context(query, {}, simple_french=False)
    cache = AnswerCache(60, db_path=str(tmp_path / "route-cache.sqlite3"))
    metrics = OpsMetricsStore(
        20,
        db_path=str(tmp_path / "route-metrics.sqlite3"),
    )
    key = build_answer_cache_key(
        resolved.retrieval_query,
        crop_id=resolved.crop_id,
        growth_stage=resolved.growth_stage,
        place_id=resolved.place_id,
        simple_french=False,
        llm_model=app_module.LLM_MODEL,
        manifest_hash_value="manifest-test",
    )
    cache.set(
        key,
        answer="Semez après des pluies régulières.",
        case={"crop": "mil", "risk_level": "Prudence"},
        sources=[{"title": "Guide mil", "type": "Base locale", "snippet": "Semis"}],
        confidence="Moyen",
        retrieved_chunk_ids=["chunk-a"],
    )

    monkeypatch.setattr(app_module, "ANSWER_CACHE_ENABLED", True)
    monkeypatch.setattr(app_module, "CASE_LOG_DB", str(tmp_path / "case_log.sqlite3"))
    monkeypatch.setattr(app_module, "answer_cache_store", cache)
    monkeypatch.setattr(app_module, "OPS_METRICS_ENABLED", True)
    monkeypatch.setattr(app_module.ops_metrics_mod, "_metrics_store", metrics)
    monkeypatch.setattr(app_module, "REQUEST_COOLDOWN_SECONDS", 0)
    monkeypatch.setattr(app_module, "get_active_manifest_hash", lambda: "manifest-test")
    monkeypatch.setattr(
        app_module,
        "classify",
        lambda query: (_ for _ in ()).throw(AssertionError("router must be skipped")),
    )
    monkeypatch.setattr(
        app_module,
        "get_rag_chain",
        lambda: (_ for _ in ()).throw(AssertionError("RAG must be skipped")),
    )
    monkeypatch.setattr(
        app_module,
        "build_weather_context",
        lambda location: (_ for _ in ()).throw(AssertionError("weather must be skipped")),
    )
    monkeypatch.setattr(
        app_module,
        "text_to_speech_to_static",
        lambda answer: (_ for _ in ()).throw(AssertionError("TTS must be skipped")),
    )

    response = app_module.app.test_client().post(
        "/ask",
        data={"messageText": query},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["answer"] == "Semez après des pluies régulières."
    assert payload["confidence"] == "Moyen"
    assert payload["audio_url"] == ""
    assert payload["case"]["crop"] == "mil"
    assert payload["journal"]["answer_path"] == "cache"
    assert payload["journal"]["ledger_created_at"] is None
    event = metrics.snapshot(limit=1)["recent"][0]
    assert event["cache_hit"] is True
    assert event["intent"] == "cache"


def test_repeat_rag_question_is_stored_then_served_without_groq(monkeypatch, tmp_path):
    query = "Comment conserver le niébé ?"
    document = SimpleNamespace(
        metadata={"source": "Guide niébé"},
        page_content="Séchez bien le niébé avant un stockage hermétique.",
    )

    class Harness:
        def __init__(self):
            self.combine_documents_chain = self
            self.search_calls = 0

        def similarity_search_with_relevance_scores(self, question, k):
            self.search_calls += 1
            return [(document, 0.4)]

        def run(self, *, input_documents, question):
            return "Séchez bien les grains puis utilisez un stockage hermétique."

    harness = Harness()
    cache = AnswerCache(60, db_path=str(tmp_path / "repeat.sqlite3"))
    monkeypatch.setattr(app_module, "CASE_LOG_DB", str(tmp_path / "case_log.sqlite3"))
    monkeypatch.setattr(app_module, "ANSWER_CACHE_ENABLED", True)
    monkeypatch.setattr(app_module, "answer_cache_store", cache)
    monkeypatch.setattr(app_module, "REQUEST_COOLDOWN_SECONDS", 0)
    monkeypatch.setattr(app_module, "get_active_manifest_hash", lambda: "manifest-repeat")
    monkeypatch.setattr(app_module, "get_rag_chain", lambda: harness)
    monkeypatch.setattr(app_module, "_rag_db", harness)
    monkeypatch.setattr(app_module, "text_to_speech_to_static", lambda answer: "")

    client = app_module.app.test_client()
    first = client.post("/ask", data={"messageText": query})
    assert first.status_code == 200
    assert harness.search_calls == 1
    first_ref = first.get_json()["journal"]["ledger_created_at"]
    assert first_ref is not None

    monkeypatch.setattr(
        app_module,
        "get_rag_chain",
        lambda: (_ for _ in ()).throw(AssertionError("Groq/RAG must be skipped")),
    )
    monkeypatch.setattr(
        app_module,
        "classify",
        lambda value: (_ for _ in ()).throw(AssertionError("router must be skipped")),
    )
    second = client.post("/ask", data={"messageText": query})

    assert second.status_code == 200
    assert second.get_json()["answer"] == first.get_json()["answer"]
    assert second.get_json()["audio_url"] == ""
    assert second.get_json()["journal"]["answer_path"] == "cache"
    assert second.get_json()["journal"]["ledger_created_at"] != first_ref
    assert harness.search_calls == 1
