"""Field-case helpers for structured agricultural advice."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


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


def split_french_sentences(text: str) -> list[str]:
    """Small sentence splitter good enough for case-card fallback text."""
    text = _clean_text(text)
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [part.strip() for part in parts if part.strip()]


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
    observations: list[str] = field(default_factory=list)
    possible_causes: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    confidence: str = "Moyen"
    risk_level: str = "À vérifier"
    needs_human_confirmation: bool = True
    confirmation: str = "Montrez la plante à un agent agricole pour confirmer."
    disclaimer: str = ""
    sources: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


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
    confirmation: str = "Montrez la plante à un agent agricole pour confirmer.",
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
        observations=_clean_items(observations),
        possible_causes=_clean_items(possible_causes),
        actions=_clean_items(actions),
        confidence=_clean_text(confidence) or "Moyen",
        risk_level=_clean_text(risk_level) or "À vérifier",
        needs_human_confirmation=True,
        confirmation=_clean_text(confirmation),
        disclaimer=_clean_text(disclaimer),
        sources=[
            {
                "title": "Gemini Vision",
                "type": "Vision",
                "snippet": "Dépistage visuel prudent à partir de la photo envoyée.",
            }
        ],
    )
    return case.to_dict()
