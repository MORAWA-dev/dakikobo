"""Tests for question vs parcelle context resolution."""

from core.query_context import (
    detect_crop_in_text,
    detect_location_in_text,
    expand_with_prior,
    is_short_followup,
    resolve_query_context,
)


def test_detect_crop_prefers_question_crop():
    assert detect_crop_in_text("comment semer le soja à Mogtedo") == "soja"
    assert detect_crop_in_text("rotation mil et sorgho") in {"mil", "sorgho"}
    assert detect_crop_in_text("bonjour") == ""


def test_detect_location_mogtedo_and_ouaga():
    assert detect_location_in_text("dans la ville de Mogtedo") == "Mogtédo"
    assert detect_location_in_text("ok a ouagadougou") == "Ouagadougou"
    assert detect_location_in_text("à Kaya") == "Kaya"


def test_short_followup_location_only():
    assert is_short_followup("ok a ouagadougou") is True
    assert is_short_followup("à Kaya") is True
    assert is_short_followup("comment bien semer le soja à Mogtedo avec quels sols") is False


def test_expand_with_prior_keeps_soja_topic():
    prior = "comment bien semer le soja dans la ville de Mogtedo"
    expanded = expand_with_prior("ok a ouagadougou", prior)
    assert "soja" in expanded
    assert "ouagadougou" in expanded.lower()
    assert "Précision" in expanded


def test_question_crop_wins_over_form_sorgho():
    resolved = resolve_query_context(
        "comment bien semer le soja dans la ville de Mogtedo, types de sols",
        {
            "crop": "sorgho",
            "growth_stage": "levée / jeune plant",
            "location": "Ouagadougou",
        },
    )
    assert resolved.crop == "soja"
    assert resolved.location == "Mogtédo"
    assert resolved.growth_stage == ""  # stale stage for another crop dropped
    assert resolved.crop_conflict is True
    assert "soja" in resolved.retrieval_query
    assert "Répondez pour soja" in resolved.retrieval_query
    # Must not force sorgho as the culture to answer for.
    assert "culture: sorgho" not in resolved.retrieval_query


def test_followup_ok_ouaga_keeps_soja_from_prior():
    resolved = resolve_query_context(
        "ok a ouagadougou",
        {
            "crop": "sorgho",
            "growth_stage": "levée / jeune plant",
            "location": "Ouagadougou",
        },
        prior_question="comment bien semer le soja dans la ville de Mogtedo",
    )
    assert resolved.expanded_from_prior is True
    assert resolved.crop == "soja"
    assert resolved.location == "Ouagadougou"
    assert "soja" in resolved.retrieval_query.lower()
    assert "culture: soja" in resolved.retrieval_query


def test_registry_ids_are_converted_to_french_prompt_labels():
    resolved = resolve_query_context(
        "Quand semer ?",
        {"crop": "mais", "location": "bobo"},
    )
    assert resolved.crop_id == "mais"
    assert resolved.crop_label_fr == "maïs"
    assert resolved.place_id == "bobo"
    assert resolved.place_label_fr == "Bobo-Dioulasso"
    assert "culture: maïs" in resolved.retrieval_query
    assert "lieu: Bobo-Dioulasso" in resolved.retrieval_query
    assert resolved.as_case_fields()["crop"] == "maïs"
    assert resolved.as_case_fields()["location"] == "Bobo-Dioulasso"


def test_oaph_acronym_is_expanded_for_stable_reviewed_source_retrieval():
    resolved = resolve_query_context("C'est quoi l'OAPH au Burkina Faso ?")
    assert "OAPH = Offensive Agropastorale et Halieutique 2023-2025" in (
        resolved.retrieval_query
    )
    assert "MAERAH" in resolved.retrieval_query
