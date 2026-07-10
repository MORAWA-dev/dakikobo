"""Resolve effective crop/location from the question vs parcelle form.

Stale form context (e.g. culture=sorgho · lieu=Ouagadougou) must not hijack a
question about another crop or place. Short follow-ups like "ok à Ouagadougou"
must keep the previous topic.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# Question-side crop aliases (broader than fertilizer tool set).
_CROP_ALIASES: dict[str, str] = {
    "sorgho": "sorgho",
    "sorghum": "sorgho",
    "mil": "mil",
    "millet": "mil",
    "petit mil": "mil",
    "maïs": "maïs",
    "mais": "maïs",
    "maize": "maïs",
    "niébé": "niébé",
    "niebe": "niébé",
    "cowpea": "niébé",
    "haricot": "niébé",
    "arachide": "arachide",
    "arachides": "arachide",
    "groundnut": "arachide",
    "cacahuète": "arachide",
    "cacahuete": "arachide",
    "soja": "soja",
    "soya": "soja",
    "soybean": "soja",
    "coton": "coton",
    "riz": "riz",
    "sésame": "sésame",
    "sesame": "sésame",
    "fonio": "fonio",
}

# Common Burkina place names (normalized key -> display label).
_LOCATION_ALIASES: dict[str, str] = {
    "ouagadougou": "Ouagadougou",
    "ouaga": "Ouagadougou",
    "bobo": "Bobo-Dioulasso",
    "bobo-dioulasso": "Bobo-Dioulasso",
    "bobodioulasso": "Bobo-Dioulasso",
    "kaya": "Kaya",
    "dori": "Dori",
    "koudougou": "Koudougou",
    "ouahigouya": "Ouahigouya",
    "banfora": "Banfora",
    "fada": "Fada N'Gourma",
    "fada n'gourma": "Fada N'Gourma",
    "tenkodogo": "Tenkodogo",
    "dedougou": "Dédougou",
    "dédougou": "Dédougou",
    "mogtedo": "Mogtédo",
    "mogtédo": "Mogtédo",
    "pouytenga": "Pouytenga",
    "koupela": "Koupéla",
    "koupéla": "Koupéla",
    "ziniare": "Ziniaré",
    "ziniaré": "Ziniaré",
    "manga": "Manga",
    "gaoua": "Gaoua",
    "kongoussi": "Kongoussi",
}


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower().strip()


def detect_crop_in_text(text: str) -> str:
    """Return canonical crop named in free text, or empty string."""
    t = _normalize(text)
    if not t:
        return ""
    for alias in sorted(_CROP_ALIASES, key=len, reverse=True):
        if re.search(rf"(?<!\w){re.escape(_normalize(alias))}(?!\w)", t):
            return _CROP_ALIASES[alias]
    return ""


def detect_location_in_text(text: str) -> str:
    """Return a display location if a known place is named, else empty."""
    t = _normalize(text)
    if not t:
        return ""
    for alias in sorted(_LOCATION_ALIASES, key=len, reverse=True):
        if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", t):
            return _LOCATION_ALIASES[alias]
    return ""


def is_short_followup(text: str) -> bool:
    """True for short clarifications that need the previous user question."""
    t = (text or "").strip()
    if not t:
        return False
    words = re.findall(r"\w+", t, flags=re.UNICODE)
    if len(words) > 12:
        return False
    lower = t.lower()
    # Location-only or ack + place ("ok a ouagadougou", "à Kaya", "et à Bobo").
    if detect_location_in_text(t) and not detect_crop_in_text(t):
        return True
    if re.match(r"^(ok|oui|non|et|donc|alors|merci)\b", lower) and len(words) <= 8:
        return True
    # Stage-only or very short continuation.
    if len(words) <= 5 and not detect_crop_in_text(t):
        return True
    return False


def expand_with_prior(query: str, prior_question: str) -> str:
    """Join a short follow-up with the previous user question for retrieval."""
    query = (query or "").strip()
    prior = (prior_question or "").strip()
    if not prior or not query or not is_short_followup(query):
        return query
    # Avoid infinite stacking if prior already includes this line.
    if query.lower() in prior.lower():
        return prior
    return (
        f"{prior}\n"
        f"(Précision de l'utilisateur: {query})"
    )


@dataclass(frozen=True)
class ResolvedQueryContext:
    """Effective fields after merging question text with the parcelle form."""

    retrieval_query: str
    crop: str
    growth_stage: str
    location: str
    form_crop: str
    form_location: str
    question_crop: str
    question_location: str
    crop_conflict: bool
    expanded_from_prior: bool

    def as_case_fields(self) -> dict[str, str]:
        return {
            "crop": self.crop,
            "growth_stage": self.growth_stage,
            "location": self.location,
        }


def resolve_query_context(
    query: str,
    form_context: dict[str, str] | None = None,
    *,
    prior_question: str = "",
) -> ResolvedQueryContext:
    """Merge free-text question with optional form context for RAG and cards.

    Priority:
    1. Crop/location named in the (expanded) question win.
    2. Form values fill gaps only when they do not contradict the question.
    3. Growth stage from the form is kept only when form crop matches effective crop
       (or form crop is empty).
    """
    form = form_context or {}
    form_crop = (form.get("crop") or "").strip()
    form_stage = (form.get("growth_stage") or "").strip()
    form_location = (form.get("location") or "").strip()

    raw_query = (query or "").strip()
    prior = (prior_question or "").strip()
    expanded = expand_with_prior(raw_query, prior)
    expanded_from_prior = expanded != raw_query

    # Detect on the expanded text so "ok à Ouagadougou" + prior soja keeps soja.
    question_crop = detect_crop_in_text(expanded)
    question_location = detect_location_in_text(expanded)

    # Also check prior alone for crop if still missing.
    if not question_crop and prior:
        question_crop = detect_crop_in_text(prior)

    crop = question_crop or form_crop
    location = question_location or form_location

    crop_conflict = bool(
        question_crop
        and form_crop
        and _normalize(question_crop) != _normalize(form_crop)
    )

    # Do not apply a stale stage from another crop.
    if crop_conflict:
        growth_stage = ""
    elif form_crop and crop and _normalize(form_crop) != _normalize(crop):
        growth_stage = ""
    else:
        growth_stage = form_stage

    retrieval_query = _build_retrieval_query(
        user_text=expanded,
        crop=crop,
        growth_stage=growth_stage,
        location=location,
        form_crop=form_crop,
        question_crop=question_crop,
        crop_conflict=crop_conflict,
    )

    return ResolvedQueryContext(
        retrieval_query=retrieval_query,
        crop=crop,
        growth_stage=growth_stage,
        location=location,
        form_crop=form_crop,
        form_location=form_location,
        question_crop=question_crop,
        question_location=question_location,
        crop_conflict=crop_conflict,
        expanded_from_prior=expanded_from_prior,
    )


def _build_retrieval_query(
    *,
    user_text: str,
    crop: str,
    growth_stage: str,
    location: str,
    form_crop: str,
    question_crop: str,
    crop_conflict: bool,
) -> str:
    """Append only non-conflicting context hints for retrieval + prompt."""
    parts: list[str] = []
    if crop:
        parts.append(f"culture: {crop}")
    if growth_stage:
        parts.append(f"stade: {growth_stage}")
    if location:
        parts.append(f"lieu: {location}")

    notes: list[str] = []
    if crop_conflict:
        notes.append(
            f"La question porte sur {question_crop}, pas sur {form_crop}. "
            f"Répondez pour {question_crop}."
        )
    elif question_crop:
        notes.append(f"Répondez pour la culture nommée dans la question: {question_crop}.")

    if not parts and not notes:
        return user_text

    suffix_bits = []
    if parts:
        suffix_bits.append("Contexte utile: " + " · ".join(parts))
    if notes:
        suffix_bits.append(" ".join(notes))
    return f"{user_text}\n({' '.join(suffix_bits)})"
