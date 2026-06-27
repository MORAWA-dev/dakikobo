# DakiKobo Project Context

## What This Project Is

DakiKobo is a French-language Flask web app for agricultural advice in Burkina Faso.
It targets smallholder farmers, extension agents, agronomy students, and cooperatives.

The app answers crop and climate questions with RAG over local PDF documents, gives
source citations, supports text-to-speech and speech input, includes deterministic
fertilizer guidance, and can optionally screen leaf photos through Gemini Vision.

Primary crops:
- mil
- sorgho
- mais
- niebe
- arachide

## Current Stack

- Flask app entry point: `app.py`
- UI: `templates/index.html`, `static/js/index.js`, `static/css/style.css`
- RAG ingestion/vector store: `core/rag_pipeline.py`
- LLM chain/prompt: `core/llm_chain.py`
- Intent routing: `core/router.py`
- Fertilizer tool: `core/fertilizer.py`
- Disease photo screening: `core/disease.py`
- Config: `config.py`
- Local documents: `Data/`
- Persistent Chroma store: `chroma_db/`

Models/config:
- Groq chat model: `llama-3.3-70b-versatile`
- Embeddings: `paraphrase-multilingual-MiniLM-L12-v2`
- Gemini vision default: `gemini-2.5-flash`

## Safety And Product Rules

- All user-facing app text should be in French.
- Do not put API keys in source code. Use `.env`.
- Advice must stay cautious and source-grounded.
- Fertilizer and disease answers must include the relevant confirmation/disclaimer.
- Do not invent exact fertilizer doses through the LLM; use `core/fertilizer.py`.
- Off-topic questions should fall back honestly instead of hallucinating.

## Useful Commands

Install dependencies:

```bash
.venv/bin/pip install -r requirements.txt
```

Run the app:

```bash
.venv/bin/python app.py
```

Run offline tests:

```bash
.venv/bin/pytest -q tests/test_disease.py tests/test_fertilizer.py tests/test_ingestion.py tests/test_router.py
```

Run the live RAG smoke test:

```bash
.venv/bin/pytest -q tests/test_rag.py
```

The live RAG test may need network access for Hugging Face/Groq.

## Current Verification Status

Last local check:
- Offline tests: 15 passed, 1 PyPDF2 deprecation warning.
- Live RAG test: passed when network access was allowed.
- Flask import/startup: passed when network access was allowed.

## Notes For Future Codex Work

- Prefer small targeted edits.
- Keep README, `IMPLEMENTATION_PLAN.md`, and config defaults in sync.
- `DATA_FOLDER` intentionally points at the full `Data` tree so recursive ingestion
  includes PDFs in subfolders.
- Generated files such as `.env`, `chroma_db/`, `static/audio/*.mp3`, and
  `data/feedback.csv` should stay uncommitted.
