"""Tests for corpus-aware answer caching and the /ask fast path."""

from types import SimpleNamespace

import app as app_module
from core.answer_cache import (
    AnswerCache,
    build_answer_cache_key,
    normalize_question,
    question_hash,
)
from core.answer_safety import safety_policy_revision
from core.query_context import resolve_query_context
from core.ops_metrics import OpsMetricsStore
from core.case_log import list_evidence


def _key(**overrides):
    values = {
        "question": "Quand semer le mil ?",
        "crop_id": "mil",
        "growth_stage": "semis",
        "place_id": "ouagadougou",
        "simple_french": False,
        "llm_model": "model-a",
        "manifest_hash_value": "corpus-a",
        "safety_revision": "safety-a",
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


def test_answer_cache_key_changes_on_safety_policy_revision():
    """A code-only safety deployment must make older answers unreachable.

    Such a deployment changes no document and no model name, so the corpus
    manifest and ``llm_model`` components stay identical. Without the safety
    revision in the key material, answers generated under the previous rules
    would keep being served until the TTL expired.
    """
    baseline = _key()
    assert _key(safety_revision="safety-b") != baseline


def test_answer_cache_key_defaults_to_the_deployed_safety_revision():
    from core.answer_safety import safety_policy_revision

    assert _key(safety_revision=None) == _key(
        safety_revision=safety_policy_revision()
    )


def test_safety_policy_revision_is_stable_and_namespaced():
    from core.answer_safety import SAFETY_POLICY_VERSION, safety_policy_revision

    revision = safety_policy_revision()
    assert revision == safety_policy_revision()
    assert revision.startswith(SAFETY_POLICY_VERSION + ".")
    # The digest covers prompt/guardrail source, so it is more than the constant.
    assert revision != SAFETY_POLICY_VERSION


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
        "evidence_question_hash",
        "evidence_created_at",
        "cached_at",
    }
    assert value["evidence_question_hash"] == ""
    assert value["evidence_created_at"] is None
    assert cache.get("key") == value


def test_question_hash_is_salted_and_never_plain_sha256():
    first = question_hash("Quand semer ?", salt="secret-a")
    second = question_hash("Quand semer ?", salt="secret-b")
    assert first != second
    assert len(first) == 64


def test_ask_cache_hit_skips_rag_weather_and_tts_but_not_safety_routing(
    monkeypatch, tmp_path
):
    """A cache hit must still avoid RAG, weather, and TTS work.

    Intent classification is deliberately *not* skipped any more: it is the
    safety gate that decides whether the deterministic fertilizer route owns the
    question, so it has to run before a persisted answer can be considered.
    """
    query = "Quand semer le mil ?"
    resolved = resolve_query_context(query, {}, simple_french=False)
    cache = AnswerCache(60, db_path=str(tmp_path / "route-cache.sqlite3"))
    metrics = OpsMetricsStore(
        20,
        db_path=str(tmp_path / "route-metrics.sqlite3"),
    )
    key = "farmer-v1:" + build_answer_cache_key(
        resolved.retrieval_query,
        crop_id=resolved.crop_id,
        growth_stage=resolved.growth_stage,
        place_id=resolved.place_id,
        simple_french=False,
        llm_model=app_module.LLM_MODEL,
        manifest_hash_value="manifest-test",
        safety_revision=safety_policy_revision(),
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
    router_calls = []
    real_classify = app_module.classify
    monkeypatch.setattr(
        app_module,
        "classify",
        lambda value: router_calls.append(value) or real_classify(value),
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
    # Safety-sensitive classification ran before the cache was consulted.
    assert router_calls == [query]
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
    normalized_variant = "  COMMENT CONSERVER LE NIÉBÉ ?  "
    second = client.post("/ask", data={"messageText": normalized_variant})

    assert second.status_code == 200
    assert second.get_json()["answer"] == first.get_json()["answer"]
    assert second.get_json()["audio_url"] == ""
    assert second.get_json()["journal"]["answer_path"] == "cache"
    assert second.get_json()["journal"]["ledger_created_at"] != first_ref
    assert harness.search_calls == 1

    feedback = client.post(
        "/feedback",
        data={
            "rating": "up", "consent": "1",
            "question": normalized_variant.strip(),
            "answer": second.get_json()["answer"],
            "answer_path": "cache",
            "ledger_created_at": second.get_json()["journal"]["ledger_created_at"],
        },
    )
    linked = list_evidence(
        str(tmp_path / "case_log.sqlite3"),
        feedback_id=feedback.get_json()["feedback_id"],
    )
    assert linked



# =====================================================================
# Audit regression — finding 4: the cache must not bypass a safety route
# =====================================================================

def test_stale_cached_answer_cannot_bypass_the_fertilizer_safety_route(
    monkeypatch, tmp_path
):
    """A cached RAG answer must not stand in for the deterministic dose gate.

    The lookup used to happen before intent classification, so an entry written
    when fertilizer questions still went to the LLM would keep answering them
    after the deterministic safety route was added. This plants exactly such an
    entry, under the key the route would compute, and proves it is never served.
    """
    query = "Quel engrais pour le sorgho ?"
    resolved = resolve_query_context(query, {}, simple_french=False)
    cache = AnswerCache(60, db_path=str(tmp_path / "stale.sqlite3"))

    monkeypatch.setattr(app_module, "ANSWER_CACHE_ENABLED", True)
    monkeypatch.setattr(app_module, "answer_cache_store", cache)
    monkeypatch.setattr(app_module, "CASE_LOG_DB", str(tmp_path / "case_log.sqlite3"))
    monkeypatch.setattr(app_module, "REQUEST_COOLDOWN_SECONDS", 0)
    monkeypatch.setattr(app_module, "get_active_manifest_hash", lambda: "manifest-x")
    monkeypatch.setattr(app_module, "text_to_speech_to_static", lambda answer: "")
    monkeypatch.setattr(
        app_module,
        "get_rag_chain",
        lambda: (_ for _ in ()).throw(AssertionError("RAG must not run")),
    )

    # Plant a poisoned entry under the exact key the route builds.
    with app_module.app.test_request_context("/ask"):
        key = app_module._answer_cache_key(resolved.retrieval_query, resolved, False)
    cache.set(
        key,
        answer="Appliquez 100 kg/ha de NPK 14-23-14 au semis.",
        case={"crop": "sorgho", "risk_level": "Faible si confirmé localement"},
        sources=[{"title": "Ancienne source", "type": "Base locale", "snippet": ""}],
        confidence="Fort",
        retrieved_chunk_ids=["chunk-old"],
    )
    assert cache.get(key) is not None, "the poisoned entry must really be stored"

    response = app_module.app.test_client().post("/ask", data={"messageText": query})
    payload = response.get_json()

    assert response.status_code == 200
    # The deterministic fertilizer gate answered, not the cache.
    assert "100 kg/ha" not in payload["answer"]
    assert "14-23-14" not in payload["answer"]
    assert payload["confidence"] == "Faible"
    assert payload["answer_kind"] == "refusal"
    assert payload["sources"] == []
    assert payload["journal"]["answer_path"] == "fertilizer"


def test_fertilizer_questions_are_never_written_to_the_answer_cache(
    monkeypatch, tmp_path
):
    """Reads and writes share one exclusion, so no such entry can accumulate."""
    cache = AnswerCache(60, db_path=str(tmp_path / "nowrite.sqlite3"))
    monkeypatch.setattr(app_module, "ANSWER_CACHE_ENABLED", True)
    monkeypatch.setattr(app_module, "answer_cache_store", cache)
    monkeypatch.setattr(app_module, "CASE_LOG_DB", str(tmp_path / "case_log.sqlite3"))
    monkeypatch.setattr(app_module, "REQUEST_COOLDOWN_SECONDS", 0)
    monkeypatch.setattr(app_module, "get_active_manifest_hash", lambda: "manifest-y")
    monkeypatch.setattr(app_module, "text_to_speech_to_static", lambda answer: "")

    query = "Quelle dose d'engrais pour le maïs ?"
    resolved = resolve_query_context(query, {}, simple_french=False)

    response = app_module.app.test_client().post("/ask", data={"messageText": query})
    assert response.status_code == 200

    with app_module.app.test_request_context("/ask"):
        key = app_module._answer_cache_key(resolved.retrieval_query, resolved, False)
    assert cache.get(key) is None, "a safety-routed question was cached"


def test_answer_cache_usable_excludes_safety_routed_questions():
    """Unit-level statement of the invariant the route relies on."""
    common = {"dynamic_context": False, "active_manifest": "manifest-z"}

    assert app_module._answer_cache_usable(safety_routed=False, **common) is True
    assert app_module._answer_cache_usable(safety_routed=True, **common) is False
    # The pre-existing guards still hold.
    assert (
        app_module._answer_cache_usable(
            safety_routed=False, dynamic_context=True, active_manifest="manifest-z"
        )
        is False
    )
    assert (
        app_module._answer_cache_usable(
            safety_routed=False, dynamic_context=False, active_manifest=""
        )
        is False
    )


def test_non_fertilizer_questions_still_use_the_cache(monkeypatch, tmp_path):
    """The exclusion is targeted: ordinary RAG questions keep their fast path."""
    cache = AnswerCache(60, db_path=str(tmp_path / "ok.sqlite3"))
    document = SimpleNamespace(
        metadata={"source": "Guide semis"},
        page_content="Semez le mil après une pluie utile.",
    )

    class Harness:
        def __init__(self):
            self.combine_documents_chain = self
            self.search_calls = 0

        def similarity_search_with_relevance_scores(self, question, k):
            self.search_calls += 1
            return [(document, 0.4)]

        def run(self, *, input_documents, question):
            return "Semez le mil après une pluie utile."

    harness = Harness()
    monkeypatch.setattr(app_module, "ANSWER_CACHE_ENABLED", True)
    monkeypatch.setattr(app_module, "answer_cache_store", cache)
    monkeypatch.setattr(app_module, "CASE_LOG_DB", str(tmp_path / "case_log.sqlite3"))
    monkeypatch.setattr(app_module, "REQUEST_COOLDOWN_SECONDS", 0)
    monkeypatch.setattr(app_module, "get_active_manifest_hash", lambda: "manifest-w")
    monkeypatch.setattr(app_module, "get_rag_chain", lambda: harness)
    monkeypatch.setattr(app_module, "_rag_db", harness)
    monkeypatch.setattr(app_module, "text_to_speech_to_static", lambda answer: "")

    client = app_module.app.test_client()
    first = client.post("/ask", data={"messageText": "Quand semer le mil ?"})
    second = client.post("/ask", data={"messageText": "Quand semer le mil ?"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert harness.search_calls == 1
    assert second.get_json()["journal"]["answer_path"] == "cache"
