"""Flask route smoke tests with live services mocked out."""

import json
from pathlib import Path
import logging
from threading import Thread
from types import SimpleNamespace

import pytest

import app as app_module
from core.case_log import list_evidence, list_feedback_events, record_feedback
from core.retrieval import chunk_id, get_active_manifest_hash, manifest_hash


@pytest.fixture(autouse=True)
def _isolate_case_log(tmp_path, monkeypatch):
    """Route tests must never append synthetic rows to the developer journal."""
    monkeypatch.setattr(
        app_module,
        "CASE_LOG_DB",
        str(tmp_path / "route_case_log.sqlite3"),
    )


def _query_starts_with(query: str, expected: str) -> None:
    """Resolved queries may append culture/lieu hints after the user text."""
    assert (query or "").startswith(expected), query


class _FakeRagChain:
    def invoke(self, query):
        _query_starts_with(query, "Quand semer le mil ?")
        return {
            "result": "Semez le mil au début de la saison des pluies.",
            "source_documents": [
                SimpleNamespace(
                    metadata={"source": "guide_mil.pdf"},
                    page_content="Semez le mil au début de la saison des pluies.",
                ),
                SimpleNamespace(
                    metadata={"source": "guide_mil.pdf"},
                    page_content="Le semis du mil suit une pluie utile.",
                ),
                SimpleNamespace(
                    metadata={"source": "calendrier.pdf"},
                    page_content="Calendrier de semis du mil au Burkina Faso.",
                ),
            ],
        }


class _SingleSourceRagChain:
    def invoke(self, query):
        _query_starts_with(query, "Quand semer le mil ?")
        return {
            "result": "Semez le mil au début de la saison des pluies.",
            "source_documents": [
                SimpleNamespace(metadata={"source": "guide_mil.pdf"}),
            ],
        }


class _MetadataSourceRagChain:
    def invoke(self, query):
        _query_starts_with(query, "Quelles données FAO existent ?")
        return {
            "result": "La FAO signale AGRISurvey, FAOSTAT et CountrySTAT.",
            "source_documents": [
                SimpleNamespace(
                    metadata={
                        "source": "FAO Burkina Faso - politiques agricoles",
                        "doc_type": "scraped_web",
                        "publisher": "FAO",
                        "year": "2026",
                        "country": "Burkina Faso",
                        "review_status": "reviewed_by_codex_pending_human_review",
                        "source_url": "https://www.fao.org/in-action/mafap/where-we-work/burkina-faso/en",
                    },
                    page_content="La FAO signale AGRISurvey, FAOSTAT et CountrySTAT pour le Burkina Faso.",
                )
            ],
        }


class _NoisySourceRagChain:
    def invoke(self, query):
        _query_starts_with(query, "Comment stocker le niébé contre les bruches ?")
        return {
            "result": "Utilisez des sacs PICS avec des grains bien secs.",
            "source_documents": [
                SimpleNamespace(
                    metadata={"source": "Source faible"},
                    page_content="Contenu secondaire peu lié au niébé.",
                ),
                SimpleNamespace(
                    metadata={"source": "IITA 2018 - Production du niebe"},
                    page_content="Les sacs PICS permettent un stockage hermétique non chimique du niébé.",
                ),
                SimpleNamespace(
                    metadata={"source": "Source moyenne"},
                    page_content="Stockage et séchage des grains.",
                ),
            ],
        }


class _RefusalRagChain:
    """Returns the grounded 'I don't know' fallback with off-topic chunks."""
    def invoke(self, query):
        return {
            "result": (
                "Je ne sais pas encore. Cette information n'est pas disponible "
                "dans la base de données de DakiKobo pour le Burkina Faso."
            ),
            "source_documents": [
                SimpleNamespace(metadata={"source": "agrobusiness.pdf"}),
                SimpleNamespace(metadata={"source": "manuel.pdf"}),
            ],
        }


class _NoSourceRagChain:
    """Returns an answer even though retrieval found no documents."""
    def invoke(self, query):
        return {
            "result": "Réponse non fondée.",
            "source_documents": [],
        }


class _UncertainRagChain:
    """Returns the first-class 'Je ne peux pas confirmer' uncertainty path."""
    def invoke(self, query):
        return {
            "result": (
                "Je ne peux pas confirmer. Les documents évoquent des pratiques "
                "générales, mais le stade et la parcelle manquent. Vérifiez au "
                "champ et demandez conseil à un agent agricole."
            ),
            "source_documents": [
                SimpleNamespace(
                    metadata={"source": "guide_general.pdf"},
                    page_content="Pratiques générales de culture au Sahel.",
                ),
            ],
        }


class _RagHarness:
    """Adapt legacy test responses to the one-search RetrievalQA seam."""

    def __init__(self, legacy_chain, scores=None):
        self.legacy_chain = legacy_chain
        self.scores = scores or {}
        self.combine_documents_chain = self
        self.search_calls = []
        self.combined_docs = None
        self._response = None

    def similarity_search_with_relevance_scores(self, query, k):
        self.search_calls.append((query, k))
        self._response = self.legacy_chain.invoke(query)
        return [
            (
                doc,
                self.scores.get(
                    (getattr(doc, "metadata", {}) or {}).get("source", "Inconnu"),
                    0.4,
                ),
            )
            for doc in self._response.get("source_documents", [])
        ]

    def run(self, *, input_documents, question):
        assert self._response is not None
        expected_docs = self._response.get("source_documents", [])
        assert input_documents == [
            doc
            for doc in expected_docs
            if self.scores.get(
                (getattr(doc, "metadata", {}) or {}).get("source", "Inconnu"),
                0.4,
            )
            >= app_module.SIMILARITY_THRESHOLD
        ]
        self.combined_docs = input_documents
        return self._response["result"]


def _install_rag(monkeypatch, legacy_chain, scores=None):
    harness = _RagHarness(legacy_chain, scores=scores)
    # Route-policy tests exercise live generation; answer-cache behavior has a
    # dedicated Phase 3 integration test.
    monkeypatch.setattr(app_module, "ANSWER_CACHE_ENABLED", False)
    monkeypatch.setattr(app_module, "get_rag_chain", lambda: harness)
    monkeypatch.setattr(app_module, "_rag_db", harness)
    return harness


def test_app_import_does_not_initialize_rag():
    assert app_module._rag_chain is None


def test_index_route_renders():
    client = app_module.app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert response.content_type.startswith("text/html")
    assert b'data-example-id="semis_mil"' in response.data
    assert b'data-example-id="oaph_burkina"' in response.data
    assert b'data-example-id="cilss_sahel"' in response.data
    assert b'data-example-id="hors_sujet"' in response.data
    assert b'data-example-id="photo_mais"' in response.data
    assert b'id="credibilityToggle"' in response.data
    assert b'id="credibilityModal"' in response.data
    assert b'Sources & limites' in response.data
    assert b'id="toolsDrawer"' in response.data
    assert b'id="toolsToggle"' in response.data
    assert b'id="weatherLocation"' in response.data
    assert b'id="soilCrop"' in response.data
    assert b'id="mediaPrivacyNote"' in response.data


def test_health_route_is_lightweight():
    client = app_module.app.test_client()
    response = client.get("/healthz")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["bot"] == "DakiKobo"
    assert payload["rag_ready"] is False
    assert payload["rag_status"] in {"cold", "warming", "ready", "error"}
    assert payload["rag_warmup"]["status"] == payload["rag_status"]


def test_rag_runtime_status_does_not_wait_for_initialization_lock(monkeypatch):
    result = {}
    monkeypatch.setattr(app_module, "_rag_chain", None)
    monkeypatch.setattr(app_module, "_rag_warmup_started", True)
    monkeypatch.setattr(app_module, "_rag_warmup_error", None)

    app_module._rag_lock.acquire()
    try:
        reader = Thread(
            target=lambda: result.update(app_module._rag_runtime_status()),
            daemon=True,
        )
        reader.start()
        reader.join(timeout=0.5)
        assert not reader.is_alive(), "readiness status waited for the RAG build lock"
    finally:
        app_module._rag_lock.release()

    assert result["status"] == "warming"


def test_crop_labels_route_returns_french_crops():
    client = app_module.app.test_client()
    response = client.get("/crop-labels")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["primary_language"] == "fr"
    ids = {c["id"] for c in payload["crops"]}
    assert "mil" in ids
    assert "maïs" in ids
    assert "niébé" in ids
    assert all(c.get("fr") for c in payload["crops"])


def test_crop_labels_error_is_stable_french_and_hides_internal_detail(monkeypatch):
    monkeypatch.setattr(
        app_module,
        "load_crop_labels",
        lambda: (_ for _ in ()).throw(ValueError("internal path detail")),
    )

    response = app_module.app.test_client().get("/crop-labels")

    assert response.status_code == 500
    assert response.get_json()["error"] == (
        "Les libellés des cultures sont indisponibles pour le moment."
    )
    assert "internal" not in response.get_data(as_text=True)


def test_version_route_reports_runtime_metadata(monkeypatch):
    client = app_module.app.test_client()
    monkeypatch.setenv("APP_COMMIT_SHA", "abc123")

    response = client.get("/version")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["bot"] == "DakiKobo"
    assert payload["app_version"]
    assert payload["commit"] == "abc123"
    assert payload["rag_status"] in {"cold", "warming", "ready", "error"}
    assert payload["config"]["llm_model"]
    assert payload["config"]["embedding_model"] == "paraphrase-multilingual-MiniLM-L12-v2"
    assert payload["config"]["prefer_markdown_kb"] is True


def test_ask_route_emits_privacy_safe_structured_log(caplog):
    client = app_module.app.test_client()
    caplog.set_level(logging.INFO, logger="dakikobo")

    response = client.post("/ask", data={"messageText": "qui es-tu ?"})

    records = [record for record in caplog.records if record.name == "dakikobo"]
    payload = json.loads(records[-1].message)

    assert response.status_code == 200
    assert payload["event"] == "http_request"
    assert payload["route"] == "/ask"
    assert payload["method"] == "POST"
    assert payload["status_code"] == 200
    assert payload["feature"] == "ask"
    assert payload["intent"] == "identity"
    assert payload["model"] == "static"
    assert payload["confidence"] == "Fort"
    assert payload["source_count"] == 0
    assert isinstance(payload["latency_ms"], float)
    assert "qui es-tu" not in payload.values()
    assert "answer" not in payload
    assert "question" not in payload


def test_validation_error_log_includes_failure_type(caplog):
    client = app_module.app.test_client()
    caplog.set_level(logging.INFO, logger="dakikobo")

    response = client.post("/ask", data={})

    records = [record for record in caplog.records if record.name == "dakikobo"]
    payload = json.loads(records[-1].message)

    assert response.status_code == 400
    assert payload["route"] == "/ask"
    assert payload["status_code"] == 400
    assert payload["outcome"] == "validation_error"
    assert payload["failure_type"] == "empty_question"
    assert payload["confidence"] == "Faible"


def test_rag_warmup_starts_once(monkeypatch):
    calls = []

    class ImmediateThread:
        def __init__(self, target, args=(), daemon=False):
            self.target = target
            self.args = args
            self.daemon = daemon

        def start(self):
            self.target(*self.args)

    monkeypatch.setattr(app_module, "_rag_chain", None)
    monkeypatch.setattr(app_module, "_rag_warmup_started", False)
    monkeypatch.setattr(app_module, "_rag_warmup_started_at", None)
    monkeypatch.setattr(app_module, "_rag_warmup_finished_at", None)
    monkeypatch.setattr(app_module, "_rag_warmup_error", None)
    monkeypatch.setattr(app_module, "Thread", ImmediateThread)
    monkeypatch.setattr(app_module, "get_rag_chain", lambda: calls.append("warm"))

    assert app_module.start_rag_warmup("test") is True
    assert calls == ["warm"]
    assert app_module._rag_warmup_started is True
    assert app_module._rag_warmup_finished_at is not None

    assert app_module.start_rag_warmup("again") is False
    assert calls == ["warm"]


def test_local_knowledge_prefers_markdown(monkeypatch):
    markdown_docs = [SimpleNamespace(page_content="markdown")]

    def fail_pdf_loader(folder):
        raise AssertionError("PDF fallback should not run when Markdown exists")

    monkeypatch.setattr(app_module, "PREFER_MARKDOWN_KB", True)
    monkeypatch.setattr(app_module, "load_markdown_from_folder", lambda folder: markdown_docs)
    monkeypatch.setattr(app_module, "load_pdfs_from_folder", fail_pdf_loader)

    docs, source = app_module._load_local_knowledge_documents()

    assert docs == markdown_docs
    assert source == "Markdown"


def test_local_knowledge_falls_back_to_pdfs_when_markdown_missing(monkeypatch):
    pdf_docs = [SimpleNamespace(page_content="pdf")]

    monkeypatch.setattr(app_module, "PREFER_MARKDOWN_KB", True)
    monkeypatch.setattr(app_module, "load_markdown_from_folder", lambda folder: [])
    monkeypatch.setattr(app_module, "load_pdfs_from_folder", lambda folder: pdf_docs)

    docs, source = app_module._load_local_knowledge_documents()

    assert docs == pdf_docs
    assert source == "PDF"


def test_existing_valid_vector_store_is_reused(monkeypatch):
    db = object()

    monkeypatch.setattr(app_module, "REBUILD_VECTORSTORE", False)
    monkeypatch.setattr(app_module, "vector_store_exists", lambda: True)
    monkeypatch.setattr(app_module, "_expected_vector_store_manifest", lambda: {"files": []})
    monkeypatch.setattr(app_module, "load_vector_store_if_usable", lambda manifest: db)
    monkeypatch.setattr(
        app_module,
        "initialize_vector_store",
        lambda docs, manifest=None: (_ for _ in ()).throw(
            AssertionError("valid store should load")
        ),
    )

    assert app_module._load_or_build_vector_store() is db
    assert get_active_manifest_hash() == manifest_hash({"files": []})


def test_invalid_existing_vector_store_is_rebuilt(monkeypatch):
    calls = []
    local_docs = [SimpleNamespace(page_content="markdown")]

    monkeypatch.setattr(app_module, "REBUILD_VECTORSTORE", False)
    monkeypatch.setattr(app_module, "KNOWLEDGE_URLS", [])
    monkeypatch.setattr(app_module, "vector_store_exists", lambda: True)
    monkeypatch.setattr(app_module, "_expected_vector_store_manifest", lambda: {"files": []})
    monkeypatch.setattr(app_module, "load_vector_store_if_usable", lambda manifest: None)
    monkeypatch.setattr(app_module, "clear_vector_store", lambda: calls.append("clear"))
    monkeypatch.setattr(
        app_module,
        "_load_local_knowledge_documents",
        lambda: (local_docs, "Markdown"),
    )
    monkeypatch.setattr(
        app_module,
        "initialize_vector_store",
        lambda docs, manifest=None: {"doc_count": len(docs), "manifest": manifest},
    )

    db = app_module._load_or_build_vector_store()

    assert calls == ["clear"]
    assert db == {"doc_count": 1, "manifest": {"files": []}}
    assert get_active_manifest_hash() == manifest_hash({"files": []})


def test_rebuild_clears_existing_vector_store(monkeypatch):
    calls = []
    local_docs = [SimpleNamespace(page_content="markdown")]

    monkeypatch.setattr(app_module, "REBUILD_VECTORSTORE", True)
    monkeypatch.setattr(app_module, "KNOWLEDGE_URLS", [])
    monkeypatch.setattr(app_module, "vector_store_exists", lambda: True)
    monkeypatch.setattr(app_module, "_expected_vector_store_manifest", lambda: {"files": []})
    monkeypatch.setattr(app_module, "clear_vector_store", lambda: calls.append("clear"))
    monkeypatch.setattr(
        app_module,
        "_load_local_knowledge_documents",
        lambda: (local_docs, "Markdown"),
    )
    monkeypatch.setattr(
        app_module,
        "initialize_vector_store",
        lambda docs, manifest=None: {"doc_count": len(docs), "manifest": manifest},
    )

    db = app_module._load_or_build_vector_store()

    assert calls == ["clear"]
    assert db == {"doc_count": 1, "manifest": {"files": []}}
    assert get_active_manifest_hash() == manifest_hash({"files": []})


def test_demo_example_route_returns_text_case_card(monkeypatch):
    client = app_module.app.test_client()
    response = client.get("/examples/semis_mil")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["case"]["input_type"] == "text"
    assert payload["case"]["summary"]
    assert payload["case"]["case_title"] == "Conseil agricole"


def test_demo_example_route_returns_text_without_live_services(monkeypatch):
    client = app_module.app.test_client()
    monkeypatch.setattr(
        app_module,
        "get_rag_chain",
        lambda: (_ for _ in ()).throw(AssertionError("RAG should not run")),
    )
    monkeypatch.setattr(
        app_module,
        "text_to_speech_to_static",
        lambda text: (_ for _ in ()).throw(AssertionError("TTS should not run")),
    )

    response = client.get("/examples/semis_mil")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["kind"] == "message"
    assert payload["question"] == "Quand semer le mil ?"
    assert payload["answer"]
    assert payload["sources"][0]["type"] == "Base locale"
    assert payload["confidence"] == "Moyen"
    assert payload["audio_url"] == ""


def test_demo_example_route_returns_fertilizer_case():
    client = app_module.app.test_client()

    response = client.get("/examples/fumure_sorgho")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["kind"] == "message"
    assert "100 kg/ha de NPK" in payload["answer"]
    assert payload["sources"][0]["type"] == "Outil engrais"
    assert payload["case"]["input_type"] == "fertilizer"


def test_demo_example_oaph_uses_correct_expansion():
    client = app_module.app.test_client()
    response = client.get("/examples/oaph_burkina")
    payload = response.get_json()

    assert response.status_code == 200
    assert "Offensive Agropastorale et Halieutique" in payload["answer"]
    assert "Office des" not in payload["answer"]
    assert payload["confidence"] == "Fort"
    assert "MAERAH" in payload["sources"][0]["title"]
    assert payload["case"]["input_type"] == "text"


def test_demo_example_cilss_and_off_topic_refusal():
    client = app_module.app.test_client()

    cilss = client.get("/examples/cilss_sahel").get_json()
    assert "CILSS" in cilss["answer"] or "secheresse" in cilss["answer"].lower() or "sécheresse" in cilss["answer"].lower()
    assert cilss["sources"]
    assert cilss["case"]["input_type"] == "text"

    off = client.get("/examples/hors_sujet").get_json()
    assert off["answer_kind"] == "refusal"
    assert "ne sais pas encore" in off["answer"].lower()
    assert off.get("sources") == []
    assert "case" not in off or not off.get("case")


def test_demo_example_route_returns_image_case():
    client = app_module.app.test_client()

    response = client.get("/examples/photo_mais")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["kind"] == "case"
    assert payload["case"]["case_id"] == "demo_photo_mais"
    assert payload["case"]["crop"] == "maïs"
    assert payload["case"]["sources"][0]["type"] == "Vision"
    assert payload["confidence"] == "Moyen"


def test_demo_example_route_404s_unknown_example():
    client = app_module.app.test_client()

    response = client.get("/examples/inconnu")
    payload = response.get_json()

    assert response.status_code == 404
    assert payload["error"] == "Exemple introuvable."
    assert payload["confidence"] == "Faible"


def test_weather_locations_route_returns_burkina_choices():
    client = app_module.app.test_client()

    response = client.get("/weather/locations")
    payload = response.get_json()

    assert response.status_code == 200
    assert {"id": "ouagadougou", "name": "Ouagadougou", "latitude": 12.3714, "longitude": -1.5197} in payload["locations"]


def test_weather_route_returns_context(monkeypatch):
    client = app_module.app.test_client()
    weather_payload = {
        "location": {"id": "bobo", "name": "Bobo-Dioulasso"},
        "metrics": {"rain_7d_mm": 12.5},
        "insights": [{"label": "Pluie utile (7 jours)", "status": "watch", "text": "Surveillez."}],
        "sources": [{"title": "Open-Meteo Forecast API", "type": "Météo"}],
    }
    monkeypatch.setattr(
        app_module,
        "build_weather_context",
        lambda location: weather_payload,
    )

    response = client.get("/weather?location=bobo")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["weather"] == weather_payload
    assert payload["confidence"] == "Moyen"


def test_weather_route_rejects_unknown_location(monkeypatch):
    client = app_module.app.test_client()
    monkeypatch.setattr(
        app_module,
        "build_weather_context",
        lambda location: (_ for _ in ()).throw(ValueError("bad location")),
    )

    response = client.get("/weather?location=inconnu")
    payload = response.get_json()

    assert response.status_code == 400
    assert "localité disponible" in payload["error"]
    assert payload["confidence"] == "Faible"


def test_weather_route_handles_api_error(monkeypatch):
    client = app_module.app.test_client()
    monkeypatch.setattr(
        app_module,
        "build_weather_context",
        lambda location: (_ for _ in ()).throw(app_module.WeatherError("offline")),
    )

    response = client.get("/weather?location=bobo")
    payload = response.get_json()

    assert response.status_code == 502
    assert "météo agricole" in payload["error"]
    assert payload["confidence"] == "Faible"


def test_soil_locations_route_returns_choices():
    client = app_module.app.test_client()

    response = client.get("/soil/locations")
    payload = response.get_json()

    assert response.status_code == 200
    assert {"id": "bobo", "name": "Bobo-Dioulasso", "latitude": 11.1771, "longitude": -4.2979} in payload["locations"]
    assert {"id": "sorgho", "name": "Sorgho"} in payload["crops"]


def test_soil_route_combines_context_and_fertilizer(monkeypatch):
    client = app_module.app.test_client()
    soil_payload = {
        "location": {"id": "bobo", "name": "Bobo-Dioulasso"},
        "crop": "sorgho",
        "depth": "0-5 cm",
        "metrics": {"sand_percent": 72.0},
        "data_available": True,
        "indicators": [
            {
                "label": "Texture",
                "status": "risk",
                "value": "Tendance sableuse",
                "text": "Rétention faible.",
            }
        ],
        "disclaimer": "Test de sol requis.",
        "sources": [{"title": "SoilGrids REST API", "type": "Sol"}],
    }
    monkeypatch.setattr(
        app_module,
        "build_soil_context",
        lambda location, crop: soil_payload,
    )

    response = client.get("/soil?location=bobo&crop=sorgho")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["soil"] == soil_payload
    assert "100 kg/ha de NPK" in payload["fertilizer"]["answer"]
    assert payload["fertilizer"]["sources"][0]["type"] == "Outil engrais"
    assert payload["sources"][0]["type"] == "Sol"
    assert payload["sources"][1]["type"] == "Outil engrais"
    assert payload["confidence"] == "Moyen"


def test_soil_route_marks_missing_metrics_low_confidence(monkeypatch):
    client = app_module.app.test_client()
    soil_payload = {
        "location": {"id": "ouagadougou", "name": "Ouagadougou"},
        "crop": "maïs",
        "depth": "0-5 cm",
        "metrics": {
            "clay_percent": None,
            "sand_percent": None,
            "soc_percent": None,
            "ph_h2o": None,
            "cec_cmol_kg": None,
        },
        "data_available": False,
        "indicators": [
            {
                "label": "Rétention des nutriments",
                "status": "watch",
                "value": "Non disponible",
                "text": "Impossible d'estimer la rétention.",
            }
        ],
        "disclaimer": "Test de sol requis.",
        "sources": [{"title": "SoilGrids REST API", "type": "Sol"}],
    }
    monkeypatch.setattr(
        app_module,
        "build_soil_context",
        lambda location, crop: soil_payload,
    )

    response = client.get("/soil?location=ouagadougou&crop=maïs")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["soil"]["data_available"] is False
    assert payload["confidence"] == "Faible"
    assert payload["soil"]["indicators"][0]["value"] == "Non disponible"


def test_soil_route_rejects_unknown_selection(monkeypatch):
    client = app_module.app.test_client()
    monkeypatch.setattr(
        app_module,
        "build_soil_context",
        lambda location, crop: (_ for _ in ()).throw(ValueError("bad selection")),
    )

    response = client.get("/soil?location=inconnu&crop=coton")
    payload = response.get_json()

    assert response.status_code == 400
    assert "localité et une culture disponibles" in payload["error"]
    assert payload["confidence"] == "Faible"


def test_soil_route_handles_api_error(monkeypatch):
    client = app_module.app.test_client()
    monkeypatch.setattr(
        app_module,
        "build_soil_context",
        lambda location, crop: (_ for _ in ()).throw(app_module.SoilError("offline")),
    )

    response = client.get("/soil?location=bobo&crop=sorgho")
    payload = response.get_json()

    assert response.status_code == 502
    assert "contexte sol" in payload["error"]
    assert payload["confidence"] == "Faible"


def test_ask_rejects_oversized_question(monkeypatch):
    client = app_module.app.test_client()
    monkeypatch.setattr(app_module, "MAX_QUESTION_CHARS", 20)
    monkeypatch.setattr(app_module, "get_rag_chain", lambda: None)

    response = client.post(
        "/ask",
        data={"messageText": "a" * 25},
    )
    payload = response.get_json()

    assert response.status_code == 400
    assert "trop longue" in payload["answer"].lower()
    assert payload["confidence"] == "Faible"


def test_ask_requires_message_text():
    client = app_module.app.test_client()
    response = client.post("/ask", data={})
    payload = response.get_json()
    assert response.status_code == 400
    assert "question agricole" in payload["answer"]
    assert payload["confidence"] == "Faible"


def test_identity_answer_is_static_and_french():
    client = app_module.app.test_client()
    response = client.post("/ask", data={"messageText": "qui es-tu ?"})
    payload = response.get_json()
    assert response.status_code == 200
    assert "Je suis DakiKobo" in payload["answer"]
    assert payload["sources"] == []
    assert payload["confidence"] == "Fort"


def test_ask_rate_limit_returns_french_error(monkeypatch):
    client = app_module.app.test_client()
    monkeypatch.setattr(app_module, "REQUEST_COOLDOWN_SECONDS", 10)

    first = client.post("/ask", data={"messageText": "qui es-tu ?"})
    second = client.post("/ask", data={"messageText": "qui es-tu ?"})
    payload = second.get_json()

    assert first.status_code == 200
    assert second.status_code == 429
    assert "Veuillez patienter" in payload["error"]
    assert payload["retry_after"] > 0
    assert payload["confidence"] == "Faible"


def test_fertilizer_route_uses_tool_not_rag(monkeypatch):
    client = app_module.app.test_client()
    monkeypatch.setattr(app_module, "get_rag_chain", lambda: None)
    monkeypatch.setattr(
        app_module,
        "text_to_speech_to_static",
        lambda text: "/static/audio/fertilizer.mp3",
    )

    response = client.post(
        "/ask", data={"messageText": "dose d'engrais pour le sorgho"}
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert "100 kg/ha de NPK" in payload["answer"]
    assert payload["sources"][0]["type"] == "Outil engrais"
    assert payload["confidence"] == "Fort"
    assert payload["audio_url"] == "/static/audio/fertilizer.mp3"
    assert payload["case"]["input_type"] == "fertilizer"
    assert payload["case"]["crop"] == "sorgho"
    assert payload["case"]["actions"]
    assert payload["case"]["do_not"]


def test_fertilizer_route_uses_form_crop_when_text_omits_crop(monkeypatch):
    client = app_module.app.test_client()
    monkeypatch.setattr(app_module, "get_rag_chain", lambda: None)
    monkeypatch.setattr(app_module, "text_to_speech_to_static", lambda text: "")

    response = client.post(
        "/ask",
        data={
            "messageText": "quelle dose d'engrais utiliser ?",
            "crop": "mil",
            "growth_stage": "croissance végétative",
            "location": "Dori",
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert "100 kg/ha de NPK" in payload["answer"]
    assert payload["case"]["crop"] == "mil"
    assert payload["case"]["growth_stage"] == "croissance végétative"
    assert payload["case"]["location"] == "Dori"


def test_ask_enriches_case_with_weather_when_location_known(monkeypatch):
    client = app_module.app.test_client()
    monkeypatch.setattr(app_module, "get_rag_chain", lambda: None)
    monkeypatch.setattr(app_module, "text_to_speech_to_static", lambda text: "")
    monkeypatch.setattr(
        app_module,
        "build_weather_context",
        lambda location_id: {
            "location": {"id": location_id, "name": "Kaya"},
            "insights": [
                {
                    "label": "Pluie utile (7 jours)",
                    "status": "watch",
                    "text": "12.0 mm récents : surveillez l'humidité.",
                }
            ],
            "sources": [{"title": "Open-Meteo", "type": "Météo", "snippet": "x"}],
        },
    )

    response = client.post(
        "/ask",
        data={
            "messageText": "dose d'engrais pour le sorgho",
            "location": "Kaya",
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["case"]["weather_signals"]
    assert "Pluie utile" in payload["case"]["weather_signals"][0]
    assert payload["weather"]["location"]["id"] == "kaya"


def test_rag_route_returns_unique_sources(monkeypatch):
    client = app_module.app.test_client()
    _install_rag(monkeypatch, _FakeRagChain())
    monkeypatch.setattr(
        app_module,
        "text_to_speech_to_static",
        lambda text: "/static/audio/rag.mp3",
    )

    response = client.post("/ask", data={"messageText": "Quand semer le mil ?"})
    payload = response.get_json()

    assert response.status_code == 200
    assert "saison des pluies" in payload["answer"]
    assert payload["sources"] == [
        {
            "title": "guide_mil.pdf",
            "type": "Base locale",
            "snippet": "Semez le mil au début de la saison des pluies.",
        },
        {
            "title": "calendrier.pdf",
            "type": "Base locale",
            "snippet": "Calendrier de semis du mil au Burkina Faso.",
        },
    ]
    assert payload["confidence"] == "Fort"
    assert payload["audio_url"] == "/static/audio/rag.mp3"
    assert payload["case"]["input_type"] == "text"
    assert payload["case"]["case_title"] == "Conseil agricole"
    assert payload["case"]["summary"]
    assert payload["case"]["needs_human_confirmation"] is True


def test_rag_ledger_links_to_feedback_in_two_steps(tmp_path, monkeypatch):
    case_log = tmp_path / "case_log.sqlite3"
    monkeypatch.setattr(app_module, "CASE_LOG_DB", str(case_log))
    _install_rag(monkeypatch, _FakeRagChain())
    monkeypatch.setattr(app_module, "text_to_speech_to_static", lambda text: "")
    client = app_module.app.test_client()

    asked = client.post(
        "/ask",
        data={
            "messageText": "Quand semer le mil ?",
            "crop": "mil",
            "location": "kaya",
        },
    )
    payload = asked.get_json()
    assert asked.status_code == 200
    assert payload["journal"]["answer_path"] == "rag"
    assert payload["journal"]["crop_id"] == "mil"
    assert payload["journal"]["place_id"] == "kaya"
    assert payload["journal"]["ledger_created_at"] is not None
    assert all(row["feedback_id"] is None for row in list_evidence(str(case_log)))

    feedback_data = {
        "rating": "up",
        "question": "Quand semer le mil ?",
        "answer": payload["answer"],
        **payload["journal"],
    }
    feedback_response = client.post("/feedback", data=feedback_data)
    feedback_id = feedback_response.get_json()["feedback_id"]

    linked = list_evidence(str(case_log), feedback_id=feedback_id)
    assert len(linked) == 3
    assert all(row["question_hash"] != "Quand semer le mil ?" for row in linked)
    journal_row = list_feedback_events(str(case_log))[0]
    assert journal_row["answer_path"] == "rag"
    assert journal_row["crop_id"] == "mil"
    assert journal_row["place_id"] == "kaya"


def test_evidence_write_failure_never_blocks_answer(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "CASE_LOG_DB", str(tmp_path / "case_log.sqlite3"))
    _install_rag(monkeypatch, _FakeRagChain())
    monkeypatch.setattr(app_module, "text_to_speech_to_static", lambda text: "")
    monkeypatch.setattr(
        app_module,
        "record_evidence",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("disk full")),
    )

    response = app_module.app.test_client().post(
        "/ask",
        data={"messageText": "Quand semer le mil ?"},
    )
    assert response.status_code == 200
    assert "saison des pluies" in response.get_json()["answer"]
    assert response.get_json()["journal"]["ledger_created_at"] is None


def test_rag_route_attaches_field_context_to_case(monkeypatch):
    client = app_module.app.test_client()
    seen = {}

    class _CtxChain:
        def invoke(self, query):
            seen["query"] = query
            return {
                "result": "Semez le mil au début de la saison des pluies.",
                "source_documents": [
                    SimpleNamespace(metadata={"source": "guide_mil.pdf"}),
                ],
            }

    _install_rag(monkeypatch, _CtxChain())
    monkeypatch.setattr(app_module, "text_to_speech_to_static", lambda text: "")

    response = client.post(
        "/ask",
        data={
            "messageText": "Quand semer le mil ?",
            "crop": "mil",
            "growth_stage": "levée / jeune plant",
            "location": "Ouahigouya",
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert "Contexte utile" in seen["query"] or "culture: mil" in seen["query"]
    assert "culture: mil" in seen["query"]
    assert payload["case"]["crop"] == "mil"
    assert payload["case"]["growth_stage"] == "levée / jeune plant"
    assert payload["case"]["location"] == "Ouahigouya"


def test_rag_route_marks_single_source_as_medium_confidence(monkeypatch):
    client = app_module.app.test_client()
    _install_rag(
        monkeypatch,
        _SingleSourceRagChain(),
        scores={"guide_mil.pdf": 0.3},
    )
    monkeypatch.setattr(
        app_module,
        "text_to_speech_to_static",
        lambda text: "/static/audio/rag.mp3",
    )

    response = client.post("/ask", data={"messageText": "Quand semer le mil ?"})
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["confidence"] == "Moyen"


def test_rag_route_exposes_source_metadata(monkeypatch):
    client = app_module.app.test_client()
    _install_rag(monkeypatch, _MetadataSourceRagChain())
    monkeypatch.setattr(
        app_module,
        "text_to_speech_to_static",
        lambda text: "/static/audio/rag.mp3",
    )

    response = client.post(
        "/ask",
        data={"messageText": "Quelles données FAO existent ?"},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["sources"] == [
        {
            "title": "FAO Burkina Faso - politiques agricoles",
            "type": "Source web revue",
            "snippet": (
                "La FAO signale AGRISurvey, FAOSTAT et CountrySTAT "
                "pour le Burkina Faso."
            ),
            "publisher": "FAO",
            "year": "2026",
            "country": "Burkina Faso",
            "review_status": "Revu, validation humaine à finaliser",
            "url": "https://www.fao.org/in-action/mafap/where-we-work/burkina-faso/en",
        }
    ]


def test_rag_route_filters_and_ranks_sources_by_relevance_score(monkeypatch):
    client = app_module.app.test_client()

    scores = {
        "IITA 2018 - Production du niebe": 0.43,
        "Source moyenne": 0.35,
        "Source faible": 0.18,
    }
    harness = _install_rag(monkeypatch, _NoisySourceRagChain(), scores=scores)
    grounded_result = {}
    real_grounded_answer = app_module.GroundedAnswer

    def capture_grounded_answer(**kwargs):
        grounded_result.update(kwargs)
        return real_grounded_answer(**kwargs)

    monkeypatch.setattr(app_module, "GroundedAnswer", capture_grounded_answer)
    monkeypatch.setattr(
        app_module,
        "text_to_speech_to_static",
        lambda text: "/static/audio/rag.mp3",
    )

    response = client.post(
        "/ask",
        data={"messageText": "Comment stocker le niébé contre les bruches ?"},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert len(harness.search_calls) == 1
    retrieval_query, k = harness.search_calls[0]
    _query_starts_with(
        retrieval_query,
        "Comment stocker le niébé contre les bruches ?",
    )
    assert k == 6
    assert [doc.metadata["source"] for doc in harness.combined_docs] == [
        "IITA 2018 - Production du niebe",
        "Source moyenne",
    ]
    assert grounded_result["retrieved_chunk_ids"] == [
        chunk_id(doc.metadata["source"], doc.page_content)
        for doc in harness._response["source_documents"]
    ]
    assert len(grounded_result["retrieved_chunk_ids"]) == 3
    assert payload["confidence"] == "Fort"
    titles = [source["title"] for source in payload["sources"]]
    assert titles == ["IITA 2018 - Production du niebe"]
    assert "Source moyenne" not in titles
    assert "Source faible" not in titles


def test_rag_route_refusal_has_no_sources_and_low_confidence(monkeypatch):
    client = app_module.app.test_client()
    _install_rag(monkeypatch, _RefusalRagChain())
    monkeypatch.setattr(
        app_module, "text_to_speech_to_static", lambda text: ""
    )

    response = client.post("/ask", data={"messageText": "comment cultiver le riz ?"})
    payload = response.get_json()

    assert response.status_code == 200
    assert "ne sais pas encore" in payload["answer"]
    assert payload["sources"] == []
    assert payload["confidence"] == "Faible"
    assert "case" not in payload
    assert payload.get("answer_kind") == "refusal"


def test_rag_route_question_crop_overrides_form_crop(monkeypatch):
    """Stale form crop=sorgho must not hijack a soja question."""
    client = app_module.app.test_client()
    seen = {}

    class _SojaChain:
        def invoke(self, query):
            seen["query"] = query
            return {
                "result": (
                    "Pour le soja à Mogtédo, préférez un sol bien drainé. "
                    "Semez après une pluie utile et confirmez avec un agent."
                ),
                "source_documents": [
                    SimpleNamespace(
                        metadata={"source": "guide_legumineuses.pdf"},
                        page_content="Le soja préfère des sols drainés au Burkina.",
                    ),
                ],
            }

    _install_rag(
        monkeypatch,
        _SojaChain(),
        scores={"guide_legumineuses.pdf": 0.42},
    )
    monkeypatch.setattr(app_module, "text_to_speech_to_static", lambda text: "")

    response = client.post(
        "/ask",
        data={
            "messageText": "comment bien semer le soja dans la ville de Mogtedo",
            "crop": "sorgho",
            "growth_stage": "levée / jeune plant",
            "location": "Ouagadougou",
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert "soja" in seen["query"].lower()
    assert "culture: soja" in seen["query"]
    assert "culture: sorgho" not in seen["query"]
    assert payload["case"]["crop"] == "soja"
    assert payload["case"]["location"] == "Mogtédo"
    assert payload["case"]["growth_stage"] == ""
    assert "sorgho" not in payload["answer"].lower()


def test_rag_route_short_followup_keeps_prior_crop(monkeypatch):
    client = app_module.app.test_client()
    seen = {}

    class _FollowChain:
        def invoke(self, query):
            seen["query"] = query
            return {
                "result": "Pour le soja à Ouagadougou, préparez le sol et attendez une pluie utile.",
                "source_documents": [
                    SimpleNamespace(
                        metadata={"source": "guide_soja.pdf"},
                        page_content="Semis du soja en zone urbaine periurbaine.",
                    ),
                ],
            }

    _install_rag(
        monkeypatch,
        _FollowChain(),
        scores={"guide_soja.pdf": 0.4},
    )
    monkeypatch.setattr(app_module, "text_to_speech_to_static", lambda text: "")

    response = client.post(
        "/ask",
        data={
            "messageText": "ok a ouagadougou",
            "crop": "sorgho",
            "growth_stage": "levée / jeune plant",
            "location": "Ouagadougou",
            "prior_question": "comment bien semer le soja dans la ville de Mogtedo",
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert "soja" in seen["query"].lower()
    assert "Précision" in seen["query"]
    assert payload["case"]["crop"] == "soja"
    assert payload["case"]["location"] == "Ouagadougou"
    assert "plants de sorgho" not in payload["answer"].lower()


def test_rag_route_uncertain_is_first_class_not_failure(monkeypatch):
    client = app_module.app.test_client()
    _install_rag(
        monkeypatch,
        _UncertainRagChain(),
        scores={"guide_general.pdf": 0.4},
    )
    monkeypatch.setattr(app_module, "text_to_speech_to_static", lambda text: "")

    response = client.post(
        "/ask",
        data={"messageText": "Quelle maladie exacte touche mon sorgho ?"},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert "je ne peux pas confirmer" in payload["answer"].lower()
    assert payload["confidence"] == "Faible"
    assert payload["answer_kind"] == "uncertain"
    assert payload["case"]["risk_level"] == "Non confirmé"
    assert payload["case"]["needs_human_confirmation"] is True
    assert payload["case"]["confirmation"]


def test_rag_route_without_retrieved_docs_forces_refusal(monkeypatch):
    client = app_module.app.test_client()
    _install_rag(monkeypatch, _NoSourceRagChain())
    monkeypatch.setattr(
        app_module, "text_to_speech_to_static", lambda text: ""
    )

    response = client.post("/ask", data={"messageText": "Quand semer le mil ?"})
    payload = response.get_json()

    assert response.status_code == 200
    assert "Je ne sais pas encore" in payload["answer"]
    assert payload["sources"] == []
    assert payload["confidence"] == "Faible"


def test_rag_route_handles_chain_errors(monkeypatch):
    class BrokenChain:
        def invoke(self, query):
            raise RuntimeError("boom")

    client = app_module.app.test_client()
    _install_rag(monkeypatch, BrokenChain())

    response = client.post("/ask", data={"messageText": "Quand semer le mil ?"})
    payload = response.get_json()

    assert response.status_code == 200
    assert "erreur de traitement" in payload["answer"]
    assert payload["sources"] == []
    assert payload["confidence"] == "Faible"


def test_speech_route_reports_unconfigured_service(monkeypatch):
    client = app_module.app.test_client()
    monkeypatch.setattr(app_module, "speech_configured", lambda: False)

    response = client.post(
        "/speech",
        data={"audio": (__import__("io").BytesIO(b"audio"), "question.webm")},
        content_type="multipart/form-data",
    )
    payload = response.get_json()

    assert response.status_code == 503
    assert "dictée vocale" in payload["error"]
    assert payload["confidence"] == "Faible"


def test_speech_route_requires_audio(monkeypatch):
    client = app_module.app.test_client()
    monkeypatch.setattr(app_module, "speech_configured", lambda: True)

    response = client.post("/speech", data={})
    payload = response.get_json()

    assert response.status_code == 400
    assert "Aucun enregistrement audio" in payload["error"]
    assert payload["confidence"] == "Faible"


def test_speech_route_transcribes_audio(monkeypatch):
    client = app_module.app.test_client()
    calls = []

    monkeypatch.setattr(app_module, "speech_configured", lambda: True)
    monkeypatch.setattr(app_module, "VOICE_COOLDOWN_SECONDS", 0)

    def fake_transcribe(audio_bytes, *, filename, mime_type):
        calls.append((audio_bytes, filename, mime_type))
        return "Quand semer le mil ?"

    monkeypatch.setattr(app_module, "transcribe_audio", fake_transcribe)

    response = client.post(
        "/speech",
        data={
            "audio": (
                __import__("io").BytesIO(b"fake audio"),
                "question.webm",
                "audio/webm",
            )
        },
        content_type="multipart/form-data",
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["text"] == "Quand semer le mil ?"
    assert payload["confidence"] == "Moyen"
    assert calls == [(b"fake audio", "question.webm", "audio/webm")]


def test_speech_route_rejects_empty_audio(monkeypatch):
    client = app_module.app.test_client()
    monkeypatch.setattr(app_module, "speech_configured", lambda: True)

    response = client.post(
        "/speech",
        data={"audio": (__import__("io").BytesIO(b""), "question.webm")},
        content_type="multipart/form-data",
    )
    payload = response.get_json()

    assert response.status_code == 400
    assert "vide" in payload["error"]
    assert payload["confidence"] == "Faible"


def test_speech_route_rejects_large_audio(monkeypatch):
    client = app_module.app.test_client()
    monkeypatch.setattr(app_module, "speech_configured", lambda: True)
    monkeypatch.setitem(app_module.app.config, "MAX_AUDIO_UPLOAD_BYTES", 4)
    monkeypatch.setitem(app_module.app.config, "MAX_AUDIO_UPLOAD_MB", 0.001)

    response = client.post(
        "/speech",
        data={"audio": (__import__("io").BytesIO(b"too large"), "question.webm")},
        content_type="multipart/form-data",
    )
    payload = response.get_json()

    assert response.status_code == 413
    assert "audio est trop lourd" in payload["error"]
    assert payload["confidence"] == "Faible"


def test_speech_route_handles_transcription_failure(monkeypatch):
    client = app_module.app.test_client()
    monkeypatch.setattr(app_module, "speech_configured", lambda: True)
    monkeypatch.setattr(app_module, "VOICE_COOLDOWN_SECONDS", 0)

    def fail_transcribe(audio_bytes, *, filename, mime_type):
        raise app_module.SpeechTranscriptionError("boom")

    monkeypatch.setattr(app_module, "transcribe_audio", fail_transcribe)

    response = client.post(
        "/speech",
        data={"audio": (__import__("io").BytesIO(b"fake audio"), "question.webm")},
        content_type="multipart/form-data",
    )
    payload = response.get_json()

    assert response.status_code == 502
    assert "dictée vocale a échoué" in payload["error"]
    assert payload["confidence"] == "Faible"


def test_screen_reports_unconfigured_service(monkeypatch):
    client = app_module.app.test_client()
    monkeypatch.setattr(app_module, "disease_configured", lambda: False)

    response = client.post("/screen", data={})
    payload = response.get_json()

    assert response.status_code == 200
    assert "clé Gemini non configurée" in payload["answer"]
    assert payload["confidence"] == "Faible"


def test_screen_requires_image_when_configured(monkeypatch):
    client = app_module.app.test_client()
    monkeypatch.setattr(app_module, "disease_configured", lambda: True)

    response = client.post("/screen", data={})
    payload = response.get_json()

    assert response.status_code == 400
    assert "Aucune image" in payload["error"]
    assert payload["confidence"] == "Faible"


def test_screen_returns_structured_case(monkeypatch):
    client = app_module.app.test_client()
    monkeypatch.setattr(app_module, "disease_configured", lambda: True)
    monkeypatch.setattr(
        app_module,
        "screen_leaf_image",
        lambda image_bytes, mime_type, **context: {
            "answer": "Observation prudente.",
            "case": {
                "case_id": "case_test",
                "input_type": "image",
                "crop": context["crop"],
                "growth_stage": context["growth_stage"],
                "location": context["location"],
                "observations": ["Taches visibles."],
                "possible_causes": ["Maladie possible."],
                "actions": ["Surveillez la parcelle."],
                "confidence": "Moyen",
                "risk_level": "À vérifier",
                "disclaimer": "Ceci n'est pas un diagnostic.",
                "sources": [{"title": "Gemini Vision", "type": "Vision"}],
            },
        },
    )
    monkeypatch.setattr(app_module, "text_to_speech_to_static", lambda text: "")

    response = client.post(
        "/screen",
        data={
            "image": (__import__("io").BytesIO(b"fake"), "leaf.jpg"),
            "crop": "maïs",
            "growth_stage": "fructification / épi",
            "location": "Bobo-Dioulasso",
        },
        content_type="multipart/form-data",
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["answer"] == "Observation prudente."
    assert payload["case"]["case_id"] == "case_test"
    assert payload["case"]["crop"] == "maïs"
    assert payload["case"]["growth_stage"] == "fructification / épi"
    assert payload["case"]["location"] == "Bobo-Dioulasso"
    assert payload["case"]["observations"] == ["Taches visibles."]
    assert payload["case"]["confidence"] == "Moyen"
    assert payload["confidence"] == "Moyen"


def test_screen_without_context_marks_confidence_low(monkeypatch):
    client = app_module.app.test_client()
    monkeypatch.setattr(app_module, "disease_configured", lambda: True)
    monkeypatch.setattr(
        app_module,
        "screen_leaf_image",
        lambda image_bytes, mime_type, **context: {
            "answer": "Observation prudente.",
            "case": {
                "case_id": "case_test",
                "input_type": "image",
                "observations": ["Taches visibles."],
                "possible_causes": ["Maladie possible."],
                "actions": ["Surveillez la parcelle."],
                "confidence": "Moyen",
                "risk_level": "À vérifier",
                "disclaimer": "Ceci n'est pas un diagnostic.",
            },
        },
    )
    monkeypatch.setattr(app_module, "text_to_speech_to_static", lambda text: "")

    response = client.post(
        "/screen",
        data={"image": (__import__("io").BytesIO(b"fake"), "leaf.jpg")},
        content_type="multipart/form-data",
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["case"]["confidence"] == "Faible"
    assert payload["confidence"] == "Faible"


def test_screen_rate_limit_returns_french_error(monkeypatch):
    client = app_module.app.test_client()
    monkeypatch.setattr(app_module, "disease_configured", lambda: True)
    monkeypatch.setattr(app_module, "IMAGE_COOLDOWN_SECONDS", 10)
    monkeypatch.setattr(
        app_module,
        "screen_leaf_image",
        lambda image_bytes, mime_type, **context: {
            "answer": "Observation prudente.",
            "case": {
                "case_id": "case_test",
                "input_type": "image",
                "observations": ["Taches visibles."],
                "possible_causes": ["Maladie possible."],
                "actions": ["Surveillez la parcelle."],
                "confidence": "Moyen",
            },
        },
    )
    monkeypatch.setattr(app_module, "text_to_speech_to_static", lambda text: "")

    first = client.post(
        "/screen",
        data={"image": (__import__("io").BytesIO(b"fake"), "leaf.jpg")},
        content_type="multipart/form-data",
    )
    second = client.post(
        "/screen",
        data={"image": (__import__("io").BytesIO(b"fake"), "leaf.jpg")},
        content_type="multipart/form-data",
    )
    payload = second.get_json()

    assert first.status_code == 200
    assert second.status_code == 429
    assert "Veuillez patienter" in payload["error"]
    assert payload["retry_after"] > 0
    assert payload["confidence"] == "Faible"


def test_screen_rejects_large_upload(monkeypatch):
    client = app_module.app.test_client()
    monkeypatch.setattr(app_module, "disease_configured", lambda: True)
    monkeypatch.setitem(app_module.app.config, "MAX_CONTENT_LENGTH", 512)
    monkeypatch.setitem(app_module.app.config, "MAX_IMAGE_UPLOAD_BYTES", 128)
    monkeypatch.setitem(app_module.app.config, "MAX_IMAGE_UPLOAD_MB", 0.001)

    response = client.post(
        "/screen",
        data={"image": (__import__("io").BytesIO(b"x" * 256), "leaf.jpg")},
        content_type="multipart/form-data",
    )
    payload = response.get_json()

    assert response.status_code == 413
    assert "trop lourd" in payload["error"]
    assert "Mo maximum" in payload["error"]
    assert payload["confidence"] == "Faible"


def test_feedback_writes_sqlite_case_log(tmp_path, monkeypatch):
    case_log = tmp_path / "feedback" / "case_log.sqlite3"
    monkeypatch.setattr(app_module, "CASE_LOG_DB", str(case_log))
    client = app_module.app.test_client()

    response = client.post(
        "/feedback",
        data={"rating": "up", "question": "Q", "answer": "A"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["feedback_id"] == 1
    rows = list_feedback_events(str(case_log))
    assert len(rows) == 1
    assert rows[0]["rating"] == "up"
    assert rows[0]["question"] == "Q"
    assert rows[0]["answer"] == "A"


def test_feedback_validation_error_is_in_french():
    response = app_module.app.test_client().post(
        "/feedback",
        data={"rating": "maybe", "question": "Q", "answer": "A"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == (
        "L’évaluation doit être positive ou négative."
    )


def test_journal_due_route_returns_only_due_metadata(tmp_path, monkeypatch):
    case_log = str(tmp_path / "case_log.sqlite3")
    monkeypatch.setattr(app_module, "CASE_LOG_DB", case_log)
    record_feedback(
        case_log,
        rating="down",
        question="Question privée",
        answer="Réponse privée",
        crop_id="mil",
        answer_path="rag",
        follow_up_due_at=1.0,
    )

    response = app_module.app.test_client().get("/journal/due")
    payload = response.get_json()
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert payload["count"] == 1
    assert payload["due"][0]["crop_id"] == "mil"
    assert "question" not in payload["due"][0]
    assert "answer" not in payload["due"][0]


def test_feedback_outcome_route_updates_row(tmp_path, monkeypatch):
    case_log = tmp_path / "outcome" / "case_log.sqlite3"
    monkeypatch.setattr(app_module, "CASE_LOG_DB", str(case_log))
    client = app_module.app.test_client()

    fb = client.post(
        "/feedback",
        data={"rating": "down", "question": "Q", "answer": "A"},
    )
    feedback_id = fb.get_json()["feedback_id"]

    response = client.post(
        "/feedback/outcome",
        data={"feedback_id": feedback_id, "outcome": "applied_improved"},
    )

    assert response.status_code == 200
    assert response.get_json()["ok"] is True
    rows = list_feedback_events(str(case_log))
    assert rows[0]["outcome"] == "applied_improved"
    assert rows[0]["outcome_at"] is not None


def test_feedback_outcome_rejects_invalid_outcome(tmp_path, monkeypatch):
    case_log = tmp_path / "outcome" / "case_log.sqlite3"
    monkeypatch.setattr(app_module, "CASE_LOG_DB", str(case_log))
    client = app_module.app.test_client()

    fb = client.post(
        "/feedback",
        data={"rating": "up", "question": "Q", "answer": "A"},
    )
    feedback_id = fb.get_json()["feedback_id"]

    response = client.post(
        "/feedback/outcome",
        data={"feedback_id": feedback_id, "outcome": "maybe_later"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Le résultat de suivi est invalide."


def test_feedback_outcome_returns_404_for_missing_id(tmp_path, monkeypatch):
    case_log = tmp_path / "outcome" / "case_log.sqlite3"
    monkeypatch.setattr(app_module, "CASE_LOG_DB", str(case_log))
    client = app_module.app.test_client()

    response = client.post(
        "/feedback/outcome",
        data={"feedback_id": 9999, "outcome": "not_applied"},
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "L’évaluation demandée est introuvable."



def test_feedback_outcome_stores_after_image(tmp_path, monkeypatch):
    case_log = tmp_path / "case_log.sqlite3"
    img_dir = tmp_path / "feedback_images"
    monkeypatch.setattr(app_module, "CASE_LOG_DB", str(case_log))
    monkeypatch.setattr(app_module, "FEEDBACK_IMAGES", str(img_dir))
    client = app_module.app.test_client()

    created = client.post(
        "/feedback",
        data={"rating": "up", "question": "Q", "answer": "A"},
    )
    feedback_id = created.get_json()["feedback_id"]

    response = client.post(
        "/feedback/outcome",
        data={
            "feedback_id": str(feedback_id),
            "outcome": "applied_improved",
            "after_image": (__import__("io").BytesIO(b"fakepng"), "after.jpg"),
        },
        content_type="multipart/form-data",
    )
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["after_image_ref"]
    rows = list_feedback_events(str(case_log))
    assert rows[0]["after_image_ref"]
    assert Path(rows[0]["after_image_ref"]).is_file()
