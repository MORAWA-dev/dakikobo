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

# --- Knowledge Base ---
# Root folder ingested recursively (**/*.pdf) at startup. Points at the whole
# Data/ tree so PDFs in subfolders (knowledge_base, New Folder With Items, ...)
# are all picked up.
DATA_FOLDER = "Data"

# External URLs to scrape at startup (add URLs here, uncomment to activate)
KNOWLEDGE_URLS = [
    # "https://www.agriculture.bf/",
    # "https://www.fao.org/in-action/agrisurvey/access-to-data/burkina-faso/en",
    # "https://www.fao.org/in-action/mafap/where-we-work/burkina-faso/en",
]

# --- TTS ---
TTS_LANGUAGE = "fr"           # French — official language of Burkina Faso
TTS_MAX_CHARS = 700           # answers run ~100 words (~600 chars); cover the full reply
AUDIO_OUTPUT_DIR = os.path.join("static", "audio")

# --- Flask ---
DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "change-me-in-production")

# --- Bot Identity ---
BOT_NAME = "DakiKobo"
BOT_CREATOR = "a Geomatics MSc expert"
