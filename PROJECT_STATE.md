# DakiKobo Project State

Last updated: 2026-07-10 (cannot-confirm + vision lab)

This file is a compact state report for another model, reviewer, or engineer to
evaluate what already exists before proposing new work.

## One-Line Summary

DakiKobo is a deployed French-language agricultural field assistant for Burkina
Faso. It combines RAG over reviewed local Markdown documents, deterministic
fertilizer guidance, weather and soil context tools, voice input/output, image
screening, citations, confidence labels, and a mobile-first chat UI.

## Live Deployment

- Public app: `https://kimcomehome-dakikobo.hf.space/`
- Hugging Face Space repo: `https://huggingface.co/spaces/kimcomehome/dakikobo`
- Space SDK: Docker
- Runtime port: `7860`
- Suggested hardware: `cpu-basic`
- Latest HF runtime commit verified: `990b80e6` (GitHub `8028159b`)
- Live health verified on 2026-07-10:
  - `ok=true`
  - `rag_ready=true`
  - `rag_status=ready`
  - warm-up finished at `2026-07-10T12:19:01+00:00`
  - OAPH probe correct: **Offensive Agropastorale et Halieutique** (not invented expansion)

Local git note:

- GitHub `origin/main` is the primary source history.
- Hugging Face `hf/main` has a separate history for the Space repo, so runtime
  deploys are applied through a temporary HF worktree.
- Do not assume GitHub and HF commit hashes match; compare feature state, not
  only commit IDs.

## Target Users

- Smallholder farmers in Burkina Faso
- Extension agents
- Agronomy students
- Cooperatives and field advisors

Primary crops:

- mil
- sorgho
- mais
- niebe
- arachide

Language:

- All user-facing app text should be French.
- Advice should stay cautious, source-grounded, and explicit about field
  confirmation.

## Current Capabilities

### 1. Text Agricultural Questions

Users can ask French questions about crops, soil, climate, disease symptoms,
planting, storage, and common farming practices.

Implementation:

- Route: `/ask`
- Entry point: `app.py`
- RAG chain: `core/llm_chain.py`
- Retrieval/ingestion: `core/rag_pipeline.py`
- Model: Groq `openai/gpt-oss-120b` (reasoning hidden). Replaced
  `llama-3.3-70b-versatile`, which Groq decommissioned on 2026-08-16.
- Embeddings: `paraphrase-multilingual-MiniLM-L12-v2`
- Vector store: ChromaDB in `chroma_db/` locally or rebuilt on HF

Behavior:

- Answers in French.
- Shows source cards below answers.
- Shows confidence labels: `Fort`, `Moyen`, `Faible`.
- Non-refusal text and fertilizer answers also return a structured evidence-first
  `case` card: short answer, why/evidence, actions, what to avoid, confirmation.
- First-class uncertainty: answers starting with « Je ne peux pas confirmer »
  return `answer_kind=uncertain`, confidence `Faible`, and a Non confirmé case.
- Uses off-topic fallback rather than inventing unsupported advice.
- Generates French TTS audio when possible.
- Shows a visible privacy note for photos and voice recordings.
- Landing strip above chat states purpose, crops, and field-confirmation limits.
- Oversized text questions are rejected via `MAX_QUESTION_CHARS` (default 1000).

### 2. RAG Knowledge Base

Active source path:

- `Data/markdown/`

Current active Markdown file count:

- 19 Markdown files

Important curated additions:

- `Data/markdown/prosol_fertilite_sols_burkina_2020.md`
- `Data/markdown/iita_niebe_afrique_ouest_2018.md`
- `Data/markdown/scraped_reviewed/fao_burkina_policy_data_profile_2026.md`
- `Data/markdown/scraped_reviewed/maerah_oaph_orientation_burkina_2026.md`
- `Data/markdown/scraped_reviewed/cilss_orientation_sahel_2026.md`

Source governance:

- `DATA_SOURCES.md` tracks source status, URL, scope, review notes, and rejected
  or comparative sources.
- Markdown is preferred over PDFs because it is lighter and cleaner for hosted
  startup.
- PDFs remain under `Data/` as source material and fallback.
- `Data/_archive/rejected_deep_research_2026-06-27/` contains rejected generated
  research outputs and is intentionally not part of active RAG.
- Persisted Chroma stores are validated at startup. If the collection is missing
  or contains zero chunks, the app clears `chroma_db/` and rebuilds from the
  active Markdown/PDF corpus.
- Persisted Chroma stores now include `source_manifest.json`. If active
  Markdown/PDF files, embedding model, chunk settings, or configured external
  knowledge URLs change, the app treats the store as stale and rebuilds it.

Retrieval status:

- Source cards are now filtered and ranked with retrieval relevance scores when
  the Chroma store is available.
- Source cards also use a crop/topic lexical guard against the full retrieved
  chunks, so mixed generic citations are suppressed for focused questions.
- Source cards expose reviewed metadata when available: publisher, year,
  country, review status, and a safe clickable source URL.
- Weak secondary citations are dropped when they score far below the best match.
- RAG answers show at most two source cards by default (`MAX_RAG_SOURCES=2`).
- If retrieval returns zero documents, the app forces the grounded fallback
  instead of returning an uncited LLM answer.
- Live tuning is still recommended because edge cases can depend on the hosted
  vector store contents and query wording.

### 3. Deterministic Fertilizer Guidance

Users can ask fertilizer questions for the main crops.

Implementation:

- `core/fertilizer.py`
- Routed before RAG through `core/router.py`

Supported crops:

- mil
- sorgho
- mais
- niebe
- arachide

Behavior:

- Does not let the LLM invent fertilizer doses.
- Returns source-grounded dose guidance.
- Includes confirmation disclaimer: exact dose depends on soil, rainfall,
  resources, and local extension advice.

### 4. Weather Context

The UI includes a weather tool behind the `Outils` drawer.

Implementation:

- Route: `/weather`
- Location route: `/weather/locations`
- Module: `core/weather.py`
- Data source: Open-Meteo

Locations include:

- Ouagadougou
- Bobo-Dioulasso
- Kaya
- Ouahigouya
- Fada N'Gourma
- Dori

Signals:

- rainfall over recent days
- short-term rain forecast
- ET0
- soil moisture signal
- practical warnings such as possible water stress or fertilizer timing risk

### 5. Soil And Fertilizer Context

The UI includes a soil + fertilizer tool behind the `Outils` drawer.

Implementation:

- Route: `/soil`
- Location/crop route: `/soil/locations`
- Module: `core/soil.py`
- Data source: SoilGrids REST API
- Fertilizer combination: `core/fertilizer.py`

Signals:

- texture tendency
- clay/sand estimates
- organic carbon
- pH
- nutrient retention risk

Safety:

- SoilGrids is treated as an indicative signal, not a field soil test.
- Responses tell the user to confirm doses through soil testing or an agent.

### 6. Leaf Photo Screening

Users can upload a leaf photo for cautious screening.

Implementation:

- Route: `/screen`
- Module: `core/disease.py`
- Model: Gemini Vision, default `gemini-2.5-flash`
- UI: image upload button plus context form

Context form asks for:

- crop
- growth stage
- optional location
- "Je ne sais pas" path

Behavior:

- Produces structured case cards.
- Includes observations, possible causes, immediate actions, confidence, risk,
  and disclaimer.
- Does not present output as a final diagnosis.
- Uploaded photos are read in memory for analysis and are not saved by the app.
- The UI tells users to avoid faces or personal identifiers in uploaded photos.
- Requires `GEMINI_API_KEY`.

### 7. Voice Input

Voice input was upgraded from fragile browser-native speech recognition to
server-side transcription.

Implementation:

- Route: `/speech`
- Module: `core/speech.py`
- Frontend: `static/js/index.js`
- STT model: Groq `whisper-large-v3-turbo`

Behavior:

- Browser records a short audio clip with `MediaRecorder`.
- Audio is posted to `/speech`.
- Backend transcribes with Groq Whisper.
- Transcript is sent as a normal `/ask` question.
- Native browser speech recognition remains as fallback.
- French errors are returned for blocked microphone, empty audio, oversized
  upload, unclear speech, or transcription failure.
- Voice recordings are read for transcription and are not written to app logs.
- The UI tells users to avoid personal identifiers in voice recordings.

Limit:

- A true microphone test must be done manually in a browser because automated
  tests cannot grant microphone permissions.

### 8. Voice Output

Text-to-speech output is available.

Implementation:

- Module: `core/rag_pipeline.py`
- Function: `text_to_speech_to_static`
- Engine: gTTS
- Output path: `static/audio/`

Behavior:

- Optional global auto-play toggle.
- Per-answer `Réécouter` button when audio exists.
- TTS failures return no audio rather than blocking the answer.
- Generated audio is git-ignored.

### 9. UI And Demo Experience

Frontend files:

- `templates/index.html`
- `static/js/index.js`
- `static/css/style.css`

Current UI state:

- Mobile-first chat interface.
- Neutral DakiKobo logo avatar.
- Example cards are visible.
- Weather and soil tools are hidden behind `Outils`.
- `Sources & limites` panel explains evidence and limits.
- Feedback buttons under answers.
- Camera, mic, send, and tools controls are available from the input area.

Quota-safe examples:

- text question
- fertilizer case
- image screening case

### 10. Structured Logs

The Flask app emits privacy-safe JSON logs for request observability.

Implementation:

- Logger name: `dakikobo`
- Config: `LOG_LEVEL`
- General fields: event, timestamp, method, route, endpoint, status code,
  latency in milliseconds
- Route-specific fields where available: feature, model, outcome, failure type,
  confidence, source count, upload byte size, refusal flag

Privacy rule:

- Logs do not include raw questions, answers, image bytes, audio bytes, API keys,
  user photos, or user recordings.

### 11. SQLite Case Log

Feedback buttons write answer ratings to a local SQLite database for later
evaluation.

Implementation:

- Module: `core/case_log.py`
- Route: `/feedback`
- Config: `CASE_LOG_DB_PATH`
- Default path: `data/case_log.sqlite3`
- Table: `feedback_events`

Stored fields:

- `id`
- `created_at`
- `rating`
- `question`
- `answer`
- `outcome` (nullable)
- `outcome_at` (nullable)

The database is runtime-generated and git-ignored.

The `/feedback/outcome` route accepts a follow-up outcome for a previously rated
answer. Valid outcomes are `applied`, `improved`, `unchanged`, and `worse`. The
outcome and its timestamp are stored alongside the original feedback event.

### 12. Evaluation Tooling

The project includes a repeatable public demo evaluator.

Implementation:

- `scripts/evaluate_rag.py`
- `.github/workflows/docker-build.yml`
- `.github/workflows/hf-smoke.yml`
- Default target: `https://kimcomehome-dakikobo.hf.space`
- Default output: `reports/rag_eval_results.md`

Coverage:

- RAG questions for mil, niébé, maïs, and arachide
- deterministic fertilizer routing
- off-topic fallback
- weather context
- soil + fertilizer context

The evaluator records HTTP status, latency, confidence, source count, source
cards, answer/context snippets, and pass/fail checks.

GitHub Actions:

- Docker build workflow: builds the Space image on push, pull request, and manual
  dispatch; runs the container with `RAG_WARMUP_ON_START=false`; polls `/healthz`.
- Manual workflow: "Hugging Face Space smoke test"
- Scheduled workflow: daily at `05:30 UTC`
- Installs only `requests`, runs `scripts/evaluate_rag.py`, and uploads
  `reports/rag_eval_results.md` as an artifact.

### 13. Firecrawl Candidate Source Ingestion

Firecrawl is wired for offline candidate collection, not runtime answering.

Implementation:

- Script: `scripts/firecrawl_ingest.py`
- Allowlist: `Data/scraped/source_allowlist.csv`
- Seed batch: `Data/scraped/seed_urls_fao_burkina.txt`
- Pending output: `Data/scraped/pending/`
- Reviewed active output: `Data/markdown/scraped_reviewed/`
- Config: `FIRECRAWL_API_KEY`, timeout, scrape-timeout, and retry env vars

Workflow:

1. Scrape selected trusted URLs into pending Markdown.
2. Review title, publisher, date, scope, license, crop facts, and risky advice.
3. Promote reviewed files with `--promote ... --reviewer ...`.
4. Rebuild the vector store before using promoted sources in RAG.

Safety:

- Scraped files carry `review_status: pending_human_review`.
- URLs are rejected unless they match the allowlist, unless `--allow-unlisted`
  is passed for a manual experiment.
- Pending files live outside `Data/markdown/`, so they do not enter active RAG.
- Promoted files remove the review checklist before ingestion.

First generated pending batch:

- FAO MAFAP Burkina Faso
- FAO AGRISurvey Burkina Faso
- FAO Country Profiles Burkina Faso
- These files are local pending review artifacts and are git-ignored until a
  reviewer cleans and promotes them.
- A short reviewed synthesis from this batch was promoted to active Markdown:
  `Data/markdown/scraped_reviewed/fao_burkina_policy_data_profile_2026.md`.
  It is limited to policy, public expenditure, price incentives, statistics,
  EPA data availability, and FAO country-profile context. It must not be used
  for exact fertilizer, pesticide, disease, or crop-calendar recommendations.

## Main Routes

| Route | Method | Purpose |
|---|---:|---|
| `/` | GET | Main UI |
| `/healthz` | GET | App and RAG warm-up status |
| `/version` | GET | App version, host commit if exposed, and runtime config flags |
| `/ask` | POST | Main text question endpoint |
| `/speech` | POST | Voice transcription endpoint |
| `/screen` | POST | Leaf image screening endpoint |
| `/weather` | GET | Weather context card |
| `/weather/locations` | GET | Available weather locations |
| `/soil` | GET | Soil + fertilizer context |
| `/soil/locations` | GET | Available soil locations and crops |
| `/examples/<example_id>` | GET | Quota-safe demo examples |
| `/feedback` | POST | Answer rating capture into SQLite case log |
| `/feedback/outcome` | POST | Follow-up outcome after advice (applied/improved/unchanged/worse) |

## Key Files For Review

Application:

- `app.py`
- `config.py`
- `requirements.txt`
- `.github/workflows/docker-build.yml`
- `.github/workflows/hf-smoke.yml`

Core modules:

- `core/rag_pipeline.py`
- `core/llm_chain.py`
- `core/router.py`
- `core/fertilizer.py`
- `core/disease.py`
- `core/speech.py`
- `core/weather.py`
- `core/soil.py`
- `core/case.py`

Frontend:

- `templates/index.html`
- `static/js/index.js`
- `static/css/style.css`

Data and governance:

- `Data/markdown/`
- `DATA_SOURCES.md`
- `TODO.md`
- `IMPLEMENTATION_PLAN.md`

Tests:

- `tests/test_app_routes.py`
- `tests/test_case_log.py`
- `tests/test_disease.py`
- `tests/test_evaluate_rag.py`
- `tests/test_fertilizer.py`
- `tests/test_frontend_assets.py`
- `tests/test_ingestion.py`
- `tests/test_rag.py`
- `tests/test_router.py`
- `tests/test_soil.py`
- `tests/test_tts.py`
- `tests/test_weather.py`

## Verification Status

Latest local full test run (2026-08-19, after the gpt-oss migration):

- `212 passed`
- 1 PyPDF2 deprecation warning
- 1 Pydantic v2 deprecation warning raised from `langchain_groq`

Note on `tests/test_rag.py::test_french_crop_question_returns_answer`: it makes a
real Groq call, so it fails with HTTP 403 `Access denied. Please check your
network settings.` on networks Groq blocks. That is an environment limitation,
not a code failure. An invalid key would return 401 instead.

Latest focused evaluator tests:

- `tests/test_app_routes.py::test_rag_route_returns_unique_sources tests/test_app_routes.py::test_rag_route_exposes_source_metadata tests/test_frontend_assets.py`
- `6 passed`
- 1 PyPDF2 deprecation warning

Latest live HF checks:

- `/healthz`: ready
- `/version`: commit `4e1c34cf6eaf624c28ac41a5717ba6342e18dd11`
- `/`: rendered `mediaPrivacyNote` and the visible media privacy text
- `/ask` FAO data question: returned the new FAO Burkina policy/data synthesis
  source with publisher/year/country/review-status URL metadata and confidence
  `Fort`
- `/ask` niébé storage question: returned one IITA source and confidence `Fort`
- `/ask` mil semis question: returned cited answer and confidence `Fort`
- `/speech` fake audio: returned expected French transcription failure, proving
  route is deployed and active

Manual browser test still recommended:

- Open HF app.
- Tap mic.
- Allow microphone permission.
- Speak a short French agricultural question.
- Stop recording.
- Confirm the transcript is sent and answered.

## Environment Variables

Required:

- `GROQ_API_KEY`

Optional but used by features:

- `GEMINI_API_KEY`
- `FLASK_SECRET_KEY`
- `APP_VERSION`
- `LLM_MODEL`
- `GROQ_USER_AGENT`
- `STT_MODEL`
- `STT_LANGUAGE`
- `STT_MAX_RETRIES`
- `STT_TIMEOUT_SECONDS`
- `MAX_AUDIO_UPLOAD_MB`
- `GEMINI_MODEL`
- `GEMINI_TIMEOUT_SECONDS`
- `LLM_TIMEOUT_SECONDS`
- `LLM_MAX_RETRIES`
- `WEATHER_TIMEOUT_SECONDS`
- `SOIL_TIMEOUT_SECONDS`
- `WEB_FETCH_TIMEOUT_SECONDS`
- `FIRECRAWL_API_KEY`
- `FIRECRAWL_API_URL`
- `FIRECRAWL_HTTP_TIMEOUT_SECONDS`
- `FIRECRAWL_SCRAPE_TIMEOUT_MS`
- `FIRECRAWL_MAX_RETRIES`
- `FIRECRAWL_PENDING_DIR`
- `FIRECRAWL_REVIEWED_DIR`
- `PREFER_MARKDOWN_KB`
- `REBUILD_VECTORSTORE`
- `RAG_WARMUP_ON_START`
- `VECTORSTORE_DIR`
- `REQUEST_COOLDOWN_SECONDS`
- `VOICE_COOLDOWN_SECONDS`
- `IMAGE_COOLDOWN_SECONDS`
- `MAX_IMAGE_UPLOAD_MB`
- `LOG_LEVEL`
- `CASE_LOG_DB_PATH`

Do not commit:

- `.env`
- `chroma_db/`
- `static/audio/*.mp3`
- `data/feedback.csv`
- `data/case_log.sqlite3*`
- user photos or recordings
- API keys

## Known Gaps

Product:

- The app still feels partly like a chat widget instead of a full field workflow.
- Text questions do not yet always collect crop, commune, growth stage, or date.
- Feedback is stored in SQLite with follow-up outcome tracking. Deferred follow-up reminders are not yet implemented.
- A short privacy note exists, but there is no full privacy policy page yet.

RAG and data:

- Document-level metadata exists for reviewed Markdown and is now exposed in RAG
  source cards when available.
- Retrieval source filtering exists, but needs more live evaluation and tuning.
- Generated/scraped data should remain outside RAG until human review.
- Firecrawl ingestion and the first FAO allowlist/seed batch exist. One curated
  FAO synthesis is active; the raw scraped files remain ignored pending
  artifacts. Additional trusted sources still need allowlist rows and review.

Vision:

- Gemini Vision works for cautious screening but is not benchmarked against
  public datasets or real phone-photo cases.
- No custom disease model is production-ready.

Operations:

- `/version` exists locally and should be verified after the next HF deploy.
- Full local Chroma rebuild over the 19-file Markdown corpus was attempted on
  2026-07-03. Loading and hashing succeeded, but CPU embedding did not complete
  in the local time window. The hosted Space should rebuild through the manifest
  guard during warm-up and must be checked with `/healthz`.
- Structured JSON logs exist; no dashboard or log aggregation exists yet.
- Docker build workflow exists; review first GitHub-hosted run for dependency
  install duration and container startup time.
- Nightly/manual HF smoke workflow exists, but the first successful remote
  artifact should be reviewed after GitHub Actions runs it from GitHub-hosted
  networking.
- SQLite case-log persistence exists for feedback; no full user/case database yet.

## Recommended Evaluation Tasks For Another Model

Evaluate in this order:

1. Check whether the app refuses unsupported or non-agricultural questions.
2. Test whether exact fertilizer doses come only from `core/fertilizer.py`, not
   from the LLM.
3. Test RAG citation quality on:
   - compost / soil fertility
   - niébé storage and bruches
   - sorghum or millet planting
   - off-topic prompts
4. Review whether source cards are relevant and whether noisy citations appear.
5. Test leaf photo screening with:
   - a clear leaf photo
   - a blurry photo
   - a non-plant image
6. Test weather and soil tools for each supported Burkina Faso location.
7. Test voice input manually in a browser.
8. Review whether all user-facing strings remain in French.
9. Check whether expensive or risky advice always includes confirmation language.
10. Propose the smallest next changes that improve field usefulness, not just UI
    polish.

## Suggested Next Engineering Work

Highest-impact next tasks:

1. [x] Add a text-question context flow for crop, location, and growth stage.
2. [x] Add follow-up outcome feedback for advice.
3. [x] Verify hosted RAG warm-up (2026-07-10 live eval 8/8 + citation ranking tune).
4. [x] Privacy-safe ops metrics at `/ops/metrics`.
5. [x] Vision eval helpers + Colab real-photo path.
6. [x] Expand Firecrawl allowlist (ministry, INERA, WASCAL, AGRHYMET, CILSS).
7. Continue scraping/promoting new allowlisted pages only after human review.

## Evaluation Principle

Treat DakiKobo as a cautious field triage assistant, not as a generic chatbot.
The best next work should make it more source-grounded, more field-aware, easier
to audit, and less likely to produce unsupported agricultural advice.
