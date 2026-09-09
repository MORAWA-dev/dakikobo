"""Tests for the deterministic fertilizer tool (no network / no LLM)."""

from core.fertilizer import is_fertilizer_query, get_fertilizer_advice


def test_detects_fertilizer_intent():
    assert is_fertilizer_query("dose d'engrais pour le sorgho")
    assert is_fertilizer_query("quelle fumure pour le mil ?")
    assert not is_fertilizer_query("quand semer le mil ?")


def test_unverified_sorgho_dose_is_withheld_with_disclaimer():
    advice = get_fertilizer_advice("dose d'engrais pour le sorgho")
    assert advice is not None
    answer = advice["answer"]
    assert "100 kg/ha" not in answer
    assert "temporairement retirées" in answer
    assert "agent agricole" in answer
    assert advice["sources"] == []
    assert advice["case"] is None
    assert advice["confidence"] == "Faible"
    assert advice["answer_kind"] == "refusal"


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
    assert "dose exacte" in advice["answer"]
    assert advice["case"] is None


def test_multiple_or_unsupported_crops_never_select_first_match():
    multiple = get_fertilizer_advice("engrais pour le mil et le maïs")
    unsupported = get_fertilizer_advice("engrais pour le soja")
    assert multiple["answer_kind"] == "clarification"
    assert unsupported["answer_kind"] == "refusal"
    assert multiple["sources"] == unsupported["sources"] == []



def test_approved_doses_are_gated_and_only_live_in_this_module():
    """PR review item 5: exact fertilizer figures are confined to core/fertilizer.

    The numeric guidance gate stays off, so the deterministic tool withholds
    doses and the model path (which strips any invented dose) is the only other
    place a dose could appear — and it is blocked there. The gate is the single
    switch that would ever release the reviewed figures, and it must stay False
    until an agronomist approves provenance.
    """
    import core.fertilizer as fert

    assert fert.NUMERIC_GUIDANCE_VERIFIED is False
    # The reviewed figures exist in this module, but are not emitted while gated.
    assert "100 kg/ha" in fert._RECOMMENDATIONS["sorgho"]["lines"][0]
    for query in ("engrais sorgho", "npk maïs", "fumure mil"):
        answer = get_fertilizer_advice(query)["answer"]
        assert "kg/ha" not in answer
        assert "14-23-14" not in answer


def test_offline_payload_withholds_doses_while_gated():
    from core.fertilizer import build_offline_fertilizer_payload

    payload = build_offline_fertilizer_payload()
    for crop in payload["crops"].values():
        assert crop["available"] is False
        assert crop["sources"] == []
        joined = " ".join(crop["lines"])
        assert "kg/ha" not in joined
        assert "14-23-14" not in joined
