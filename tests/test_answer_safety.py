"""Regression tests for the model-output guardrails (audit findings 1 and 2).

Each test names the behaviour that was previously broken, so a future change
that reintroduces it fails here rather than in front of a farmer.
"""

import pytest

from core.answer_safety import (
    BLOCKED_ADVICE_ANSWER,
    CHEMICAL_DOSE,
    DEFINITIVE_DIAGNOSIS,
    PESTICIDE_PRODUCT,
    REDACTION_NOTICE,
    SAFETY_POLICY_VERSION,
    VISION_CONFIDENCE_LEVELS,
    clamp_case_confidence,
    clamp_vision_confidence,
    filter_safe_items,
    normalize_scalar,
    normalize_string_list,
    normalize_vision_payload,
    redact_unsafe_text,
    safety_policy_revision,
    unsafe_reasons,
    with_redaction_notice,
)


# ---------------------------------------------------------------------------
# Finding 1 — payload validation and the confidence ceiling
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "payload",
    [
        ["observation", "autre"],
        "juste du texte",
        42,
        3.5,
        True,
        None,
    ],
)
def test_non_object_vision_json_is_rejected_not_indexed(payload):
    """A bare list/string/number parses as JSON but is not a screening payload.

    The old code called ``.get`` on whatever ``json.loads`` returned, so any of
    these raised ``AttributeError`` inside a function documented as never
    raising.
    """
    assert normalize_vision_payload(payload) is None


def test_wrongly_typed_vision_fields_are_normalized_without_crashing():
    payload = {
        # A string where a list was requested.
        "observations": "Taches brunes sur les feuilles.",
        # A mapping where a list was requested.
        "problemes_possibles": {"a": "Carence possible.", "b": "Maladie possible."},
        # Nested objects and mixed types inside the list.
        "actions_immediates": [{"texte": "Retirez les feuilles."}, 5, None, "Surveillez."],
        # A number where text was requested.
        "reponse_courte": 1234,
        # A list where a sentence was requested.
        "a_confirmer_par": ["Agent", "agricole"],
        "niveau_de_confiance": ["Moyen"],
    }

    normalized = normalize_vision_payload(payload)

    assert normalized["observations"] == ["Taches brunes sur les feuilles."]
    assert normalized["problemes_possibles"] == ["Carence possible.", "Maladie possible."]
    assert normalized["actions_immediates"] == ["Retirez les feuilles.", "5", "Surveillez."]
    assert normalized["reponse_courte"] == "1234"
    assert normalized["a_confirmer_par"] == "Agent agricole"
    assert normalized["niveau_de_confiance"] in VISION_CONFIDENCE_LEVELS
    # Every list field really is a list of strings.
    for key in ("observations", "problemes_possibles", "actions_immediates"):
        assert isinstance(normalized[key], list)
        assert all(isinstance(item, str) for item in normalized[key])


def test_missing_vision_fields_become_empty_not_absent():
    normalized = normalize_vision_payload({})

    assert normalized["observations"] == []
    assert normalized["reponse_courte"] == ""
    assert normalized["niveau_de_confiance"] == "Faible"


@pytest.mark.parametrize(
    "reported",
    ["Fort", "fort", "FORTE", "Élevé", "eleve", "haute", "high", "strong", "certain"],
)
def test_vision_confidence_never_reports_fort(reported):
    """A photo screening is an aid; 'Fort' must be unreachable."""
    clamped = clamp_vision_confidence(reported)

    assert clamped == "Moyen"
    assert clamped in VISION_CONFIDENCE_LEVELS
    assert clamped != "Fort"


@pytest.mark.parametrize(
    "reported",
    ["Faible", "low", "", None, 0.95, True, "inconnu", [], {}],
)
def test_unrecognized_vision_confidence_degrades_to_faible(reported):
    assert clamp_vision_confidence(reported) == "Faible"


def test_clamp_case_confidence_caps_a_prebuilt_case():
    case = {"case_id": "x", "confidence": "Fort", "actions": ["a"]}

    clamped = clamp_case_confidence(case)

    assert clamped["confidence"] == "Moyen"
    # The original mapping is not mutated.
    assert case["confidence"] == "Fort"
    assert clamped["actions"] == ["a"]
    assert clamp_case_confidence(None) is None


def test_normalize_scalar_and_list_never_raise_on_odd_types():
    assert normalize_scalar(None) == ""
    assert normalize_scalar(True) == ""
    assert normalize_scalar(7) == "7"
    assert normalize_scalar(["a", None, "b"]) == "a b"
    assert normalize_scalar({"k": "v"}) == "v"
    assert normalize_string_list(None) == []
    assert normalize_string_list("seule") == ["seule"]
    # Duplicates collapse so a card does not repeat itself.
    assert normalize_string_list(["a", "a", "b"]) == ["a", "b"]


# ---------------------------------------------------------------------------
# Finding 2 — pesticide names, chemical doses, definitive diagnoses
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "sentence,reason",
    [
        ("Pulvérisez du mancozèbe sur les feuilles.", PESTICIDE_PRODUCT),
        ("Achetez du Roundup contre les mauvaises herbes.", PESTICIDE_PRODUCT),
        ("Appliquez 250 ml de glyphosate par hectare.", PESTICIDE_PRODUCT),
        ("Appliquez un insecticide systémique tout de suite.", PESTICIDE_PRODUCT),
        ("Mélangez le produit phytosanitaire avant usage.", PESTICIDE_PRODUCT),
        ("Utilisez 100 kg/ha de NPK au semis.", CHEMICAL_DOSE),
        ("Mettez 2 g d'urée par poquet.", CHEMICAL_DOSE),
        ("Apportez du NPK 14-23-14 au semis.", CHEMICAL_DOSE),
        ("Diluez 10 ml de produit par litre d'eau.", CHEMICAL_DOSE),
        ("Il s'agit de la rouille du mil.", DEFINITIVE_DIAGNOSIS),
        ("C'est la rouille du sorgho.", DEFINITIVE_DIAGNOSIS),
        ("Diagnostic : anthracnose.", DEFINITIVE_DIAGNOSIS),
        ("Je confirme une carence en azote.", DEFINITIVE_DIAGNOSIS),
        ("Votre plante a certainement le mildiou.", DEFINITIVE_DIAGNOSIS),
        ("Maladie identifiée sur vos épis.", DEFINITIVE_DIAGNOSIS),
    ],
)
def test_unsafe_model_claims_are_detected(sentence, reason):
    assert reason in unsafe_reasons(sentence)


@pytest.mark.parametrize(
    "sentence",
    [
        # The mandatory disclaimer must survive: "plante à votre agent" is not a
        # claim that the plant has something.
        "⚠️ Ceci n'est pas un diagnostic. Pour confirmer, montrez la plante à votre agent agricole.",
        "Montrez la plante à votre agent agricole.",
        "Il pourrait s'agir d'une carence en azote.",
        "Une maladie foliaire est possible ; surveillez la parcelle.",
        "Semez le mil au début de la saison des pluies.",
        "C'est le moment de semer après une pluie utile.",
        # Yields and agronomic spacing are not doses.
        "Le rendement peut atteindre 1 200 kg/ha en bonne année.",
        "Semez 20 kg de semences à l'hectare.",
        "Respectez 80 cm entre les lignes.",
        "Attendez 15 jours après la levée pour sarcler.",
        "Confirmez toujours la dose avec votre agent agricole.",
        "Les sacs PICS permettent un stockage hermétique sans produit chimique.",
        "Le niébé fixe l'azote de l'air, ce qui améliore le sol.",
    ],
)
def test_safe_field_advice_is_not_redacted(sentence):
    assert unsafe_reasons(sentence) == ()


def test_redaction_keeps_safe_sentences_and_line_structure():
    text = (
        "Il pourrait s'agir d'une maladie foliaire.\n"
        "• Retirez les feuilles très atteintes.\n"
        "• Pulvérisez du mancozèbe à 25 g par litre d'eau.\n"
        "Surveillez la parcelle après la pluie."
    )

    review = redact_unsafe_text(text)

    assert "mancozèbe" not in review.text
    assert "25 g" not in review.text
    assert "Retirez les feuilles très atteintes." in review.text
    assert "Surveillez la parcelle après la pluie." in review.text
    # The surviving bullet keeps its marker.
    assert "• Retirez" in review.text
    assert PESTICIDE_PRODUCT in review.reasons
    assert review.blocked is False
    assert review.redacted is True


def test_redaction_blocks_when_nothing_safe_survives():
    review = redact_unsafe_text("Il s'agit de la rouille. Traitez avec du Décis.")

    assert review.text == ""
    assert review.blocked is True
    assert DEFINITIVE_DIAGNOSIS in review.reasons


def test_clean_text_is_returned_unchanged_and_unflagged():
    review = redact_unsafe_text("Semez après une pluie utile. Sarclez tôt.")

    assert review.text == "Semez après une pluie utile. Sarclez tôt."
    assert review.reasons == ()
    assert review.blocked is False
    assert review.redacted is False


def test_redaction_notice_is_added_once_and_only_when_needed():
    assert with_redaction_notice("Conseil.", ()) == "Conseil."
    once = with_redaction_notice("Conseil.", (CHEMICAL_DOSE,))
    assert REDACTION_NOTICE in once
    assert with_redaction_notice(once, (CHEMICAL_DOSE,)).count(REDACTION_NOTICE) == 1


def test_filter_safe_items_drops_only_the_unsafe_entries():
    safe, reasons = filter_safe_items(
        [
            "Retirez les feuilles atteintes.",
            "Pulvérisez du chlorpyrifos.",
            "Surveillez après la pluie.",
        ]
    )

    assert safe == ["Retirez les feuilles atteintes.", "Surveillez après la pluie."]
    assert PESTICIDE_PRODUCT in reasons


def test_diagnosis_check_can_be_disabled_for_grounded_text():
    """RAG answers are graded for products and doses, not for hedging style."""
    sentence = "Il s'agit d'une pratique courante au Burkina Faso."

    assert DEFINITIVE_DIAGNOSIS in unsafe_reasons(sentence, check_diagnosis=True)
    assert unsafe_reasons(sentence, check_diagnosis=False) == ()


def test_blocked_advice_answer_is_french_and_defers_to_an_agent():
    assert "agent agricole" in BLOCKED_ADVICE_ANSWER
    assert "diagnostic" in BLOCKED_ADVICE_ANSWER
    # The deterministic refusal must not itself trip the guardrails.
    assert unsafe_reasons(BLOCKED_ADVICE_ANSWER) == ()
    assert unsafe_reasons(REDACTION_NOTICE) == ()


# ---------------------------------------------------------------------------
# Finding 3 — deployment identity of the safety policy
# ---------------------------------------------------------------------------

def test_safety_policy_revision_tracks_prompt_and_policy_source():
    revision = safety_policy_revision()

    assert revision.startswith(SAFETY_POLICY_VERSION + ".")
    # Stable within a process (it is cached) and not just the bare constant.
    assert revision == safety_policy_revision()
    assert revision != SAFETY_POLICY_VERSION
    assert len(revision) > len(SAFETY_POLICY_VERSION) + 1
