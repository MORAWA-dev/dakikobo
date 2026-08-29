"""French simple mode helpers for field-facing answers.

Goal: keep French primary, but make answers easier for farmers with lower
literacy or less technical vocabulary — without inventing agronomy content.

Two layers:
1. Prompt-side style instruction (appended to the retrieval query).
2. Deterministic glossary footnotes for technical terms that remain in the answer.
"""

from __future__ import annotations

import re
from typing import Iterable

# Style instruction appended to RAG queries when simple mode is on.
# Kept short so it does not dominate retrieval.
SIMPLE_STYLE_INSTRUCTION = (
    "Répondez en français très simple : phrases courtes, mots du quotidien, "
    "pas de jargon inutile. Expliquez un terme technique seulement s'il est "
    "indispensable. Restez prudent et n'inventez pas de doses ou de dates."
)

# Technical term -> plain French explanation (Burkina field vocabulary).
# Keys should be matched case-insensitively as whole-ish phrases.
GLOSSARY: dict[str, str] = {
    # Crops / agronomy
    "semis": "mettre les graines en terre",
    "repiquage": "replanter un jeune plant",
    "levée": "quand la graine sort de terre",
    "montaison": "quand la tige monte et pousse vite",
    "floraison": "quand la plante fait des fleurs",
    "fructification": "quand les fruits ou épis se forment",
    "maturité": "quand la culture est prête à récolter",
    "sarclage": "enlever les mauvaises herbes",
    "binage": "ameublir le sol autour des plants",
    "paillage": "couvrir le sol avec de la paille ou des restes de plantes",
    "mulching": "couvrir le sol pour garder l'humidité",
    "rotation": "changer de culture d'une année à l'autre sur la même parcelle",
    "association culturale": "cultiver deux cultures ensemble",
    "jachère": "laisser la terre se reposer sans culture",
    "poquet": "petit trou où l'on met les graines",
    "densité de semis": "nombre de plants par surface",
    "écimage": "couper le haut de la plante",
    # Fertilizer / soil
    "NPK": "engrais qui apporte azote, phosphore et potassium",
    "urée": "engrais riche en azote (pour la croissance verte)",
    "fumure": "apport d'engrais ou de fumier",
    "fumure organique": "fumier, compost ou restes de plantes pour nourrir le sol",
    "microdose": "petite quantité d'engrais mise près de la graine",
    "dose vulgarisée": "quantité d'engrais recommandée en vulgarisation",
    "azote": "élément qui aide la plante à devenir verte et pousser",
    "phosphore": "élément qui aide les racines et la formation des grains",
    "potassium": "élément qui renforce la plante face au stress",
    "pH": "mesure de l'acidité du sol",
    "matière organique": "restes de plantes et d'animaux dans le sol",
    "lessivage": "quand la pluie emporte l'engrais dans le sol en profondeur",
    "stress hydrique": "manque d'eau pour la plante",
    "évapotranspiration": "eau perdue par le sol et les plantes",
    "rétention d'eau": "capacité du sol à garder l'eau",
    "texture du sol": "si le sol est plutôt sableux, limoneux ou argileux",
    # Weather / climate
    "pluie utile": "pluie qui aide vraiment la culture",
    "début de saison": "début des pluies utiles pour semer",
    "fenêtre de semis": "période favorable pour semer",
    "sécheresse": "longue période sans assez de pluie",
    # Plant health
    "chlorose": "feuilles qui jaunissent par manque d'éléments ou maladie",
    "nécrose": "partie de feuille ou de tige qui meurt et sèche",
    "taches foliaires": "taches sur les feuilles",
    "flétrissement": "plante qui se ramollit et s'affaisse",
    "ravageur": "insecte ou animal qui abîme la culture",
    "pathogène": "microbe qui peut rendre la plante malade",
    "fongicide": "produit contre les champignons (à confirmer avec un agent)",
    "herbicide": "produit contre les mauvaises herbes (à confirmer avec un agent)",
    "insecticide": "produit contre les insectes (à confirmer avec un agent)",
    # Institutions / programmes (Burkina)
    "OAPH": "Offensive Agropastorale et Halieutique (programme national 2023-2025)",
    "MAERAH": "ministère de l'Agriculture, de l'Élevage et des Ressources halieutiques",
    "agent agricole": "conseiller de terrain qui connaît votre zone",
    "vulgarisation": "conseils agricoles donnés aux producteurs",
}

_TRUTHY = {"1", "true", "yes", "oui", "on", "simple", "fr_simple"}


def is_simple_mode(value) -> bool:
    """Parse form/query flag for French simple mode."""
    if value is True:
        return True
    if value is False or value is None:
        return False
    return str(value).strip().lower() in _TRUTHY


def apply_simple_style_to_query(query: str) -> str:
    """Append a short style instruction so the LLM prefers plain French."""
    q = (query or "").strip()
    if not q:
        return q
    if SIMPLE_STYLE_INSTRUCTION in q:
        return q
    return f"{q}\n({SIMPLE_STYLE_INSTRUCTION})"


def _find_terms(text: str) -> list[str]:
    """Return glossary keys present in text, longest-first to prefer phrases."""
    if not text:
        return []
    lowered = text.lower()
    # Prefer multi-word keys first.
    keys = sorted(GLOSSARY.keys(), key=lambda k: (-len(k), k.lower()))
    found: list[str] = []
    for key in keys:
        pattern = re.compile(re.escape(key), re.IGNORECASE)
        if pattern.search(text) or key.lower() in lowered:
            # Avoid duplicate concepts already covered by a longer key.
            if any(key.lower() in other.lower() and key != other for other in found):
                continue
            found.append(key)
    return found


def glossary_notes(text: str, *, max_terms: int = 5) -> list[str]:
    """Build short plain-French notes for technical terms found in the answer."""
    notes = []
    for key in _find_terms(text)[: max(0, max_terms)]:
        notes.append(f"{key} : {GLOSSARY[key]}")
    return notes


def enrich_answer_with_glossary(answer: str, *, max_terms: int = 5) -> str:
    """Append a compact 'Mots simples' block when technical terms appear."""
    text = (answer or "").rstrip()
    if not text:
        return text
    notes = glossary_notes(text, max_terms=max_terms)
    if not notes:
        return text
    # Avoid double-append if already enriched.
    if "Mots simples :" in text or "Mots simples:" in text:
        return text
    block = "\n\nMots simples :\n- " + "\n- ".join(notes)
    return text + block


def light_replacements(text: str) -> str:
    """Optional light wording swaps for a few heavy phrases (safe, non-dose)."""
    if not text:
        return text
    replacements: Iterable[tuple[str, str]] = (
        (r"\bConfirmez toujours avec votre agent agricole\b",
         "Demandez toujours confirmation à votre agent agricole"),
        (r"\brecommandations générales issues de la recherche\b",
         "conseils généraux tirés de la recherche"),
        (r"\bobservation de parcelle\b", "visite de votre champ"),
        (r"\bstress hydrique\b", "manque d'eau"),
    )
    out = text
    for pattern, repl in replacements:
        out = re.sub(pattern, repl, out, flags=re.IGNORECASE)
    return out


def simplify_answer(answer: str, *, max_terms: int = 5) -> str:
    """Apply light replacements while preserving notes for replaced terms."""
    original = answer or ""
    simplified = light_replacements(original)
    notes = glossary_notes(original, max_terms=max_terms)
    if not simplified or not notes:
        return simplified
    if "Mots simples :" in simplified or "Mots simples:" in simplified:
        return simplified
    return simplified.rstrip() + "\n\nMots simples :\n- " + "\n- ".join(notes)
