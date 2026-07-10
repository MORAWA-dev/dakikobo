# app.py — DakiKobo Flask entry point

import os
import json
import logging
import re
import unicodedata
from math import ceil
from time import perf_counter, time
from threading import Lock, Thread
from datetime import datetime, timezone
from flask import Flask, render_template, request, jsonify, session, g, has_request_context
from werkzeug.exceptions import RequestEntityTooLarge

from core.rag_pipeline import (
    fetch_website_content,
    load_markdown_from_folder,
    load_pdfs_from_folder,
    list_markdown_files,
    list_pdf_files,
    build_source_manifest,
    initialize_vector_store,
    clear_vector_store,
    vector_store_exists,
    load_vector_store_if_usable,
    text_to_speech_to_static,
)
from core.llm_chain import setup_retrieval_qa
from core.fertilizer import get_fertilizer_advice, is_fertilizer_query
from core.router import classify, INTENT_FERTILIZER
from core.disease import screen_leaf_image, is_configured as disease_configured
from core.speech import (
    SpeechTranscriptionError,
    is_configured as speech_configured,
    transcribe_audio,
)
from core.examples import get_demo_example
from core.case import build_advice_case
from core.case_log import record_feedback, record_outcome
from core import ops_metrics as ops_metrics_mod
from core.weather import (
    WeatherError,
    build_weather_context,
    list_weather_locations,
    resolve_weather_location_id,
)
from core.soil import (
    SoilError,
    build_soil_context,
    list_soil_crops,
    list_soil_locations,
)
from config import (
    KNOWLEDGE_URLS,
    APP_VERSION,
    LOG_LEVEL,
    DATA_FOLDER,
    MARKDOWN_FOLDER,
    PREFER_MARKDOWN_KB,
    LLM_MODEL,
    GEMINI_MODEL,
    STT_MODEL,
    EMBEDDING_MODEL,
    VECTORSTORE_DIR,
    DEBUG,
    SECRET_KEY,
    BOT_NAME,
    BOT_CREATOR,
    CONFIDENCE_STRONG_SCORE,
    CONFIDENCE_MEDIUM_SCORE,
    CITATION_SCORE_MARGIN,
    MAX_RAG_SOURCES,
    REBUILD_VECTORSTORE,
    RAG_WARMUP_ON_START,
    REQUEST_COOLDOWN_SECONDS,
    IMAGE_COOLDOWN_SECONDS,
    MAX_IMAGE_UPLOAD_BYTES,
    MAX_IMAGE_UPLOAD_MB,
    VOICE_COOLDOWN_SECONDS,
    MAX_AUDIO_UPLOAD_BYTES,
    MAX_AUDIO_UPLOAD_MB,
    MAX_QUESTION_CHARS,
    OPS_METRICS_ENABLED,
    OPS_METRICS_MAX_EVENTS,
    CASE_LOG_DB_PATH,
)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(message)s",
)
logger = logging.getLogger("dakikobo")

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = max(MAX_IMAGE_UPLOAD_BYTES, MAX_AUDIO_UPLOAD_BYTES)
app.config["MAX_IMAGE_UPLOAD_BYTES"] = MAX_IMAGE_UPLOAD_BYTES
app.config["MAX_IMAGE_UPLOAD_MB"] = MAX_IMAGE_UPLOAD_MB
app.config["MAX_AUDIO_UPLOAD_BYTES"] = MAX_AUDIO_UPLOAD_BYTES
app.config["MAX_AUDIO_UPLOAD_MB"] = MAX_AUDIO_UPLOAD_MB

# Runtime feedback/case log. SQLite file is generated and git-ignored.
CASE_LOG_DB = CASE_LOG_DB_PATH

# Privacy-safe in-process metrics (reconfigurable via env / tests).
if OPS_METRICS_ENABLED:
    ops_metrics_mod.configure_metrics_store(OPS_METRICS_MAX_EVENTS)


def _set_log_fields(**fields) -> None:
    if not has_request_context():
        return
    current = getattr(g, "log_fields", {})
    current.update({key: value for key, value in fields.items() if value is not None})
    g.log_fields = current


def _log_payload(event: str, **fields) -> None:
    payload = {
        "event": event,
        "timestamp": _utc_now_iso(),
        **fields,
    }
    logger.info(json.dumps(payload, ensure_ascii=False, sort_keys=True))


@app.before_request
def _request_log_start():
    g.request_started_at = perf_counter()
    g.log_fields = {}


@app.after_request
def _request_log_finish(response):
    started_at = getattr(g, "request_started_at", None)
    latency_ms = None
    if started_at is not None:
        latency_ms = round((perf_counter() - started_at) * 1000, 2)

    payload = {
        "method": request.method,
        "route": request.path,
        "endpoint": request.endpoint,
        "status_code": response.status_code,
        "latency_ms": latency_ms,
    }
    payload.update(getattr(g, "log_fields", {}))
    _log_payload("http_request", **payload)
    if OPS_METRICS_ENABLED:
        ops_metrics_mod.metrics_store.record(
            timestamp=_utc_now_iso(),
            **payload,
        )
    return response


def _short_snippet(text: str, max_chars: int = 150) -> str:
    text = " ".join((text or "").split())
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit(" ", 1)[0]
    return f"{cut}..."


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
    "reviewed_by_codex": "Revu par Codex",
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
    "sesame", "sorgho",
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
    "profil des moyens d'existence",  # seasonal calendar ok for semis; still weak for disease
)

_CITATION_ALIASES = {
    "arachide": {"groundnut", "cacahuete"},
    "bruche": {"bruches", "insecte", "insectes", "ravageur", "ravageurs"},
    "bruches": {"bruche", "insecte", "insectes", "ravageur", "ravageurs"},
    "carence": {"carences", "chlorose", "jaunissement"},
    "chlorose": {"carence", "carences", "jaunissement"},
    "conservation": {"conserver", "stockage", "stocker"},
    "conserver": {"conservation", "stockage", "stocker"},
    "engrais": {"fertilisation", "fertiliser", "fumure"},
    "fertilisation": {"engrais", "fertiliser", "fumure"},
    "fertiliser": {"engrais", "fertilisation", "fumure"},
    "feuille": {"feuilles", "foliaire", "tache", "taches"},
    "feuilles": {"feuille", "foliaire", "tache", "taches"},
    "fumure": {"engrais", "fertilisation", "fertiliser"},
    "maladie": {"maladies", "symptome", "symptomes", "feuille", "tache"},
    "maladies": {"maladie", "symptome", "symptomes", "feuille", "tache"},
    "semer": {"semis"},
    "semis": {"semer"},
    "stockage": {"conservation", "conserver", "stocker"},
    "stocker": {"conservation", "conserver", "stockage"},
    "symptome": {"maladie", "maladies", "symptomes", "tache", "feuille"},
    "symptomes": {"maladie", "maladies", "symptome", "tache", "feuille"},
    "tache": {"taches", "feuille", "feuilles", "maladie"},
    "taches": {"tache", "feuille", "feuilles", "maladie"},
}


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


def _source_rank_score(title: str, base_score: float) -> float:
    """Adjust retrieval score for ranking: demote known weak/generic titles."""
    penalty = 0.12 if _is_weak_source_title(title) else 0.0
    return float(base_score) - penalty


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


def _is_refusal(answer: str) -> bool:
    """True when the model returned the grounded 'I don't know' fallback.

    A refusal must never show confidence or sources: retrieval may surface
    weakly related chunks, but the model declined to answer from them.
    """
    text = (answer or "").lower()
    return "ne sais pas encore" in text or "n'est pas disponible dans la base" in text


def _is_uncertain(answer: str) -> bool:
    """True when the model used the first-class 'Je ne peux pas confirmer' path.

    Uncertainty is not a failure: the app still returns a structured case with
    low confidence and requires human confirmation.
    """
    text = (answer or "").lower()
    return "je ne peux pas confirmer" in text


def _no_rag_context_answer() -> str:
    return (
        "Je ne sais pas encore. Cette information n'est pas disponible "
        f"dans la base de données de {BOT_NAME} pour le Burkina Faso."
    )


def _uncertain_fallback_answer() -> str:
    return (
        "Je ne peux pas confirmer. Les documents disponibles ne suffisent pas "
        "pour une réponse ferme sur ce point. Notez ce que vous observez au "
        "champ (culture, stade, symptômes) et confirmez avec un agent agricole "
        f"ou le service de vulgarisation local avant d'agir. {BOT_NAME} privilégie "
        "l'incertitude honnête plutôt qu'une précision inventée."
    )


def _field_context_from_request() -> dict[str, str]:
    """Optional crop / stage / location supplied by the field-context form."""
    crop = (request.form.get("crop") or "").strip()[:80]
    growth_stage = (request.form.get("growth_stage") or "").strip()[:80]
    location = (request.form.get("location") or "").strip()[:120]
    # Treat explicit "je ne sais pas" as unset. Keep "autre" for display/meta.
    if crop.lower() in {"je ne sais pas", "inconnu"}:
        crop = ""
    return {
        "crop": crop,
        "growth_stage": growth_stage,
        "location": location,
    }


def _query_with_field_context(query: str, context: dict[str, str]) -> str:
    """Append parcelle context for retrieval without changing the user wording."""
    parts = []
    if context.get("crop"):
        parts.append(f"culture: {context['crop']}")
    if context.get("growth_stage"):
        parts.append(f"stade: {context['growth_stage']}")
    if context.get("location"):
        parts.append(f"lieu: {context['location']}")
    if not parts:
        return query
    return f"{query}\n(Contexte parcelle: {'; '.join(parts)})"


def _weather_signals_for_location(location_text: str) -> tuple[list[str], dict | None]:
    """Optional weather enrichment when field location maps to a known city."""
    loc_id = resolve_weather_location_id(location_text)
    if not loc_id:
        return [], None
    try:
        weather = build_weather_context(loc_id)
    except (WeatherError, ValueError, Exception) as exc:
        print(f"Weather enrichment skipped for {loc_id}: {exc}")
        return [], None
    signals = []
    for insight in weather.get("insights") or []:
        label = (insight.get("label") or "").strip()
        text = (insight.get("text") or "").strip()
        if label and text:
            signals.append(f"{label} : {text}")
        elif text:
            signals.append(text)
    return signals[:4], weather


def _confidence_from_score(top_score: float) -> str:
    """Map the best retrieval relevance score to a confidence label."""
    if top_score >= CONFIDENCE_STRONG_SCORE:
        return "Fort"
    if top_score >= CONFIDENCE_MEDIUM_SCORE:
        return "Moyen"
    return "Faible"


def _source_scores(query: str) -> dict:
    """Best relevance score per source title for this query.

    Returns an empty dict when the vector store is unavailable (e.g. unit tests
    that mock the chain), which makes callers fall back to count-based logic.
    """
    if _rag_db is None:
        return {}
    try:
        scored = _rag_db.similarity_search_with_relevance_scores(query, k=8)
    except Exception as e:  # never let scoring break an answer
        print(f"Score lookup failed; using count-based confidence: {e}")
        return {}

    best = {}
    for doc, score in scored:
        title = doc.metadata.get("source", "Inconnu")
        if title not in best or score > best[title]:
            best[title] = score
    return best


def _grounded_sources_and_confidence(query: str, source_docs) -> tuple[list[dict], str]:
    """Build the source cards and confidence from retrieval relevance scores.

    Drops secondary citations that either miss the query's crop/topic concepts
    or score far below the best match. Demotes known weak/generic titles when
    ranking. Falls back to the count-based heuristic when no scores exist.
    """
    sources = _format_rag_sources(source_docs)
    scores = _source_scores(query)

    if not sources or not scores:
        return sources, _confidence_from_sources(sources)

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
        sources = [s for s in sources if crop_overlaps.get(s["title"], 0) > 0]
        had_crop_filter = True

    topic_overlaps = {
        title: len(tokens.intersection(query_topic_tokens))
        for title, tokens in source_tokens.items()
    }
    if query_topic_tokens and any(topic_overlaps.get(s["title"], 0) > 0 for s in sources):
        sources = [s for s in sources if topic_overlaps.get(s["title"], 0) > 0]

    overlaps = {
        s["title"]: _source_overlap(s, query_tokens, match_texts.get(s["title"], ""))
        for s in sources
    }
    if any(overlaps.values()):
        max_overlap = max(overlaps.values())
        min_overlap = max(1, max_overlap - 1) if max_overlap >= 3 else 1
        sources = [s for s in sources if overlaps.get(s["title"], 0) >= min_overlap]

    scored_known = [scores[s["title"]] for s in sources if s["title"] in scores]
    if not scored_known:
        return sources, _confidence_from_sources(sources)

    top = max(scored_known)
    floor = top - CITATION_SCORE_MARGIN
    kept = [
        s for s in sources
        if s["title"] in scores and scores[s["title"]] >= floor
    ]
    if not kept:
        kept = [s for s in sources if s["title"] in scores and scores[s["title"]] == top]

    # Drop weak generic titles when at least one stronger source remains.
    strong = [s for s in kept if not _is_weak_source_title(s["title"])]
    if strong:
        kept = strong

    # Prefer title crop match, then content crop overlap, then adjusted score.
    ranked = sorted(
        kept,
        key=lambda source: (
            _title_crop_hits(source["title"], query_crop_tokens),
            crop_overlaps.get(source["title"], 0),
            _source_rank_score(source["title"], scores.get(source["title"], -1.0)),
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
    # If the best remaining citation is still a weak generic source, stay Moyen.
    if ranked and _is_weak_source_title(ranked[0]["title"]) and confidence == "Fort":
        confidence = "Moyen"
        max_sources = min(max_sources, 1)

    return ranked[:max_sources], confidence


def _confidence_for_screen(case: dict | None, has_context: bool) -> str:
    if not has_context:
        return "Faible"
    if case and case.get("confidence"):
        return case["confidence"]
    return "Moyen"


def _limit_label_mb() -> str:
    value = float(app.config["MAX_IMAGE_UPLOAD_MB"])
    return str(int(value)) if value.is_integer() else f"{value:.1f}"


def _audio_limit_label_mb() -> str:
    value = float(app.config["MAX_AUDIO_UPLOAD_MB"])
    return str(int(value)) if value.is_integer() else f"{value:.1f}"


def _rate_limit_response(action: str, cooldown_seconds: float):
    if cooldown_seconds <= 0:
        return None

    now = time()
    key = f"rate_limit_{action}_last_at"
    last_at = float(session.get(key, 0) or 0)
    retry_after = ceil(cooldown_seconds - (now - last_at))

    if retry_after > 0:
        _set_log_fields(
            feature=action,
            outcome="rate_limited",
            failure_type="rate_limit",
            retry_after=retry_after,
        )
        return jsonify({
            "error": (
                f"Veuillez patienter {retry_after} seconde"
                f"{'s' if retry_after > 1 else ''} avant de réessayer."
            ),
            "retry_after": retry_after,
            "confidence": "Faible",
        }), 429

    session[key] = now
    return None


def _upload_too_large_response():
    return jsonify({
        "error": (
            "Le fichier envoyé est trop lourd. "
            f"Pour les photos, utilisez une image de {_limit_label_mb()} Mo maximum."
        ),
        "confidence": "Faible",
    }), 413


def _audio_too_large_response():
    return jsonify({
        "error": (
            "L'enregistrement audio est trop lourd. "
            f"Utilisez une dictée courte de {_audio_limit_label_mb()} Mo maximum."
        ),
        "confidence": "Faible",
    }), 413


# =================================================================
# RAG INITIALIZATION — lazy, cached after the first RAG request
# =================================================================

_rag_chain = None
_rag_db = None
_rag_lock = Lock()
_rag_warmup_lock = Lock()
_rag_warmup_started = False
_rag_warmup_started_at = None
_rag_warmup_finished_at = None
_rag_warmup_error = None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _runtime_commit() -> str:
    for key in (
        "APP_COMMIT_SHA",
        "SPACE_COMMIT_SHA",
        "COMMIT_SHA",
        "GIT_COMMIT",
        "SOURCE_VERSION",
    ):
        value = os.getenv(key, "").strip()
        if value:
            return value
    return "unknown"


def _load_local_knowledge_documents() -> tuple[list, str]:
    """Load reviewed Markdown first, with PDFs as a safety fallback."""
    local_docs = []
    local_source = "PDF"
    if PREFER_MARKDOWN_KB:
        print(f"2. Loading reviewed Markdown from {MARKDOWN_FOLDER}...")
        local_docs = load_markdown_from_folder(MARKDOWN_FOLDER)
        local_source = "Markdown"
        if not local_docs:
            print("Warning: No Markdown documents found; falling back to PDFs.")

    if not local_docs:
        print(f"2. Loading PDFs from {DATA_FOLDER}...")
        local_docs = load_pdfs_from_folder(DATA_FOLDER)
        local_source = "PDF"

    return local_docs, local_source


def _expected_vector_store_manifest() -> dict:
    """Describe the source files that should be represented in Chroma."""
    source_type = "PDF"
    source_files = []
    if PREFER_MARKDOWN_KB:
        source_files = list_markdown_files(MARKDOWN_FOLDER)
        source_type = "Markdown"

    if not source_files:
        source_files = list_pdf_files(DATA_FOLDER)
        source_type = "PDF"

    return build_source_manifest(
        source_files,
        source_type=source_type,
        external_sources=KNOWLEDGE_URLS,
    )


def _load_or_build_vector_store():
    store_exists = vector_store_exists()
    expected_manifest = _expected_vector_store_manifest()
    if store_exists and not REBUILD_VECTORSTORE:
        print("1. Loading existing vector store (set REBUILD_VECTORSTORE=true to rebuild)...")
        db = load_vector_store_if_usable(expected_manifest)
        if db is not None:
            return db
        print("1. Clearing unusable vector store for a clean rebuild...")
        clear_vector_store()

    if store_exists and REBUILD_VECTORSTORE:
        print("1. Clearing existing vector store for a clean rebuild...")
        clear_vector_store()

    print("1. Fetching external content...")
    website_docs = []
    try:
        for url in KNOWLEDGE_URLS:
            website_docs.extend(fetch_website_content(url))
    except Exception as e:
        print(f"Warning: Web scraping failed: {e}")
        website_docs = []

    local_docs, local_source = _load_local_knowledge_documents()
    print(
        "3. Building & persisting vector store "
        f"({len(local_docs)} {local_source} docs + {len(website_docs)} web sources)..."
    )
    all_docs = website_docs + local_docs
    return initialize_vector_store(all_docs, expected_manifest)


def get_rag_chain():
    """Initialize the RAG stack once, when the first RAG question needs it."""
    global _rag_chain, _rag_db
    if _rag_chain is None:
        with _rag_lock:
            if _rag_chain is None:
                db = _load_or_build_vector_store()
                print("4. Setting up RetrievalQA chain...")
                _rag_chain = setup_retrieval_qa(db)
                _rag_db = db  # kept so /ask can read relevance scores
                print(f"✅ {BOT_NAME} is ready!")
    return _rag_chain


def _rag_warmup_worker(reason: str):
    global _rag_warmup_finished_at, _rag_warmup_error
    try:
        print(f"RAG warm-up started ({reason})...")
        get_rag_chain()
        with _rag_warmup_lock:
            _rag_warmup_finished_at = _utc_now_iso()
            _rag_warmup_error = None
        print("RAG warm-up finished.")
    except Exception as e:
        with _rag_warmup_lock:
            _rag_warmup_finished_at = _utc_now_iso()
            _rag_warmup_error = str(e)
        print(f"RAG warm-up failed: {e}")


def start_rag_warmup(reason: str = "startup") -> bool:
    """Start one background RAG initialization job.

    Returns True when a new thread was started, False when RAG is already ready
    or a warm-up job has already been requested.
    """
    global _rag_warmup_started, _rag_warmup_started_at
    if _rag_chain is not None:
        return False

    with _rag_warmup_lock:
        if _rag_warmup_started:
            return False
        _rag_warmup_started = True
        _rag_warmup_started_at = _utc_now_iso()

    Thread(target=_rag_warmup_worker, args=(reason,), daemon=True).start()
    return True


def _rag_runtime_status() -> dict:
    with _rag_warmup_lock:
        warmup_started = _rag_warmup_started
        started_at = _rag_warmup_started_at
        finished_at = _rag_warmup_finished_at
        error = _rag_warmup_error

    if _rag_chain is not None:
        status = "ready"
    elif error:
        status = "error"
    elif warmup_started:
        status = "warming"
    else:
        status = "cold"

    return {
        "status": status,
        "started_at": started_at,
        "finished_at": finished_at,
        "error": error,
    }


# =================================================================
# FLASK ROUTES
# =================================================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/healthz")
def healthz():
    rag_runtime = _rag_runtime_status()
    return jsonify({
        "ok": True,
        "bot": BOT_NAME,
        "rag_ready": _rag_chain is not None,
        "rag_status": rag_runtime["status"],
        "rag_warmup": rag_runtime,
    })


@app.route("/ops")
@app.route("/ops/metrics")
def ops_metrics_view():
    """Privacy-safe demo observability snapshot (JSON)."""
    if not OPS_METRICS_ENABLED:
        return jsonify({
            "enabled": False,
            "error": "Les métriques ops sont désactivées.",
        }), 503
    try:
        limit = int(request.args.get("limit", "50"))
    except (TypeError, ValueError):
        limit = 50
    snapshot = ops_metrics_mod.metrics_store.snapshot(limit=limit)
    snapshot["enabled"] = True
    snapshot["bot"] = BOT_NAME
    return jsonify(snapshot)


@app.route("/version")
def version():
    rag_runtime = _rag_runtime_status()
    return jsonify({
        "bot": BOT_NAME,
        "app_version": APP_VERSION,
        "commit": _runtime_commit(),
        "rag_status": rag_runtime["status"],
        "config": {
            "llm_model": LLM_MODEL,
            "embedding_model": EMBEDDING_MODEL,
            "vectorstore_dir": VECTORSTORE_DIR,
            "prefer_markdown_kb": PREFER_MARKDOWN_KB,
            "rag_warmup_on_start": RAG_WARMUP_ON_START,
        },
    })


@app.route("/examples/<example_id>")
def demo_example(example_id):
    example = get_demo_example(example_id)
    if example is None:
        return jsonify({
            "error": "Exemple introuvable.",
            "confidence": "Faible",
        }), 404
    return jsonify(example)


@app.route("/weather/locations")
def weather_locations():
    return jsonify({"locations": list_weather_locations()})


@app.route("/weather")
def weather_context():
    _set_log_fields(feature="weather")
    location_id = request.args.get("location", "ouagadougou").strip()
    try:
        weather = build_weather_context(location_id)
    except ValueError:
        _set_log_fields(outcome="validation_error", failure_type="bad_location")
        return jsonify({
            "error": "Choisissez une localité disponible pour la météo agricole.",
            "confidence": "Faible",
        }), 400
    except WeatherError:
        _set_log_fields(outcome="service_error", failure_type="weather_error")
        return jsonify({
            "error": "La météo agricole n'est pas disponible pour le moment.",
            "confidence": "Faible",
        }), 502
    _set_log_fields(outcome="ok", location=location_id, confidence="Moyen")
    return jsonify({
        "weather": weather,
        "confidence": "Moyen",
    })


@app.route("/soil/locations")
def soil_locations():
    return jsonify({
        "locations": list_soil_locations(),
        "crops": list_soil_crops(),
    })


@app.route("/soil")
def soil_context():
    _set_log_fields(feature="soil")
    location_id = request.args.get("location", "ouagadougou").strip()
    crop = request.args.get("crop", "sorgho").strip()
    try:
        soil = build_soil_context(location_id, crop)
    except ValueError:
        _set_log_fields(outcome="validation_error", failure_type="bad_selection")
        return jsonify({
            "error": "Choisissez une localité et une culture disponibles pour le contexte sol.",
            "confidence": "Faible",
        }), 400
    except SoilError:
        _set_log_fields(outcome="service_error", failure_type="soil_error")
        return jsonify({
            "error": "Le contexte sol n'est pas disponible pour le moment.",
            "confidence": "Faible",
        }), 502

    fertilizer = get_fertilizer_advice(f"engrais {soil['crop']}") or {
        "answer": "",
        "sources": [],
    }
    confidence = "Moyen" if soil.get("data_available") else "Faible"
    _set_log_fields(
        outcome="ok",
        location=location_id,
        crop=crop,
        confidence=confidence,
        soil_data_available=bool(soil.get("data_available")),
        source_count=len(soil["sources"] + fertilizer["sources"]),
    )
    return jsonify({
        "soil": soil,
        "fertilizer": fertilizer,
        "sources": soil["sources"] + fertilizer["sources"],
        "confidence": confidence,
    })


@app.errorhandler(RequestEntityTooLarge)
def request_entity_too_large(error):
    if request.path == "/speech":
        return _audio_too_large_response()
    return _upload_too_large_response()


@app.route("/ask", methods=["POST"])
def ask():
    _set_log_fields(feature="ask", model=LLM_MODEL)
    query = request.form.get("messageText", "").strip()
    _set_log_fields(input_chars=len(query))
    if not query:
        _set_log_fields(outcome="validation_error", failure_type="empty_question", confidence="Faible")
        return jsonify({
            "answer": "Veuillez écrire une question agricole avant d'envoyer.",
            "sources": [],
            "confidence": "Faible",
            "audio_url": "",
        }), 400
    if len(query) > MAX_QUESTION_CHARS:
        _set_log_fields(
            outcome="validation_error",
            failure_type="question_too_long",
            confidence="Faible",
        )
        return jsonify({
            "answer": (
                f"Votre question est trop longue (max. {MAX_QUESTION_CHARS} caractères). "
                "Formulez une question plus courte et précise."
            ),
            "sources": [],
            "confidence": "Faible",
            "audio_url": "",
        }), 400

    limited = _rate_limit_response("ask", REQUEST_COOLDOWN_SECONDS)
    if limited is not None:
        return limited

    field_context = _field_context_from_request()
    weather_signals, weather_payload = _weather_signals_for_location(
        field_context.get("location", "")
    )
    _set_log_fields(
        crop_provided=bool(field_context["crop"]),
        growth_stage_provided=bool(field_context["growth_stage"]),
        location_provided=bool(field_context["location"]),
        weather_enriched=bool(weather_signals),
    )
    retrieval_query = _query_with_field_context(query, field_context)

    # Bot self-identification (French + English triggers)
    identity_triggers = [
        "who developed you?", "who created you?", "who made you?",
        "qui t'a développé ?", "qui t'a développé?", "qui t'a créé ?",
        "qui t'a créé?", "qui t'a fait ?", "qui t'a fait?",
        "qui es-tu ?", "qui es-tu?", "qui es tu ?", "qui es tu?",
    ]
    if query.lower() in identity_triggers:
        _set_log_fields(
            intent="identity",
            model="static",
            outcome="ok",
            confidence="Fort",
            source_count=0,
            audio_generated=False,
        )
        return jsonify({
            "answer": f"Je suis {BOT_NAME}, un assistant agricole intelligent développé par {BOT_CREATOR}.",
            "sources": [],
            "confidence": "Fort",
            "audio_url": "",
        })

    # Route by intent. Fertilizer questions get deterministic, grounded, cited
    # doses (never LLM-invented); everything else falls through to RAG.
    # Form crop can complete a fertilizer question that omits the crop in text.
    if is_fertilizer_query(query) or classify(query) == INTENT_FERTILIZER:
        advice = get_fertilizer_advice(
            query,
            crop=field_context["crop"] or None,
            growth_stage=field_context["growth_stage"],
            location=field_context["location"],
        )
        if advice is not None:
            audio_url = text_to_speech_to_static(advice["answer"])
            case = advice.get("case")
            if case is not None and weather_signals:
                case = dict(case)
                case["weather_signals"] = weather_signals
            _set_log_fields(
                intent="fertilizer",
                model="deterministic",
                outcome="ok",
                confidence="Fort",
                source_count=len(advice["sources"]),
                audio_generated=bool(audio_url),
                case_structured=bool(case),
            )
            payload = {
                "answer": advice["answer"],
                "sources": advice["sources"],
                "confidence": "Fort",
                "audio_url": audio_url,
                "case": case,
                "answer_kind": "advice",
            }
            if weather_payload is not None:
                payload["weather"] = weather_payload
            return jsonify(payload)

    try:
        response = get_rag_chain().invoke(retrieval_query)
        answer = response["result"]

        # Surface the documents the answer was grounded in, ranked and filtered
        # by retrieval relevance score so confidence reflects match quality, not
        # how many chunks came back.
        source_docs = response.get("source_documents", [])
        case = None
        answer_kind = "advice"
        case_kwargs = {
            "question": query,
            "input_type": "text",
            "crop": field_context["crop"],
            "growth_stage": field_context["growth_stage"],
            "location": field_context["location"],
            "weather_signals": weather_signals,
        }
        if not source_docs:
            answer = _no_rag_context_answer()
            sources, confidence = [], "Faible"
            refusal = True
            answer_kind = "refusal"
        elif _is_refusal(answer):
            # The model declined to answer; do not imply confidence or evidence.
            sources, confidence = [], "Faible"
            refusal = True
            answer_kind = "refusal"
        elif _is_uncertain(answer):
            # First-class uncertainty: keep weak sources for transparency, force
            # Faible confidence, and surface a non-confirmed field case.
            sources, _ = _grounded_sources_and_confidence(retrieval_query, source_docs)
            confidence = "Faible"
            refusal = False
            answer_kind = "uncertain"
            case = build_advice_case(
                answer=answer,
                sources=sources,
                confidence=confidence,
                risk_level="Non confirmé",
                confirmation=(
                    "Je ne peux pas confirmer sans observation de parcelle. "
                    "Montrez le cas à un agent agricole avant d'agir."
                ),
                **case_kwargs,
            )
        else:
            sources, confidence = _grounded_sources_and_confidence(
                retrieval_query, source_docs
            )
            refusal = False
            answer_kind = "advice"
            case = build_advice_case(
                answer=answer,
                sources=sources,
                confidence=confidence,
                **case_kwargs,
            )

        audio_url = text_to_speech_to_static(answer)
        _set_log_fields(
            intent="rag",
            outcome="ok",
            confidence=confidence,
            source_count=len(sources),
            retrieved_doc_count=len(source_docs),
            refusal=refusal,
            answer_kind=answer_kind,
            audio_generated=bool(audio_url),
            case_structured=case is not None,
        )
        payload = {
            "answer": answer,
            "sources": sources,
            "confidence": confidence,
            "audio_url": audio_url,
            "answer_kind": answer_kind,
        }
        if case is not None:
            payload["case"] = case
        if weather_payload is not None and not refusal:
            payload["weather"] = weather_payload
        return jsonify(payload)

    except Exception as e:
        print(f"ERROR — LLM/RAG execution failed: {e}")
        _set_log_fields(
            intent="rag",
            outcome="service_error",
            failure_type=type(e).__name__,
            confidence="Faible",
        )
        return jsonify({
            "answer": f"Désolé, {BOT_NAME} a rencontré une erreur de traitement. Veuillez réessayer plus tard.",
            "sources": [],
            "confidence": "Faible",
            "audio_url": "",
        })


@app.route("/speech", methods=["POST"])
def speech():
    """Transcribe a short voice question recorded by the browser."""
    _set_log_fields(feature="speech", model=STT_MODEL)
    if not speech_configured():
        _set_log_fields(outcome="not_configured", failure_type="missing_groq_key", confidence="Faible")
        return jsonify({
            "error": "La dictée vocale n'est pas configurée sur ce serveur.",
            "confidence": "Faible",
        }), 503

    file = request.files.get("audio")
    if file is None or not file.filename:
        _set_log_fields(outcome="validation_error", failure_type="missing_audio", confidence="Faible")
        return jsonify({
            "error": "Aucun enregistrement audio n'a été envoyé.",
            "confidence": "Faible",
        }), 400

    audio_bytes = file.read()
    _set_log_fields(audio_bytes=len(audio_bytes), audio_mime_type=file.mimetype or "audio/webm")
    if not audio_bytes:
        _set_log_fields(outcome="validation_error", failure_type="empty_audio", confidence="Faible")
        return jsonify({
            "error": "L'enregistrement audio est vide.",
            "confidence": "Faible",
        }), 400
    if len(audio_bytes) > app.config["MAX_AUDIO_UPLOAD_BYTES"]:
        _set_log_fields(outcome="validation_error", failure_type="audio_too_large", confidence="Faible")
        return _audio_too_large_response()

    limited = _rate_limit_response("speech", VOICE_COOLDOWN_SECONDS)
    if limited is not None:
        return limited

    try:
        text = transcribe_audio(
            audio_bytes,
            filename=file.filename,
            mime_type=file.mimetype or "audio/webm",
        )
    except SpeechTranscriptionError as e:
        print(f"ERROR — speech transcription failed: {e}")
        _set_log_fields(outcome="service_error", failure_type=type(e).__name__, confidence="Faible")
        return jsonify({
            "error": "La dictée vocale a échoué. Veuillez réessayer ou taper votre question.",
            "confidence": "Faible",
        }), 502

    if not text:
        _set_log_fields(outcome="no_speech", failure_type="empty_transcript", confidence="Faible")
        return jsonify({
            "error": "Aucune parole claire n'a été détectée. Veuillez réessayer plus près du micro.",
            "confidence": "Faible",
        }), 422

    _set_log_fields(outcome="ok", confidence="Moyen", transcript_chars=len(text))
    return jsonify({
        "text": text,
        "confidence": "Moyen",
    })


@app.route("/screen", methods=["POST"])
def screen():
    """Leaf disease screening from an uploaded photo (Gemini Vision)."""
    _set_log_fields(feature="screen", model=GEMINI_MODEL)
    if not disease_configured():
        _set_log_fields(outcome="not_configured", failure_type="missing_gemini_key", confidence="Faible")
        return jsonify({
            "answer": "L'analyse d'image n'est pas disponible (clé Gemini non "
            "configurée).",
            "sources": [],
            "confidence": "Faible",
            "audio_url": "",
        })

    file = request.files.get("image")
    if file is None or not file.filename:
        _set_log_fields(outcome="validation_error", failure_type="missing_image", confidence="Faible")
        return jsonify({
            "error": "Aucune image n'a été envoyée.",
            "confidence": "Faible",
        }), 400

    image_bytes = file.read()
    _set_log_fields(image_bytes=len(image_bytes), image_mime_type=file.mimetype or "image/jpeg")
    if not image_bytes:
        _set_log_fields(outcome="validation_error", failure_type="empty_image", confidence="Faible")
        return jsonify({
            "error": "L'image envoyée est vide.",
            "confidence": "Faible",
        }), 400
    if len(image_bytes) > app.config["MAX_IMAGE_UPLOAD_BYTES"]:
        _set_log_fields(outcome="validation_error", failure_type="image_too_large", confidence="Faible")
        return _upload_too_large_response()

    limited = _rate_limit_response("screen", IMAGE_COOLDOWN_SECONDS)
    if limited is not None:
        return limited

    mime_type = file.mimetype or "image/jpeg"
    crop = request.form.get("crop", "").strip()[:80]
    growth_stage = request.form.get("growth_stage", "").strip()[:80]
    location = request.form.get("location", "").strip()[:120]
    _set_log_fields(
        crop_provided=bool(crop),
        growth_stage_provided=bool(growth_stage),
        location_provided=bool(location),
    )
    result = screen_leaf_image(
        image_bytes,
        mime_type,
        crop=crop,
        growth_stage=growth_stage,
        location=location,
    )
    answer = result["answer"]
    case = result.get("case")
    confidence = _confidence_for_screen(
        case,
        has_context=bool(crop or growth_stage or location),
    )
    if case is not None:
        case = dict(case)
        case["confidence"] = confidence
    audio_url = text_to_speech_to_static(answer)
    _set_log_fields(
        outcome="ok",
        confidence=confidence,
        case_structured=case is not None,
        audio_generated=bool(audio_url),
    )
    return jsonify({
        "answer": answer,
        "case": case,
        "sources": [],
        "confidence": confidence,
        "audio_url": audio_url,
    })


@app.route("/feedback", methods=["POST"])
def feedback():
    _set_log_fields(feature="feedback")
    rating = request.form.get("rating", "").strip()
    question = request.form.get("question", "").strip()
    answer = request.form.get("answer", "").strip()

    if rating not in ("up", "down"):
        _set_log_fields(outcome="validation_error", failure_type="invalid_rating")
        return jsonify({"ok": False, "error": "invalid rating"}), 400

    try:
        feedback_id = record_feedback(
            CASE_LOG_DB,
            rating=rating,
            question=question,
            answer=answer,
        )
        _set_log_fields(outcome="ok", rating=rating, feedback_id=feedback_id)
        return jsonify({"ok": True, "feedback_id": feedback_id})
    except Exception as e:
        print(f"ERROR — feedback write failed: {e}")
        _set_log_fields(outcome="write_error", failure_type=type(e).__name__)
        return jsonify({"ok": False, "error": "write failed"}), 500


@app.route("/feedback/outcome", methods=["POST"])
def feedback_outcome():
    """Record follow-up outcome after a farmer applies (or not) advice."""
    _set_log_fields(feature="feedback_outcome")
    try:
        feedback_id = int(request.form.get("feedback_id", 0))
    except (ValueError, TypeError):
        feedback_id = 0
    outcome_value = request.form.get("outcome", "").strip()

    if not feedback_id:
        _set_log_fields(outcome="validation_error", failure_type="missing_feedback_id")
        return jsonify({"ok": False, "error": "missing feedback_id"}), 400

    try:
        updated = record_outcome(
            CASE_LOG_DB,
            feedback_id=feedback_id,
            outcome=outcome_value,
        )
    except ValueError:
        _set_log_fields(outcome="validation_error", failure_type="invalid_outcome")
        return jsonify({"ok": False, "error": "invalid outcome"}), 400
    except Exception as e:
        print(f"ERROR — outcome write failed: {e}")
        _set_log_fields(outcome="write_error", failure_type=type(e).__name__)
        return jsonify({"ok": False, "error": "write failed"}), 500

    if not updated:
        _set_log_fields(outcome="not_found", failure_type="feedback_id_not_found")
        return jsonify({"ok": False, "error": "feedback_id not found"}), 404

    _set_log_fields(outcome="ok", rating_outcome=outcome_value, feedback_id=feedback_id)
    return jsonify({"ok": True})


if RAG_WARMUP_ON_START:
    start_rag_warmup("startup")


if __name__ == "__main__":
    app.run(debug=DEBUG)
