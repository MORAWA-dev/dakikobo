"""Quota-safe public demo examples for the DakiKobo UI."""

from __future__ import annotations

from copy import deepcopy

from core.case import build_advice_case
from core.case_contract import DemoCaseProfile
from core.fertilizer import get_fertilizer_advice


_TEXT_SOURCE = {
    "title": "Exemple DakiKobo - base locale",
    "type": "Base locale",
    "snippet": "Reponse de demonstration preparee pour presenter le comportement du chatbot sans appeler le LLM.",
}

_VISION_SOURCE = {
    "title": "Exemple DakiKobo - depistage photo",
    "type": "Vision",
    "snippet": "Cas de demonstration prepare pour montrer la carte de depistage sans appeler Gemini.",
}

_MAERAH_SOURCE = {
    "title": "MAERAH Burkina Faso - orientation institutionnelle et OAPH 2023-2025",
    "type": "Source web revue",
    "snippet": "OAPH = Offensive Agropastorale et Halieutique 2023-2025 (programme national).",
    "publisher": "MAERAH",
    "year": "2026",
    "country": "Burkina Faso",
    "review_status": "Validé par le propriétaire",
    "url": "https://www.agriculture.bf/offensive-agropastorale-et-halieutique-2023-2025/",
}

_IITA_SOURCE = {
    "title": "IITA 2018 - Production du niebe en Afrique de l'Ouest",
    "type": "Base locale",
    "snippet": "Le niebe fixe une partie de l'azote et s'inscrit dans les rotations avec les cereales.",
}

_CILSS_SOURCE = {
    "title": "CILSS - orientation regionale Sahel et Afrique de l'Ouest",
    "type": "Source web revue",
    "snippet": "Organisation regionale pour la secheresse, la resilience et la securite alimentaire.",
    "publisher": "CILSS",
    "year": "2026",
    "country": "Sahel / Afrique de l'Ouest",
    "review_status": "Validé par le propriétaire",
    "url": "https://www.cilss.int/",
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
            "La rotation niébé-céréales aide la fertilite du systeme cultural parce que "
            "le niebe fixe une partie de l'azote atmospherique, ce qui peut profiter "
            "aux cereales (mil, sorgho, mais) qui suivent. Elle limite aussi la "
            "dominance de certaines mauvaises herbes et de problemes lies a une "
            "monoculture. Confirmez le schema de rotation avec un agent agricole "
            "selon votre sol et vos pluies."
        ),
        "sources": [_IITA_SOURCE],
        "confidence": "Moyen",
        "audio_url": "",
    },
    "oaph_burkina": {
        "kind": "message",
        "question": "C'est quoi l'OAPH au Burkina Faso ?",
        "answer": (
            "L'OAPH 2023-2025 est l'Offensive Agropastorale et Halieutique, un plan "
            "operationnel national porte par le MAERAH pour renforcer la production "
            "agricole, pastorale et halieutique et la souverainete alimentaire. "
            "Ce n'est pas un office d'amenagements. Les pratiques de parcelle "
            "(doses, calendriers) restent a confirmer avec un agent agricole local."
        ),
        "sources": [_MAERAH_SOURCE],
        "confidence": "Fort",
        "audio_url": "",
    },
    "cilss_sahel": {
        "kind": "message",
        "question": "C'est quoi le CILSS ?",
        "answer": (
            "Le CILSS est le Comite permanent Inter-Etats de Lutte contre la "
            "Secheresse dans le Sahel. C'est une organisation regionale qui "
            "travaille sur la secheresse, la resilience et la securite alimentaire "
            "en Afrique de l'Ouest et au Sahel. Cela n'indique pas la pluie exacte "
            "sur votre parcelle : pour le court terme, utilisez l'outil meteo, "
            "puis confirmez avec les services nationaux. Les bulletins AGRHYMET "
            "ne sont pas encore indexes ici."
        ),
        "sources": [_CILSS_SOURCE],
        "confidence": "Moyen",
        "audio_url": "",
    },
    "hors_sujet": {
        "kind": "message",
        "question": "Comment réparer un moteur de voiture ?",
        "answer": (
            "Je ne sais pas encore. Cette information n'est pas disponible dans la "
            "base de donnees de DakiKobo pour le Burkina Faso. Posez une question "
            "agricole (cultures, engrais, humidite, photo de feuille) pour un "
            "conseil prudent et source."
        ),
        "sources": [],
        "confidence": "Faible",
        "audio_url": "",
        "answer_kind": "refusal",
    },
    # The fertilizer example is never hardcoded: its response is produced by the
    # deterministic gate in core/fertilizer at request time (see get_demo_example),
    # so it shows exactly what /ask would — the gated refusal while
    # NUMERIC_GUIDANCE_VERIFIED is False, and the reviewed doses only once an
    # agronomist flips that gate. Exact figures never live in this demo file.
    "fumure_sorgho": {
        "kind": "fertilizer_gate",
        "question": "Quelle dose d'engrais pour le sorgho ?",
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


def _fertilizer_gate_example(result: dict) -> dict:
    """Build the fertilizer demo from the deterministic gate.

    The exact same output a farmer sees at ``/ask``: the gated refusal while
    numeric guidance is unverified, or the reviewed advice once an agronomist
    turns the gate on. No dose figure is ever stored in this module.
    """
    question = result.get("question", "")
    advice = get_fertilizer_advice(question) or {}
    return {
        "kind": "message",
        "question": question,
        "answer": advice.get("answer", ""),
        "sources": advice.get("sources") or [],
        "confidence": advice.get("confidence") or "Faible",
        "audio_url": "",
        "answer_kind": advice.get("answer_kind", "refusal"),
        "case": advice.get("case"),
        "answer_path": "fertilizer",
    }


def get_demo_example(example_id: str) -> dict | None:
    """Return a copy of a public demo example, or None if it does not exist."""
    example = DEMO_EXAMPLES.get(example_id)
    if example is None:
        return None
    result = deepcopy(example)

    # The fertilizer demo is generated by the deterministic gate, so approved
    # figures can only ever be released through core.fertilizer, never from a
    # static string in this file.
    if result.get("kind") == "fertilizer_gate":
        return _fertilizer_gate_example(result)

    profile = DemoCaseProfile.from_mapping(result.pop("_case_profile", None))
    # Text/fertilizer demos get the same evidence-first card shape as live /ask.
    # Refusals stay plain (no fake evidence card).
    if example_id == "hors_sujet" or result.get("answer_kind") == "refusal":
        result["answer_kind"] = "refusal"
        result.pop("case", None)
        return result
    if result.get("kind") == "message" and not result.get("case"):
        result["case"] = build_advice_case(
            answer=result.get("answer", ""),
            question=result.get("question", ""),
            input_type=profile.input_type,
            crop=profile.crop,
            sources=result.get("sources") or [],
            confidence=result.get("confidence") or "Moyen",
            risk_level=profile.risk_level,
        )
    return result
