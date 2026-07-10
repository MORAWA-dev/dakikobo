# DakiKobo TODO - from working demo to standout field tool

This roadmap starts from the current live Hugging Face demo and focuses on
building something useful, credible, and hard to dismiss: a Burkina Faso field
advisor that combines local documents, crop stage, photos, weather, soil, and
traceable sources.

## Current status - already working

- [x] Public Hugging Face Space is live: `https://kimcomehome-dakikobo.hf.space/`
- [x] Flask app with French chat UI.
- [x] RAG over reviewed local Markdown in `Data/markdown/`, with original PDFs kept as fallback/source files.
- [x] Chroma startup validation rebuilds the vector store when the persisted collection is missing or empty.
- [x] Source citations rendered under answers.
- [x] Off-topic fallback instead of confident hallucination.
- [x] Persistent Chroma vector store locally, with lazy initialization for hosted startup.
- [x] Groq chat model wired through LangChain.
- [x] Multilingual MiniLM embeddings for French retrieval.
- [x] Deterministic fertilizer tool for mil, sorgho, mais, niebe, arachide.
- [x] Fertilizer answers include confirmation disclaimer.
- [x] Gemini Vision photo screening endpoint and camera upload UI.
- [x] Disease/photo answers include non-diagnosis disclaimer.
- [x] Text-to-speech output and server-side Groq Whisper voice input, with browser fallback.
- [x] Feedback capture route and UI buttons.
- [x] Mobile-first UI is usable on phones.
- [x] Weather and soil tools are tucked behind an `Outils` drawer so chat remains the first-screen focus.
- [x] The demo UI uses the neutral DakiKobo logo avatar, compact wrapped examples, and clearer action controls.
- [x] TTS has one global auto-play toggle plus per-answer `Réécouter` buttons when audio is available.
- [x] A `Sources & limites` panel explains evidence, deterministic tools, and required field confirmation.
- [x] Source cards now expose publisher, year, country, review status, and clickable URL when reviewed metadata exists.
- [x] A visible privacy note explains that photos/audio are used for analysis and should not include personal identifiers.
- [x] Hugging Face starts a background RAG warm-up so the first real question is not the warm-up trigger.
- [x] Markdown corpus audit completed: 16/16 converted documents now match PDF text volume closely enough for RAG review.
- [x] Docker/Hugging Face deployment files exist.
- [x] Route tests and offline tests are passing.
- [x] Repeatable public demo evaluation script writes `reports/rag_eval_results.md`.

## Current gaps

- [x] Field workflow UX: context first (open by default), numbered steps, tools sync from location.
- [x] Image diagnosis answers use structured case cards (inspection sections).
- [x] Optional field context (crop, growth stage, location) for text questions and photos.
- [x] RAG citations: relevance filtering + weak-source demotion; live suite mostly green (soil external flaky).
- [x] Feedback is stored in a SQLite case log instead of a CSV-only file.
- [x] Privacy-safe ops metrics ring + `/ops/metrics` snapshot (latency, failures, recent routes).
- [x] Offline trusted-source refresh script (`scripts/refresh_trusted_sources.py`; cron-ready, never auto-promotes).
- [x] Vision evaluation helpers + Colab notebook path for real phone-photo runs.
- [x] Weather and soil tools exist; field-context location can auto-enrich answers with weather signals.
- [x] Markdown is now the primary RAG source, with PDF fallback if Markdown is missing or disabled.
- [x] Clear public demo story: sample cases, citations, confidence, and a compact sources/limits panel.

## Product direction

Build DakiKobo around a "field case" instead of a generic chat:

1. Farmer sends text, voice, or photo.
2. App asks for missing context: crop, commune/location, growth stage, planting date.
3. App creates a case card with observations, possible causes, risk level, next actions,
   sources, and what still needs human confirmation.
4. App can enrich the case with weather, soil, and local agronomy documents.
5. App logs anonymized cases for evaluation and improvement.

The goal is not "an AI chatbot for agriculture". The goal is "a cautious field
triage assistant that explains its evidence".

## Next sprint - highest impact

- [x] Create a `core/case.py` module with a case schema:
  - `case_id`, `created_at`, `input_type`, `crop`, `growth_stage`, `location`,
    `question`, `image_present`, `answer`, `sources`, `risk_level`, `needs_human`.
  - Keep it JSON-serializable so it can later move to SQLite/Postgres.

- [x] Replace raw disease text with a structured disease card:
  - `observations`
  - `problemes_possibles`
  - `actions_immediates`
  - `niveau_de_confiance`
  - `a_confirmer_par`
  - mandatory disclaimer

- [x] Add a lightweight context form after image upload:
  - crop selector: mil, sorgho, mais, niebe, arachide, autre
  - growth stage selector
  - optional commune/GPS text input
  - "Je ne sais pas" option for farmers

- [x] Improve source display:
  - show document title, short snippet, and source type
  - show "Base locale", "Outil engrais", "Vision", "Météo", "Sol"
  - keep filenames available but not as the only citation
  - show publisher, year, country, review status, and safe clickable URLs when metadata exists

- [x] Add confidence labels in French:
  - `Fort` when deterministic/tool or multiple good RAG sources agree
  - `Moyen` when one source or vision-only screening
  - `Faible` when context is missing or sources are weak

- [x] Add relevance-score citation filtering:
  - confidence now uses retrieval score when available
  - weak secondary citations are dropped when far below the best match
  - source cards now require crop/topic overlap when the query contains those concepts
  - RAG source cards are capped by `MAX_RAG_SOURCES`
  - kept citations are ordered by relevance score
  - zero-document retrieval forces the grounded fallback instead of an uncited answer

- [x] Add rate-limit and abuse protection:
  - per-session request cooldown
  - max uploaded image size
  - clear French error messages

- [x] Add a public "Examples" panel:
  - 3 text questions
  - 1 fertilizer case
  - 1 image diagnosis case
  - each example should be safe to run without exhausting API quotas

## Standout features to build

### 1. Weather-aware advice

- [x] Add `core/weather.py`.
- [x] Use Open-Meteo or NASA POWER for location-based rainfall, temperature,
  evapotranspiration, and soil moisture signals.
- [x] Start with simple insights:
  - "Pluie utile dans les 7 derniers jours"
  - "Risque de stress hydrique"
  - "Fenetre de semis probable"
  - "Eviter l'apport d'uree avant une forte pluie"
- [x] Cache weather responses by location/date to protect the free Space.
- [x] Display weather as a small context card, not a long paragraph.

Candidate sources:
- NASA POWER API: https://power.larc.nasa.gov/docs/services/api/
- Open-Meteo historical/forecast APIs: https://open-meteo.com/en/docs

### 2. Soil-aware fertilizer guidance

- [x] Add optional soil context using SoilGrids.
- [x] Start with explanatory soil indicators, not false precision:
  - texture / clay-sand tendency
  - organic carbon class
  - pH class
  - likely nutrient-retention risk
- [x] Combine soil context with deterministic fertilizer recommendations.
- [x] Always say soil-test/local agent confirmation is required.

Candidate source:
- SoilGrids REST API: https://rest.isric.org/soilgrids/v2.0/docs

### 3. Firecrawl knowledge ingestion pipeline

- [x] Add a Deep Research / iAskPro prompt for strict RAG-ready Markdown data curation.
- [x] Add a source-first research prompt so models must verify title, publisher, year, country, and URL before generating RAG Markdown.
- [x] Archive rejected deep-research outputs and keep a verification audit.
- [x] Add `scripts/firecrawl_ingest.py` that uses `FIRECRAWL_API_KEY`.
- [x] Do not scrape at user request time. Scrape offline, review, then ingest.
- [x] Maintain an allowlist of trusted sources:
  - [x] Burkina Faso agriculture ministry pages (allowlisted; scrape still offline/reviewed)
  - [x] FAO Burkina Faso pages
  - [x] WASCAL / AGRHYMET / CILSS climate-agriculture resources (allowlisted)
  - [x] INERA patterns allowlisted (public pages only; promote after human review)
- [x] Scrape the first FAO Burkina Faso seed batch into local pending review files.
- [x] Store crawled output as pending Markdown under `Data/scraped/pending/`.
- [x] Promote a curated FAO Burkina policy/data synthesis from the first seed batch into active Markdown.
- [x] Add metadata: URL, title, publisher, date crawled, language, license/usage note.
- [x] Add a review flag before documents enter RAG.
- [x] Add source-manifest validation so Chroma rebuilds when the active corpus changes.
- [x] Verify hosted RAG warm-up after recent deploys (status ready/warming checked live).
- [x] Curated MAERAH/OAPH orientation promoted to `Data/markdown/scraped_reviewed/` (not raw homepage).
- [x] CILSS curated orientation added to active Markdown (regional, not field doses).
- [x] Trusted URL health probe script (`scripts/check_trusted_sources.py`) for pre-scrape reachability.
- [ ] WASCAL / INERA still unreachable (timeout) — retry when online; failures under `Data/scraped/rejected/`.
- [ ] AGRHYMET still down — retry when online; never promote error pages.
- [x] Source verification of MAERAH/CILSS synthesis (OAPH expansion, filières, license notes, audit file) — owner sign-off still open.
- [ ] Final **owner** validation of MAERAH/CILSS before marketing-wide claims.
- [x] Feedback evaluation CSV/JSONL export script (`scripts/export_feedback_eval.py`).
- [x] Feedback export can feed smoke re-asks via `evaluate_rag.py --feedback-csv` (private only).
- [ ] Keep generated research packs in `Data/research_pack/` until human review approves them for RAG.

Firecrawl docs:
- https://docs.firecrawl.dev/introduction

### 4. Vision diagnosis lab

- [ ] Keep Gemini Vision in production for now because it works and gives cautious text.
- [ ] Use Colab credits for evaluation, not hype training.
- [ ] Build a notebook that compares:
  - Gemini Vision prompt variants
  - SCOLD / LeafNet-style image-text retrieval
  - simple ViT/ConvNeXt classifier baselines
  - optional YOLO-style lesion detector if labelled data is available
- [ ] Evaluate on:
  - clean public datasets
  - real phone photos collected manually
  - "not a plant" and blurry-photo negatives
- [ ] Never ship a custom diagnosis model until it beats Gemini on real phone photos.

Candidate resources:
- SCOLD model: https://huggingface.co/enalis/scold
- PlantVillageVQA dataset: https://huggingface.co/datasets/SyedNazmusSakib/PlantVillageVQA
- PlantDoc paper/dataset direction: https://arxiv.org/abs/1911.10317

### 5. Field journal and follow-up

- [x] Convert `data/feedback.csv` into a SQLite case log.
- [x] Add "Avez-vous appliqué ce conseil ?" follow-up question.
- [x] Add "Result after 3-7 days" feedback:
  - improved
  - unchanged
  - worse
  - not sure
- [x] Store before/after image references where possible (SQLite refs + optional after photo on follow-up).
- [x] Use this as a private evaluation dataset (export + smoke re-ask; not public training without consent).

### 6. Evidence-first answer format

- [x] Make every sensitive answer use this structure:
  - short answer
  - why / evidence
  - what to do now
  - what not to do
  - confirm with agent
  - sources
- [x] Text and fertilizer `/ask` answers now return a structured field `case` card
  (image screening already did). Refusals stay plain text without fake evidence.
- [x] Prompt safety: never invent exact fertilizer doses, pesticides, or precise dates.
- [x] Add "Je ne peux pas confirmer" as a first-class response, not a failure.
- [x] Further live tuning of evidence heuristics on real HF queries
  (FEWS demotion, practice-query penalty, IITA rotation + ProSol humidite sections).

### 7. Local language path, carefully

- [ ] Do not rush local-language generation.
- [x] Start with a glossary:
  - crop names
  - symptoms
  - fertilizer terms
  - weather terms
  - institutions (OAPH, MAERAH)
- [x] Add "French simple" mode first (`core/simple_french.py` + UI toggle).
- [ ] Later test Mooré / Dioula / Fulfulde snippets with human review.

### 8. Public demo polish

- [x] Add a landing strip above the chat:
  - what DakiKobo does
  - supported crops
  - safety disclaimer
  - "Essayez ces exemples"
- [x] Document known limits in the Sources panel (`Limites connues`) and `DEMO_SCRIPT.md`.
- [x] Add a short Hugging Face Space README demo story (screenshots optional later).
- [x] Add a 60-second demo script (`DEMO_SCRIPT.md`):
  - text question
  - fertilizer question
  - leaf image screening
  - source citation
  - disclaimer

## Colab credit burn plan

Use the Colab Pro credits for experiments that produce reusable artifacts:

- [x] Notebook 1: build a disease-photo evaluation set and metrics (`notebooks/01_disease_photo_eval.ipynb`).
- [x] Notebook 2 scaffold: Gemini prompt variants + optional live REST call for phone photos (helpers in `scripts/vision_eval_helpers.py`).
- [x] Notebook 3 scaffold: SCOLD helpers + Colab `embed_image` wiring in `03_scold_retrieval_eval.ipynb` (run real weights in Colab; Gemini stays production).
- [ ] Notebook 4: train a small baseline classifier only as a research comparison.
- [ ] Notebook 5: export a lightweight model only if it is clearly useful.

Do not spend credits training a model just to say "we trained a model". Spend them
to prove what works, what fails, and why.

## Data governance

- [x] Add a `DATA_SOURCES.md` file with source, license, URL, date added, review status.
- [ ] Add document-level metadata during ingestion.
- [x] Regenerate `Data/markdown/New Folder With Items/Caractéristiques des ménages agricoles au Burkina Faso_0.md` from its PDF; current file has 128 page sections and about 216k extracted characters.
- [x] Add Markdown-first RAG ingestion with PDF fallback once the converted corpus is complete and reviewed.
- [x] Extract ProSol 2020 into a curated Markdown source for Burkina Faso soil fertility, compost, organic manure, and CES preparation.
- [x] Extract IITA 2018 into a curated regional Markdown source for niébé agronomy, symptoms, and storage, excluding chemical product tables.
- [ ] Keep scraped documents separate from manually reviewed PDFs.
- [x] Keep Firecrawl scraped candidates outside active RAG until promotion.
- [ ] Remove or quarantine any source with unclear rights.
- [x] Add a privacy note for uploaded images and voice recordings.
- [ ] Never commit API keys, `.env`, generated audio, feedback logs, or user photos.

## Engineering hardening

- [x] Add `/version` route with app version, host commit if available, and runtime config flags.
- [x] Add privacy-safe structured JSON logging for route, status, latency, model/feature, confidence, source count, upload size, and failure type.
- [x] Add `scripts/evaluate_rag.py` for public Space RAG/tool/safety smoke reports.
- [x] Harden TTS fallback/timeouts so slow gTTS cannot block an answer.
- [x] Add timeout/retry handling around Groq chat, Groq STT, Gemini, TTS, weather, soil, and web fetches.
- [x] Add Firecrawl ingestion script with timeout/retry handling and review workflow.
- [x] Add simple request size limits (image/audio upload caps + `MAX_QUESTION_CHARS` for text).
- [x] Add SQLite for local/dev case logs.
- [x] Add Docker build test in CI.
- [x] Add a nightly/manual smoke test against the Hugging Face Space.

## Priority order

1. [x] Structured case cards for image and text answers.
2. [x] Weather context card.
3. [x] Follow-up feedback after advice.
4. [x] Colab evaluation notebooks for vision (scaffold in `notebooks/`).
5. [x] Soil context.
6. [x] Public demo story and example gallery (landing strip + examples panel).
7. [x] Text-question field context flow (crop / stade / lieu).

## Definition of "incredible"

DakiKobo is incredible when a tester can say:

- "It asked the right follow-up question."
- "It used my photo, crop, location, and weather."
- "It told me what it knows and what it cannot confirm."
- "It gave practical next actions, not generic AI text."
- "It showed where the advice came from."
- "It felt like a careful field assistant, not a fake LinkedIn chatbot."
