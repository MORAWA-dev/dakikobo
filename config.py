# config.py — Central configuration for DakiKobo
# All tuneable values live here. Secret keys are loaded from environment variables.

import os
from dotenv import load_dotenv

load_dotenv()  # Loads variables from a .env file if present

# --- LLM ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", 512))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0.1))

# --- Gemini Vision (leaf disease screening) ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# --- Embeddings & Vector Store ---
# Multilingual model — much better for French queries/corpus than all-MiniLM
# (English) while staying light/fast enough to embed on CPU.
# NOTE: changing this model changes the vector dimension; rebuild the store
# (delete chroma_db/ or run with REBUILD_VECTORSTORE=true).
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
SIMILARITY_THRESHOLD = 0.2  # on-topic FR queries score ~0.3-0.4, off-topic <=0.0 (measured)
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

# Persistent Chroma store: built once, then loaded on restart (folder is git-ignored).
# Set REBUILD_VECTORSTORE=true to force a fresh rebuild (e.g. after changing the
# embedding model or adding documents).
VECTORSTORE_DIR = os.getenv("VECTORSTORE_DIR", "chroma_db")
REBUILD_VECTORSTORE = os.getenv("REBUILD_VECTORSTORE", "false").lower() == "true"
RAG_WARMUP_ON_START = os.getenv("RAG_WARMUP_ON_START", "false").lower() == "true"

# --- Knowledge Base ---
# Root folder for source documents. The reviewed Markdown conversion is preferred
# for RAG because it is smaller and cleaner than extracting PDFs at startup. PDFs
# remain available as a fallback when Markdown is missing or explicitly disabled.
DATA_FOLDER = os.getenv("DATA_FOLDER", "Data")
MARKDOWN_FOLDER = os.getenv("MARKDOWN_FOLDER", os.path.join(DATA_FOLDER, "markdown"))
PREFER_MARKDOWN_KB = os.getenv("PREFER_MARKDOWN_KB", "true").lower() == "true"

# External URLs to scrape at startup (add URLs here, uncomment to activate)
KNOWLEDGE_URLS = [
    # "https://www.agriculture.bf/",
    # "https://www.fao.org/in-action/agrisurvey/access-to-data/burkina-faso/en",
    # "https://www.fao.org/in-action/mafap/where-we-work/burkina-faso/en",
]

# --- TTS ---
TTS_LANGUAGE = "fr"           # French — official language of Burkina Faso
TTS_MAX_CHARS = 700           # answers run ~100 words (~600 chars); cover the full reply
TTS_TIMEOUT_SECONDS = float(os.getenv("TTS_TIMEOUT_SECONDS", "8.0"))
AUDIO_OUTPUT_DIR = os.path.join("static", "audio")

# --- Flask ---
DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "change-me-in-production")
REQUEST_COOLDOWN_SECONDS = float(os.getenv("REQUEST_COOLDOWN_SECONDS", "2.0"))
IMAGE_COOLDOWN_SECONDS = float(os.getenv("IMAGE_COOLDOWN_SECONDS", "6.0"))
MAX_IMAGE_UPLOAD_MB = float(os.getenv("MAX_IMAGE_UPLOAD_MB", "5.0"))
MAX_IMAGE_UPLOAD_BYTES = int(MAX_IMAGE_UPLOAD_MB * 1024 * 1024)

# --- Bot Identity ---
BOT_NAME = "DakiKobo"
BOT_CREATOR = "a Geomatics MSc expert"
