"""Tests for speech-to-text client behavior."""

import pytest

import core.speech as speech


def test_transcribe_audio_passes_timeout_and_retries(monkeypatch):
    calls = {}

    class FakeTranscriptions:
        def create(self, **kwargs):
            calls["create"] = kwargs
            return type("Transcript", (), {"text": " bonjour producteurs "})()

    class FakeAudio:
        transcriptions = FakeTranscriptions()

    class FakeGroq:
        def __init__(self, **kwargs):
            calls["client"] = kwargs
            self.audio = FakeAudio()

    monkeypatch.setattr(speech, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(speech, "GROQ_USER_AGENT", "DakiKoboTest/1.0")
    monkeypatch.setattr(speech, "STT_MODEL", "test-whisper")
    monkeypatch.setattr(speech, "STT_LANGUAGE", "fr")
    monkeypatch.setattr(speech, "STT_TIMEOUT_SECONDS", 4.5)
    monkeypatch.setattr(speech, "STT_MAX_RETRIES", 0)
    monkeypatch.setattr(speech, "Groq", FakeGroq)

    text = speech.transcribe_audio(
        b"abc",
        filename="question.webm",
        mime_type="audio/webm",
    )

    assert text == "bonjour producteurs"
    assert calls["client"]["api_key"] == "test-key"
    assert calls["client"]["timeout"] == 4.5
    assert calls["client"]["max_retries"] == 0
    assert calls["client"]["default_headers"] == {"User-Agent": "DakiKoboTest/1.0"}
    assert calls["create"]["model"] == "test-whisper"
    assert calls["create"]["language"] == "fr"
    assert calls["create"]["file"] == ("question.webm", b"abc", "audio/webm")


def test_transcribe_audio_wraps_client_errors(monkeypatch):
    class FailingGroq:
        def __init__(self, **kwargs):
            raise RuntimeError("client timeout")

    monkeypatch.setattr(speech, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(speech, "Groq", FailingGroq)

    with pytest.raises(speech.SpeechTranscriptionError, match="client timeout"):
        speech.transcribe_audio(b"abc")
