# app.py — DakiKobo Flask entry point

import os
import csv
from datetime import datetime, timezone
from flask import Flask, render_template, request, jsonify

from core.rag_pipeline import (
    fetch_website_content,
    load_pdfs_from_folder,
    initialize_vector_store,
    vector_store_exists,
    load_vector_store,
    text_to_speech_to_static,
)
from core.llm_chain import llm, setup_retrieval_qa
from core.fertilizer import get_fertilizer_advice
from core.router import classify, INTENT_FERTILIZER
from core.disease import screen_leaf_image, is_configured as disease_configured
from config import (
    KNOWLEDGE_URLS,
    DATA_FOLDER,
    DEBUG,
    BOT_NAME,
    BOT_CREATOR,
    REBUILD_VECTORSTORE,
)

app = Flask(__name__)

# Lightweight feedback log (no database) — one CSV row per thumbs up/down.
FEEDBACK_FILE = os.path.join("data", "feedback.csv")


# =================================================================
# RAG INITIALIZATION — runs once at startup
# =================================================================

if vector_store_exists() and not REBUILD_VECTORSTORE:
    print("1. Loading existing vector store (set REBUILD_VECTORSTORE=true to rebuild)...")
    db = load_vector_store()
else:
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
    db = initialize_vector_store(all_docs)

print("4. Setting up RetrievalQA chain...")
chain = setup_retrieval_qa(db)
print(f"✅ {BOT_NAME} is ready!")


# =================================================================
# FLASK ROUTES
# =================================================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/ask", methods=["POST"])
def ask():
    query = request.form["messageText"].strip()

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
            "audio_url": "",
        })

    # Route by intent. Fertilizer questions get deterministic, grounded, cited
    # doses (never LLM-invented); everything else falls through to RAG.
    if classify(query) == INTENT_FERTILIZER:
        advice = get_fertilizer_advice(query)
        audio_url = text_to_speech_to_static(advice["answer"])
        return jsonify({
            "answer": advice["answer"],
            "sources": advice["sources"],
            "audio_url": audio_url,
        })

    try:
        response = chain.invoke(query)
        answer = response["result"]

        # Surface the documents the answer was grounded in (unique filenames).
        source_docs = response.get("source_documents", [])
        sources = sorted({doc.metadata.get("source", "Inconnu") for doc in source_docs})

        audio_url = text_to_speech_to_static(answer)
        return jsonify({"answer": answer, "sources": sources, "audio_url": audio_url})

    except Exception as e:
        print(f"ERROR — LLM/RAG execution failed: {e}")
        return jsonify({
            "answer": f"Désolé, {BOT_NAME} a rencontré une erreur de traitement. Veuillez réessayer plus tard.",
            "sources": [],
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
            "audio_url": "",
        })

    file = request.files.get("image")
    if file is None or not file.filename:
        return jsonify({"error": "no image"}), 400

    image_bytes = file.read()
    if not image_bytes:
        return jsonify({"error": "empty image"}), 400

    mime_type = file.mimetype or "image/jpeg"
    result = screen_leaf_image(image_bytes, mime_type)
    answer = result["answer"]
    audio_url = text_to_speech_to_static(answer)
    return jsonify({"answer": answer, "sources": [], "audio_url": audio_url})


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
