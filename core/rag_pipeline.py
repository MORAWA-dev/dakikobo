# core/rag_pipeline.py — RAG data ingestion, vector store, and TTS utilities

import os
import glob
import random
import string

import requests
import PyPDF2
import gtts
from flask import url_for

from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddings,
)

from config import (
    EMBEDDING_MODEL,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    TTS_LANGUAGE,
    TTS_MAX_CHARS,
    TTS_TIMEOUT_SECONDS,
    AUDIO_OUTPUT_DIR,
    VECTORSTORE_DIR,
)


# =================================================================
# WEB SCRAPING
# =================================================================

def fetch_website_content(url: str) -> list[Document]:
    """Fetch raw HTML from a URL as a Document tagged with its source URL.

    Returns an empty list on failure.
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return [Document(page_content=response.text, metadata={"source": url})]
    except requests.exceptions.RequestException as e:
        print(f"Warning: Could not fetch {url}. Error: {e}")
        return []


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


def load_pdfs_from_folder(folder_path: str) -> list[Document]:
    """Return a Document per readable PDF found recursively under folder_path.

    Each Document carries metadata["source"] = the PDF filename, so retrieved
    chunks can be cited. Subfolders are included. An unreadable or empty PDF is
    logged and skipped (never crashes startup).
    """
    pdf_files = sorted(
        glob.glob(os.path.join(folder_path, "**", "*.pdf"), recursive=True)
    )
    print(f"Found {len(pdf_files)} PDF(s) in and under {folder_path}")
    docs = []
    for f in pdf_files:
        text = extract_pdf_text(f)
        if text.strip():
            docs.append(
                Document(page_content=text, metadata={"source": os.path.basename(f)})
            )
            status = "ok"
        else:
            status = "EMPTY — skipped"
        print(f"  - {os.path.relpath(f, folder_path)} ({status})")
    return docs


# =================================================================
# TEXT SPLITTING & VECTOR STORE
# =================================================================

def split_documents(documents: list[Document]) -> list[Document]:
    """Split Documents into chunks, preserving each chunk's source metadata."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    return splitter.split_documents(documents)


def _embeddings():
    return SentenceTransformerEmbeddings(model_name=EMBEDDING_MODEL)


def vector_store_exists() -> bool:
    """True if a persisted Chroma store already exists on disk."""
    return os.path.isdir(VECTORSTORE_DIR) and bool(os.listdir(VECTORSTORE_DIR))


def load_vector_store():
    """Load the persisted Chroma store from disk (no re-embedding)."""
    return Chroma(persist_directory=VECTORSTORE_DIR, embedding_function=_embeddings())


def initialize_vector_store(documents: list[Document]):
    """
    Build a persistent ChromaDB vector store from a list of Documents and save it
    to VECTORSTORE_DIR. Each chunk keeps its source metadata.
    Returns None if there is no content.
    """
    valid = [d for d in documents if d.page_content and d.page_content.strip()]
    if not valid:
        print("FATAL: No valid content to initialize vector store.")
        return None

    chunks = split_documents(valid)
    db = Chroma.from_documents(
        chunks,
        _embeddings(),
        persist_directory=VECTORSTORE_DIR,
        # Cosine keeps relevance scores in a stable, model-independent range so
        # SIMILARITY_THRESHOLD works regardless of the embedding model.
        collection_metadata={"hnsw:space": "cosine"},
    )
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

        tts = gtts.gTTS(
            text=truncated,
            lang=TTS_LANGUAGE,
            timeout=TTS_TIMEOUT_SECONDS,
        )
        tts.save(output_path)

        return url_for("static", filename="audio/" + filename)
    except Exception as e:
        print(f"Audio generation skipped: {e}")
        return ""
