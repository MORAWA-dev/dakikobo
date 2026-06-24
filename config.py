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
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
SIMILARITY_THRESHOLD = 0.6
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

# --- Knowledge Base ---
# Relative path from app.py to the folder containing your PDF files
DATA_FOLDER = os.path.join("data", "knowledge_base")

# External URLs to scrape at startup (add URLs here, uncomment to activate)
KNOWLEDGE_URLS = [
    # "https://www.agriculture.bf/",
    # "https://www.fao.org/in-action/agrisurvey/access-to-data/burkina-faso/en",
    # "https://www.fao.org/in-action/mafap/where-we-work/burkina-faso/en",
]

# --- TTS ---
TTS_LANGUAGE = "fr"           # French — official language of Burkina Faso
TTS_MAX_CHARS = 180           # gTTS limit; keep conservative
AUDIO_OUTPUT_DIR = os.path.join("static", "audio")

# --- Flask ---
DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "change-me-in-production")

# --- Bot Identity ---
BOT_NAME = "DakiKobo"
BOT_CREATOR = "a Geomatics MSc expert"
