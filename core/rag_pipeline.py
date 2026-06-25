# core/rag_pipeline.py — RAG data ingestion, vector store, and TTS utilities

import os
import glob
import random
import string
from itertools import chain

import requests
import PyPDF2
import gtts
from flask import url_for

from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddings,
)

from config import (
    EMBEDDING_MODEL,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    TTS_LANGUAGE,
    TTS_MAX_CHARS,
    AUDIO_OUTPUT_DIR,
)


# =================================================================
# WEB SCRAPING
# =================================================================

def fetch_website_content(url: str) -> str:
    """Fetch raw HTML from a URL. Returns empty string on failure."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Warning: Could not fetch {url}. Error: {e}")
        return ""


# =================================================================
# PDF EXTRACTION
# =================================================================

def extract_pdf_text(pdf_file: str) -> str:
    """Extract all text from a PDF file. Returns empty string on failure."""
    try:
        with open(pdf_file, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            return "".join(
                page.extract_text() or "" for page in reader.pages
            )
    except Exception as e:
        print(f"Error reading PDF {pdf_file}: {e}")
        return ""


def load_pdfs_from_folder(folder_path: str) -> list[str]:
    """Return extracted text from every PDF found in folder_path."""
    pdf_files = glob.glob(os.path.join(folder_path, "*.pdf"))
    print(f"Found {len(pdf_files)} PDF(s) in {folder_path}")
    return [extract_pdf_text(f) for f in pdf_files]


# =================================================================
# TEXT SPLITTING & VECTOR STORE
# =================================================================

def split_text(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    return splitter.split_text(text)


def initialize_vector_store(contents: list[str]):
    """
    Build a ChromaDB vector store from a list of text strings.
    Returns None if no valid content is provided.
    """
    valid = [c for c in contents if c and c.strip()]
    if not valid:
        print("FATAL: No valid content to initialize vector store.")
        return None

    embedding_fn = SentenceTransformerEmbeddings(model_name=EMBEDDING_MODEL)
    chunks = list(chain.from_iterable(split_text(c) for c in valid))
    db = Chroma.from_texts(chunks, embedding_fn)
    return db


# =================================================================
# TEXT-TO-SPEECH (TTS)
# =================================================================

def _random_filename(length: int = 15) -> str:
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choice(chars) for _ in range(length)) + ".mp3"


def _truncate_for_speech(text: str, max_chars: int) -> str:
    """Trim text to max_chars without cutting a word in half.

    Prefers to end on the last sentence boundary (.!?) within the limit; falls
    back to the last whitespace, so the audio never stops mid-word.
    """
    text = text.strip()
    if len(text) <= max_chars:
        return text

    window = text[:max_chars]
    cut = max(window.rfind(". "), window.rfind("! "), window.rfind("? "))
    if cut == -1:
        cut = window.rfind(" ")
    if cut == -1:
        return window  # single very long token; nothing to cut on
    # +1 keeps the sentence-ending punctuation when we cut on it
    return window[: cut + 1].strip()


def text_to_speech_to_static(text: str) -> str:
    """
    Convert text to an MP3 file saved under static/audio/.
    Returns the browser-accessible URL path, or '' on failure.
    """
    try:
        os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)
        truncated = _truncate_for_speech(text, TTS_MAX_CHARS)
        filename = _random_filename()
        output_path = os.path.join(AUDIO_OUTPUT_DIR, filename)

        tts = gtts.gTTS(text=truncated, lang=TTS_LANGUAGE)
        tts.save(output_path)

        return url_for("static", filename="audio/" + filename)
    except Exception as e:
        print(f"Audio generation error: {e}")
        return ""
