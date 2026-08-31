"""Shared field-case data contract used by builders and demo examples."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


DEFAULT_DISEASE_CONFIRMATION = "Montrez la plante à un agent agricole pour confirmer."
DEFAULT_ADVICE_CONFIRMATION = "Confirmez avec un agent agricole local avant une décision coûteuse."

_CASE_TITLES = {
    "image": "Cas de terrain - feuille",
    "fertilizer": "Conseil engrais",
    "text": "Conseil agricole",
}


def case_title_for(input_type: str) -> str:
    """Return the stable French heading for a field-case input type."""
    return _CASE_TITLES.get((input_type or "").strip(), "Conseil agricole")


@dataclass(frozen=True)
class DemoCaseProfile:
    """Declarative case metadata kept alongside a quota-safe demo example."""

    input_type: str = "text"
    crop: str = ""
    risk_level: str = "À vérifier"

    @classmethod
    def from_mapping(cls, value: dict | None) -> "DemoCaseProfile":
        data = value or {}
        return cls(
            input_type=(data.get("input_type") or "text").strip(),
            crop=(data.get("crop") or "").strip(),
            risk_level=(data.get("risk_level") or "À vérifier").strip(),
        )


@dataclass
class FieldCase:
    """Stable JSON contract shared by text, fertilizer, and image cases."""

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
