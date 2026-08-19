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
    # "test-model" is not a reasoning model, so no reasoning params are sent.
    assert calls["model_kwargs"] == {}


@pytest.mark.parametrize(
    "model",
    ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.6-27b"],
)
def test_reasoning_models_hide_chain_of_thought(monkeypatch, model):
    """Farmer-facing answers must never contain reasoning tokens."""
    monkeypatch.setattr(llm_chain, "LLM_REASONING_FORMAT", "hidden")
    monkeypatch.setattr(llm_chain, "LLM_REASONING_EFFORT", "low")

    assert llm_chain._reasoning_model_kwargs(model) == {
        "reasoning_format": "hidden",
        "reasoning_effort": "low",
    }


@pytest.mark.parametrize("model", ["llama-3.3-70b-versatile", "gemma2-9b-it"])
def test_non_reasoning_models_get_no_reasoning_params(model):
    """Groq returns HTTP 400 if these params go to a non-reasoning model."""
    assert llm_chain._reasoning_model_kwargs(model) == {}


def test_default_model_is_not_decommissioned():
    """Guard against shipping a Groq model ID that Groq no longer serves."""
    import config

    retired = {
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "qwen/qwen3-32b",
        "deepseek-r1-distill-llama-70b",
        "mixtral-8x7b-32768",
    }
    assert config.LLM_MODEL not in retired


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("<think>je réfléchis</think>Semez en juin.", "Semez en juin."),
        ("<reasoning>abc</reasoning>\n\nSemez en juin.", "Semez en juin."),
        ("Semez en juin.<think>plus de pensées", "Semez en juin."),
        ("final: Semez en juin.", "Semez en juin."),
        ("Semez en juin.", "Semez en juin."),
    ],
)
def test_strip_reasoning_removes_chain_of_thought(raw, expected):
    assert llm_chain.strip_reasoning(raw) == expected


def test_strip_reasoning_never_empties_a_real_answer():
    """If the whole reply was a reasoning block, keep it rather than show nothing."""
    only_reasoning = "<think>je réfléchis</think>"
    assert llm_chain.strip_reasoning(only_reasoning) == only_reasoning


def test_strip_reasoning_handles_empty_input():
    assert llm_chain.strip_reasoning("") == ""
    assert llm_chain.strip_reasoning(None) is None


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Caution : évitez de semer tôt.", "Attention : évitez de semer tôt."),
        ("**Caution:** évitez cela.", "Attention: évitez cela."),
        ("- Warning : sol sec.", "- Attention : sol sec."),
        ("Summary: le mil.", "Résumé: le mil."),
        # Mid-sentence prose must not be rewritten.
        ("Utilisez la caution : non.", "Utilisez la caution : non."),
        ("Semez en juin.", "Semez en juin."),
    ],
)
def test_normalize_french_labels(raw, expected):
    assert llm_chain.normalize_french_labels(raw) == expected


def test_sanitize_answer_strips_reasoning_and_translates_labels():
    raw = "<think>hmm</think>Semez en juin.\nCaution : évitez le retard."
    assert llm_chain.sanitize_answer(raw) == (
        "Semez en juin.\nAttention : évitez le retard."
    )


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
