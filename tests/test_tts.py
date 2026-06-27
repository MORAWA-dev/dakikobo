"""Tests for TTS generation behavior without live gTTS calls."""

from pathlib import Path

import app as app_module
from core import rag_pipeline


def test_tts_passes_timeout_and_returns_static_url(tmp_path, monkeypatch):
    calls = {}

    class FakeGTTS:
        def __init__(self, text, lang, timeout):
            calls["text"] = text
            calls["lang"] = lang
            calls["timeout"] = timeout

        def save(self, output_path):
            Path(output_path).write_bytes(b"fake mp3")

    monkeypatch.setattr(rag_pipeline.gtts, "gTTS", FakeGTTS)
    monkeypatch.setattr(rag_pipeline, "AUDIO_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(rag_pipeline, "TTS_TIMEOUT_SECONDS", 3.5)

    with app_module.app.test_request_context("/"):
        audio_url = rag_pipeline.text_to_speech_to_static("Bonjour les producteurs.")

    assert audio_url.startswith("/static/audio/")
    assert audio_url.endswith(".mp3")
    assert calls == {
        "text": "Bonjour les producteurs.",
        "lang": "fr",
        "timeout": 3.5,
    }
    assert list(tmp_path.glob("*.mp3"))


def test_tts_failure_returns_empty_audio_url(tmp_path, monkeypatch):
    class FailingGTTS:
        def __init__(self, text, lang, timeout):
            pass

        def save(self, output_path):
            raise TimeoutError("gTTS took too long")

    monkeypatch.setattr(rag_pipeline.gtts, "gTTS", FailingGTTS)
    monkeypatch.setattr(rag_pipeline, "AUDIO_OUTPUT_DIR", str(tmp_path))

    with app_module.app.test_request_context("/"):
        audio_url = rag_pipeline.text_to_speech_to_static("Bonjour.")

    assert audio_url == ""
    assert list(tmp_path.glob("*.mp3")) == []


def test_tts_truncation_prefers_sentence_boundary():
    text = "Première phrase. Deuxième phrase longue avec beaucoup de détails."

    assert rag_pipeline._truncate_for_speech(text, 30) == "Première phrase."
