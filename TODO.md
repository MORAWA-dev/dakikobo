# DakiKobo TODO - from working demo to standout field tool

This roadmap starts from the current live Hugging Face demo and focuses on
building something useful, credible, and hard to dismiss: a Burkina Faso field
advisor that combines local documents, crop stage, photos, weather, soil, and
traceable sources.

## Current status - already working

- [x] Public Hugging Face Space is live: `https://kimcomehome-dakikobo.hf.space/`
- [x] Flask app with French chat UI.
- [x] RAG over local agricultural PDFs in `Data/`.
- [x] Source citations rendered under answers.
- [x] Off-topic fallback instead of confident hallucination.
- [x] Persistent Chroma vector store locally, with lazy initialization for hosted startup.
- [x] Groq chat model wired through LangChain.
- [x] Multilingual MiniLM embeddings for French retrieval.
- [x] Deterministic fertilizer tool for mil, sorgho, mais, niebe, arachide.
- [x] Fertilizer answers include confirmation disclaimer.
- [x] Gemini Vision photo screening endpoint and camera upload UI.
- [x] Disease/photo answers include non-diagnosis disclaimer.
- [x] Text-to-speech output and browser speech input.
- [x] Feedback capture route and UI buttons.
- [x] Mobile-first UI is usable on phones.
- [x] Weather and soil tools are tucked behind an `Outils` drawer so chat remains the first-screen focus.
- [x] The demo UI uses the neutral DakiKobo logo avatar, compact wrapped examples, and clearer action controls.
- [x] TTS has one global auto-play toggle plus per-answer `Réécouter` buttons when audio is available.
- [x] A `Sources & limites` panel explains evidence, deterministic tools, and required field confirmation.
- [x] Hugging Face starts a background RAG warm-up so the first real question is not the warm-up trigger.
- [x] Docker/Hugging Face deployment files exist.
- [x] Route tests and offline tests are passing.

## Current gaps

- [ ] The UI is still mostly a chat widget; it should feel like a real field workflow.
- [ ] Image diagnosis answers are useful but not structured enough for inspection.
- [ ] The app does not yet ask for crop, growth stage, location, or recent weather.
- [ ] RAG citations show filenames, but not confidence, snippets, or "why this source".
- [ ] Feedback is stored as CSV, not a reusable case/evaluation dataset.
- [ ] No observability dashboard for failures, quotas, slow responses, or bad answers.
- [ ] No scheduled knowledge refresh from trusted web sources.
- [ ] No benchmark suite for vision/photo diagnosis quality.
- [ ] No weather, soil, or rainfall-onset intelligence.
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

- [x] Add confidence labels in French:
  - `Fort` when deterministic/tool or multiple good RAG sources agree
  - `Moyen` when one source or vision-only screening
  - `Faible` when context is missing or sources are weak

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

- [ ] Add `scripts/crawl_sources.py` that uses `FIRECRAWL_API_KEY`.
- [ ] Do not scrape at user request time. Scrape offline, review, then ingest.
- [ ] Maintain an allowlist of trusted sources:
  - Burkina Faso agriculture ministry pages
  - FAO Burkina Faso pages
  - WASCAL / AGRHYMET / CILSS climate-agriculture resources
  - INERA / extension manuals where accessible
- [ ] Store crawled output as markdown under `Data/web/`.
- [ ] Add metadata: URL, title, publisher, date crawled, language, license/usage note.
- [ ] Add a review flag before documents enter RAG.

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

- [ ] Convert `data/feedback.csv` into a case log.
- [ ] Add "Avez-vous applique ce conseil ?" follow-up question.
- [ ] Add "Result after 3-7 days" feedback:
  - improved
  - unchanged
  - worse
  - not sure
- [ ] Store before/after image references where possible.
- [ ] Use this as an evaluation dataset, not as public training data without consent.

### 6. Evidence-first answer format

- [ ] Make every sensitive answer use this structure:
  - short answer
  - why / evidence
  - what to do now
  - what not to do
  - confirm with agent
  - sources
- [ ] Add "Je ne peux pas confirmer" as a first-class response, not a failure.
- [ ] Stop the model from inventing pesticides, exact doses, or dates.

### 7. Local language path, carefully

- [ ] Do not rush local-language generation.
- [ ] Start with a glossary:
  - crop names
  - symptoms
  - fertilizer terms
  - weather terms
- [ ] Add "French simple" mode first.
- [ ] Later test Mooré / Dioula / Fulfulde snippets with human review.

### 8. Public demo polish

- [ ] Add a landing strip above the chat:
  - what DakiKobo does
  - supported crops
  - safety disclaimer
  - "Essayez ces exemples"
- [ ] Add a public limitations page.
- [ ] Add a short Hugging Face Space README story with screenshots.
- [ ] Add a 60-second demo script:
  - text question
  - fertilizer question
  - leaf image screening
  - source citation
  - disclaimer

## Colab credit burn plan

Use the Colab Pro credits for experiments that produce reusable artifacts:

- [ ] Notebook 1: build a disease-photo evaluation set and metrics.
- [ ] Notebook 2: benchmark Gemini prompt variants against public datasets and real phone photos.
- [ ] Notebook 3: test SCOLD/foundation image embeddings for retrieval and few-shot classification.
- [ ] Notebook 4: train a small baseline classifier only as a research comparison.
- [ ] Notebook 5: export a lightweight model only if it is clearly useful.

Do not spend credits training a model just to say "we trained a model". Spend them
to prove what works, what fails, and why.

## Data governance

- [ ] Add a `DATA_SOURCES.md` file with source, license, URL, date added, review status.
- [ ] Add document-level metadata during ingestion.
- [ ] Keep scraped documents separate from manually reviewed PDFs.
- [ ] Remove or quarantine any source with unclear rights.
- [ ] Add a privacy note for uploaded images.
- [ ] Never commit API keys, `.env`, generated audio, feedback logs, or user photos.

## Engineering hardening

- [ ] Add `/version` route with app version and Git commit.
- [ ] Add structured logging for `/ask`, `/screen`, errors, latency.
- [x] Harden TTS fallback/timeouts so slow gTTS cannot block an answer.
- [ ] Add timeout handling around Groq, Gemini, TTS, weather, Firecrawl.
- [ ] Add simple request size limits.
- [ ] Add SQLite for local/dev case logs.
- [ ] Add Docker build test in CI if the repo moves to GitHub Actions.
- [ ] Add a nightly smoke test against the Hugging Face Space.

## Priority order

1. Structured case cards for image and text answers.
2. Weather context card.
3. Better source/citation cards.
4. Firecrawl ingestion script with review workflow.
5. Case log and follow-up feedback.
6. Colab evaluation notebooks for vision.
7. Soil context.
8. Public demo story and example gallery.

## Definition of "incredible"

DakiKobo is incredible when a tester can say:

- "It asked the right follow-up question."
- "It used my photo, crop, location, and weather."
- "It told me what it knows and what it cannot confirm."
- "It gave practical next actions, not generic AI text."
- "It showed where the advice came from."
- "It felt like a careful field assistant, not a fake LinkedIn chatbot."
