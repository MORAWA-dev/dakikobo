"""Quota-safe public demo examples for the DakiKobo UI."""

from __future__ import annotations

from copy import deepcopy


_TEXT_SOURCE = {
    "title": "Exemple DakiKobo - base locale",
    "type": "Base locale",
    "snippet": "Reponse de demonstration preparee pour presenter le comportement du chatbot sans appeler le LLM.",
}

_FERTILIZER_SOURCE = {
    "title": "Recherche INERA - microdose Burkina",
    "type": "Outil engrais",
    "snippet": "Essais sur sorgho, mil et niebe: doses vulgarisees NPK/uree et options microdose.",
}

_VISION_SOURCE = {
    "title": "Exemple DakiKobo - depistage photo",
    "type": "Vision",
    "snippet": "Cas de demonstration prepare pour montrer la carte de depistage sans appeler Gemini.",
}


DEMO_EXAMPLES = {
    "semis_mil": {
        "kind": "message",
        "question": "Quand semer le mil ?",
        "answer": (
            "Pour le mil, attendez que les pluies soient regulieres avant de semer. "
            "Evitez de semer apres une seule pluie isolee : si le sol se desseche juste "
            "apres, les jeunes plants peuvent manquer d'eau. En pratique, semez quand "
            "le sol est bien humide sur plusieurs centimetres et que la saison semble "
            "installee. Gardez une partie des semences pour un ressemis si la premiere "
            "levee est mauvaise."
        ),
        "sources": [_TEXT_SOURCE],
        "confidence": "Moyen",
        "audio_url": "",
    },
    "humidite_sorgho": {
        "kind": "message",
        "question": "Comment garder l'humidite du sol pour le sorgho ?",
        "answer": (
            "Pour aider le sorgho pendant les periodes seches, limitez l'evaporation et "
            "gardez l'eau pres des racines : sarclez tot, laissez des residus vegetaux "
            "quand c'est possible, utilisez des cordons pierreux ou des zai sur les sols "
            "encroûtes, et apportez du fumier bien decompose. Sur une pente, ralentir le "
            "ruissellement est souvent plus important que multiplier les arrosages."
        ),
        "sources": [_TEXT_SOURCE],
        "confidence": "Moyen",
        "audio_url": "",
    },
    "rotation_niebe": {
        "kind": "message",
        "question": "Pourquoi faire une rotation niébé-céréales ?",
        "answer": (
            "La rotation niébé-céréales aide a casser les cycles de ravageurs et de "
            "maladies, et elle peut ameliorer la fertilite du sol parce que le niebe est "
            "une legumineuse. Evitez de remettre la meme culture au meme endroit chaque "
            "annee, surtout si vous avez observe beaucoup de maladies ou une baisse de "
            "rendement. Apres le niebe, gardez si possible les residus au champ ou "
            "valorisez-les avec le fumier."
        ),
        "sources": [_TEXT_SOURCE],
        "confidence": "Moyen",
        "audio_url": "",
    },
    "fumure_sorgho": {
        "kind": "message",
        "question": "Quelle dose d'engrais pour le sorgho ?",
        "answer": (
            "Fumure recommandee pour le sorgho au Burkina Faso :\n"
            "• Dose vulgarisee : 100 kg/ha de NPK (14-23-14) au semis + 50 kg/ha "
            "d'uree (46 %) a la montaison.\n"
            "• Microdose plus economique : 2 g de NPK par poquet au semis + 1 g "
            "d'uree par poquet a la montaison.\n\n"
            "Ce sont des recommandations generales issues de la recherche. Confirmez "
            "toujours avec votre agent agricole : la bonne dose depend du sol, de la "
            "pluie et de vos moyens."
        ),
        "sources": [_FERTILIZER_SOURCE],
        "confidence": "Fort",
        "audio_url": "",
    },
    "photo_mais": {
        "kind": "case",
        "question": "[Exemple photo] Taches sur feuille de maïs",
        "answer": (
            "Exemple de depistage : les taches visibles peuvent faire penser a une "
            "maladie foliaire ou a des degats de ravageurs, mais la confirmation doit "
            "se faire au champ."
        ),
        "sources": [_VISION_SOURCE],
        "confidence": "Moyen",
        "audio_url": "",
        "case": {
            "case_id": "demo_photo_mais",
            "created_at": "demo",
            "input_type": "image",
            "crop": "maïs",
            "growth_stage": "fructification / épi",
            "location": "Exemple",
            "question": "Dépistage photo de feuille",
            "image_present": False,
            "answer": (
                "Exemple de depistage : les taches visibles peuvent faire penser a "
                "une maladie foliaire ou a des degats de ravageurs."
            ),
            "observations": [
                "Taches sombres et zones jaunatres visibles sur une feuille.",
                "Symptomes localises, sans information sur toute la parcelle.",
            ],
            "possible_causes": [
                "Maladie foliaire possible, a confirmer sur plusieurs plants.",
                "Degats de ravageurs ou stress local possible.",
            ],
            "actions": [
                "Observer plusieurs plants dans la parcelle avant de traiter.",
                "Retirer les feuilles tres atteintes si elles sont peu nombreuses.",
                "Montrer la plante a un agent agricole avant d'utiliser un pesticide.",
            ],
            "confidence": "Moyen",
            "risk_level": "À vérifier",
            "needs_human_confirmation": True,
            "confirmation": "Montrez la plante a un agent agricole pour confirmer.",
            "disclaimer": "Ceci est un exemple et n'est pas un diagnostic.",
            "sources": [_VISION_SOURCE],
        },
    },
}


def get_demo_example(example_id: str) -> dict | None:
    """Return a copy of a public demo example, or None if it does not exist."""
    example = DEMO_EXAMPLES.get(example_id)
    if example is None:
        return None
    return deepcopy(example)
