"""Tests for Groq chat client configuration."""

import pytest

import core.llm_chain as llm_chain


def test_get_llm_passes_timeout_and_retries(monkeypatch):
    calls = {}

    class FakeChatGroq:
        def __init__(self, **kwargs):
            calls.update(kwargs)

    monkeypatch.setattr(llm_chain, "_llm", None)
    monkeypatch.setattr(llm_chain, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(llm_chain, "GROQ_USER_AGENT", "DakiKoboTest/1.0")
    monkeypatch.setattr(llm_chain, "LLM_MODEL", "test-model")
    monkeypatch.setattr(llm_chain, "LLM_MAX_TOKENS", 123)
    monkeypatch.setattr(llm_chain, "LLM_TEMPERATURE", 0.2)
    monkeypatch.setattr(llm_chain, "LLM_TIMEOUT_SECONDS", 7.5)
    monkeypatch.setattr(llm_chain, "LLM_MAX_RETRIES", 0)
    monkeypatch.setattr(llm_chain, "ChatGroq", FakeChatGroq)

    llm = llm_chain.get_llm()

    assert isinstance(llm, FakeChatGroq)
    assert calls["model"] == "test-model"
    assert calls["max_tokens"] == 123
    assert calls["temperature"] == 0.2
    assert calls["timeout"] == 7.5
    assert calls["max_retries"] == 0
    assert calls["groq_api_key"] == "test-key"
    assert calls["default_headers"] == {"User-Agent": "DakiKoboTest/1.0"}


def test_get_llm_requires_api_key(monkeypatch):
    monkeypatch.setattr(llm_chain, "_llm", None)
    monkeypatch.setattr(llm_chain, "GROQ_API_KEY", "")

    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        llm_chain.get_llm()


def test_prompt_requires_evidence_first_safety():
    template = llm_chain._PROMPT_TEMPLATE
    assert "short answer" in template.lower() or "Structure" in template
    assert "fertilizer doses" in template.lower() or "exact fertilizer" in template.lower()
    assert "ALWAYS reply in French" in template
    assert "Je ne sais pas encore" in template
    assert "Je ne peux pas confirmer" in template
    assert "Topic priority" in template
    assert "soja" in template.lower() or "Soybean" in template
    assert "Follow-ups" in template
