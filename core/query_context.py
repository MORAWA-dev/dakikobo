"""Resolve effective crop/location from the question vs parcelle form.

Stale form context (e.g. culture=sorgho · lieu=Ouagadougou) must not hijack a
question about another crop or place. Short follow-ups like "ok à Ouagadougou"
must keep the previous topic.

Crop and place vocabularies are no longer duplicated here: detection delegates
to the ``core.crops`` / ``core.places`` registries (A1), so this module and the
weather/soil/fertilizer paths always agree on what a crop or place is called.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from core.crops import resolve_crop
from core.places import resolve_place


_OAPH_RETRIEVAL_EXPANSION = (
    "OAPH = Offensive Agropastorale et Halieutique 2023-2025, "
    "programme national du MAERAH"
)


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower().strip()


def detect_crop_in_text(text: str) -> str:
    """Return canonical French crop label named in free text, or empty string."""
    crop = resolve_crop(text)
    return crop.label_fr if crop else ""


def detect_crop_id_in_text(text: str) -> str:
    """Return the ascii crop id named in free text, or empty string."""
    crop = resolve_crop(text)
    return crop.id if crop else ""


def detect_location_in_text(text: str) -> str:
    """Return a display location if a known place is named, else empty."""
    place = resolve_place(text)
    return place.label_fr if place else ""


def detect_location_id_in_text(text: str) -> str:
    """Return the slug place id named in free text, or empty string."""
    place = resolve_place(text)
    return place.id if place else ""


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


def _expand_reviewed_retrieval_terms(query: str) -> str:
    """Add verified meanings for acronyms whose short form retrieves noisily."""
    if not re.search(r"\bOAPH\b", query or "", flags=re.IGNORECASE):
        return query
    if "Offensive Agropastorale et Halieutique" in query:
        return query
    return f"{query}\n(Terme vérifié : {_OAPH_RETRIEVAL_EXPANSION}.)"


@dataclass(frozen=True)
class ResolvedQueryContext:
    """Effective fields after merging question text with the parcelle form.

    Carries the id/label pair for both crop and place (§7.2): ``*_id`` is the
    registry slug used for cache keys and weather/soil/fertilizer lookups,
    ``*_label_fr`` is the French display/prompt text. ``crop``/``location``
    remain the label-valued fields the prompt and the card already use, so
    retrieval and card output stay byte-identical.
    """

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
    crop_id: str = ""
    crop_label_fr: str = ""
    place_id: str = ""
    place_label_fr: str = ""
    simple_french: bool = False

    def as_case_fields(self) -> dict[str, str]:
        return {
            "crop": self.crop_label_fr or self.crop,
            "growth_stage": self.growth_stage,
            "location": self.place_label_fr or self.location,
        }


def resolve_query_context(
    query: str,
    form_context: dict[str, str] | None = None,
    *,
    prior_question: str = "",
    simple_french: bool = False,
) -> ResolvedQueryContext:
    """Merge free-text question with optional form context for RAG and cards.

    Priority:
    1. Crop/location named in the (expanded) question win.
    2. Form values fill gaps only when they do not contradict the question.
    3. Growth stage from the form is kept only when form crop matches effective crop
       (or form crop is empty).
    """
    form = form_context or {}
    form_crop_raw = (form.get("crop") or "").strip()
    form_stage = (form.get("growth_stage") or "").strip()
    form_location_raw = (form.get("location") or "").strip()

    # Browser selects submit stable registry ids. Convert those ids (and any
    # accepted aliases from older clients) to French labels before they reach
    # the prompt or the farmer-facing card.
    form_crop_entry = resolve_crop(form_crop_raw) if form_crop_raw else None
    form_place_entry = resolve_place(form_location_raw) if form_location_raw else None
    form_crop = form_crop_entry.label_fr if form_crop_entry else form_crop_raw
    form_location = (
        form_place_entry.label_fr if form_place_entry else form_location_raw
    )

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
    retrieval_query = _expand_reviewed_retrieval_terms(retrieval_query)

    # Registry ids for cache keys and weather/soil/fertilizer lookups. Resolving
    # the effective label back through the registry keeps form-supplied values
    # (which may be aliases or unaccented) on the same vocabulary as the question.
    resolved_crop = resolve_crop(crop) if crop else None
    resolved_place = resolve_place(location) if location else None

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
        crop_id=resolved_crop.id if resolved_crop else "",
        crop_label_fr=resolved_crop.label_fr if resolved_crop else crop,
        place_id=resolved_place.id if resolved_place else "",
        place_label_fr=resolved_place.label_fr if resolved_place else location,
        simple_french=simple_french,
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
