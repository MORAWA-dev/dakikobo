"""Tests for structured field-case helpers."""

from core.case import (
    build_advice_case,
    build_disease_case,
    case_title_for,
    is_usable_field_sentence,
    split_french_sentences,
)


def test_case_title_for_known_types():
    assert case_title_for("image") == "Cas de terrain - feuille"
    assert case_title_for("fertilizer") == "Conseil engrais"
    assert case_title_for("text") == "Conseil agricole"
    assert case_title_for("other") == "Conseil agricole"


def test_split_french_sentences_handles_bullets():
    text = "Première phrase. Deuxième phrase!\n• Troisième action."
    parts = split_french_sentences(text)
    assert parts[0] == "Première phrase."
    assert "Deuxième phrase!" in parts
    assert any("Troisième" in part for part in parts)


def test_build_disease_case_unclear_photo():
    case = build_disease_case(
        answer="Photo floue.",
        disclaimer="Ceci n'est pas un diagnostic.",
        unclear=True,
    )
    assert case["input_type"] == "image"
    assert case["image_present"] is True
    assert case["confidence"] == "Faible"
    assert case["case_title"] == "Cas de terrain - feuille"
    assert case["observations"]
    assert case["actions"]
    assert case["evidence"] == []
    assert case["do_not"] == []
    assert case["summary"] == ""
    assert "diagnostic" in case["disclaimer"]


def test_build_advice_case_fertilizer_structure():
    answer = (
        "Fumure recommandée pour le sorgho au Burkina Faso. "
        "Dose vulgarisée : 100 kg/ha de NPK au semis. "
        "Évitez l'urée juste avant une forte pluie."
    )
    case = build_advice_case(
        answer=answer,
        question="dose d'engrais pour le sorgho",
        input_type="fertilizer",
        crop="sorgho",
        sources=[
            {
                "title": "INERA",
                "type": "Outil engrais",
                "snippet": "Essais microdose sur sorgho.",
            }
        ],
        confidence="Fort",
        summary="Fumure recommandée pour le sorgho.",
        actions=["100 kg/ha de NPK au semis"],
        do_not=["Évitez l'urée juste avant une forte pluie."],
        disclaimer="Confirmez avec votre agent.",
    )
    assert case["input_type"] == "fertilizer"
    assert case["case_title"] == "Conseil engrais"
    assert case["crop"] == "sorgho"
    assert case["summary"].startswith("Fumure recommandée")
    assert case["actions"] == ["100 kg/ha de NPK au semis"]
    assert case["do_not"]
    assert case["evidence"] == ["Essais microdose sur sorgho."]
    assert case["needs_human_confirmation"] is True
    assert case["sources"][0]["type"] == "Outil engrais"
    assert "agent" in case["confirmation"].lower()


def test_rejects_fews_market_dump_as_evidence():
    garbage = (
        "Porcs Volaille Maïs Vente de bois de chauffage Sorgho/Mil Bovins "
        "Niébé Produit Route commerciale Céréales (sorgho, mil) Djibasso"
    )
    assert is_usable_field_sentence(garbage) is False
    case = build_advice_case(
        answer=(
            "Alternez mil et sorgho d'une saison à l'autre. "
            "Parce que la rotation aide la fertilité du sol. "
            "Récoltez le sorgho avant de semer le mil."
        ),
        question="alterner mil et sorgho",
        input_type="text",
        crop="sorgho",
        sources=[
            {
                "title": "Burkina Faso - Profil des moyens d'existence (FEWS NET)",
                "type": "Profil pays",
                "snippet": garbage,
            },
            {
                "title": "Manuel extension mil et sorgho",
                "type": "Manuel de formation",
                "snippet": "La rotation mil-sorgho aide à maintenir la fertilité du sol.",
            },
        ],
        confidence="Moyen",
        weather_signals=[
            "Risque de stress hydrique : Risque élevé.",
            "Pluie utile (7 jours) : 6.4 mm récents.",
            "Fenêtre de semis probable : Possible.",
        ],
    )
    assert garbage not in case["evidence"]
    assert all("Route commerciale" not in e for e in case["evidence"])
    assert all("FEWS" not in (s.get("title") or "") for s in case["sources"])
    assert len(case["sources"]) <= 2
    assert case["sources"][0]["title"].startswith("Manuel")
    assert case["summary"]
    assert len(case["actions"]) <= 3
    assert len(case["evidence"]) <= 1
    assert len(case["weather_signals"]) <= 1
    assert "Risque" in case["weather_signals"][0]


def test_build_advice_case_parses_free_text():
    answer = (
        "Semez le mil quand les pluies sont régulières. "
        "Parce que le sol doit rester humide plusieurs jours. "
        "Gardez des semences pour un ressemis. "
        "Évitez de semer après une seule pluie isolée."
    )
    case = build_advice_case(
        answer=answer,
        question="Quand semer le mil ?",
        input_type="text",
        crop="mil",
        growth_stage="levée / jeune plant",
        location="Kaya",
        confidence="Moyen",
    )
    assert case["input_type"] == "text"
    assert case["case_title"] == "Conseil agricole"
    assert case["summary"]
    assert case["actions"]
    assert case["do_not"]
    assert case["image_present"] is False
    assert case["crop"] == "mil"
    assert case["growth_stage"] == "levée / jeune plant"
    assert case["location"] == "Kaya"
