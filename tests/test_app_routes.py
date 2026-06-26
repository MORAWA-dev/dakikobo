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


def test_app_import_does_not_initialize_rag():
    assert app_module._rag_chain is None


def test_index_route_renders():
    client = app_module.app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert response.content_type.startswith("text/html")


def test_health_route_is_lightweight():
    client = app_module.app.test_client()
    response = client.get("/healthz")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["bot"] == "DakiKobo"
    assert payload["rag_ready"] is False


def test_ask_requires_message_text():
    client = app_module.app.test_client()
    response = client.post("/ask", data={})
    payload = response.get_json()
    assert response.status_code == 400
    assert "question agricole" in payload["answer"]


def test_identity_answer_is_static_and_french():
    client = app_module.app.test_client()
    response = client.post("/ask", data={"messageText": "qui es-tu ?"})
    payload = response.get_json()
    assert response.status_code == 200
    assert "Je suis DakiKobo" in payload["answer"]
    assert payload["sources"] == []


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
    assert payload["sources"]
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
    assert payload["sources"] == ["calendrier.pdf", "guide_mil.pdf"]
    assert payload["audio_url"] == "/static/audio/rag.mp3"


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


def test_screen_reports_unconfigured_service(monkeypatch):
    client = app_module.app.test_client()
    monkeypatch.setattr(app_module, "disease_configured", lambda: False)

    response = client.post("/screen", data={})
    payload = response.get_json()

    assert response.status_code == 200
    assert "clé Gemini non configurée" in payload["answer"]


def test_screen_requires_image_when_configured(monkeypatch):
    client = app_module.app.test_client()
    monkeypatch.setattr(app_module, "disease_configured", lambda: True)

    response = client.post("/screen", data={})
    payload = response.get_json()

    assert response.status_code == 400
    assert "Aucune image" in payload["error"]


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
