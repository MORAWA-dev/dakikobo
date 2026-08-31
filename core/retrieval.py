"""Retrieval citation logic, extracted out of Flask so it is unit-testable (A2).

This module owns the citation policy: which retrieved chunks become source
cards, how they are ranked, and what confidence label the answer earns. It has
no Flask dependency and never touches the network. The vector-store relevance
scores are injected by the caller as a query-less ``score_lookup`` callable, so
this module can be exercised directly in tests without a Flask client or a
running Chroma store.
"""

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field

from config import (
    CITATION_SCORE_MARGIN,
    CONFIDENCE_MEDIUM_SCORE,
    CONFIDENCE_STRONG_SCORE,
    MAX_RAG_SOURCES,
)


# ---------------------------------------------------------------------------
# Public surface (locked by the execution spec)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SourceCard:
    """A single, UI-friendly citation for a retrieved source document.

    ``score`` and ``confidence`` are internal policy metadata; ``as_dict``
    intentionally keeps the existing farmer-facing ``/ask`` JSON shape.
    """

    title: str
    publisher: str = ""
    year: str = ""
    review_status: str = ""
    url: str = ""
    score: float = 0.0
    confidence: str = ""
    type: str = "Base locale"
    snippet: str = ""
    country: str = ""

    def as_dict(self) -> dict:
        """Serialize without exposing internal ranking fields."""
        card = {
            "title": self.title,
            "type": self.type,
            "snippet": self.snippet,
        }
        for key in ("publisher", "year", "country", "review_status", "url"):
            value = getattr(self, key)
            if value:
                card[key] = value
        return card


@dataclass(frozen=True)
class GroundedAnswer:
    """The grounded citation + confidence result for one retrieval."""

    sources: list[SourceCard]
    confidence: str  # "Fort" | "Moyen" | "Faible"
    retrieved_chunk_ids: list[str]  # sha256(source|content[:64])[:16]
    evidence_decisions: list["EvidenceDecision"] = field(default_factory=list)


@dataclass(frozen=True)
class EvidenceDecision:
    """Offline-testable citation decision for one retrieved chunk."""

    chunk_id: str
    source_title: str
    score: float | None
    kept: bool
    demoted_reason: str = ""


def chunk_id(source_title: str, page_content: str) -> str:
    """Stable identifier for one retrieved chunk (used by the cache/ledger)."""
    raw = f"{source_title}|{(page_content or '')[:64]}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


_ACTIVE_MANIFEST_HASH: str | None = None


def set_active_manifest_hash(value: str | None) -> None:
    """Record the corpus manifest hash for the active vector store (Phase 2)."""
    global _ACTIVE_MANIFEST_HASH
    _ACTIVE_MANIFEST_HASH = value


def get_active_manifest_hash() -> str | None:
    """Hash of the manifest used to build the currently loaded vector store."""
    return _ACTIVE_MANIFEST_HASH


def manifest_hash(manifest: dict | None) -> str | None:
    """Derive a stable short hash from a source manifest dict."""
    if not manifest:
        return None
    dumped = json.dumps(manifest, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Moved verbatim from app.py (no behaviour change)
# ---------------------------------------------------------------------------

# Copied from app.py. The labels are the French UI text for each document type.
_DOC_TYPE_LABELS = {
    "fao_report": "Rapport FAO",
    "csa_plan": "Plan CSA",
    "training_manual": "Manuel de formation",
    "research_article": "Article de recherche",
    "country_profile": "Profil pays",
    "program_doc": "Document de programme",
    "survey_report": "Enquête agricole",
    "scraped_web": "Source web revue",
}

_REVIEW_STATUS_LABELS = {
    "reviewed_by_codex_pending_human_review": "Revu, validation humaine à finaliser",
    "source_verified_pending_owner_signoff": "Source vérifiée, signature propriétaire en attente",
    "reviewed_by_codex": "Revu par Codex",
    "reviewed_by_owner": "Validé par le propriétaire",
    "pending_human_review": "À vérifier humainement",
    "pending_verification": "Vérification requise",
}

_CITATION_STOPWORDS = {
    "avec", "dans", "pour", "contre", "comment", "quelle", "quand", "quoi",
    "vous", "votre", "cette", "cela", "faire", "avoir", "etre", "sont",
    "plus", "bien", "agricole", "agriculture", "burkina", "faso", "les",
    "des", "sur", "aux", "une", "est", "son", "ses", "mes", "vos", "nos",
    "par", "pas", "que", "qui", "quel", "elle", "ils", "elles", "leur",
}

_CROP_TOKENS = {
    "arachide", "coton", "fonio", "mais", "mil", "niebe", "riz",
    "sesame", "soja", "sorgho",
}

# Generic or off-scope titles that often pollute crop-specific answers.
# Ranking demotes these when stronger crop-matched sources are available.
_WEAK_SOURCE_MARKERS = (
    "farmer's handbook",
    "farmer_training",
    "basic agriculture",
    "caracteristiques des menages",
    "cartographie des zones socio",
    "zones socio-rurales",
    "agrobusiness",
    "modernisation agricole",
    "comprehensive report",
    "foncier",
    "profil des moyens d'existence",  # seasonal calendar ok for semis; weak for agronomy
    "fews net",
    "fews",
    "moyens d'existence",
    "livelihood",
    "household survey",
    "orpaillage",
)

# Field-practice questions should not lead with livelihood/FEWS-style profiles
# when stronger extension sources exist.
_FIELD_PRACTICE_TOKENS = {
    "rotation",
    "humidite",
    "paillage",
    "mulching",
    "mulch",
    "fumure",
    "engrais",
    "semis",
    "semer",
    "stockage",
    "stocker",
    "bruche",
    "maladie",
    "tache",
    "compost",
    "azote",
    "infiltration",
    "ruissellement",
}

_CITATION_ALIASES = {
    "arachide": {"groundnut", "cacahuete"},
    "bruche": {"bruches", "insecte", "insectes", "ravageur", "ravageurs"},
    "bruches": {"bruche", "insecte", "insectes", "ravageur", "ravageurs"},
    "carence": {"carences", "chlorose", "jaunissement"},
    "chlorose": {"carence", "carences", "jaunissement"},
    "conservation": {"conserver", "stockage", "stocker", "eau", "humidite"},
    "conserver": {"conservation", "stockage", "stocker"},
    "engrais": {"fertilisation", "fertiliser", "fumure"},
    "fertilisation": {"engrais", "fertiliser", "fumure"},
    "fertiliser": {"engrais", "fertilisation", "fumure"},
    "feuille": {"feuilles", "foliaire", "tache", "taches"},
    "feuilles": {"feuille", "foliaire", "tache", "taches"},
    "fumure": {"engrais", "fertilisation", "fertiliser"},
    "humidite": {"paillage", "mulching", "eau", "infiltration", "evaporation"},
    "maladie": {"maladies", "symptome", "symptomes", "feuille", "tache"},
    "maladies": {"maladie", "symptome", "symptomes", "feuille", "tache"},
    "paillage": {"mulching", "mulch", "residus", "humidite"},
    "rotation": {"azote", "legumineuse", "cereales", "fertilite"},
    "semer": {"semis"},
    "semis": {"semer"},
    "stockage": {"conservation", "conserver", "stocker"},
    "stocker": {"conservation", "conserver", "stockage"},
    "symptome": {"maladie", "maladies", "symptomes", "tache", "feuille"},
    "symptomes": {"maladie", "maladies", "symptome", "tache", "feuille"},
    "tache": {"taches", "feuille", "feuilles", "maladie"},
    "taches": {"tache", "feuille", "feuilles", "maladie"},
}


def _short_snippet(text: str, max_chars: int = 150) -> str:
    text = " ".join((text or "").split())
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit(" ", 1)[0]
    return f"{cut}..."


def _normalize_for_match(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower()


def _citation_tokens(text: str) -> set[str]:
    normalized = _normalize_for_match(text)
    tokens = set(re.findall(r"[a-z0-9]{3,}", normalized))
    filtered = {token for token in tokens if token not in _CITATION_STOPWORDS}
    expanded = set()
    for token in filtered:
        expanded.add(token)
        expanded.update(_CITATION_ALIASES.get(token, set()))
    return expanded


def _source_match_texts(source_docs) -> dict[str, str]:
    by_title = {}
    for doc in source_docs:
        title = doc.metadata.get("source", "Inconnu")
        by_title.setdefault(title, []).append(getattr(doc, "page_content", ""))
    return {title: " ".join(texts) for title, texts in by_title.items()}


def _source_tokens(source: dict, match_text: str) -> set[str]:
    source_text = f"{source.get('title', '')} {source.get('snippet', '')} {match_text}"
    return _citation_tokens(source_text)


def _source_overlap(source: dict, query_tokens: set[str], match_text: str = "") -> int:
    if not query_tokens:
        return 0
    return len(query_tokens.intersection(_source_tokens(source, match_text)))


def _is_weak_source_title(title: str) -> bool:
    normalized = _normalize_for_match(title)
    return any(marker in normalized for marker in _WEAK_SOURCE_MARKERS)


def _source_rank_score(title: str, base_score: float, *, heavy: bool = False) -> float:
    """Adjust retrieval score for ranking: demote known weak/generic titles."""
    if not _is_weak_source_title(title):
        return float(base_score)
    # Heavier demotion for field-practice questions (rotation, humidite, etc.).
    penalty = 0.28 if heavy else 0.12
    return float(base_score) - penalty


def _is_field_practice_query(query_tokens: set[str]) -> bool:
    return bool(query_tokens.intersection(_FIELD_PRACTICE_TOKENS))


def _title_crop_hits(title: str, crop_tokens: set[str]) -> int:
    if not crop_tokens:
        return 0
    return len(_citation_tokens(title).intersection(crop_tokens))


def _safe_source_url(metadata: dict) -> str:
    url = (metadata.get("source_url") or "").strip()
    if not url:
        source_file = (metadata.get("source_file") or "").strip()
        if source_file.startswith(("http://", "https://")):
            url = source_file
    if url.startswith(("http://", "https://")):
        return url
    return ""


def _source_card_from_doc(doc) -> dict:
    metadata = getattr(doc, "metadata", {}) or {}
    title = metadata.get("source", "Inconnu")
    doc_type = metadata.get("doc_type", "")
    card = {
        "title": title,
        "type": _DOC_TYPE_LABELS.get(doc_type, "Base locale"),
        "snippet": _short_snippet(getattr(doc, "page_content", "")),
    }
    for key in ("publisher", "year", "country"):
        value = (metadata.get(key) or "").strip()
        if value:
            card[key] = value

    review_status = (metadata.get("review_status") or "").strip()
    review_label = _REVIEW_STATUS_LABELS.get(review_status)
    if review_label:
        card["review_status"] = review_label

    url = _safe_source_url(metadata)
    if url:
        card["url"] = url

    return card


def _format_rag_sources(source_docs) -> list[dict]:
    """Return unique, UI-friendly source cards from retrieved documents.

    The card type reflects the document's `doc_type` metadata when available
    (e.g. "Rapport FAO"), and cards expose reviewed document metadata when
    available: publisher, year, country, review status, and source URL.
    """
    by_title = {}
    for doc in source_docs:
        metadata = getattr(doc, "metadata", {}) or {}
        title = metadata.get("source", "Inconnu")
        if title in by_title:
            continue
        by_title[title] = _source_card_from_doc(doc)
    return sorted(by_title.values(), key=lambda item: item["title"])


def _confidence_from_sources(sources: list[dict]) -> str:
    """Count-based fallback, used only when relevance scores are unavailable."""
    if len(sources) >= 2:
        return "Fort"
    if len(sources) == 1:
        return "Moyen"
    return "Faible"


def _confidence_from_score(top_score: float) -> str:
    """Map the best retrieval relevance score to a confidence label."""
    if top_score >= CONFIDENCE_STRONG_SCORE:
        return "Fort"
    if top_score >= CONFIDENCE_MEDIUM_SCORE:
        return "Moyen"
    return "Faible"


def _as_source_cards(sources: list[dict], scores: dict) -> list[SourceCard]:
    """Coerce internal dict cards to the public SourceCard dataclass."""
    return [
        SourceCard(
            title=source["title"],
            publisher=source.get("publisher", ""),
            year=source.get("year", ""),
            review_status=source.get("review_status", ""),
            url=source.get("url", ""),
            score=scores.get(source["title"], 0.0),
            confidence="",
            type=source.get("type", "Base locale"),
            snippet=source.get("snippet", ""),
            country=source.get("country", ""),
        )
        for source in sources
    ]


def _retrieved_chunk_ids(source_docs) -> list[str]:
    """Stable ids for every retrieved chunk (captured once per retrieval).

    Derived from the full ``source_docs`` list delivered by the vector store,
    not from the filtered citation cards, so the cache/ledger sees exactly the
    chunks that were retrieved for this question.
    """
    ids = []
    for doc in source_docs:
        metadata = getattr(doc, "metadata", {}) or {}
        title = metadata.get("source", "Inconnu")
        ids.append(chunk_id(title, getattr(doc, "page_content", "")))
    return ids


def _evidence_decisions(
    source_docs,
    *,
    scores: dict,
    kept_titles: set[str],
    reasons: dict[str, str],
) -> list[EvidenceDecision]:
    decisions = []
    for doc in source_docs:
        metadata = getattr(doc, "metadata", {}) or {}
        title = metadata.get("source", "Inconnu")
        kept = title in kept_titles
        decisions.append(EvidenceDecision(
            chunk_id=chunk_id(title, getattr(doc, "page_content", "")),
            source_title=title,
            score=float(scores[title]) if title in scores else None,
            kept=kept,
            demoted_reason="" if kept else reasons.get(title, "low_overlap"),
        ))
    return decisions


def merge_scored_evidence(
    scored,
    grounded: GroundedAnswer,
    *,
    similarity_threshold: float,
) -> list[EvidenceDecision]:
    """Overlay exact per-chunk scores and include threshold-dropped candidates."""
    policy_by_chunk = {
        decision.chunk_id: decision
        for decision in grounded.evidence_decisions
    }
    merged = []
    for doc, raw_score in scored:
        metadata = getattr(doc, "metadata", {}) or {}
        title = metadata.get("source", "Inconnu")
        identifier = chunk_id(title, getattr(doc, "page_content", ""))
        policy = policy_by_chunk.get(identifier)
        if policy is None:
            merged.append(EvidenceDecision(
                chunk_id=identifier,
                source_title=title,
                score=float(raw_score),
                kept=False,
                demoted_reason="low_overlap",
            ))
            continue
        merged.append(EvidenceDecision(
            chunk_id=identifier,
            source_title=title,
            score=float(raw_score),
            kept=policy.kept and float(raw_score) >= similarity_threshold,
            demoted_reason=(
                policy.demoted_reason
                if policy.demoted_reason
                else ("" if float(raw_score) >= similarity_threshold else "low_overlap")
            ),
        ))
    return merged


def ground_answer(query: str, source_docs, *, score_lookup) -> GroundedAnswer:
    """Build the source cards and confidence from retrieval relevance scores.

    ``score_lookup`` is a query-less callable returning ``{source_title: score}``;
    it closes over the single scored retrieval for the request. When it returns
    an empty dict (e.g. the vector store is unavailable) the count-based
    heuristic is used instead.

    Drops secondary citations that either miss the query's crop/topic concepts
    or score far below the best match. Demotes known weak/generic titles when
    ranking. Falls back to the count-based heuristic when no scores exist.
    """
    sources = _format_rag_sources(source_docs)
    try:
        scores = score_lookup() or {}
    except Exception as exc:
        # Citation grading is best-effort. Retrieval/LLM output must remain
        # usable even if score aggregation fails unexpectedly.
        print(f"Score lookup failed; using count-based confidence: {exc}")
        scores = {}

    retrieved_ids = _retrieved_chunk_ids(source_docs)
    reasons: dict[str, str] = {}
    if not sources or not scores:
        cards = _as_source_cards(sources, scores)
        kept_titles = {source["title"] for source in sources}
        return GroundedAnswer(
            sources=cards,
            confidence=_confidence_from_sources(sources),
            retrieved_chunk_ids=retrieved_ids,
            evidence_decisions=_evidence_decisions(
                source_docs,
                scores=scores,
                kept_titles=kept_titles,
                reasons=reasons,
            ),
        )

    query_tokens = _citation_tokens(query)
    match_texts = _source_match_texts(source_docs)
    source_tokens = {
        s["title"]: _source_tokens(s, match_texts.get(s["title"], ""))
        for s in sources
    }
    query_crop_tokens = query_tokens.intersection(_CROP_TOKENS)
    query_topic_tokens = query_tokens - query_crop_tokens

    crop_overlaps = {
        title: len(tokens.intersection(query_crop_tokens))
        for title, tokens in source_tokens.items()
    }
    had_crop_filter = False
    if query_crop_tokens and any(crop_overlaps.values()):
        for source in sources:
            if crop_overlaps.get(source["title"], 0) <= 0:
                reasons[source["title"]] = "low_overlap"
        sources = [s for s in sources if crop_overlaps.get(s["title"], 0) > 0]
        had_crop_filter = True

    topic_overlaps = {
        title: len(tokens.intersection(query_topic_tokens))
        for title, tokens in source_tokens.items()
    }
    if query_topic_tokens and any(topic_overlaps.get(s["title"], 0) > 0 for s in sources):
        for source in sources:
            if topic_overlaps.get(source["title"], 0) <= 0:
                reasons[source["title"]] = "low_overlap"
        sources = [s for s in sources if topic_overlaps.get(s["title"], 0) > 0]

    overlaps = {
        s["title"]: _source_overlap(s, query_tokens, match_texts.get(s["title"], ""))
        for s in sources
    }
    if any(overlaps.values()):
        max_overlap = max(overlaps.values())
        min_overlap = max(1, max_overlap - 1) if max_overlap >= 3 else 1
        for source in sources:
            if overlaps.get(source["title"], 0) < min_overlap:
                reasons[source["title"]] = "low_overlap"
        sources = [s for s in sources if overlaps.get(s["title"], 0) >= min_overlap]

    scored_known = [scores[s["title"]] for s in sources if s["title"] in scores]
    if not scored_known:
        cards = _as_source_cards(sources, scores)
        kept_titles = {source["title"] for source in sources}
        return GroundedAnswer(
            sources=cards,
            confidence=_confidence_from_sources(sources),
            retrieved_chunk_ids=retrieved_ids,
            evidence_decisions=_evidence_decisions(
                source_docs,
                scores=scores,
                kept_titles=kept_titles,
                reasons=reasons,
            ),
        )

    top = max(scored_known)
    floor = top - CITATION_SCORE_MARGIN
    kept = [
        s for s in sources
        if s["title"] in scores and scores[s["title"]] >= floor
    ]
    kept_titles_before_margin = {source["title"] for source in kept}
    for source in sources:
        if source["title"] not in kept_titles_before_margin:
            reasons[source["title"]] = "score_margin"
    if not kept:
        kept = [s for s in sources if s["title"] in scores and scores[s["title"]] == top]

    practice_query = _is_field_practice_query(query_tokens)

    # Drop weak generic titles when at least one stronger source remains.
    # If only weak titles remain, keep them but force low confidence below
    # (still better than answering with zero citations after the LLM saw chunks).
    strong = [s for s in kept if not _is_weak_source_title(s["title"])]
    if strong:
        for source in kept:
            if _is_weak_source_title(source["title"]):
                reasons[source["title"]] = "weak_title"
        kept = strong

    if not kept:
        return GroundedAnswer(
            sources=[],
            confidence="Faible",
            retrieved_chunk_ids=retrieved_ids,
            evidence_decisions=_evidence_decisions(
                source_docs,
                scores=scores,
                kept_titles=set(),
                reasons=reasons,
            ),
        )

    # Prefer title crop match, then content crop overlap, then adjusted score.
    ranked = sorted(
        kept,
        key=lambda source: (
            _title_crop_hits(source["title"], query_crop_tokens),
            crop_overlaps.get(source["title"], 0),
            _source_rank_score(
                source["title"],
                scores.get(source["title"], -1.0),
                heavy=practice_query,
            ),
        ),
        reverse=True,
    )

    max_sources = MAX_RAG_SOURCES
    confidence = _confidence_from_score(top)
    # Crop-focused questions without any crop-matching source: keep one card
    # and avoid overstating confidence.
    if query_crop_tokens and not had_crop_filter:
        max_sources = 1
        if confidence == "Fort":
            confidence = "Moyen"
    # If the best remaining citation is still a weak generic source, stay Moyen
    # (or Faible for field-practice questions).
    if ranked and _is_weak_source_title(ranked[0]["title"]):
        max_sources = min(max_sources, 1)
        if practice_query:
            confidence = "Faible"
        elif confidence == "Fort":
            confidence = "Moyen"

    dropped_by_limit = ranked[max_sources:]
    for source in dropped_by_limit:
        reasons[source["title"]] = "score_margin"
    ranked = ranked[:max_sources]
    cards = _as_source_cards(ranked, scores)
    kept_titles = {source["title"] for source in ranked}
    return GroundedAnswer(
        sources=cards,
        confidence=confidence,
        retrieved_chunk_ids=retrieved_ids,
        evidence_decisions=_evidence_decisions(
            source_docs,
            scores=scores,
            kept_titles=kept_titles,
            reasons=reasons,
        ),
    )
