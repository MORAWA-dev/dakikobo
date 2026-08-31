# app.py — DakiKobo Flask entry point

import os
import json
import logging
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
from core.llm_chain import sanitize_answer, setup_retrieval_qa
from core.retrieval import (
    GroundedAnswer,
    chunk_id,
    get_active_manifest_hash,
    ground_answer,
    manifest_hash,
    merge_scored_evidence,
    set_active_manifest_hash,
)
from core.answer_cache import AnswerCache, build_answer_cache_key, question_hash
from core.cache import interprocess_file_lock
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
from core.case_log import (
    SCHEMA_VERSION as CASE_LOG_SCHEMA_VERSION,
    VALID_ANSWER_PATHS,
    clone_evidence_batch,
    list_due_followups,
    record_evidence,
    record_feedback,
    record_outcome,
    set_before_image_ref,
)
from core.query_context import resolve_query_context
from core.simple_french import (
    apply_simple_style_to_query,
    is_simple_mode,
    light_replacements,
    simplify_answer,
)
from core.crop_labels import load_crop_labels
from core import ops_metrics as ops_metrics_mod
from core.weather import (
    WeatherError,
    build_weather_context,
    list_weather_locations,
    resolve_weather_location_id,
)
from core.crops import list_crops, resolve_crop
from core.places import list_places, resolve_place
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
    SIMILARITY_THRESHOLD,
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
    ANSWER_CACHE_ENABLED,
    ANSWER_CACHE_TTL_SECONDS,
    STATE_DB_PATH,
    CASE_LOG_DB_PATH,
    FEEDBACK_IMAGE_DIR,
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
FEEDBACK_IMAGES = FEEDBACK_IMAGE_DIR

# Privacy-safe shared SQLite metrics (local facade is reconfigurable in tests).
if OPS_METRICS_ENABLED:
    ops_metrics_mod.configure_metrics_store(
        OPS_METRICS_MAX_EVENTS,
        db_path=STATE_DB_PATH,
    )

# Shared SQLite answer cache. The corpus manifest is part of every key, so a
# successful re-ingestion automatically makes older entries unreachable.
answer_cache_store = (
    AnswerCache(ANSWER_CACHE_TTL_SECONDS, db_path=STATE_DB_PATH)
    if ANSWER_CACHE_ENABLED
    else None
)


def _safe_feedback_image_ext(filename: str, mime_type: str) -> str:
    name = (filename or "").lower()
    mime = (mime_type or "").lower()
    if name.endswith(".png") or "png" in mime:
        return ".png"
    if name.endswith(".webp") or "webp" in mime:
        return ".webp"
    if name.endswith(".gif") or "gif" in mime:
        return ".gif"
    return ".jpg"


def _store_feedback_image(
    *,
    feedback_id: int,
    kind: str,
    file_storage,
) -> str:
    """Save an optional before/after photo; return opaque relative ref or ''."""
    if file_storage is None or not getattr(file_storage, "filename", None):
        return ""
    raw = file_storage.read()
    if not raw:
        return ""
    if len(raw) > app.config["MAX_IMAGE_UPLOAD_BYTES"]:
        raise ValueError("image_too_large")
    ext = _safe_feedback_image_ext(file_storage.filename, file_storage.mimetype or "")
    os.makedirs(FEEDBACK_IMAGES, exist_ok=True)
    filename = f"fb_{int(feedback_id)}_{kind}{ext}"
    path = os.path.join(FEEDBACK_IMAGES, filename)
    with open(path, "wb") as handle:
        handle.write(raw)
    # Store path relative to project for evaluation tooling (not a public URL).
    return path


def _set_log_fields(**fields) -> None:
    if not has_request_context():
        return
    current = getattr(g, "log_fields", {})
    current.update({key: value for key, value in fields.items() if value is not None})
    g.log_fields = current


def _journal_metadata(
    *,
    answer_path: str,
    crop_id: str = "",
    place_id: str = "",
    ledger_created_at: float | None = None,
) -> dict:
    """Client round-trip metadata; never exposes the salted question hash."""
    return {
        "answer_path": answer_path,
        "crop_id": crop_id or "",
        "place_id": place_id or "",
        "ledger_created_at": ledger_created_at,
    }


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
        ops_metrics_mod.get_metrics_store().record(
            timestamp=_utc_now_iso(),
            **payload,
        )
    return response


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


def _prior_question_from_request() -> str:
    """Previous user question for short follow-ups (client-supplied)."""
    return (request.form.get("prior_question") or "").strip()[:500]


def _query_with_field_context(query: str, context: dict[str, str]) -> str:
    """Append parcelle context for retrieval (legacy helper; prefer resolve_query_context)."""
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


def _simple_french_from_request() -> bool:
    """Optional Français simple toggle from form or query string."""
    raw = request.form.get("simple_french")
    if raw is None:
        raw = request.args.get("simple_french")
    return is_simple_mode(raw)


def _maybe_simplify(answer: str, enabled: bool) -> str:
    """Apply plain-French post-processing when the toggle is on."""
    if not enabled or not answer:
        return answer
    return simplify_answer(answer)


def _maybe_simplify_case(case: dict | None, enabled: bool) -> dict | None:
    """Keep structured case text aligned with simplified mode (light touch)."""
    if not enabled or not case:
        return case
    updated = dict(case)
    # Prefer light wording swaps on list fields; full glossary only once on answer.
    if updated.get("answer"):
        updated["answer"] = simplify_answer(str(updated["answer"]))
    for key in ("summary", "confirmation"):
        if updated.get(key):
            updated[key] = light_replacements(str(updated[key]))
    for list_key in (
        "observations",
        "possible_causes",
        "actions",
        "evidence",
        "do_not",
        "weather_signals",
    ):
        items = updated.get(list_key)
        if isinstance(items, list) and items:
            updated[list_key] = [light_replacements(str(item)) for item in items]
    return updated


def _answer_cache_key(retrieval_query: str, resolved, simple_french: bool) -> str:
    return build_answer_cache_key(
        retrieval_query,
        crop_id=resolved.crop_id,
        growth_stage=resolved.growth_stage,
        place_id=resolved.place_id,
        simple_french=simple_french,
        llm_model=LLM_MODEL,
        manifest_hash_value=get_active_manifest_hash(),
    )


def _cached_answer_kind(cached: dict) -> str:
    case = cached.get("case")
    if isinstance(case, dict) and case.get("risk_level") == "Non confirmé":
        return "uncertain"
    if not case and not cached.get("sources"):
        return "refusal"
    return "advice"


def _weather_signals_for_location(location_text: str) -> tuple[list[str], dict | None]:
    """Optional weather enrichment when field location maps to a known city."""
    loc_id = resolve_weather_location_id(location_text)
    if not loc_id:
        return [], None
    try:
        weather = build_weather_context(loc_id)
    # Weather enrichment is optional; any provider/parser failure must not
    # prevent the main agricultural answer from being returned.
    except Exception as exc:
        print(f"Weather enrichment skipped for {loc_id}: {exc}")
        return [], None
    # Prefer one actionable signal (risk > watch > good) for compact cards.
    ranked = []
    for insight in weather.get("insights") or []:
        label = (insight.get("label") or "").strip()
        text = (insight.get("text") or "").strip()
        status = (insight.get("status") or "watch").strip()
        if not text:
            continue
        line = f"{label} : {text}" if label else text
        priority = {"risk": 0, "watch": 1, "good": 2}.get(status, 1)
        ranked.append((priority, line))
    ranked.sort(key=lambda item: item[0])
    signals = [line for _, line in ranked[:1]]
    return signals, weather


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


def _load_or_build_vector_store_locked():
    """Load/rebuild Chroma while the caller holds the cross-worker file lock."""
    store_exists = vector_store_exists()
    expected_manifest = _expected_vector_store_manifest()
    active_hash = manifest_hash(expected_manifest)
    # Never expose a stale corpus identity if loading/rebuilding fails.
    set_active_manifest_hash(None)

    if store_exists and not REBUILD_VECTORSTORE:
        print("1. Loading existing vector store (set REBUILD_VECTORSTORE=true to rebuild)...")
        db = load_vector_store_if_usable(expected_manifest)
        if db is not None:
            set_active_manifest_hash(active_hash)
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
    db = initialize_vector_store(all_docs, expected_manifest)
    if db is not None:
        set_active_manifest_hash(active_hash)
    return db


def _load_or_build_vector_store():
    # Chroma performs schema migrations during first creation. Two workers
    # entering that path together can corrupt the transient `collections_tmp`
    # table, so serialize build/load publication across processes.
    lock_path = f"{os.path.abspath(VECTORSTORE_DIR)}.build.lock"
    with interprocess_file_lock(lock_path):
        return _load_or_build_vector_store_locked()


def get_rag_chain():
    """Initialize the RAG stack once, when the first RAG question needs it."""
    global _rag_chain, _rag_db
    if _rag_chain is None:
        with _rag_lock:
            if _rag_chain is None:
                db = _load_or_build_vector_store()
                print("4. Setting up RetrievalQA chain...")
                chain = setup_retrieval_qa(db)
                # `_rag_chain` is the readiness sentinel. Publish the database
                # first so requests racing background warm-up never see a ready
                # chain without the vector store required by `/ask`.
                _rag_db = db
                _rag_chain = chain
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

    # `_rag_chain` is published only after `_rag_db` and the complete chain are
    # ready. Reading that sentinel must stay lock-free: `_rag_lock` is held for
    # the full model/index warm-up, and health checks need to report `warming`
    # immediately while that work is in progress.
    rag_ready = _rag_chain is not None

    if rag_ready:
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


@app.route("/sw.js")
def service_worker():
    """Serve the static worker at the site root so it can control every route."""
    response = app.send_static_file("sw.js")
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache"
    return response


@app.route("/crop-labels")
def crop_labels_route():
    """French-primary crop labels for the field UI (local names optional later)."""
    try:
        data = load_crop_labels()
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        logger.warning("Crop labels unavailable: %s", exc)
        return jsonify({
            "error": "Les libellés des cultures sont indisponibles pour le moment.",
            "crops": [],
        }), 500
    crops = []
    for crop in data.get("crops") or []:
        crop_id = (crop.get("id") or "").strip()
        if not crop_id:
            continue
        # Preserve this existing route's accented form-value contract. The
        # registry endpoint separately exposes stable ASCII ids.
        form_id = {
            "mais": "maïs",
            "niebe": "niébé",
        }.get(crop_id, crop_id)
        crops.append(
            {
                "id": form_id,
                "fr": crop.get("fr") or form_id,
                "fr_simple": crop.get("fr_simple") or crop.get("fr") or form_id,
            }
        )
    return jsonify(
        {
            "primary_language": (data.get("meta") or {}).get("primary_language", "fr"),
            "status": (data.get("meta") or {}).get("status", "experimental"),
            "crops": crops,
        }
    )


@app.route("/registry")
def registry():
    """Canonical crop and place registry for populating UI selects (Phase 1)."""
    try:
        crops = list_crops()
        places = list_places()
    except Exception as exc:
        logger.exception("Registry loading failed: %s", exc)
        return jsonify({
            "error": "Le registre des cultures et des lieux est indisponible.",
            "crops": [],
            "places": [],
        }), 500
    response = jsonify({"crops": crops, "places": places})
    response.headers["Cache-Control"] = "public, max-age=3600"
    return response


@app.route("/healthz")
def healthz():
    rag_runtime = _rag_runtime_status()
    return jsonify({
        "ok": True,
        "bot": BOT_NAME,
        "rag_ready": rag_runtime["status"] == "ready",
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
    snapshot = ops_metrics_mod.get_metrics_store().snapshot(limit=limit)
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
            "answer_cache_enabled": ANSWER_CACHE_ENABLED,
            "field_journal_schema_version": CASE_LOG_SCHEMA_VERSION,
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
    input_type = (example.get("case") or {}).get("input_type", "text")
    answer_path = "vision" if input_type == "image" else (
        "fertilizer" if input_type == "fertilizer" else "rag"
    )
    example["journal"] = _journal_metadata(answer_path=answer_path)
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
    prior_question = _prior_question_from_request()
    simple_french = _simple_french_from_request()
    resolved = resolve_query_context(
        query,
        field_context,
        prior_question=prior_question,
        simple_french=simple_french,
    )
    effective_context = resolved.as_case_fields()
    _set_log_fields(
        crop_provided=bool(effective_context["crop"]),
        growth_stage_provided=bool(effective_context["growth_stage"]),
        location_provided=bool(effective_context["location"]),
        weather_enriched=False,
        simple_french=simple_french,
        crop_conflict=resolved.crop_conflict,
        followup_expanded=resolved.expanded_from_prior,
        cache_hit=False,
    )
    retrieval_query = resolved.retrieval_query
    if simple_french:
        retrieval_query = apply_simple_style_to_query(retrieval_query)

    # The active corpus hash is required before a persisted answer can be
    # trusted. Lookup happens before intent routing and all upstream calls.
    active_manifest = get_active_manifest_hash()
    if ANSWER_CACHE_ENABLED and answer_cache_store is not None and active_manifest:
        cache_key = _answer_cache_key(retrieval_query, resolved, simple_french)
        try:
            cached = answer_cache_store.get(cache_key)
        except Exception as exc:
            logger.warning("Answer cache lookup skipped: %s", exc)
            cached = None
        if cached is not None:
            answer_kind = _cached_answer_kind(cached)
            refusal = answer_kind == "refusal"
            sources = cached.get("sources") or []
            case = cached.get("case")
            try:
                cached_evidence_hash = cached.get("evidence_question_hash") or ""
                cached_evidence_created_at = cached.get("evidence_created_at")
                ledger_created_at = (
                    clone_evidence_batch(
                        CASE_LOG_DB,
                        question_hash_value=cached_evidence_hash,
                        source_created_at=float(cached_evidence_created_at),
                        target_question_hash_value=question_hash(query),
                    )
                    if cached_evidence_hash and cached_evidence_created_at is not None
                    else None
                )
            except Exception as exc:
                logger.warning("Evidence ledger cache clone skipped: %s", exc)
                ledger_created_at = None
            _set_log_fields(
                intent="cache",
                model="cache",
                outcome="ok",
                confidence=cached.get("confidence") or "Faible",
                source_count=len(sources),
                retrieved_doc_count=len(cached.get("retrieved_chunk_ids") or []),
                refusal=refusal,
                answer_kind=answer_kind,
                audio_generated=False,
                case_structured=case is not None,
                cache_hit=True,
            )
            payload = {
                "answer": cached.get("answer") or "",
                "sources": sources,
                "confidence": cached.get("confidence") or "Faible",
                "audio_url": "",
                "answer_kind": answer_kind,
                "simple_french": simple_french,
                "journal": _journal_metadata(
                    answer_path="cache",
                    crop_id=resolved.crop_id,
                    place_id=resolved.place_id,
                    ledger_created_at=ledger_created_at,
                ),
            }
            if case is not None:
                payload["case"] = case
            return jsonify(payload)

    weather_signals, weather_payload = _weather_signals_for_location(
        effective_context.get("location", "")
    )
    _set_log_fields(weather_enriched=bool(weather_signals))

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
    # Effective crop (question wins over form) completes fertilizer questions.
    fert_query = resolved.retrieval_query if resolved.expanded_from_prior else query
    if is_fertilizer_query(fert_query) or classify(fert_query) == INTENT_FERTILIZER:
        advice = get_fertilizer_advice(
            fert_query,
            crop=effective_context["crop"] or None,
            growth_stage=effective_context["growth_stage"],
            location=effective_context["location"],
        )
        if advice is not None:
            answer = _maybe_simplify(advice["answer"], simple_french)
            case = advice.get("case")
            if case is not None:
                case = dict(case)
                case["crop"] = effective_context["crop"] or case.get("crop", "")
                case["growth_stage"] = effective_context["growth_stage"] or case.get(
                    "growth_stage", ""
                )
                case["location"] = effective_context["location"] or case.get(
                    "location", ""
                )
                if weather_signals:
                    case["weather_signals"] = weather_signals
            case = _maybe_simplify_case(case, simple_french)
            audio_url = text_to_speech_to_static(answer)
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
                "answer": answer,
                "sources": advice["sources"],
                "confidence": "Fort",
                "audio_url": audio_url,
                "case": case,
                "answer_kind": "advice",
                "simple_french": simple_french,
                "journal": _journal_metadata(
                    answer_path="fertilizer",
                    crop_id=resolved.crop_id,
                    place_id=resolved.place_id,
                ),
            }
            if weather_payload is not None:
                payload["weather"] = weather_payload
            return jsonify(payload)

    try:
        chain = get_rag_chain()
        if _rag_db is None:
            raise RuntimeError("Le magasin vectoriel RAG n'est pas initialisé.")

        # One scored retrieval is the sole evidence set for both generation and
        # citation grading. This avoids RetrievalQA invoking the retriever a
        # second time and keeps the answer aligned with the displayed sources.
        scored = _rag_db.similarity_search_with_relevance_scores(
            retrieval_query,
            k=6,
        )
        retrieved_chunk_ids = [
            chunk_id(
                (getattr(doc, "metadata", {}) or {}).get("source", "Inconnu"),
                getattr(doc, "page_content", ""),
            )
            for doc, _ in scored
        ]
        accepted_scored = [
            (doc, score)
            for doc, score in scored
            if score >= SIMILARITY_THRESHOLD
        ]
        source_docs = [doc for doc, _ in accepted_scored]
        source_scores = {}
        for doc, score in accepted_scored:
            metadata = getattr(doc, "metadata", {}) or {}
            title = metadata.get("source", "Inconnu")
            if title not in source_scores or score > source_scores[title]:
                source_scores[title] = score

        raw_answer = chain.combine_documents_chain.run(
            input_documents=source_docs,
            question=retrieval_query,
        )
        # Reasoning models can leak chain-of-thought into `content`; never show
        # that to a farmer.
        answer = sanitize_answer(raw_answer)
        grounded_policy = ground_answer(
            retrieval_query,
            source_docs,
            score_lookup=lambda: source_scores,
        )
        evidence_decisions = merge_scored_evidence(
            scored,
            grounded_policy,
            similarity_threshold=SIMILARITY_THRESHOLD,
        )
        grounded = GroundedAnswer(
            sources=grounded_policy.sources,
            confidence=grounded_policy.confidence,
            retrieved_chunk_ids=retrieved_chunk_ids,
            evidence_decisions=evidence_decisions,
        )

        # Threshold-accepted documents ground generation and citations, while
        # provenance retains every raw top-six candidate for cache/ledger use.
        case = None
        answer_kind = "advice"
        case_kwargs = {
            "question": query,
            "input_type": "text",
            "crop": effective_context["crop"],
            "growth_stage": effective_context["growth_stage"],
            "location": effective_context["location"],
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
            sources = [card.as_dict() for card in grounded.sources]
            confidence = "Faible"
            refusal = False
            answer_kind = "uncertain"
            answer = _maybe_simplify(answer, simple_french)
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
            sources = [card.as_dict() for card in grounded.sources]
            confidence = grounded.confidence
            refusal = False
            answer_kind = "advice"
            answer = _maybe_simplify(answer, simple_french)

            case = build_advice_case(
                answer=answer,
                sources=sources,
                confidence=confidence,
                **case_kwargs,
            )

        # Refusals stay plain; still allow light simple-mode wording.
        if refusal and simple_french:
            answer = _maybe_simplify(answer, True)

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

        try:
            ledger_created_at = record_evidence(
                CASE_LOG_DB,
                question_hash_value=question_hash(query),
                decisions=grounded.evidence_decisions,
            )
        except Exception as exc:
            logger.warning("Evidence ledger write skipped: %s", exc)
            ledger_created_at = None

        payload = {
            "answer": answer,
            "sources": sources,
            "confidence": confidence,
            "audio_url": audio_url,
            "answer_kind": answer_kind,
            "simple_french": simple_french,
            "journal": _journal_metadata(
                answer_path="rag",
                crop_id=resolved.crop_id,
                place_id=resolved.place_id,
                ledger_created_at=ledger_created_at,
            ),
        }
        if case is not None:
            payload["case"] = case
        if weather_payload is not None and not refusal:
            payload["weather"] = weather_payload

        if ANSWER_CACHE_ENABLED and answer_cache_store is not None:
            active_manifest = get_active_manifest_hash()
            if active_manifest:
                try:
                    answer_cache_store.set(
                        _answer_cache_key(
                            retrieval_query,
                            resolved,
                            simple_french,
                        ),
                        answer=answer,
                        case=case,
                        sources=sources,
                        confidence=confidence,
                        retrieved_chunk_ids=retrieved_chunk_ids,
                        evidence_question_hash=question_hash(query),
                        evidence_created_at=ledger_created_at,
                    )
                except Exception as exc:
                    logger.warning("Answer cache write skipped: %s", exc)
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
    simple_french = _simple_french_from_request()
    _set_log_fields(
        crop_provided=bool(crop),
        growth_stage_provided=bool(growth_stage),
        location_provided=bool(location),
        simple_french=simple_french,
    )
    result = screen_leaf_image(
        image_bytes,
        mime_type,
        crop=crop,
        growth_stage=growth_stage,
        location=location,
    )
    answer = _maybe_simplify(result["answer"], simple_french)
    case = result.get("case")
    confidence = _confidence_for_screen(
        case,
        has_context=bool(crop or growth_stage or location),
    )
    if case is not None:
        case = dict(case)
        case["confidence"] = confidence
    case = _maybe_simplify_case(case, simple_french)
    audio_url = text_to_speech_to_static(answer)
    crop_entry = resolve_crop(crop) if crop else None
    place_entry = resolve_place(location) if location else None
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
        "simple_french": simple_french,
        "journal": _journal_metadata(
            answer_path="vision",
            crop_id=crop_entry.id if crop_entry else "",
            place_id=place_entry.id if place_entry else "",
        ),
    })


@app.route("/journal/due")
def journal_due():
    """Privacy-minimized reminder digest for feedback awaiting an outcome."""
    _set_log_fields(feature="journal_due")
    try:
        cases = list_due_followups(CASE_LOG_DB)
    except Exception as exc:
        logger.warning("Journal due read failed: %s", exc)
        _set_log_fields(outcome="read_error", failure_type=type(exc).__name__)
        return jsonify({"ok": False, "error": "Le journal est indisponible pour le moment."}), 500
    _set_log_fields(outcome="ok", due_count=len(cases))
    response = jsonify({"ok": True, "due": cases, "count": len(cases)})
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/feedback", methods=["POST"])
def feedback():
    _set_log_fields(feature="feedback")
    rating = request.form.get("rating", "").strip()
    question = request.form.get("question", "").strip()
    answer = request.form.get("answer", "").strip()
    before_ref = (request.form.get("before_image_ref") or "").strip()[:240]
    place_id = (request.form.get("place_id") or "").strip()[:80]
    crop_id = (request.form.get("crop_id") or "").strip()[:80]
    answer_path = (request.form.get("answer_path") or "").strip()
    try:
        ledger_created_at = float(request.form.get("ledger_created_at"))
    except (TypeError, ValueError):
        ledger_created_at = None

    if rating not in ("up", "down"):
        _set_log_fields(outcome="validation_error", failure_type="invalid_rating")
        return jsonify({"ok": False, "error": "L’évaluation doit être positive ou négative."}), 400
    if answer_path and answer_path not in VALID_ANSWER_PATHS:
        _set_log_fields(outcome="validation_error", failure_type="invalid_answer_path")
        return jsonify({"ok": False, "error": "Le type de réponse est invalide."}), 400

    try:
        feedback_id = record_feedback(
            CASE_LOG_DB,
            rating=rating,
            question=question,
            answer=answer,
            before_image_ref=before_ref,
            place_id=place_id,
            crop_id=crop_id,
            answer_path=answer_path,
            question_hash_value=question_hash(question),
            ledger_created_at=ledger_created_at,
        )
        # Optional multipart before photo (stored only as opaque local ref).
        before_file = request.files.get("before_image")
        if before_file and before_file.filename:
            try:
                stored = _store_feedback_image(
                    feedback_id=feedback_id,
                    kind="before",
                    file_storage=before_file,
                )
                if stored:
                    set_before_image_ref(
                        CASE_LOG_DB,
                        feedback_id=feedback_id,
                        before_image_ref=stored,
                    )
                    before_ref = stored
            except ValueError:
                _set_log_fields(outcome="validation_error", failure_type="image_too_large")
                return jsonify({"ok": False, "error": "L’image envoyée est trop lourde."}), 413
        _set_log_fields(
            outcome="ok",
            rating=rating,
            feedback_id=feedback_id,
            before_image_stored=bool(before_ref),
        )
        return jsonify({
            "ok": True,
            "feedback_id": feedback_id,
            "before_image_ref": before_ref or "",
        })
    except Exception as e:
        print(f"ERROR — feedback write failed: {e}")
        _set_log_fields(outcome="write_error", failure_type=type(e).__name__)
        return jsonify({"ok": False, "error": "L’évaluation n’a pas pu être enregistrée."}), 500


@app.route("/feedback/outcome", methods=["POST"])
def feedback_outcome():
    """Record follow-up outcome after a farmer applies (or not) advice."""
    _set_log_fields(feature="feedback_outcome")
    try:
        feedback_id = int(request.form.get("feedback_id", 0))
    except (ValueError, TypeError):
        feedback_id = 0
    outcome_value = request.form.get("outcome", "").strip()
    after_ref = (request.form.get("after_image_ref") or "").strip()[:240]

    if not feedback_id:
        _set_log_fields(outcome="validation_error", failure_type="missing_feedback_id")
        return jsonify({"ok": False, "error": "L’identifiant de l’évaluation est manquant."}), 400

    after_file = request.files.get("after_image")
    if after_file and after_file.filename:
        try:
            after_ref = _store_feedback_image(
                feedback_id=feedback_id,
                kind="after",
                file_storage=after_file,
            ) or after_ref
        except ValueError:
            _set_log_fields(outcome="validation_error", failure_type="image_too_large")
            return jsonify({"ok": False, "error": "L’image envoyée est trop lourde."}), 413

    try:
        updated = record_outcome(
            CASE_LOG_DB,
            feedback_id=feedback_id,
            outcome=outcome_value,
            after_image_ref=after_ref,
        )
    except ValueError:
        _set_log_fields(outcome="validation_error", failure_type="invalid_outcome")
        return jsonify({"ok": False, "error": "Le résultat de suivi est invalide."}), 400
    except Exception as e:
        print(f"ERROR — outcome write failed: {e}")
        _set_log_fields(outcome="write_error", failure_type=type(e).__name__)
        return jsonify({"ok": False, "error": "Le suivi n’a pas pu être enregistré."}), 500

    if not updated:
        _set_log_fields(outcome="not_found", failure_type="feedback_id_not_found")
        return jsonify({"ok": False, "error": "L’évaluation demandée est introuvable."}), 404

    _set_log_fields(
        outcome="ok",
        rating_outcome=outcome_value,
        feedback_id=feedback_id,
        after_image_stored=bool(after_ref),
    )
    return jsonify({"ok": True, "after_image_ref": after_ref or ""})


if RAG_WARMUP_ON_START:
    start_rag_warmup("startup")


if __name__ == "__main__":
    app.run(debug=DEBUG)
