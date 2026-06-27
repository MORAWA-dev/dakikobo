---
title: DakiKobo
sdk: docker
app_port: 7860
suggested_hardware: cpu-basic
startup_duration_timeout: 1h
preload_from_hub:
  - sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
---

# DakiKobo — AI Agricultural Advisor for Burkina Faso 🌾

DakiKobo is a French-language AI assistant for smallholder farmers in Burkina Faso.
It uses a **Retrieval-Augmented Generation (RAG)** pipeline grounded in agricultural
reference documents (FAO, AGRA, WFP and technical guides for the Sahel and Sudanian
Savanna zones) so answers stay accurate and source-backed rather than invented.

The focus crops are **mil (millet), sorgho (sorghum), maïs (maize), niébé (cowpea)
and arachide (groundnut)**. All output — answers, UI labels and voice — is in French,
and the interface is mobile-first for use on phones.

---

## Features

- **Grounded French answers** — RAG over a local document corpus; off-topic questions
  fall back to an honest "je ne sais pas" instead of hallucinating.
- **Source citations** — each answer shows which document(s) it was drawn from.
- **Fast inference** — Groq-hosted `llama-3.3-70b-versatile`.
- **Multilingual retrieval** — `paraphrase-multilingual-MiniLM-L12-v2` embeddings for
  good French matching, stored in a **persistent ChromaDB** (built once, fast on restart).
- **Hosted warm-up** — the Docker Space can prepare RAG in the background after startup so the
  first public question is less likely to pay the full indexing cost.
- **Voice output (TTS)** — answers can auto-play in French via gTTS and be replayed
  from their answer bubble.
- **Voice input (STT)** — records a short browser audio clip and transcribes it with
  Groq Whisper, with native browser speech recognition as a fallback.
- **Quota-safe public examples** — one-tap demo answers for text, fertilizer guidance and a
  sample image case, without spending live API calls.
- **Focused mobile UI** — examples stay visible, while weather and soil tools sit behind an
  `Outils` drawer so the conversation remains the main workspace.
- **Trust panel** — a compact `Sources & limites` dialog explains evidence, approximate signals,
  and required field confirmation.
- **Deterministic fertilizer doses** — source-grounded INERA/Burkina recommendations (never
  invented), with a "confirmez avec votre agent" disclaimer.
- **Leaf disease screening (optional)** — upload a leaf photo for a hedged French screening via
  Gemini Vision, with a "ceci n'est pas un diagnostic" disclaimer (requires a Gemini API key).
- **Weather-aware field signals** — Open-Meteo rainfall, ET0, soil moisture and short-term
  forecast cards for selected Burkina Faso locations.
- **Soil-aware fertilizer context** — SoilGrids texture, organic carbon, pH and retention-risk
  classes combined with deterministic fertilizer guidance.
- **Feedback capture** — 👍 / 👎 under each answer, logged to `data/feedback.csv` (no database).
- **Mobile-first responsive UI** — fills the screen on phones, input pinned to the bottom.

---

## Tech stack

| Component        | Technology                                            |
| ---------------- | ----------------------------------------------------- |
| Web framework    | Flask                                                 |
| LLM inference    | Groq — `llama-3.3-70b-versatile`                       |
| RAG orchestration| LangChain (core + community)                          |
| Embeddings       | `sentence-transformers` — multilingual MiniLM L12     |
| Vector store     | ChromaDB (persistent)                                 |
| Knowledge ingestion | Reviewed Markdown primary; PyPDF2 PDF fallback     |
| Text-to-speech   | gTTS (French)                                         |
| Weather data     | Open-Meteo Forecast API                               |
| Soil indicators  | SoilGrids REST API                                    |

---

## Setup

### Prerequisites

- Python **3.10 or 3.11**
- A **Groq API key** (from the [Groq console](https://console.groq.com))
- [`uv`](https://github.com/astral-sh/uv) recommended for fast environments
  (plain `venv` + `pip` also works)

### 1. Create the environment and install dependencies

Using `uv` (recommended):

```bash
uv venv .venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
```

Or with standard tools:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure your API key

Secrets are loaded from a `.env` file — **never put keys in source code**.

```bash
cp .env.example .env
```

Then edit `.env` and set your key:

```dotenv
GROQ_API_KEY=your_real_key_here
```

Optional — leaf disease screening needs a Google Gemini key (from
[Google AI Studio](https://aistudio.google.com/apikey)):

```dotenv
GEMINI_API_KEY=your_gemini_api_key_here
```

Verify it works anytime with:

```bash
python scripts/test_gemini.py
```

Optional overrides (defaults in `config.py` are fine for development):

```dotenv
# LLM_MODEL=llama-3.3-70b-versatile
# LLM_MAX_TOKENS=512
# LLM_TEMPERATURE=0.1
# STT_MODEL=whisper-large-v3-turbo
# STT_LANGUAGE=fr
# MAX_AUDIO_UPLOAD_MB=5.0
# GEMINI_MODEL=gemini-2.5-flash
# FLASK_DEBUG=true
# PREFER_MARKDOWN_KB=true # use Data/markdown before PDF fallback
# REBUILD_VECTORSTORE=true   # force a fresh index rebuild
```

### 3. Add knowledge documents

Place reviewed Markdown documents under `Data/markdown/`. DakiKobo uses this
Markdown corpus first because it is smaller and cleaner than extracting PDFs at
startup. Keep original Burkina Faso agriculture PDFs anywhere under `Data/` as
source files and as a fallback; subfolders are discovered recursively.

### 4. Run

```bash
python app.py
```

Open <http://127.0.0.1:5000> in your browser.

> **First run:** DakiKobo builds the vector index from the reviewed Markdown
> corpus and saves it to `chroma_db/`. On CPU this one-time build can take
> several minutes. Subsequent starts load the saved index and are fast. To
> rebuild later (e.g. after adding documents or changing the embedding model),
> start with `REBUILD_VECTORSTORE=true` to replace the saved index.

---

## Usage

- **Ask a question** about Burkina Faso agriculture in French.
- **Quick chips** above the input send common questions in one tap.
- **Voice output:** tick *"Activer la lecture vocale"* to hear answers read aloud.
- **Voice input:** tap the microphone, speak, then tap again to stop or wait for auto-stop.
- **Feedback:** use 👍 / 👎 under an answer — entries are appended to `data/feedback.csv`.

---

## Configuration reference

All tunables live in `config.py` (overridable via environment variables where shown):

| Setting                | Default                                  | Purpose                                  |
| ---------------------- | ---------------------------------------- | ---------------------------------------- |
| `LLM_MODEL`            | `llama-3.3-70b-versatile`                | Groq chat model                          |
| `EMBEDDING_MODEL`      | `paraphrase-multilingual-MiniLM-L12-v2`  | Sentence-transformer for retrieval       |
| `SIMILARITY_THRESHOLD` | `0.2`                                    | Min relevance to use a chunk (else fallback) |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `500` / `100`                    | Document splitting                       |
| `VECTORSTORE_DIR`      | `chroma_db`                              | Persisted index location (git-ignored)   |
| `RAG_WARMUP_ON_START`  | `false` locally, `true` in Docker        | Background RAG warm-up on hosted startup |
| `DATA_FOLDER`          | `Data`                                   | Root folder for source documents         |
| `MARKDOWN_FOLDER`      | `Data/markdown`                          | Reviewed Markdown corpus for RAG         |
| `PREFER_MARKDOWN_KB`   | `true`                                   | Use Markdown first; fallback to PDFs if needed |
| `TTS_LANGUAGE`         | `fr`                                     | Voice output language                    |
| `TTS_TIMEOUT_SECONDS`  | `8.0`                                    | Max wait for gTTS before returning no audio |
| `STT_MODEL`            | `whisper-large-v3-turbo`                 | Groq model for voice input transcription |
| `STT_LANGUAGE`         | `fr`                                     | Voice input language hint                |
| `MAX_AUDIO_UPLOAD_MB`  | `5.0`                                    | Maximum uploaded voice recording size    |
| `REQUEST_COOLDOWN_SECONDS` | `2.0`                                | Per-session cooldown for `/ask` requests |
| `VOICE_COOLDOWN_SECONDS` | `2.0`                                  | Per-session cooldown for voice transcription |
| `IMAGE_COOLDOWN_SECONDS` | `6.0`                                  | Per-session cooldown for image screening |
| `MAX_IMAGE_UPLOAD_MB`  | `5.0`                                    | Maximum uploaded image size              |

---

## Project layout

```
dakikobo/
├── app.py               # Flask entry point + routes (/ , /ask , /feedback)
├── config.py            # Central configuration
├── core/
│   ├── llm_chain.py     # LLM + RetrievalQA setup and French prompt
│   └── rag_pipeline.py  # Markdown/PDF ingestion, embeddings, Chroma, TTS
├── templates/index.html # Chat UI
├── static/              # CSS, JS, images, generated audio
├── Data/                # Source PDFs + reviewed Markdown knowledge corpus
└── requirements.txt
```

---

## Notes

- `.env`, `chroma_db/`, generated audio and `data/feedback.csv` are git-ignored.
- This tool gives general guidance; users should confirm specifics (e.g. fertilizer
  doses) with a local agricultural extension agent.
