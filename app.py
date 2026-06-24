# app.py — DakiKobo Flask entry point

import os
from flask import Flask, render_template, request, jsonify

from core.rag_pipeline import (
    fetch_website_content,
    load_pdfs_from_folder,
    initialize_vector_store,
    text_to_speech_to_static,
)
from core.llm_chain import llm, setup_retrieval_qa
from config import KNOWLEDGE_URLS, DATA_FOLDER, DEBUG, BOT_NAME, BOT_CREATOR

app = Flask(__name__)


# =================================================================
# RAG INITIALIZATION — runs once at startup
# =================================================================

print("1. Fetching external content...")
try:
    website_contents = [fetch_website_content(url) for url in KNOWLEDGE_URLS]
except Exception as e:
    print(f"Warning: Web scraping failed: {e}")
    website_contents = []

print(f"2. Loading PDFs from {DATA_FOLDER}...")
pdf_texts = load_pdfs_from_folder(DATA_FOLDER)
valid_pdf_count = sum(1 for t in pdf_texts if t)

print(f"3. Initializing Vector Store ({valid_pdf_count} PDFs + {len(website_contents)} web sources)...")
all_contents = website_contents + pdf_texts
db = initialize_vector_store(all_contents)

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

    # Bot self-identification
    if query.lower() in ["who developed you?", "who created you?", "who made you?"]:
        return jsonify({
            "answer": f"I am {BOT_NAME}, an AI AgriBot developed by {BOT_CREATOR}.",
            "audio_url": "",
        })

    try:
        response = chain.invoke(query)
        answer = response["result"]
        audio_url = text_to_speech_to_static(answer)
        return jsonify({"answer": answer, "audio_url": audio_url})

    except Exception as e:
        print(f"ERROR — LLM/RAG execution failed: {e}")
        return jsonify({
            "answer": f"Sorry, {BOT_NAME} encountered a processing error. Please check the server logs.",
            "audio_url": "",
        })


if __name__ == "__main__":
    app.run(debug=DEBUG)
