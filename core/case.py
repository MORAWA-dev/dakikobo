"""Field-case helpers for structured agricultural advice."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

DEFAULT_DISEASE_CONFIRMATION = "Montrez la plante à un agent agricole pour confirmer."
DEFAULT_ADVICE_CONFIRMATION = "Confirmez avec un agent agricole local avant une décision coûteuse."

# Livelihood / market profiles often match crop names but are weak field advice.
_WEAK_DISPLAY_SOURCE_MARKERS = (
    "fews",
    "moyens d'existence",
    "livelihood",
    "profil des moyens",
    "zones socio",
    "household survey",
)

_CASE_TITLES = {
    "image": "Cas de terrain - feuille",
    "fertilizer": "Conseil engrais",
    "text": "Conseil agricole",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_text(value: str | None) -> str:
    return (value or "").strip()


def _clean_items(values) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    cleaned = []
    for value in values:
        text = _clean_text(str(value))
        if text:
            cleaned.append(text)
    return cleaned


def is_usable_field_sentence(text: str) -> bool:
    """Reject market lists / livelihood-profile dumps as fake 'evidence'."""
    t = _clean_text(text)
    if len(t) < 18 or len(t) > 320:
        return False
    lower = t.lower()
    # FEWS-style commercial route noise often appears in RAG snippets.
    noise_hits = 0
    for marker in (
        "route commerciale",
        "marchés villageois",
        "marches villageois",
        "vente de bois",
        "produit route",
        "→",
        "",
        "djibasso",
        "natiaboani",
        "pouytenga",
        "kaibo",
        "porcs volaille",
        "bovins niébé",
        "bovins niebe",
    ):
        if marker in lower:
            noise_hits += 1
    if noise_hits >= 1 and not any(
        k in lower for k in ("parce que", "car ", "selon", "rotation", "azote", "semis")
    ):
        return False
    if t.count(",") >= 5:
        return False
    if t.count("→") + t.count("") >= 1:
        return False
    # Too many title-case tokens in a row often means a market list.
    caps = re.findall(r"\b[A-ZÀÂÄÉÈÊËÎÏÔÖÙÛÜÇ][\w'’-]{2,}\b", t)
    if len(caps) >= 6 and len(t) < 200:
        return False
    return True


def filter_usable_sentences(values) -> list[str]:
    return [item for item in _clean_items(values) if is_usable_field_sentence(item)]


def is_weak_display_source(title: str) -> bool:
    """True for livelihood/FEWS-style titles that clutter field advice cards."""
    lower = _clean_text(title).lower()
    return any(marker in lower for marker in _WEAK_DISPLAY_SOURCE_MARKERS)


def compact_source_cards(sources) -> list[dict]:
    """Keep at most 2 clean source cards; drop empty weak profiles when others exist."""
    cards: list[dict] = []
    for source in sources or []:
        if isinstance(source, dict):
            cards.append(dict(source))
        elif source:
            cards.append({"title": str(source), "type": "Base locale", "snippet": ""})

    for card in cards:
        snip = _clean_text(card.get("snippet"))
        if snip and not is_usable_field_sentence(snip):
            card["snippet"] = ""

    strong = [
        card
        for card in cards
        if not is_weak_display_source(card.get("title", ""))
        or _clean_text(card.get("snippet"))
    ]
    if not strong:
        strong = cards[:1]
    return strong[:2]


def _strip_disclaimer(answer: str, disclaimer: str) -> str:
    answer = _clean_text(answer)
    disclaimer = _clean_text(disclaimer)
    if disclaimer and disclaimer in answer:
        return answer.replace(disclaimer, "").strip()
    return answer


def case_title_for(input_type: str) -> str:
    """French title for a field-case card."""
    return _CASE_TITLES.get(_clean_text(input_type), "Conseil agricole")


def split_french_sentences(text: str) -> list[str]:
    """Small sentence splitter good enough for case-card fallback text."""
    text = _clean_text(text)
    if not text:
        return []
    # Split on sentence ends and bullet-style line breaks.
    normalized = re.sub(r"\n+", "\n", text)
    parts: list[str] = []
    for block in normalized.split("\n"):
        block = block.strip(" •-\t")
        if not block:
            continue
        chunks = re.split(r"(?<=[.!?])\s+", block)
        parts.extend(chunk.strip() for chunk in chunks if chunk.strip())
    return parts


def _fallback_sections(answer: str, disclaimer: str) -> dict[str, list[str]]:
    body = _strip_disclaimer(answer, disclaimer)
    sentences = split_french_sentences(body)
    if not sentences:
        return {
            "observations": [],
            "possible_causes": [],
            "actions": [],
        }

    observations = [sentences[0]]
    causes = []
    actions = []
    action_markers = (
        "verifiez",
        "vérifiez",
        "retirez",
        "enlevez",
        "rincez",
        "apportez",
        "evitez",
        "évitez",
        "surveillez",
        "montrez",
        "reprenez",
        "semez",
        "gardez",
        "utilisez",
        "limitez",
    )
    cause_markers = (
        "pourrait",
        "possible",
        "s'agir",
        "maladie",
        "carence",
        "ravageur",
        "champignon",
        "insecte",
    )

    for sentence in sentences[1:]:
        lower = sentence.lower()
        if any(marker in lower for marker in action_markers):
            actions.append(sentence)
        elif any(marker in lower for marker in cause_markers):
            causes.append(sentence)
        else:
            actions.append(sentence)

    if not causes and len(sentences) > 1:
        causes.append(sentences[1])
    if not actions and len(sentences) > 2:
        actions.extend(sentences[2:])

    return {
        "observations": observations[:2],
        "possible_causes": causes[:3],
        "actions": actions[:3],
    }


def _advice_sections(answer: str, disclaimer: str) -> dict[str, list[str] | str]:
    """Heuristic evidence-first sections for text/fertilizer answers."""
    body = _strip_disclaimer(answer, disclaimer)
    # Drop emoji-heavy headers while keeping useful text.
    body = re.sub(r"[🌱⚠️•]+", " ", body)
    body = re.sub(r"\s+", " ", body).strip()
    sentences = split_french_sentences(body)
    if not sentences:
        return {
            "summary": "",
            "evidence": [],
            "actions": [],
            "do_not": [],
        }

    summary = sentences[0]
    evidence: list[str] = []
    actions: list[str] = []
    do_not: list[str] = []

    evidence_markers = (
        "parce que",
        "car ",
        "selon",
        "issu",
        "recherche",
        "document",
        "source",
        "essai",
        "inera",
        "pourquoi",
        "aide a",
        "aide à",
        "améliore",
        "ameliore",
        "fixe l'azote",
        "fixe l’azote",
    )
    avoid_markers = (
        "evitez",
        "évitez",
        "ne pas",
        "n'augmentez",
        "n’augmentez",
        "n'appliquez",
        "n’appliquez",
        "sans conseil",
        "pas de ",
        "jamais ",
    )
    action_markers = (
        "semez",
        "apportez",
        "utilisez",
        "gardez",
        "surveillez",
        "confirmez",
        "verifiez",
        "vérifiez",
        "limitez",
        "sarclez",
        "dose",
        "microdose",
        "fumure",
        "attendez",
        "observez",
        "retirez",
        "montrez",
        "pratique",
        "recommande",
    )

    for sentence in sentences[1:]:
        lower = sentence.lower()
        if any(marker in lower for marker in avoid_markers):
            do_not.append(sentence)
        elif any(marker in lower for marker in evidence_markers):
            evidence.append(sentence)
        elif any(marker in lower for marker in action_markers):
            actions.append(sentence)
        else:
            actions.append(sentence)

    if not actions and len(sentences) > 1:
        actions.append(sentences[1])
    if not evidence and len(sentences) > 2:
        # Prefer a middle sentence as weak evidence rather than inventing content.
        for candidate in sentences[1:]:
            if candidate not in actions and candidate not in do_not:
                evidence.append(candidate)
                break

    return {
        "summary": summary,
        "evidence": evidence[:3],
        "actions": actions[:4],
        "do_not": do_not[:3],
    }


@dataclass
class FieldCase:
    case_id: str
    created_at: str
    input_type: str
    crop: str = ""
    growth_stage: str = ""
    location: str = ""
    question: str = ""
    image_present: bool = False
    answer: str = ""
    summary: str = ""
    observations: list[str] = field(default_factory=list)
    possible_causes: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    do_not: list[str] = field(default_factory=list)
    confidence: str = "Moyen"
    risk_level: str = "À vérifier"
    needs_human_confirmation: bool = True
    confirmation: str = DEFAULT_DISEASE_CONFIRMATION
    disclaimer: str = ""
    sources: list[dict[str, str]] = field(default_factory=list)
    case_title: str = ""
    weather_signals: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        data = asdict(self)
        if not data.get("case_title"):
            data["case_title"] = case_title_for(self.input_type)
        return data


def build_disease_case(
    *,
    answer: str,
    disclaimer: str,
    crop: str = "",
    growth_stage: str = "",
    location: str = "",
    observations=None,
    possible_causes=None,
    actions=None,
    confidence: str = "Moyen",
    risk_level: str = "À vérifier",
    confirmation: str = DEFAULT_DISEASE_CONFIRMATION,
    unclear: bool = False,
) -> dict:
    """Build a JSON-ready field case for a leaf-photo screening."""
    if unclear:
        observations = observations or [
            "La photo ne permet pas une observation fiable de la feuille."
        ]
        possible_causes = possible_causes or []
        actions = actions or [
            "Reprenez une photo nette, de près, en plein jour.",
            "Montrez la plante à un agent agricole si les symptômes persistent.",
        ]
        confidence = "Faible"
        risk_level = "À confirmer"
    else:
        fallback = _fallback_sections(answer, disclaimer)
        observations = _clean_items(observations) or fallback["observations"]
        possible_causes = _clean_items(possible_causes) or fallback["possible_causes"]
        actions = _clean_items(actions) or fallback["actions"]

    case = FieldCase(
        case_id=f"case_{uuid4().hex[:12]}",
        created_at=_now_iso(),
        input_type="image",
        crop=_clean_text(crop),
        growth_stage=_clean_text(growth_stage),
        location=_clean_text(location),
        question="Dépistage photo de feuille",
        image_present=True,
        answer=_clean_text(answer),
        summary="",
        observations=_clean_items(observations),
        possible_causes=_clean_items(possible_causes),
        evidence=[],
        actions=_clean_items(actions),
        do_not=[],
        confidence=_clean_text(confidence) or "Moyen",
        risk_level=_clean_text(risk_level) or "À vérifier",
        needs_human_confirmation=True,
        confirmation=_clean_text(confirmation) or DEFAULT_DISEASE_CONFIRMATION,
        disclaimer=_clean_text(disclaimer),
        sources=[
            {
                "title": "Gemini Vision",
                "type": "Vision",
                "snippet": "Dépistage visuel prudent à partir de la photo envoyée.",
            }
        ],
        case_title=case_title_for("image"),
        weather_signals=[],
    )
    return case.to_dict()


def build_advice_case(
    *,
    answer: str,
    question: str = "",
    input_type: str = "text",
    crop: str = "",
    growth_stage: str = "",
    location: str = "",
    sources=None,
    confidence: str = "Moyen",
    summary: str = "",
    evidence=None,
    actions=None,
    do_not=None,
    disclaimer: str = "",
    confirmation: str = DEFAULT_ADVICE_CONFIRMATION,
    risk_level: str = "À vérifier",
    weather_signals=None,
) -> dict:
    """Build a JSON-ready evidence-first case for text or fertilizer advice."""
    cleaned_type = _clean_text(input_type) or "text"
    if cleaned_type not in {"text", "fertilizer"}:
        cleaned_type = "text"

    parsed = _advice_sections(answer, disclaimer)
    source_cards = []
    for source in sources or []:
        if isinstance(source, dict):
            source_cards.append(dict(source))
        elif source:
            source_cards.append(
                {
                    "title": str(source),
                    "type": "Base locale",
                    "snippet": "",
                }
            )

    # Prefer explicit evidence, then sentences from the answer, then only
    # *usable* source snippets (never FEWS market-route dumps).
    evidence_items = filter_usable_sentences(evidence)
    if not evidence_items:
        evidence_items = filter_usable_sentences(parsed["evidence"])
    if not evidence_items:
        evidence_items = filter_usable_sentences(
            [card.get("snippet") for card in source_cards]
        )

    action_items = filter_usable_sentences(actions) or filter_usable_sentences(
        parsed["actions"]
    )
    # If filters removed everything, keep short heuristic actions from the answer.
    if not action_items:
        action_items = [
            s for s in _clean_items(parsed["actions"]) if 12 <= len(s) <= 220
        ][:3]

    # Prefer one weather signal only (risk first) so cards stay scannable.
    weather_items = _clean_items(weather_signals)
    risk_first = [w for w in weather_items if "risque" in w.lower()]
    weather_items = (risk_first or weather_items)[:1]

    # Evidence: at most one short why-line; never market dumps.
    evidence_items = evidence_items[:1]

    case = FieldCase(
        case_id=f"case_{uuid4().hex[:12]}",
        created_at=_now_iso(),
        input_type=cleaned_type,
        crop=_clean_text(crop),
        growth_stage=_clean_text(growth_stage),
        location=_clean_text(location),
        question=_clean_text(question),
        image_present=False,
        answer=_clean_text(answer),
        summary=_clean_text(summary) or parsed["summary"],
        observations=[],
        possible_causes=[],
        evidence=evidence_items,
        actions=action_items[:3],
        do_not=(
            filter_usable_sentences(do_not)
            or filter_usable_sentences(parsed["do_not"])
        )[:1],
        confidence=_clean_text(confidence) or "Moyen",
        risk_level=_clean_text(risk_level) or "À vérifier",
        needs_human_confirmation=True,
        confirmation=_clean_text(confirmation) or DEFAULT_ADVICE_CONFIRMATION,
        disclaimer=_clean_text(disclaimer),
        sources=compact_source_cards(source_cards),
        case_title=case_title_for(cleaned_type),
        weather_signals=weather_items,
    )
    return case.to_dict()
