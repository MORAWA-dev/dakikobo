# DakiKobo Project State

Last updated: 2026-06-27

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
- Latest HF runtime commit verified: `abef3a32`
- Live health verified on 2026-06-27:
  - `ok=true`
  - `rag_ready=true`
  - `rag_status=ready`
  - warm-up finished at `2026-06-27T12:30:41+00:00`

Local git note:

- Local `main` latest commit: `18a5dac2`
- HF `main` latest commit: `abef3a32`
- These represent the same latest feature set, but HF has a separate history, so
  deploys are applied through a temporary HF worktree and cherry-pick.
- Local `main` is ahead of `origin/main`; GitHub may not have the newest local/HF
  work unless pushed separately.

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
- Model: Groq `llama-3.3-70b-versatile`
- Embeddings: `paraphrase-multilingual-MiniLM-L12-v2`
- Vector store: ChromaDB in `chroma_db/` locally or rebuilt on HF

Behavior:

- Answers in French.
- Shows source cards below answers.
- Shows confidence labels: `Fort`, `Moyen`, `Faible`.
- Uses off-topic fallback rather than inventing unsupported advice.
- Generates French TTS audio when possible.

### 2. RAG Knowledge Base

Active source path:

- `Data/markdown/`

Current active Markdown file count:

- 18 Markdown files

Important curated additions:

- `Data/markdown/prosol_fertilite_sols_burkina_2020.md`
- `Data/markdown/iita_niebe_afrique_ouest_2018.md`

Source governance:

- `DATA_SOURCES.md` tracks source status, URL, scope, review notes, and rejected
  or comparative sources.
- Markdown is preferred over PDFs because it is lighter and cleaner for hosted
  startup.
- PDFs remain under `Data/` as source material and fallback.
- `Data/_archive/rejected_deep_research_2026-06-27/` contains rejected generated
  research outputs and is intentionally not part of active RAG.

Retrieval status:

- Source cards are now filtered and ranked with retrieval relevance scores when
  the Chroma store is available.
- Weak secondary citations are dropped when they score far below the best match.
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
| `/feedback` | POST | Answer rating capture |

## Key Files For Review

Application:

- `app.py`
- `config.py`
- `requirements.txt`

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
- `tests/test_disease.py`
- `tests/test_fertilizer.py`
- `tests/test_frontend_assets.py`
- `tests/test_ingestion.py`
- `tests/test_rag.py`
- `tests/test_router.py`
- `tests/test_soil.py`
- `tests/test_tts.py`
- `tests/test_weather.py`

## Verification Status

Latest local full test run:

- `73 passed`
- 2 warnings:
  - PyPDF2 deprecation warning
  - LangChain/Groq Pydantic `dict` deprecation warning

Latest HF worktree test run:

- `71 passed`
- `2 skipped`
- 1 PyPDF2 deprecation warning

Latest live HF checks:

- `/healthz`: ready
- `/version`: available locally after 2026-06-30 changes; deploy to HF before
  expecting it on the public Space.
- `/ask` compost question: returned ProSol source
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
- `STT_TIMEOUT_SECONDS`
- `MAX_AUDIO_UPLOAD_MB`
- `GEMINI_MODEL`
- `PREFER_MARKDOWN_KB`
- `REBUILD_VECTORSTORE`
- `RAG_WARMUP_ON_START`
- `VECTORSTORE_DIR`
- `REQUEST_COOLDOWN_SECONDS`
- `VOICE_COOLDOWN_SECONDS`
- `IMAGE_COOLDOWN_SECONDS`
- `MAX_IMAGE_UPLOAD_MB`

Do not commit:

- `.env`
- `chroma_db/`
- `static/audio/*.mp3`
- `data/feedback.csv`
- user photos or recordings
- API keys

## Known Gaps

Product:

- The app still feels partly like a chat widget instead of a full field workflow.
- Text questions do not yet always collect crop, commune, growth stage, or date.
- Feedback is stored as CSV, not a reusable case/evaluation database.
- There is no user-facing privacy note for uploaded photos/audio yet.

RAG and data:

- Document-level metadata should be added during ingestion.
- Retrieval source filtering exists, but needs more live evaluation and tuning.
- Generated/scraped data should remain outside RAG until human review.
- Firecrawl pipeline is planned but not implemented.

Vision:

- Gemini Vision works for cautious screening but is not benchmarked against
  public datasets or real phone-photo cases.
- No custom disease model is production-ready.

Operations:

- `/version` exists locally and should be verified after the next HF deploy.
- No structured logging dashboard yet.
- No nightly HF smoke test yet.
- No persistent database yet.

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

1. Add structured JSON logs for route, latency, status, model, and failure type.
2. Add document-level metadata to ingestion and source cards.
3. Add a privacy note for uploaded photos/audio.
4. Convert `data/feedback.csv` into a small SQLite case log.
5. Add a text-question context flow for crop, location, and growth stage.
6. Add Firecrawl offline ingestion script with allowlist and review gate.
7. Continue live retrieval evaluation and tune citation thresholds if needed.

## Evaluation Principle

Treat DakiKobo as a cautious field triage assistant, not as a generic chatbot.
The best next work should make it more source-grounded, more field-aware, easier
to audit, and less likely to produce unsupported agricultural advice.
