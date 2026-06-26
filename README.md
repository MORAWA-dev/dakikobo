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
- **Voice output (TTS)** — answers can be read aloud in French via gTTS.
- **Voice input (STT)** — optional French speech-to-text in supported browsers, with a
  visible "listening" indicator.
- **Quick-action chips** — one-tap common questions (semis du mil, fertilisation, etc.).
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
| PDF ingestion    | PyPDF2                                                 |
| Text-to-speech   | gTTS (French)                                         |

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

Optional overrides (defaults in `config.py` are fine for development):

```dotenv
# LLM_MODEL=llama-3.3-70b-versatile
# LLM_MAX_TOKENS=512
# LLM_TEMPERATURE=0.1
# FLASK_DEBUG=true
# REBUILD_VECTORSTORE=true   # force a fresh index rebuild
```

### 3. Add knowledge documents

Place your Burkina Faso agriculture PDFs anywhere under the `Data/` folder
(subfolders are ingested recursively).

### 4. Run

```bash
python app.py
```

Open <http://127.0.0.1:5000> in your browser.

> **First run:** DakiKobo builds the vector index from your PDFs and saves it to
> `chroma_db/`. On CPU this one-time build can take several minutes. Subsequent
> starts load the saved index and are fast. To rebuild later (e.g. after adding
> documents or changing the embedding model), delete `chroma_db/` or start with
> `REBUILD_VECTORSTORE=true`.

---

## Usage

- **Ask a question** about Burkina Faso agriculture in French.
- **Quick chips** above the input send common questions in one tap.
- **Voice output:** tick *"Activer la lecture vocale"* to hear answers read aloud.
- **Voice input:** tap the microphone (Chrome/supported browsers); it pulses while listening.
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
| `DATA_FOLDER`          | `Data`                                   | Root folder ingested recursively         |
| `TTS_LANGUAGE`         | `fr`                                     | Voice output language                    |

---

## Project layout

```
dakikobo/
├── app.py               # Flask entry point + routes (/ , /ask , /feedback)
├── config.py            # Central configuration
├── core/
│   ├── llm_chain.py     # LLM + RetrievalQA setup and French prompt
│   └── rag_pipeline.py  # PDF ingestion, embeddings, Chroma, TTS
├── templates/index.html # Chat UI
├── static/              # CSS, JS, images, generated audio
├── Data/                # Knowledge-base PDFs (recursive)
└── requirements.txt
```

---

## Notes

- `.env`, `chroma_db/`, generated audio and `data/feedback.csv` are git-ignored.
- This tool gives general guidance; users should confirm specifics (e.g. fertilizer
  doses) with a local agricultural extension agent.
