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

## Essayer la démo (60 s)

Live Space: **https://kimcomehome-dakikobo.hf.space/**

1. **Contexte parcelle** (optionnel) — culture, stade, lieu ; activez **Français simple** pour des phrases plus claires.
2. **Question texte** — ex. « Quand semer le mil ? » → carte *Conseil agricole* + sources.
3. **Engrais** — ex. « Dose d'engrais pour le sorgho » → doses **déterministes** (pas inventées par le LLM) + disclaimer agent.
4. **Photo de feuille** — dépistage prudent (*pas un diagnostic*).
5. **Sources & limites** — preuves, météo/sol indicatifs, confirmation terrain obligatoire.

Script détaillé : [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md).

Collecte de données (plus tard, hors code) : [`Data/reviews/DATA_COLLECTION_TASKS.md`](Data/reviews/DATA_COLLECTION_TASKS.md).  
Continuité agent : [`SESSION.md`](SESSION.md).

**Ce que DakiKobo n'est pas :** un oracle de rendement, un diagnostic officiel, ou un
remplacement de l'agent agricole.

---

## Features

- **Grounded French answers** — RAG over a local document corpus; off-topic questions
  fall back to an honest "je ne sais pas" instead of hallucinating.
- **Source citations and evidence ledger** — one scored retrieval grounds both the generated
  answer and its ranked source cards; every kept or dropped chunk is recorded by salted question
  hash with its score and citation decision for private offline evaluation.
- **Fast inference** — Groq-hosted `openai/gpt-oss-120b`, with reasoning tokens
  hidden so answers stay short and farmer-readable.
- **Multilingual retrieval** — `paraphrase-multilingual-MiniLM-L12-v2` embeddings for
  good French matching, stored in a **persistent ChromaDB** (built once, fast on restart).
- **Hosted warm-up** — the Docker Space can prepare RAG in the background after startup so the
  first public question is less likely to pay the full indexing cost.
- **Shared answer and context cache** — SQLite WAL serves repeat grounded answers immediately and
  shares weather, soil, and privacy-safe ops state across two threaded workers; Chroma startup is
  serialized across workers to prevent concurrent schema migrations.
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
- **Offline-first PWA** — after one connected load, the app shell, registry, demo examples and
  previously saved answers remain available; the same deterministic fertilizer tables work without
  network access, while uncached questions receive an honest offline notice.
- **Leaf disease screening (optional)** — upload a leaf photo for a hedged French screening via
  Gemini Vision, with a "ceci n'est pas un diagnostic" disclaimer (requires a Gemini API key).
- **Weather-aware field signals** — Open-Meteo rainfall, ET0, soil moisture and short-term
  forecast cards for selected Burkina Faso locations.
- **Soil-aware fertilizer context** — SoilGrids texture, organic carbon, pH and retention-risk
  classes combined with deterministic fertilizer guidance.
- **Field journal** — 👍 / 👎, crop/place ids, answer path, optional before/after photos, a
  seven-day reminder digest and follow-up outcomes are stored in a local SQLite case log.
- **Français simple** — optional plain-language mode with a field glossary (NPK, microdose, OAPH, etc.).
- **Field weather enrichment** — known locations can attach rainfall / water-stress signals to answers.
- **Mobile-first responsive UI** — fills the screen on phones, input pinned to the bottom.

---

## Tech stack

| Component        | Technology                                            |
| ---------------- | ----------------------------------------------------- |
| Web framework    | Flask                                                 |
| LLM inference    | Groq — `openai/gpt-oss-120b`                          |
| RAG orchestration| LangChain (core + community)                          |
| Embeddings       | `sentence-transformers` — multilingual MiniLM L12     |
| Vector store     | ChromaDB (persistent)                                 |
| Knowledge ingestion | Reviewed Markdown primary; PyPDF2 PDF fallback     |
| Text-to-speech   | gTTS (French)                                         |
| Weather data     | Open-Meteo Forecast API                               |
| Soil indicators  | SoilGrids REST API                                    |
| Runtime state    | SQLite WAL (answer/weather/soil caches + ops metrics) |
| Offline web app  | Service worker + Web App Manifest                    |

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
# LLM_MODEL=openai/gpt-oss-120b
# LLM_REASONING_FORMAT=hidden
# LLM_REASONING_EFFORT=low
# APP_VERSION=0.1.0
# LOG_LEVEL=INFO
# LLM_MAX_TOKENS=1024
# LLM_TEMPERATURE=0.1
# LLM_TIMEOUT_SECONDS=30.0
# LLM_MAX_RETRIES=1
# STT_MODEL=whisper-large-v3-turbo
# STT_LANGUAGE=fr
# STT_TIMEOUT_SECONDS=30.0
# STT_MAX_RETRIES=1
# MAX_AUDIO_UPLOAD_MB=5.0
# GEMINI_MODEL=gemini-2.5-flash
# GEMINI_TIMEOUT_SECONDS=45.0
# WEATHER_TIMEOUT_SECONDS=10.0
# SOIL_TIMEOUT_SECONDS=12.0
# WEB_FETCH_TIMEOUT_SECONDS=15.0
# FIRECRAWL_API_KEY=your_firecrawl_api_key_here
# FIRECRAWL_HTTP_TIMEOUT_SECONDS=45.0
# FIRECRAWL_SCRAPE_TIMEOUT_MS=60000
# FIRECRAWL_MAX_RETRIES=2
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
- **Feedback:** use 👍 / 👎 under an answer; DakiKobo links the rating and later field outcome to
  the exact retrieval decisions in `data/case_log.sqlite3`.
- **Due follow-ups:** `GET /journal/due` returns a privacy-minimized reminder digest without
  question or answer text.

---

## Evaluation

Run a repeatable public demo check against the Hugging Face Space:

```bash
python scripts/evaluate_rag.py
```

The script waits for `/healthz`, exercises RAG, fertilizer, weather, soil, and
off-topic safety cases, then writes `reports/rag_eval_results.md`.

The same evaluator is wired into GitHub Actions as
`.github/workflows/hf-smoke.yml`. It can run manually from the Actions tab and
also runs daily on schedule, uploading the Markdown report as an artifact.
The Docker image is checked by `.github/workflows/docker-build.yml`, which builds
the Space container and smoke-tests `/healthz` without pushing an image.

Useful options:

```bash
python scripts/evaluate_rag.py --base-url http://127.0.0.1:8005
python scripts/evaluate_rag.py --strict
```

## Offline Source Ingestion

Firecrawl is available for collecting candidate web pages, but scraped output is
not ingested directly. It is written to `Data/scraped/pending/` with source
metadata and a review checklist. URLs are checked against
`Data/scraped/source_allowlist.csv` by default.

Use the first curated FAO Burkina Faso seed batch:

```bash
python scripts/firecrawl_ingest.py --list-seeds
python scripts/firecrawl_ingest.py --seed-batch
```

Scrape a single allowlisted URL:

```bash
python scripts/firecrawl_ingest.py \
  --url https://www.fao.org/in-action/mafap/where-we-work/burkina-faso/en \
  --publisher "Publisher name" \
  --topics "semis, fertilite" \
  --crops "mil, sorgho"
```

For manual experiments outside the allowlist, pass `--allow-unlisted`. Do not
promote those files without adding a reviewed allowlist row first.

After human review and cleanup, promote the pending file into the active Markdown
corpus:

```bash
python scripts/firecrawl_ingest.py \
  --promote Data/scraped/pending/20260702_example_abc12345.md \
  --reviewer your_name
```

Then rebuild the vector store with `REBUILD_VECTORSTORE=true`.

---

## Configuration reference

All tunables live in `config.py` (overridable via environment variables where shown):

| Setting                | Default                                  | Purpose                                  |
| ---------------------- | ---------------------------------------- | ---------------------------------------- |
| `APP_VERSION`          | `0.1.0`                                  | Version string returned by `/version`    |
| `LOG_LEVEL`            | `INFO`                                   | Structured JSON application log level    |
| `LLM_MODEL`            | `openai/gpt-oss-120b`                    | Groq chat model                          |
| `LLM_REASONING_FORMAT` | `hidden`                                 | Keep chain-of-thought out of answers     |
| `LLM_REASONING_EFFORT` | `low`                                    | Reasoning budget (gpt-oss: low/med/high) |
| `LLM_TIMEOUT_SECONDS`  | `30.0`                                   | Max wait for Groq chat responses         |
| `LLM_MAX_RETRIES`      | `1`                                      | Groq chat retry count                    |
| `EMBEDDING_MODEL`      | `paraphrase-multilingual-MiniLM-L12-v2`  | Sentence-transformer for retrieval       |
| `SIMILARITY_THRESHOLD` | `0.2`                                    | Min relevance to use a chunk (else fallback) |
| `CITATION_SCORE_MARGIN` | `0.12`                                  | Drop secondary source cards far below the best match |
| `MAX_RAG_SOURCES`      | `2`                                      | Maximum RAG source cards shown per answer |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `500` / `100`                    | Document splitting                       |
| `VECTORSTORE_DIR`      | `chroma_db`                              | Persisted index location (git-ignored)   |
| `RAG_WARMUP_ON_START`  | `false` locally, `true` in Docker        | Background RAG warm-up on hosted startup |
| `DATA_FOLDER`          | `Data`                                   | Root folder for source documents         |
| `MARKDOWN_FOLDER`      | `Data/markdown`                          | Reviewed Markdown corpus for RAG         |
| `PREFER_MARKDOWN_KB`   | `true`                                   | Use Markdown first; fallback to PDFs if needed |
| `CASE_LOG_DB_PATH`     | `data/case_log.sqlite3`                  | Runtime SQLite feedback/case log         |
| `FOLLOW_UP_DELAY_DAYS` | `7`                                        | Days before a rated case is due for follow-up |
| `STATE_DB_PATH`        | `data/runtime_state.sqlite3`             | Shared SQLite cache and ops state         |
| `ANSWER_CACHE_ENABLED` | `true`                                   | Enable corpus-aware repeat-answer cache   |
| `ANSWER_CACHE_TTL_SECONDS` | `86400`                              | Answer cache lifetime (24 hours)          |
| `TTS_LANGUAGE`         | `fr`                                     | Voice output language                    |
| `TTS_TIMEOUT_SECONDS`  | `8.0`                                    | Max wait for gTTS before returning no audio |
| `STT_MODEL`            | `whisper-large-v3-turbo`                 | Groq model for voice input transcription |
| `STT_LANGUAGE`         | `fr`                                     | Voice input language hint                |
| `STT_TIMEOUT_SECONDS`  | `30.0`                                   | Max wait for Groq voice transcription    |
| `STT_MAX_RETRIES`      | `1`                                      | Groq voice transcription retry count     |
| `GEMINI_MODEL`         | `gemini-2.5-flash`                       | Gemini Vision model for leaf screening   |
| `GEMINI_TIMEOUT_SECONDS` | `45.0`                                 | Max wait for Gemini image screening      |
| `WEATHER_TIMEOUT_SECONDS` | `10.0`                                | Max wait for Open-Meteo requests         |
| `SOIL_TIMEOUT_SECONDS` | `18.0`                                   | Max wait for SoilGrids requests          |
| `WEB_FETCH_TIMEOUT_SECONDS` | `15.0`                              | Max wait for web knowledge fetches       |
| `FIRECRAWL_API_KEY`    | empty                                    | Firecrawl key for offline source scraping |
| `FIRECRAWL_HTTP_TIMEOUT_SECONDS` | `45.0`                         | Max wait for Firecrawl API requests      |
| `FIRECRAWL_SCRAPE_TIMEOUT_MS` | `60000`                            | Firecrawl page scrape timeout            |
| `FIRECRAWL_MAX_RETRIES` | `2`                                    | Retry count for retryable Firecrawl failures |
| `MAX_AUDIO_UPLOAD_MB`  | `5.0`                                    | Maximum uploaded voice recording size    |
| `REQUEST_COOLDOWN_SECONDS` | `2.0`                                | Per-session cooldown for `/ask` requests |
| `VOICE_COOLDOWN_SECONDS` | `2.0`                                  | Per-session cooldown for voice transcription |
| `IMAGE_COOLDOWN_SECONDS` | `6.0`                                  | Per-session cooldown for image screening |
| `MAX_IMAGE_UPLOAD_MB`  | `5.0`                                    | Maximum uploaded image size              |

---

## Project layout

```
dakikobo/
├── app.py               # Flask entry point + routes (/ask, /feedback, /journal/due)
├── config.py            # Central configuration
├── core/
│   ├── crops.py         # Canonical crop ids, French labels and capabilities
│   ├── places.py        # Canonical place ids, labels and weather coverage
│   ├── retrieval.py     # Citation ranking, confidence and stable chunk ids
│   ├── case_contract.py # Shared field-case data contract
│   ├── case_log.py      # SQLite field journal and evidence ledger
│   ├── llm_chain.py     # LLM + RetrievalQA setup and French prompt
│   └── rag_pipeline.py  # Markdown/PDF ingestion, embeddings, Chroma, TTS
├── templates/index.html # Chat UI
├── static/              # CSS, JS, images, generated audio
├── scripts/             # Utility scripts, including public RAG evaluation
├── reports/             # Generated evaluation reports
├── Data/                # Source PDFs + reviewed Markdown knowledge corpus
└── requirements.txt
```

---

## Notes

- `.env`, `chroma_db/`, generated audio, `data/feedback.csv` and
  `data/case_log.sqlite3*` are git-ignored.
- `/healthz` reports readiness; `/version` reports app version, commit if exposed
  by the host, key runtime config flags, and the field-journal schema version.
- Runtime logs are JSON lines with route, status, latency, model/feature, failure
  type and confidence where available. Raw questions, answers, images and audio
  are not logged.
- Leaf photos and voice recordings are used only for the requested analysis or
  transcription. The app warns users not to send faces, names, numbers or
  personal documents.
- This tool gives general guidance; users should confirm specifics (e.g. fertilizer
  doses) with a local agricultural extension agent.
