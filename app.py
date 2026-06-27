# app.py — DakiKobo Flask entry point

import os
import csv
from math import ceil
from time import time
from threading import Lock
from datetime import datetime, timezone
from flask import Flask, render_template, request, jsonify, session
from werkzeug.exceptions import RequestEntityTooLarge

from core.rag_pipeline import (
    fetch_website_content,
    load_pdfs_from_folder,
    initialize_vector_store,
    vector_store_exists,
    load_vector_store,
    text_to_speech_to_static,
)
from core.llm_chain import setup_retrieval_qa
from core.fertilizer import get_fertilizer_advice
from core.router import classify, INTENT_FERTILIZER
from core.disease import screen_leaf_image, is_configured as disease_configured
from core.examples import get_demo_example
from core.weather import (
    WeatherError,
    build_weather_context,
    list_weather_locations,
)
from core.soil import (
    SoilError,
    build_soil_context,
    list_soil_crops,
    list_soil_locations,
)
from config import (
    KNOWLEDGE_URLS,
    DATA_FOLDER,
    DEBUG,
    SECRET_KEY,
    BOT_NAME,
    BOT_CREATOR,
    REBUILD_VECTORSTORE,
    REQUEST_COOLDOWN_SECONDS,
    IMAGE_COOLDOWN_SECONDS,
    MAX_IMAGE_UPLOAD_BYTES,
    MAX_IMAGE_UPLOAD_MB,
)

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = MAX_IMAGE_UPLOAD_BYTES
app.config["MAX_IMAGE_UPLOAD_BYTES"] = MAX_IMAGE_UPLOAD_BYTES
app.config["MAX_IMAGE_UPLOAD_MB"] = MAX_IMAGE_UPLOAD_MB

# Lightweight feedback log (no database) — one CSV row per thumbs up/down.
FEEDBACK_FILE = os.path.join("data", "feedback.csv")


def _short_snippet(text: str, max_chars: int = 150) -> str:
    text = " ".join((text or "").split())
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit(" ", 1)[0]
    return f"{cut}..."


def _format_rag_sources(source_docs) -> list[dict]:
    """Return unique, UI-friendly source cards from retrieved documents."""
    by_title = {}
    for doc in source_docs:
        title = doc.metadata.get("source", "Inconnu")
        if title in by_title:
            continue
        by_title[title] = {
            "title": title,
            "type": "Base locale",
            "snippet": _short_snippet(getattr(doc, "page_content", "")),
        }
    return sorted(by_title.values(), key=lambda item: item["title"])


def _confidence_from_sources(sources: list[dict]) -> str:
    if len(sources) >= 2:
        return "Fort"
    if len(sources) == 1:
        return "Moyen"
    return "Faible"


def _confidence_for_screen(case: dict | None, has_context: bool) -> str:
    if not has_context:
        return "Faible"
    if case and case.get("confidence"):
        return case["confidence"]
    return "Moyen"


def _limit_label_mb() -> str:
    value = float(app.config["MAX_IMAGE_UPLOAD_MB"])
    return str(int(value)) if value.is_integer() else f"{value:.1f}"


def _rate_limit_response(action: str, cooldown_seconds: float):
    if cooldown_seconds <= 0:
        return None

    now = time()
    key = f"rate_limit_{action}_last_at"
    last_at = float(session.get(key, 0) or 0)
    retry_after = ceil(cooldown_seconds - (now - last_at))

    if retry_after > 0:
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


# =================================================================
# RAG INITIALIZATION — lazy, cached after the first RAG request
# =================================================================

_rag_chain = None
_rag_lock = Lock()


def _load_or_build_vector_store():
    if vector_store_exists() and not REBUILD_VECTORSTORE:
        print("1. Loading existing vector store (set REBUILD_VECTORSTORE=true to rebuild)...")
        return load_vector_store()

    print("1. Fetching external content...")
    website_docs = []
    try:
        for url in KNOWLEDGE_URLS:
            website_docs.extend(fetch_website_content(url))
    except Exception as e:
        print(f"Warning: Web scraping failed: {e}")
        website_docs = []

    print(f"2. Loading PDFs from {DATA_FOLDER}...")
    pdf_docs = load_pdfs_from_folder(DATA_FOLDER)

    print(f"3. Building & persisting vector store ({len(pdf_docs)} PDFs + {len(website_docs)} web sources)...")
    all_docs = website_docs + pdf_docs
    return initialize_vector_store(all_docs)


def get_rag_chain():
    """Initialize the RAG stack once, when the first RAG question needs it."""
    global _rag_chain
    if _rag_chain is None:
        with _rag_lock:
            if _rag_chain is None:
                db = _load_or_build_vector_store()
                print("4. Setting up RetrievalQA chain...")
                _rag_chain = setup_retrieval_qa(db)
                print(f"✅ {BOT_NAME} is ready!")
    return _rag_chain


# =================================================================
# FLASK ROUTES
# =================================================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/healthz")
def healthz():
    return jsonify({
        "ok": True,
        "bot": BOT_NAME,
        "rag_ready": _rag_chain is not None,
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
    location_id = request.args.get("location", "ouagadougou").strip()
    try:
        weather = build_weather_context(location_id)
    except ValueError:
        return jsonify({
            "error": "Choisissez une localité disponible pour la météo agricole.",
            "confidence": "Faible",
        }), 400
    except WeatherError:
        return jsonify({
            "error": "La météo agricole n'est pas disponible pour le moment.",
            "confidence": "Faible",
        }), 502
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
    location_id = request.args.get("location", "ouagadougou").strip()
    crop = request.args.get("crop", "sorgho").strip()
    try:
        soil = build_soil_context(location_id, crop)
    except ValueError:
        return jsonify({
            "error": "Choisissez une localité et une culture disponibles pour le contexte sol.",
            "confidence": "Faible",
        }), 400
    except SoilError:
        return jsonify({
            "error": "Le contexte sol n'est pas disponible pour le moment.",
            "confidence": "Faible",
        }), 502

    fertilizer = get_fertilizer_advice(f"engrais {soil['crop']}") or {
        "answer": "",
        "sources": [],
    }
    confidence = "Moyen" if soil.get("data_available") else "Faible"
    return jsonify({
        "soil": soil,
        "fertilizer": fertilizer,
        "sources": soil["sources"] + fertilizer["sources"],
        "confidence": confidence,
    })


@app.errorhandler(RequestEntityTooLarge)
def request_entity_too_large(error):
    return _upload_too_large_response()


@app.route("/ask", methods=["POST"])
def ask():
    query = request.form.get("messageText", "").strip()
    if not query:
        return jsonify({
            "answer": "Veuillez écrire une question agricole avant d'envoyer.",
            "sources": [],
            "confidence": "Faible",
            "audio_url": "",
        }), 400

    limited = _rate_limit_response("ask", REQUEST_COOLDOWN_SECONDS)
    if limited is not None:
        return limited

    # Bot self-identification (French + English triggers)
    identity_triggers = [
        "who developed you?", "who created you?", "who made you?",
        "qui t'a développé ?", "qui t'a développé?", "qui t'a créé ?",
        "qui t'a créé?", "qui t'a fait ?", "qui t'a fait?",
        "qui es-tu ?", "qui es-tu?", "qui es tu ?", "qui es tu?",
    ]
    if query.lower() in identity_triggers:
        return jsonify({
            "answer": f"Je suis {BOT_NAME}, un assistant agricole intelligent développé par {BOT_CREATOR}.",
            "sources": [],
            "confidence": "Fort",
            "audio_url": "",
        })

    # Route by intent. Fertilizer questions get deterministic, grounded, cited
    # doses (never LLM-invented); everything else falls through to RAG.
    if classify(query) == INTENT_FERTILIZER:
        advice = get_fertilizer_advice(query)
        if advice is not None:
            audio_url = text_to_speech_to_static(advice["answer"])
            return jsonify({
                "answer": advice["answer"],
                "sources": advice["sources"],
                "confidence": "Fort",
                "audio_url": audio_url,
            })

    try:
        response = get_rag_chain().invoke(query)
        answer = response["result"]

        # Surface the documents the answer was grounded in.
        source_docs = response.get("source_documents", [])
        sources = _format_rag_sources(source_docs)
        confidence = _confidence_from_sources(sources)

        audio_url = text_to_speech_to_static(answer)
        return jsonify({
            "answer": answer,
            "sources": sources,
            "confidence": confidence,
            "audio_url": audio_url,
        })

    except Exception as e:
        print(f"ERROR — LLM/RAG execution failed: {e}")
        return jsonify({
            "answer": f"Désolé, {BOT_NAME} a rencontré une erreur de traitement. Veuillez réessayer plus tard.",
            "sources": [],
            "confidence": "Faible",
            "audio_url": "",
        })


@app.route("/screen", methods=["POST"])
def screen():
    """Leaf disease screening from an uploaded photo (Gemini Vision)."""
    if not disease_configured():
        return jsonify({
            "answer": "L'analyse d'image n'est pas disponible (clé Gemini non "
            "configurée).",
            "sources": [],
            "confidence": "Faible",
            "audio_url": "",
        })

    file = request.files.get("image")
    if file is None or not file.filename:
        return jsonify({
            "error": "Aucune image n'a été envoyée.",
            "confidence": "Faible",
        }), 400

    image_bytes = file.read()
    if not image_bytes:
        return jsonify({
            "error": "L'image envoyée est vide.",
            "confidence": "Faible",
        }), 400
    if len(image_bytes) > app.config["MAX_IMAGE_UPLOAD_BYTES"]:
        return _upload_too_large_response()

    limited = _rate_limit_response("screen", IMAGE_COOLDOWN_SECONDS)
    if limited is not None:
        return limited

    mime_type = file.mimetype or "image/jpeg"
    crop = request.form.get("crop", "").strip()[:80]
    growth_stage = request.form.get("growth_stage", "").strip()[:80]
    location = request.form.get("location", "").strip()[:120]
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
    return jsonify({
        "answer": answer,
        "case": case,
        "sources": [],
        "confidence": confidence,
        "audio_url": audio_url,
    })


@app.route("/feedback", methods=["POST"])
def feedback():
    rating = request.form.get("rating", "").strip()
    question = request.form.get("question", "").strip()
    answer = request.form.get("answer", "").strip()

    if rating not in ("up", "down"):
        return jsonify({"ok": False, "error": "invalid rating"}), 400

    try:
        os.makedirs(os.path.dirname(FEEDBACK_FILE), exist_ok=True)
        file_exists = os.path.isfile(FEEDBACK_FILE)
        with open(FEEDBACK_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["timestamp", "rating", "question", "answer"])
            writer.writerow(
                [datetime.now(timezone.utc).isoformat(), rating, question, answer]
            )
        return jsonify({"ok": True})
    except Exception as e:
        print(f"ERROR — feedback write failed: {e}")
        return jsonify({"ok": False, "error": "write failed"}), 500


if __name__ == "__main__":
    app.run(debug=DEBUG)
