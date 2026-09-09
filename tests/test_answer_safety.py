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
    safe_confirmation,
    safety_policy_revision,
    unsafe_reasons,
    with_redaction_notice,
)

_AGENT_FALLBACK = "Montrez la plante à un agent agricole pour confirmer."


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


def test_diagnosis_check_flag_is_honoured_both_ways():
    """The diagnosis rule is opt-out via the flag.

    The application enables it on every model path (vision and RAG); this test
    only pins the flag's mechanics so a caller can still request product/dose
    grading alone if a future path needs it. The sentence carries disease
    context, so it is a firm diagnosis when the flag is on.
    """
    sentence = "Il s'agit de la rouille du mil."

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



# ---------------------------------------------------------------------------
# PR revision — token-boundary pesticide matching (revision item 4)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "sentence",
    [
        # These merely *contain* the trade name "decis" as a substring.
        "La décision dépend de la pluie.",
        "La décision dépend de la pluie et du sol.",
        "Décision prise après la récolte.",
        "Cette indécision coûte cher au producteur.",
        "Les décisions du comité seront affichées.",
    ],
)
def test_decision_is_not_confused_with_the_trade_name_decis(sentence):
    assert PESTICIDE_PRODUCT not in unsafe_reasons(sentence)
    assert unsafe_reasons(sentence) == ()


@pytest.mark.parametrize(
    "sentence",
    [
        "Utilisez du Décis contre les chenilles.",
        "Appliquez du mancozèbe sur les feuilles.",   # inflected form of "mancozeb"
        "Fumigez avec du phosphure d'aluminium.",     # multi-word phrase
        "Bouillie bordelaise recommandée.",           # multi-word phrase
        "Roundup pour désherber.",
        "Traitez au Karaté.",
    ],
)
def test_pesticide_names_still_match_on_token_and_phrase_boundaries(sentence):
    assert PESTICIDE_PRODUCT in unsafe_reasons(sentence)


# ---------------------------------------------------------------------------
# PR revision — chemical context required for quantities (revision item 3)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "sentence",
    [
        # Irrigation per pied/plant — no chemical context.
        "Apportez 20 litres d'eau par pied chaque semaine.",
        "Arrosez avec 20 litres d'eau par pied.",
        "10 litres d'eau par plant au repiquage.",
        # Compost per pied — organic, not a chemical dose.
        "Ajoutez 5 kg de compost par pied.",
        "Mettez une poignée de fumier par poquet.",
        # Seed, spacing, and yield quantities.
        "Semez 20 kg de semences à l'hectare.",
        "Respectez 80 cm entre les lignes et 40 cm sur la ligne.",
        "Le rendement peut atteindre 1 200 kg/ha en bonne année.",
    ],
)
def test_legitimate_quantities_are_preserved(sentence):
    assert CHEMICAL_DOSE not in unsafe_reasons(sentence)
    assert unsafe_reasons(sentence) == ()


@pytest.mark.parametrize(
    "sentence",
    [
        "Utilisez 100 kg/ha de NPK au semis.",
        "Mettez 2 g d'urée par poquet.",
        "Apportez du NPK 14-23-14.",
        "Diluez 10 g de fongicide par litre.",
        "Ajoutez 50 kg de phosphate à l'hectare.",
    ],
)
def test_chemical_quantities_are_still_flagged(sentence):
    assert CHEMICAL_DOSE in unsafe_reasons(sentence)


def test_per_pied_water_quantity_survives_redaction_intact():
    text = "Apportez 20 litres d'eau par pied chaque semaine."
    review = redact_unsafe_text(text)
    assert review.text == text
    assert review.reasons == ()


def test_decision_sentence_survives_redaction_intact():
    text = "La décision dépend de la pluie."
    review = redact_unsafe_text(text)
    assert review.text == text
    assert review.reasons == ()


# ---------------------------------------------------------------------------
# PR revision — safe_confirmation (revision item 2)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "value",
    [
        "Agent agricole local.",
        "Montrez la plante à un agronome.",
        "Confirmez avec le service de vulgarisation.",
        "Demandez à un technicien agricole.",
        "Faites analyser en laboratoire.",
    ],
)
def test_safe_confirmation_keeps_valid_agent_directions(value):
    assert safe_confirmation(value, fallback=_AGENT_FALLBACK) == value


@pytest.mark.parametrize(
    "value",
    [
        "",                                        # empty
        "   ",                                     # whitespace only
        "ok",                                      # too short / malformed
        "x" * 250,                                 # too long / malformed
        "Traitez avec du Décis à 10 ml.",          # unsafe: product
        "Appliquez 100 kg/ha de NPK.",             # unsafe: dose
        "Il s'agit de la rouille.",                # unsafe: diagnosis
        "Regardez encore la photo demain.",        # not agent-directed
        "Attendez la prochaine pluie.",            # not agent-directed
        None,                                      # missing
        12345,                                     # wrong type
    ],
)
def test_safe_confirmation_falls_back_when_unusable(value):
    assert safe_confirmation(value, fallback=_AGENT_FALLBACK) == _AGENT_FALLBACK


def test_safe_confirmation_fallback_is_itself_agent_directed_and_safe():
    # The fallback must pass its own gate, or a second pass would drop it.
    assert safe_confirmation(_AGENT_FALLBACK, fallback="AUTRE") == _AGENT_FALLBACK



# ---------------------------------------------------------------------------
# PR review round 2 — cross-sentence dose, firmer diagnosis, anchored certainty
# ---------------------------------------------------------------------------

# Item 1: a dose split across adjacent sentences.

def test_cross_sentence_dose_is_blocked_by_redaction():
    """"L'urée convient. Appliquez 100 kg/ha." — the quantity and its chemical
    noun sit in neighbouring sentences, so a per-sentence check missed it."""
    review = redact_unsafe_text("L'urée convient. Appliquez 100 kg/ha.")

    assert CHEMICAL_DOSE in review.reasons
    assert "100 kg/ha" not in review.text
    assert "kg/ha" not in review.text


def test_cross_sentence_dose_blocked_regardless_of_order():
    review = redact_unsafe_text("Appliquez 100 kg/ha. C'est de l'urée.")

    assert CHEMICAL_DOSE in review.reasons
    assert "100 kg/ha" not in review.text


def test_dose_window_does_not_flag_a_quantity_far_from_chemistry():
    """The window is small: an irrigation or seed quantity with no chemical
    noun anywhere nearby stays safe."""
    irrigation = redact_unsafe_text("Arrosez le champ. Comptez 20 litres d'eau par pied.")
    assert CHEMICAL_DOSE not in irrigation.reasons
    assert "20 litres d'eau par pied" in irrigation.text

    seed = redact_unsafe_text("Préparez le sol. Semez 20 kg de semences par hectare.")
    assert CHEMICAL_DOSE not in seed.reasons
    assert "20 kg de semences" in seed.text


# Item 2: firmer diagnosis forms.

@pytest.mark.parametrize(
    "sentence",
    [
        "La cause est la rouille du mil.",
        "Ces signes confirment une rouille du mil.",
        "Le problème est une carence en azote sur les feuilles.",
        "Ces symptômes confirment le mildiou.",
    ],
)
def test_firm_diagnosis_forms_are_blocked(sentence):
    assert DEFINITIVE_DIAGNOSIS in unsafe_reasons(sentence)


# Item 3: generic certainty only counts with disease/pest/symptom/damage context.

@pytest.mark.parametrize(
    "sentence",
    [
        "Il s'agit du programme OAPH.",
        "Il s'agit d'une technique de conservation de l'eau.",
        "C'est certainement le bon moment pour semer.",
        "Il s'agit peut-être d'une méthode utile.",
        # Neighbours of the above, to be safe.
        "Il s'agit de la rotation des cultures.",
        "C'est certainement une bonne pratique.",
        "La cause est le manque de pluie cette année.",
    ],
)
def test_generic_certainty_without_disease_context_is_safe(sentence):
    assert DEFINITIVE_DIAGNOSIS not in unsafe_reasons(sentence)
    assert unsafe_reasons(sentence) == ()


@pytest.mark.parametrize(
    "sentence",
    [
        "Il s'agit de la rouille du mil.",
        "C'est certainement le mildiou sur ces feuilles.",
        "Il s'agit d'une attaque de chenilles.",
        "C'est assurément une carence, vu ces taches.",
    ],
)
def test_generic_certainty_with_disease_context_is_blocked(sentence):
    assert DEFINITIVE_DIAGNOSIS in unsafe_reasons(sentence)


def test_hedged_diagnosis_is_still_allowed():
    """The prompt mandates hedging; "il s'agit peut-être" must survive."""
    assert unsafe_reasons("Il s'agit peut-être d'une rouille, à confirmer.") == ()
    assert unsafe_reasons("Il pourrait s'agir d'une carence en azote.") == ()


def test_full_redaction_path_for_each_review_sentence():
    """The complete redact_unsafe_text path, not just unsafe_reasons."""
    # Blocked ones are removed.
    for text in [
        "L'urée convient. Appliquez 100 kg/ha.",
        "La cause est la rouille du mil.",
        "Ces signes confirment une rouille du mil.",
    ]:
        review = redact_unsafe_text(text)
        assert review.reasons, f"expected redaction for: {text}"
        assert "100 kg/ha" not in review.text

    # Safe ones pass through untouched.
    for text in [
        "Il s'agit du programme OAPH.",
        "Il s'agit d'une technique de conservation de l'eau.",
        "C'est certainement le bon moment pour semer.",
        "Il s'agit peut-être d'une méthode utile.",
    ]:
        review = redact_unsafe_text(text)
        assert review.reasons == ()
        assert review.text == text
