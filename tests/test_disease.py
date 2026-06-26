"""Tests for leaf disease screening logic (HTTP mocked — no network/key needed)."""

import core.disease as disease
from core.disease import screen_leaf_image, UNCLEAR_MESSAGE, DISCLAIMER


class _FakeResp:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = "error body"

    def json(self):
        return self._payload


def _candidate(text):
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def _patch(monkeypatch, resp):
    monkeypatch.setattr(disease, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(disease.requests, "post", lambda *a, **k: resp)


def test_unclear_photo_returns_polite_message(monkeypatch):
    _patch(monkeypatch, _FakeResp(200, _candidate("UNCLEAR")))
    out = screen_leaf_image(b"x", "image/jpeg")
    assert out["answer"] == UNCLEAR_MESSAGE


def test_normal_screening_gets_disclaimer_appended(monkeypatch):
    _patch(monkeypatch, _FakeResp(200, _candidate(
        "Il pourrait s'agir d'une carence en azote. Apportez de la fumure."
    )))
    out = screen_leaf_image(b"x", "image/jpeg")
    assert "carence en azote" in out["answer"]
    assert DISCLAIMER in out["answer"]


def test_existing_disclaimer_not_duplicated(monkeypatch):
    text = "Possible mildiou. Ceci n'est pas un diagnostic, voyez votre agent."
    _patch(monkeypatch, _FakeResp(200, _candidate(text)))
    out = screen_leaf_image(b"x", "image/jpeg")
    assert out["answer"].lower().count("pas un diagnostic") == 1


def test_rate_limit_returns_friendly_message(monkeypatch):
    _patch(monkeypatch, _FakeResp(429))
    out = screen_leaf_image(b"x", "image/jpeg")
    assert "quota" in out["answer"].lower()


def test_missing_key_is_handled(monkeypatch):
    monkeypatch.setattr(disease, "GEMINI_API_KEY", "")
    out = screen_leaf_image(b"x", "image/jpeg")
    assert "configur" in out["answer"].lower()
