"""Field-case helpers for structured agricultural advice."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

DEFAULT_DISEASE_CONFIRMATION = "Montrez la plante à un agent agricole pour confirmer."
DEFAULT_ADVICE_CONFIRMATION = (
    "Confirmez toujours avec un agent agricole ou un service de vulgarisation local "
    "avant une décision coûteuse."
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

    # Prefer explicit evidence, then source snippets, then heuristic parse.
    evidence_items = _clean_items(evidence) or [
        _clean_text(card.get("snippet"))
        for card in source_cards
        if _clean_text(card.get("snippet"))
    ] or parsed["evidence"]

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
        evidence=_clean_items(evidence_items)[:4],
        actions=_clean_items(actions) or parsed["actions"],
        do_not=_clean_items(do_not) or parsed["do_not"],
        confidence=_clean_text(confidence) or "Moyen",
        risk_level=_clean_text(risk_level) or "À vérifier",
        needs_human_confirmation=True,
        confirmation=_clean_text(confirmation) or DEFAULT_ADVICE_CONFIRMATION,
        disclaimer=_clean_text(disclaimer),
        sources=source_cards,
        case_title=case_title_for(cleaned_type),
        weather_signals=_clean_items(weather_signals)[:4],
    )
    return case.to_dict()
