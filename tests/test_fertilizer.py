"""Tests for the deterministic fertilizer tool (no network / no LLM)."""

from core.fertilizer import is_fertilizer_query, get_fertilizer_advice


def test_detects_fertilizer_intent():
    assert is_fertilizer_query("dose d'engrais pour le sorgho")
    assert is_fertilizer_query("quelle fumure pour le mil ?")
    assert not is_fertilizer_query("quand semer le mil ?")


def test_sorgho_dose_is_grounded_with_disclaimer():
    advice = get_fertilizer_advice("dose d'engrais pour le sorgho")
    assert advice is not None
    answer = advice["answer"]
    # Specific, source-grounded numbers (not invented).
    assert "100 kg/ha de NPK (14-23-14)" in answer
    assert "50 kg/ha d'urée" in answer
    # Mandatory French disclaimer.
    assert "Confirmez toujours avec votre agent agricole" in answer
    assert advice["sources"], "fertilizer advice must cite a source"
    assert advice["sources"][0]["type"] == "Outil engrais"
    assert advice["sources"][0]["snippet"]
    assert advice["case"]["input_type"] == "fertilizer"
    assert advice["case"]["crop"] == "sorgho"
    assert advice["case"]["summary"]
    assert advice["case"]["actions"]
    assert advice["case"]["do_not"]
    assert advice["case"]["case_title"] == "Conseil engrais"


def test_each_supported_crop_returns_advice():
    for q in [
        "engrais sorgho",
        "fumure mil",
        "npk maïs",
        "fertilisation niébé",
        "engrais arachide",
    ]:
        assert get_fertilizer_advice(q) is not None, q


def test_no_crop_defers_to_rag():
    # Fertilizer intent but no crop named -> None so the caller falls back to RAG.
    assert get_fertilizer_advice("quelle dose d'engrais utiliser ?") is None


def test_form_crop_fills_missing_crop_name():
    advice = get_fertilizer_advice(
        "quelle dose d'engrais utiliser ?",
        crop="sorgho",
        growth_stage="levée / jeune plant",
        location="Kaya",
    )
    assert advice is not None
    assert "100 kg/ha de NPK" in advice["answer"]
    assert advice["case"]["crop"] == "sorgho"
    assert advice["case"]["growth_stage"] == "levée / jeune plant"
    assert advice["case"]["location"] == "Kaya"
