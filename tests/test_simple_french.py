"""Tests for French simple mode helpers."""

from core.simple_french import (
    GLOSSARY,
    SIMPLE_STYLE_INSTRUCTION,
    apply_simple_style_to_query,
    enrich_answer_with_glossary,
    is_simple_mode,
    light_replacements,
    simplify_answer,
)


def test_is_simple_mode_truthy_values():
    assert is_simple_mode(True) is True
    assert is_simple_mode("1") is True
    assert is_simple_mode("oui") is True
    assert is_simple_mode("yes") is True
    assert is_simple_mode("simple") is True
    assert is_simple_mode(False) is False
    assert is_simple_mode("0") is False
    assert is_simple_mode("") is False
    assert is_simple_mode(None) is False


def test_apply_simple_style_to_query_appends_once():
    q = "Quand semer le mil ?"
    out = apply_simple_style_to_query(q)
    assert q in out
    assert SIMPLE_STYLE_INSTRUCTION in out
    assert apply_simple_style_to_query(out) == out
    assert "n'inventez pas" in SIMPLE_STYLE_INSTRUCTION
    assert "ne inventez pas" not in SIMPLE_STYLE_INSTRUCTION


def test_glossary_has_core_field_terms():
    for key in ("NPK", "urée", "microdose", "stress hydrique", "OAPH", "semis"):
        assert key in GLOSSARY
        assert len(GLOSSARY[key]) > 5


def test_enrich_answer_with_glossary_adds_block():
    answer = "Utilisez du NPK et de l'urée en microdose."
    out = enrich_answer_with_glossary(answer)
    assert "Mots simples" in out
    assert "NPK" in out
    assert "urée" in out
    # Idempotent
    assert enrich_answer_with_glossary(out) == out


def test_enrich_skips_when_no_terms():
    answer = "Arrosez si le sol est sec."
    assert enrich_answer_with_glossary(answer) == answer


def test_light_replacements_and_simplify():
    text = "Il y a un stress hydrique. Confirmez toujours avec votre agent agricole."
    light = light_replacements(text)
    assert "manque d'eau" in light
    assert "Demandez toujours confirmation" in light
    full = simplify_answer("Dose vulgarisée et NPK au semis.")
    assert "Mots simples" in full


def test_simplify_keeps_glossary_note_for_replaced_stress_hydrique():
    out = simplify_answer("Le mil subit un stress hydrique.")
    assert "manque d'eau" in out
    assert "stress hydrique :" in out
