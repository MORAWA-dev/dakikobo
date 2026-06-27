"""Flask route smoke tests with live services mocked out."""

from types import SimpleNamespace

import app as app_module


class _FakeRagChain:
    def invoke(self, query):
        assert query == "Quand semer le mil ?"
        return {
            "result": "Semez le mil au début de la saison des pluies.",
            "source_documents": [
                SimpleNamespace(metadata={"source": "guide_mil.pdf"}),
                SimpleNamespace(metadata={"source": "guide_mil.pdf"}),
                SimpleNamespace(metadata={"source": "calendrier.pdf"}),
            ],
        }


class _SingleSourceRagChain:
    def invoke(self, query):
        assert query == "Quand semer le mil ?"
        return {
            "result": "Semez le mil au début de la saison des pluies.",
            "source_documents": [
                SimpleNamespace(metadata={"source": "guide_mil.pdf"}),
            ],
        }


def test_app_import_does_not_initialize_rag():
    assert app_module._rag_chain is None


def test_index_route_renders():
    client = app_module.app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert response.content_type.startswith("text/html")
    assert b'data-example-id="semis_mil"' in response.data
    assert b'data-example-id="photo_mais"' in response.data
    assert b'id="credibilityToggle"' in response.data
    assert b'id="credibilityModal"' in response.data
    assert b'Sources & limites' in response.data
    assert b'id="toolsDrawer"' in response.data
    assert b'id="toolsToggle"' in response.data
    assert b'id="weatherLocation"' in response.data
    assert b'id="soilCrop"' in response.data


def test_health_route_is_lightweight():
    client = app_module.app.test_client()
    response = client.get("/healthz")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["bot"] == "DakiKobo"
    assert payload["rag_ready"] is False


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
    assert payload["confidence"] == "Fort"


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


def test_rag_route_returns_unique_sources(monkeypatch):
    client = app_module.app.test_client()
    monkeypatch.setattr(app_module, "get_rag_chain", lambda: _FakeRagChain())
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
            "title": "calendrier.pdf",
            "type": "Base locale",
            "snippet": "",
        },
        {
            "title": "guide_mil.pdf",
            "type": "Base locale",
            "snippet": "",
        },
    ]
    assert payload["confidence"] == "Fort"
    assert payload["audio_url"] == "/static/audio/rag.mp3"


def test_rag_route_marks_single_source_as_medium_confidence(monkeypatch):
    client = app_module.app.test_client()
    monkeypatch.setattr(app_module, "get_rag_chain", lambda: _SingleSourceRagChain())
    monkeypatch.setattr(
        app_module,
        "text_to_speech_to_static",
        lambda text: "/static/audio/rag.mp3",
    )

    response = client.post("/ask", data={"messageText": "Quand semer le mil ?"})
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["confidence"] == "Moyen"


def test_rag_route_handles_chain_errors(monkeypatch):
    class BrokenChain:
        def invoke(self, query):
            raise RuntimeError("boom")

    client = app_module.app.test_client()
    monkeypatch.setattr(app_module, "get_rag_chain", lambda: BrokenChain())

    response = client.post("/ask", data={"messageText": "Quand semer le mil ?"})
    payload = response.get_json()

    assert response.status_code == 200
    assert "erreur de traitement" in payload["answer"]
    assert payload["sources"] == []
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


def test_feedback_writes_csv(tmp_path, monkeypatch):
    feedback_file = tmp_path / "feedback" / "feedback.csv"
    monkeypatch.setattr(app_module, "FEEDBACK_FILE", str(feedback_file))
    client = app_module.app.test_client()

    response = client.post(
        "/feedback",
        data={"rating": "up", "question": "Q", "answer": "A"},
    )

    assert response.status_code == 200
    assert response.get_json() == {"ok": True}
    content = feedback_file.read_text(encoding="utf-8")
    assert "timestamp,rating,question,answer" in content
    assert ",up,Q,A" in content
