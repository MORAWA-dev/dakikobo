# DakiKobo session log

**Purpose:** Persist decisions and progress across chat resets.  
**Do not** treat chat history as the source of truth for long work.

## How to continue after a context reset

```text
@SESSION.md continue from the last decision and implement the next item
```

Or point at a specific date block:

```text
@SESSION.md implement the first open item under "Next up"
```

After every major step (or end of a 60–90 min session), **append** a new dated entry below (do not rewrite history). Keep bullets short.

---

## Project anchors (stable)

| Item           | Value                                                                                                                                            |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| App            | French field advisor for Burkina Faso (Flask + RAG)                                                                                              |
| Live Space     | https://kimcomehome-dakikobo.hf.space/                                                                                                           |
| HF Space repo  | https://huggingface.co/spaces/kimcomehome/dakikobo                                                                                               |
| GitHub         | `origin/main` (primary history)                                                                                                                  |
| HF deploy      | Separate history via worktree + rsync; commit message `Deploy GitHub main <sha> to Space`                                                        |
| Entry          | `app.py`                                                                                                                                         |
| Product rules  | French UI; no invented fertilizer doses; cautious/source-grounded; secrets in `.env` only                                                        |
| Offline tests  | `.venv/bin/pytest -q tests/test_disease.py tests/test_fertilizer.py tests/test_ingestion.py tests/test_router.py` (+ route/eval tests as needed) |
| Live smoke     | `.venv/bin/python scripts/evaluate_rag.py --strict --min-pass-rate 0.75`                                                                         |
| Longer roadmap | `TODO.md`, `PROJECT_STATE.md`, `Agents.md`                                                                                                       |

### HF deploy recipe (worktree; do not rsync-delete `.git` file)

```bash
SHA=$(git rev-parse --short HEAD)
WT=/tmp/dakikobo-hf-deploy-$$
git fetch hf
git worktree add "$WT" hf/main
rsync -a --delete \
  --exclude '.git' --exclude '.git/' \
  --exclude '.venv/' --exclude 'chroma_db/' --exclude '.env' \
  --exclude '__pycache__/' --exclude '.pytest_cache/' \
  --exclude 'static/audio/' --exclude 'data/feedback.csv' \
  --exclude 'data/case_log.sqlite*' \
  ./ "$WT"/
cd "$WT" && git add -A && git commit -m "Deploy GitHub main ${SHA} to Space" && git push hf HEAD:main
cd - && git worktree remove "$WT" --force
```

---

## Next up (ordered)

1. **You (async):** collect data using `Data/reviews/DATA_COLLECTION_TASKS.md` (tracks A climate, B photos, C crop names).
2. **When you say “ingest what I collected”:** agent reviews inbox → curated RAG / vision / glossary (no raw auto-promote).
3. **When climate hosts UP (agent):** health probe + refresh for WASCAL/INERA/AGRHYMET.
4. Optional: local agent review of French field phrasing.

---

## Session entries

### 2026-07-10 — Chat-first UI (uncrowd interface)

**Decided**

- User report: UI too crowded to chat / upload image flow blocked by panels.
- Default: **collapsed** field context + examples; compact landing (2 lines).
- Chat area gets min-height; examples open as horizontal scroll strip.
- Emoji keyboard in screenshot is OS/browser (not app) — not fixed in code.

**Files changed**

- `templates/index.html`, `static/css/style.css`, `static/js/index.js`, tests

**Git / deploy**

- GitHub: `c09c843a`
- HF: `10dd1f2c`

---

### 2026-07-10 — Persist field context + examples scroll

**Decided**

- Continue code-only while owner collects A/B/C data later.
- Persist parcelle context + Français simple in `localStorage` (device only, no server PII).
- Crop select uses `fr_simple` labels when Français simple is on.
- Examples panel scrolls when many cards; heading notes quota-safe demos.

**Files changed**

- `static/js/index.js`, `static/css/style.css`, `templates/index.html`
- `tests/test_frontend_assets.py`, `SESSION.md`

**Git / deploy**

- GitHub: `dc73b453`
- HF: deploy after push

---

### 2026-07-10 — Code-only demo polish (CILSS + honest refusal)

**Decided**

- User gathers A/B/C data later via DATA_COLLECTION_TASKS; agent continues **code-only**.
- Add quota-safe demos: **CILSS** (regional, no field rain) and **Hors sujet** (honest refusal, no fake case card).
- README points to collection tasks + SESSION.

**Files changed**

- `core/examples.py`, `templates/index.html`, `DEMO_SCRIPT.md`, `README.md`
- tests, `SESSION.md`

**Git / deploy**

- GitHub: `d4132257`
- HF: deploy after push

**Next action**

- More code polish, or wait for owner data / climate UP.

---

### 2026-07-10 — Data collection task list for owner

**Decided**

- User will gather climate docs, leaf photos, and local crop names later (online + people).
- All “inputs needed” are organized in `Data/reviews/DATA_COLLECTION_TASKS.md` (tracks A/B/C, inbox paths, done criteria).
- Agent waits for “ingest what I collected” before processing; no invented local names or climate content.

**Files changed**

- `Data/reviews/DATA_COLLECTION_TASKS.md`
- `SESSION.md`

**Next action**

- Owner works through DATA_COLLECTION_TASKS at own pace; agent continues code-only if asked.

---

### 2026-07-10 — UP-only refresh + crop-labels API + vision eval kit

**Decided**

- Preflight refresh: 5/9 UP (MAERAH, CILSS, FAO×3); climate hosts still DOWN.
- Firecrawl refused overwrite of existing pending files — no new promote needed.
- Add `GET /crop-labels` for French crop UI labels (no local-language generation).
- Add `Data/vision_eval/` manifest template for Colab phone-photo runs.

**Files changed**

- `app.py`, `static/js/index.js`, tests
- `Data/vision_eval/*`, `.gitignore` samples
- `SESSION.md`, `notebooks/README.md`

**Git / deploy**

- GitHub: `98f3c4bd`
- HF: deploy after push

**Next action**

- Climate when UP, or real phone photos for vision, or local crop names.

---

### 2026-07-10 — Owner sign-off MAERAH/CILSS (morawa-dev)

**Decided**

- Owner **morawa-dev** authorized the agent to record sign-off on GitHub identity.
- MAERAH and CILSS curated docs: `review_status` → `reviewed_by_owner`.
- Budget/emploi figures: only as **official published targets**, never field promises.
- Crop local-language labels left open (not part of this sign-off).

**Files changed**

- `Data/reviews/OWNER_SIGNOFF.md`
- `Data/reviews/SOURCE_VERIFICATION_AUDIT_2026-07-10.md`
- `Data/markdown/scraped_reviewed/maerah_oaph_orientation_burkina_2026.md`
- `Data/markdown/scraped_reviewed/cilss_orientation_sahel_2026.md`
- `DATA_SOURCES.md`, `TODO.md`, `SESSION.md`, `core/examples.py` (demo card label)

**Git / deploy**

- GitHub: `af8a066b`
- HF: deploy after push

**Next action**

- Climate scrape when UP, or vision Colab, or crop glossary human fill.

---

### 2026-07-10 — Demo OAPH example + owner sign-off form + notebook 05

**Decided**

- Climate hosts still DOWN — no scrape this pass.
- Add quota-safe **OAPH** demo example (correct expansion, MAERAH source card).
- Align rotation demo answer with azote / IITA-style message.
- Provide **OWNER_SIGNOFF.md** for human checkboxes (not agent-signed).
- Notebook 05 = export criteria only (no model packaging).
- DEMO_SCRIPT covers français simple + OAPH.

**Files changed**

- `core/examples.py`, `templates/index.html`
- `DEMO_SCRIPT.md`
- `Data/reviews/OWNER_SIGNOFF.md`
- `notebooks/05_export_criteria.ipynb`, `notebooks/README.md`
- `SESSION.md`, `TODO.md`, tests

**Git / deploy**

- GitHub: `bc6ad426` + test fix
- HF Space: `087ffd0f`

**Next action**

- Human owner sign-off, or Colab vision, or climate scrape when UP.

---

### 2026-07-10 — Refresh preflight skip + notebook 04 + crop glossary data

**Decided**

- Owner sign-off still human-only.
- WASCAL/INERA/AGRHYMET still DOWN — no scrape.
- `refresh_trusted_sources.py` now **preflight-probes** and scrapes only UP URLs (unless `--skip-health-check`).
- Notebook 04 scaffold for baseline classifier research (no training hype).
- Crop label glossary JSON: French primary; local-language fields **empty** until native-speaker fill; not wired to LLM generation.

**Files changed**

- `scripts/refresh_trusted_sources.py`, `tests/test_refresh_trusted_sources.py`
- `notebooks/04_baseline_classifier.ipynb`, `notebooks/README.md`
- `Data/glossaries/crop_labels.json`, `Data/glossaries/README.md`, `core/crop_labels.py`, `tests/test_crop_labels.py`
- `Data/scraped/seed_urls_trusted_bf.txt` — comment bare agriculture.bf SSL issue
- `SESSION.md`, `TODO.md`

**Git / deploy**

- GitHub: `8e7982e2` (feature `fd2a1663`)
- HF Space: `5c1fcfef`

**Next action**

- Owner sign-off, or Colab vision runs, or fill crop glossary with humans.

---

### 2026-07-10 — Trusted health probe + SCOLD Colab wiring

**Decided**

- Owner sign-off still human-only; skipped for agent work.
- WASCAL / INERA / AGRHYMET still **unreachable** (HTTP fail/timeout) — no scrape/promote.
- Pending ministry/FAO scrapes already covered by curated RAG (MAERAH/OAPH, CILSS, FAO profile); no new promote.
- Add lightweight **`scripts/check_trusted_sources.py`** for pre-refresh HTTP probes (cron-friendly, no Firecrawl key required).
- Notebook 03 gets a concrete Colab `embed_image` / HF AutoModel scaffold; production remains Gemini until eval wins.

**Files changed**

- `scripts/check_trusted_sources.py`, `tests/test_check_trusted_sources.py`
- `notebooks/03_scold_retrieval_eval.ipynb`, `notebooks/README.md`
- `.gitignore` — `reports/trusted_source_health.md`
- `SESSION.md`, `TODO.md` (if updated)

**Git / deploy**

- GitHub: `b6a48959` (feature `5662fdf8`)
- HF Space: `d1ec8c6c`

**Still open**

- Owner MAERAH/CILSS sign-off
- Climate/research sites when network allows
- Real SCOLD run on phone photos in Colab

**Next action**

- Owner sign-off, or re-probe trusted sources later, or phone-photo Colab experiment.

---

### 2026-07-10 — MAERAH/CILSS source verification (next-up #1)

**Decided**

- Agent **source verification** completed for MAERAH/OAPH and CILSS; **owner sign-off** remains required (not claimed as full human approval).
- OAPH facts locked: expansion confirmed on official page; 8 strategic value chains (riz, maïs, pomme de terre, blé, poisson, bétail-viande, volaille, mangue); adopted 30 Aug 2023 per page text.
- License stance: short orientation synthesis + URL citation only; institutions keep full page rights; no bulk republication.
- AGRHYMET / WASCAL / INERA still unreachable (timeout) — do not invent climate/INERA content.
- Audit lives under `Data/reviews/` (not under `Data/markdown/`) so it is **not** RAG-ingested.
- New review_status: `source_verified_pending_owner_signoff` (UI label in `app.py`).

**Files changed**

- `Data/markdown/scraped_reviewed/maerah_oaph_orientation_burkina_2026.md`
- `Data/markdown/scraped_reviewed/cilss_orientation_sahel_2026.md`
- `Data/reviews/SOURCE_VERIFICATION_AUDIT_2026-07-10.md`
- `Data/scraped/rejected/_unreachable_20260710_session.md`
- `app.py` — review status labels
- `DATA_SOURCES.md`, `TODO.md`, `SESSION.md`

**Git / deploy**

- GitHub: `9e169448` (verify commit stack `b36b6d6d` + session note)
- HF Space: `8d4ce3b9` (Deploy GitHub main 9e169448)

**Still open**

- Owner checkboxes on MAERAH/CILSS files
- WASCAL / INERA / AGRHYMET when online
- Vision SCOLD encoder; local languages later

**Next action for the following session**

- Implement next open item after owner sign-off, or retry unreachable climate/research sites, or optional pending→curated KB only if high field value.

---

### 2026-07-10 — Field citations, eval gate, French simple, session log

**Decided**

- OAPH = **Offensive Agropastorale et Halieutique 2023-2025** only (never invent “Office des Aménagements…”); source: curated MAERAH md.
- Scrapes stay **offline → pending → human review → promote**; never auto-ingest into RAG.
- **Français simple** is a UI toggle + glossary footnotes (`core/simple_french.py`), not full local-language generation.
- Feedback export is **private evaluation only** (consent); wire via `--feedback-csv` smoke re-asks.
- Trusted refresh is cron-ready (`scripts/refresh_trusted_sources.py`) and **never auto-promotes**.
- Citation policy: demote FEWS/livelihood-style titles on field-practice queries; prefer IITA/ProSol extension manuals; if only weak sources remain, keep one card at **Faible** (do **not** strip all sources—uncited LLM answers failed mil/maladie smoke).
- Retriever `k=6`, score lookup `k=10` to surface extension manuals.
- SoilGrids external 502: smoke allows HTTP 200/502/503; soft source-count when not 200.
- Live gate: hard checks structural; keywords/confidence **advisory**; `--min-pass-rate 0.75`.

**Files changed (major)**

- `core/simple_french.py`, `templates/index.html`, `static/js/index.js`, `static/css/style.css` — Français simple
- `Data/markdown/scraped_reviewed/maerah_oaph_orientation_burkina_2026.md`, `cilss_orientation_sahel_2026.md`
- `Data/markdown/iita_niebe_afrique_ouest_2018.md` — rotation niébé-céréales section
- `Data/markdown/prosol_fertilite_sols_burkina_2020.md` — humidité / CES section
- `app.py` — citation demotion, practice-query ranking, simple-french wiring
- `core/llm_chain.py` — retriever k=6
- `scripts/evaluate_rag.py` — OAPH, rotation, humidité, simple-french cases; soil 502 tolerance; `--feedback-csv`
- `scripts/export_feedback_eval.py`, `scripts/refresh_trusted_sources.py`
- `scripts/vision_eval_helpers.py`, `notebooks/03_scold_retrieval_eval.ipynb`
- `Data/scraped/rejected/*` — WASCAL/INERA tunnel, AGRHYMET 502, CILSS 404
- `README.md` — Space demo story; `TODO.md` / `PROJECT_STATE.md` updates

**Git / deploy (end of day)**

- GitHub `main`: `83144836` (and earlier stack through OAPH/CILSS/simple-french)
- HF Space verified: `ede2e40f` — live eval **14/14 hard-pass** when RAG ready
- Public checks: OAPH correct; rotation → IITA; humidité → ProSol; français simple engrais → “Mots simples”

**Still open**

- Human license/details review for MAERAH + CILSS synthesis
- WASCAL / INERA / AGRHYMET scrapes when Firecrawl/sites healthy
- SCOLD real encoder in Colab; notebooks 4–5 research only
- Mooré / Dioula / Fulfulde not started
- Optional screenshots for Space README

**Do not**

- Promote raw Firecrawl pending pages or error HTML
- Invent fertilizer doses or pesticide product lists in LLM path
- Commit `.env`, `chroma_db/`, `reports/feedback_eval.csv`, private feedback exports
- Rely only on chat history for the next session — update this file instead

---

### 2026-08-24 — Phase 1: the registry (core/places.py, core/crops.py)

**Decided**

- Executed Phase 1 of the locked spec in `plans/dakikobo_assessment_and_plan.md` — single source of truth for places (20) and crops (10).
- `core/places.py`: `Place` dataclass + `PLACES` dict + `resolve_place` / `list_places`; 6 weather-backed places with coords (ouagadougou, bobo, kaya, ouahigouya, fada, dori), 14 with `has_weather=False`.
- `core/crops.py`: `Crop` dataclass + `CROPS` dict + `resolve_crop` / `list_crops`; `fertilizer_supported=True` only for sorgho, mil, mais, niebe, arachide.
- Rewired consumers onto the registries: `weather.py`, `soil.py`, `query_context.py`, `fertilizer.py` (`_match_crop` via `resolve_crop` + guard), `crop_labels.py`.
- Frontend selects now populated from `GET /registry` with `place.id`/`crop.id` option values; deleted `FIELD_LOCATION_TO_WEATHER`/`FIELD_LOCATION_TO_SOIL`; `syncToolsFromFieldLocation` uses the selected id directly with `option[value=...]` existence guards.
- Sentinel options (`""`, `autre`, `__custom__`) preserved via `.detach()`/re-append; init deferred behind async `/registry` fetch with `.always(initFieldContext)`.
- Note: stored `location_select` values were display labels — after switching to ids they fail to restore and degrade safely to "field unset" via existing existence guard (no state corruption).

**Files changed**

- `core/places.py`, `core/crops.py` — new registries
- `core/weather.py`, `core/soil.py`, `core/query_context.py`, `core/fertilizer.py`, `core/crop_labels.py` — rewired onto registries
- `app.py` — `GET /registry` route
- `static/js/index.js` — `populateRegistrySelects`, direct-id sync, init reordering
- `tests/test_registry.py` — 15 new tests
- `tests/test_app_routes.py`, `tests/test_frontend_assets.py` — (updated where needed)

**Tests**

- Full offline suite: **226 passed** (excludes live-network `tests/test_rag.py`). Only pre-existing PyPDF2 deprecation warning.

**Still open**

- Phase 2 (extract retrieval & citation into `core/retrieval.py`) is the next phase in the locked spec.

**Next action for the following session**

- Implement Phase 2 of the locked spec, or run the live RAG smoke test when network is available.

---

### 2026-08-26 — Phase 2: retrieval and citation extraction

**Decided**

- Executed Phase 2 of the locked spec in `plans/dakikobo_assessment_and_plan.md`.
- Moved citation normalization, matching, metadata formatting, weak-source demotion, ranking, and confidence policy from Flask into the network-free `core/retrieval.py` seam.
- Added immutable `SourceCard` / `GroundedAnswer`, stable runtime chunk IDs, query-less score injection, source-card JSON compatibility, and best-effort count-based fallback when score grading fails.
- Rewired `/ask` to perform exactly one scored vector search (`k=6`), retain the configured similarity threshold, and pass the same accepted documents to the LLM combine chain and citation grading.
- The active corpus manifest hash is now set only after a persisted vector store is accepted or a rebuild succeeds, and is cleared before each load/build attempt to prevent stale cache identity.
- Preserved refusal, uncertainty, deterministic fertilizer, French response, and source metadata behavior. Docker/Gunicorn worker settings were intentionally unchanged for Hugging Face compatibility.

**Files changed**

- `core/retrieval.py` — extracted citation policy and Phase 2 public API.
- `app.py` — removed duplicate citation policy, activated manifest hashing, and replaced double retrieval with one scored search.
- `tests/test_retrieval.py` — offline policy coverage for chunk IDs, source metadata, noisy/weak source handling, FEWS demotion, count fallback, and manifest state.
- `tests/test_app_routes.py` — one-search orchestration, exact document handoff, source JSON, and manifest load/rebuild assertions.
- `config.py` — corrected citation-policy code reference.

**Tests**

- Retrieval policy: **10 passed**.
- Route + retrieval target: **74 passed**.
- Full offline suite: **234 passed** (excludes live-network `tests/test_rag.py`). Only the pre-existing PyPDF2 deprecation warning.
- Python compilation and `git diff --check`: passed.
- Public Space pre-deploy check: `/healthz` reports `ready`; `/version` reports `openai/gpt-oss-120b`, multilingual MiniLM embeddings, Markdown KB, startup warm-up enabled, and commit `5374ee13aa82e0cc4deb7ba117cc25756eb7c7a0`.

**Git / deploy**

- Phase 2 remains in the local working tree; no commit, push, or Hugging Face production deployment was performed automatically.
- Existing one-worker Gunicorn deployment contract remains unchanged. Deploy through the documented HF worktree flow after review, then rerun the strict public evaluation.

**Still open**

- Phase 3 (SQLite cache and concurrency migration) is next in the locked spec.
- Post-deploy verification must confirm the new Space commit, `rag_status=ready`, one-search behavior, and strict public RAG evaluation.

**Next action for the following session**

- Review and deploy Phase 2 to the Hugging Face Space, then run `scripts/evaluate_rag.py --strict --min-pass-rate 0.75` against the public URL.

---

### 2026-08-29 — Phase 0/1 audit repairs + Phase 2 deployment verification

**Decided**

- Audited the uncommitted Phase 0/1/2 work against the locked plan instead of trusting the earlier completion notes.
- Phase 0 still contained the live XSS typing path, five-argument photo case call, simple-French elision/footnote loss, stale docs, dead metrics privacy constant, redundant exception tuple, and unlocked readiness reads; all are now repaired.
- Phase 1 now converts registry ids to French labels before prompt/card construction, populates all five selects from `/registry`, preserves the existing accented `/crop-labels` contract, and returns the registry cache header required by §7.16.
- Phase 2 remains one scored top-six vector search per `/ask`; the same threshold-accepted documents ground generation and citation grading, while stable ids retain provenance for all retrieved candidates.
- Kept Docker/Gunicorn at one worker; the plan forbids raising concurrency before Phase 3 moves volatile state to SQLite.

**Files changed**

- `static/js/index.js`, `templates/index.html`, `core/simple_french.py`, `core/ops_metrics.py` — Phase 0 repairs and dynamic registry UI.
- `core/crops.py`, `core/places.py`, `core/query_context.py`, `core/crop_labels.py`, `core/fertilizer.py`, `core/weather.py`, `core/soil.py`, `app.py` — Phase 1 registry and id/label wiring.
- `core/retrieval.py`, `app.py`, `config.py` — Phase 2 extraction, manifest identity, and one-search orchestration.
- `tests/test_frontend_assets.py`, `tests/test_simple_french.py`, `tests/test_registry.py`, `tests/test_query_context.py`, `tests/test_retrieval.py`, `tests/test_app_routes.py` — regression and orchestration coverage.
- `README.md`, `IMPLEMENTATION_PLAN.md` — current modules, citation flow, and token default.

**Verification**

- Full offline suite excluding live RAG: **243 passed**, one existing PyPDF2 deprecation warning.
- Targeted Phase 0/1/2 suite: **139 passed**.
- Python compilation and Flask import: passed.
- Production Gunicorn smoke: booted with the Docker-compatible one-worker command; `/healthz` returned 200 and `/registry` returned 200 with 10 crops, 20 places, and `Cache-Control: public, max-age=3600`.
- Local live `tests/test_rag.py`: no test result; stopped after 142 s while `huggingface_hub` was waiting for model assets.
- Current public Space (before this work is pushed): `/healthz` is `ready`; `/version` is commit `5374ee13aa82e0cc4deb7ba117cc25756eb7c7a0`; `/registry` is 404, confirming Phase 1/2 are not deployed yet.

**Git / deploy**

- No commit or push performed. New imported modules are untracked, so deployment must include `core/crops.py`, `core/places.py`, and `core/retrieval.py`; do not use `git commit -am` alone.
- After pushing GitHub and the HF worktree, verify `/registry`, `/version`, `/healthz`, then run `scripts/evaluate_rag.py --strict --min-pass-rate 0.75`.

**Still open**

- The plan demands 20 places but the pre-registry alias table had only 17 unique labels; the existing Phase 1 draft fills the locked count with Réo, Boromo, and Yako. Obtain product-owner confirmation before changing that vocabulary.
- Phase 3 is next; do not change worker count before its SQLite cache/state migration.

---

### Template for the next session entry

```markdown
### YYYY-MM-DD — short title

**Decided**

- …

**Files changed**

- `path` — why

**Git / deploy**

- GitHub: `sha`
- HF: `sha` (eval result if run)

**Still open**

- …

**Next action for the following session**

- …
```

---

### 2026-08-30 — Phase 2 live deployment completed

**Decided**

- Kept the Phase 2 retrieval architecture and repaired the final public-evaluation regression by expanding the reviewed OAPH acronym only in the retrieval query.
- The expansion uses the verified MAERAH meaning, while the original farmer question remains unchanged for display and answer generation.

**Files changed**

- `core/query_context.py` — add the reviewed OAPH retrieval expansion.
- `tests/test_query_context.py` — protect the expansion with a regression test.

**Verification**

- Full offline suite: **244 passed**, with one existing PyPDF2 deprecation warning.
- Public `/version`: commit `2dd12b4866346a49d75a9075d05a390744961409`, `rag_status=ready`.
- Public `/registry`: 10 crops and 20 places.
- Strict public RAG evaluation: **14/14 hard-passed (100%)**; the OAPH case passed with HTTP 200, medium confidence, and one grounded source. Five advisory warnings remain non-blocking.

**Git / deploy**

- GitHub feature commit: `cfe791432b159d17e3cc832c9a21a9d339a33885`.
- Hugging Face Space deploy: `2dd12b4866346a49d75a9075d05a390744961409`.

**Still open**

- Phase 3 is next; keep the production worker count at one until the SQLite state migration is complete.

**Next action for the following session**

- Begin Phase 3 from `plans/dakikobo_assessment_and_plan.md` when requested.

---

### 2026-08-30 — Phase 3 cache and concurrency deployed

**Decided**

- Moved answer, weather, soil, and privacy-safe ops state to one WAL-enabled SQLite database with a 30-second busy timeout.
- Answer-cache keys include the normalized resolved retrieval query, canonical crop/place ids, growth stage, Français simple flag, LLM model, and active corpus-manifest hash.
- Cache hits bypass intent routing, Groq, retrieval, weather enrichment, and TTS while preserving the grounded answer, case, sources, confidence, and top-six chunk provenance.
- Raised production serving to two Gunicorn workers × four threads with a 90-second timeout only after shared-state tests passed.
- The first live two-worker deploy exposed a Chroma `collections_tmp` migration race. Added a kernel file lock around vector-store initialization so one worker builds and the other loads the completed store.
- Pruned unused direct dependencies and pinned NumPy 1.26.4, Torch 2.2.2, and Transformers 4.57.6.

**Files changed**

- `core/cache.py`, `core/answer_cache.py`, `core/ops_metrics.py` — shared SQLite cache/metrics boundary, stable answer keys, salted question hash, bounded cross-worker metrics, and Chroma startup lock.
- `core/weather.py`, `core/soil.py`, `core/case_log.py` — persistent TTL caches and once-per-process case-log initialization.
- `app.py`, `config.py`, `Dockerfile`, `Procfile` — `/ask` cache fast path, cache-hit metrics, environment defaults, and concurrent serving.
- `requirements.txt`, `.env.example`, `.gitignore`, `.dockerignore`, `README.md`, `DEPLOYMENT.md`, `IMPLEMENTATION_PLAN.md` — dependency, runtime-state, deployment, and operator documentation.
- `tests/test_cache.py`, `tests/test_answer_cache.py`, `tests/test_ops_metrics.py` and route/weather/soil tests — Phase 3 regression and concurrency coverage.

**Verification**

- Full offline suite excluding the separate live `tests/test_rag.py`: **261 passed**, one existing PyPDF2 deprecation warning.
- Two-worker local Gunicorn smoke: both gthread workers booted; 24 concurrent `/healthz` calls produced one shared ops snapshot with 24 events and coherent p50/p95 values.
- Public `/version`: deploy `40e92d546d651568edf9f0bb83bc3a409a691081`, answer cache enabled, RAG ready.
- Twelve alternating public `/healthz` samples reached both workers; both reported `ready` with no Chroma error and distinct successful warm-up completion timestamps.
- Live repeated OAPH request: first HTTP 200 in 2.49 s; subsequent HTTP 200 responses in 0.46 s. Ops recorded `rag/cache_hit=false` followed by two `cache/cache_hit=true` events with 1.52 ms and 4.01 ms server latency.
- Public weather and soil responses reported `cached=true`; ops metrics were shared and queryable.
- Strict public RAG evaluation: **14/14 hard-passed (100%)**, with two non-blocking advisory warnings.

**Git / deploy**

- GitHub Phase 3: `6348f69b` plus Chroma concurrency fix `b6d4d70b`.
- Hugging Face Space: `40e92d546d651568edf9f0bb83bc3a409a691081`.

**Still open**

- Phase 4 (field journal and evidence ledger) is next in the locked plan.
- Free-Space cold warm-up remains CPU-bound at roughly four minutes; once warm, two workers remain ready and repeat answers use the shared cache.

**Next action for the following session**

- Begin Phase 4 from `plans/dakikobo_assessment_and_plan.md` when requested.

---

### 2026-08-31 — Phase 4 field journal and evidence ledger implemented

**Decided**

- Migrated the field journal additively to schema v4 with canonical crop/place ids, the answer
  path (`rag`, `fertilizer`, `vision`, `cache`), and a seven-day follow-up deadline.
- Added a privacy-safe evidence ledger: every top-six chunk receives its exact score, kept/dropped
  decision, and `weak_title`, `low_overlap`, or `score_margin` reason under the existing salted
  question hash. Question and answer text never enter this ledger.
- `/ask` writes the evidence batch best-effort; `/feedback` links it atomically using the salted
  hash plus exact batch timestamp. Cache hits clone the original decision batch without another
  retrieval or Groq call.
- Added a privacy-minimized `GET /journal/due` digest, plus evidence decisions in private CSV/JSONL
  feedback exports.
- Extracted `core/case_contract.py` beneath the case builder and demo examples, moved demo case
  metadata into declarative profiles, and removed the late-import/per-id workaround from B9.

**Files changed**

- `core/case_log.py`, `core/retrieval.py`, `core/case_contract.py` — schema v4, journal/ledger APIs,
  exact retrieval decisions, cache-hit evidence cloning, and shared field-case contract.
- `app.py`, `static/js/index.js`, `config.py`, `.env.example` — two-step response/feedback linkage,
  answer-path and registry-id propagation, due route, schema visibility, and follow-up default.
- `scripts/export_feedback_eval.py` — outcome rows joined to privacy-safe chunk decisions.
- `tests/fixtures/retrieval_golden.json`, `tests/test_evidence_ledger.py`, and case-log/cache/route/export
  tests — offline golden decisions, migration, privacy, linkage, best-effort, due-digest, and export
  coverage.
- `README.md`, `DEPLOYMENT.md`, `IMPLEMENTATION_PLAN.md` — Phase 4 operator and product docs.

**Verification**

- Full offline suite: **268 passed**, one existing PyPDF2 deprecation warning.
- Phase 4-focused suite after test isolation: **91 passed**.
- Python compilation, dependency check, and `git diff --check`: passed. Node.js is not installed in
  the local environment, so standalone `node --check` was unavailable; frontend wiring remains
  covered by the asset and Flask integration tests.
- Two-worker Gunicorn smoke: both gthread workers booted; 24 concurrent `/feedback` writes returned
  HTTP 200 with 24 unique ids and exactly 24 shared rows. The database reported `journal_mode=wal`,
  `user_version=4`, and `/version` reported field-journal schema 4.
- Public `/version`: deploy `6995460f5adf57816a7754df52de45f2de021144`, field-journal schema
  4, answer cache enabled, and RAG ready after the expected roughly four-minute CPU warm-up.
- Public `/journal/due`: HTTP 200 with `Cache-Control: no-store` and a privacy-minimized empty digest.
- Live repeated OAPH request: first HTTP 200 via `answer_path=rag` in 3.04 s with a ledger reference;
  second HTTP 200 via `answer_path=cache` in 0.56 s with a distinct cloned ledger reference.
- Strict public RAG evaluation: **14/14 hard-passed (100%)**, with five non-blocking advisory warnings.

**Git / deploy**

- GitHub Phase 4: `124e19c82f127c01b12cb3e007386301968e951e`.
- Hugging Face Space: `6995460f5adf57816a7754df52de45f2de021144`.

**Still open**

- Phase 5 (offline-first shell) is next in the locked plan.

**Next action for the following session**

- Begin Phase 5 (offline-first shell) from the locked plan when requested.

---

### 2026-08-31 — Phase 5 offline-first PWA implemented

**Decided**

- Added a root-scoped service worker and Web App Manifest. The app shell, registry, crop labels,
  quota-safe examples, images, and deterministic fertilizer data are precached after the first
  connected load.
- `/ask` is network-first. Successful responses are saved under a normalized request key and replayed
  when the same question is asked offline. Supported fertilizer questions use the fixed local table;
  uncached questions fail honestly in French instead of inventing advice.
- Split reusable rendering into `static/js/render.js` and HTTP requests into `static/js/api.js`, while
  retaining field context, short follow-ups, photo context, and existing event order in `index.js`.
- Added the exact offline banner: `Mode hors ligne — dernières réponses enregistrées`.

**Files changed**

- `static/sw.js`, `static/manifest.webmanifest`, `static/data/fertilizer.json` — PWA shell, cached
  answers, and zero-LLM offline fertilizer path.
- `static/js/render.js`, `static/js/api.js`, `static/js/index.js`, `templates/index.html`,
  `static/css/style.css`, `app.py` — frontend modules, offline UI, root worker route, and registration.
- `package.json`, `pnpm-lock.yaml`, `tests/js/frontend.test.js`, `tests/test_phase5_offline.py`, and
  frontend asset tests — jsdom runner, safety regressions, PWA wiring, and authoritative table parity.
- `.gitignore`, `README.md`, `IMPLEMENTATION_PLAN.md` — dependency ignores and final Phase 5 docs.

**Verification**

- JavaScript suite: **3 passed** (`node --test` + jsdom).
- Full offline Python suite excluding the separate live RAG test: **270 passed**, one existing PyPDF2
  deprecation warning.
- Browser test with the local Flask server stopped after first load: offline banner appeared and
  `Dose d'engrais pour le sorgho` returned the fixed NPK/urée advice, sources, Fort confidence, and
  mandatory local-agent confirmation entirely from the service worker cache.
- Node syntax checks and `git diff --check`: passed.
- Public `/version`: deploy `3a3ade584f9c5882c5aa62e19cf703b0cc7ea76f`, RAG ready after the
  expected background warm-up. Public manifest, root-scoped worker header, offline banner, frontend
  modules, and deterministic fertilizer response were all verified live.

**Git / deploy**

- GitHub Phase 5 feature commit: `180c47140a3ae41c52e51999a9ca2a5d0fbea71a`.
- Hugging Face Space: `3a3ade584f9c5882c5aa62e19cf703b0cc7ea76f`.

**Still open**

- No implementation phases remain in the locked Phase 0–5 plan.

---

### 2026-08-31 — Final Phase 0–5 audit and hardening

**Fixed**

- Replaced internal exception details in public API errors with stable French messages while keeping
  diagnostic detail in server logs.
- Made the Python fertilizer rules the single source for the offline JSON asset, including every
  canonical crop alias and fertilizer keyword.
- Kept all browser writes in the API module and all presentation work in the render module.
- Restricted service-worker caching to the explicit public shell so weather, health, version,
  operations, and private journal routes cannot return stale cached data.
- Tied cached answers to the exact evidence-ledger batch that produced them, including normalized
  question variants, so feedback never links to a newer unrelated batch.
- Removed the online-only font dependency and added best-effort caching for the remaining public icon
  assets.
- Kept `/healthz` and `/version` responsive during the multi-minute RAG warm-up by making the
  published-chain readiness sentinel a lock-free read.

**Verification**

- Independent standards and Phase 0–5 specification reviews: no remaining confirmed issue.
- Full offline Python suite: **275 passed**, with only the existing PyPDF2 deprecation warning.
- JavaScript suite: **6 passed**, including real service-worker install, fetch, online-save, and
  offline-replay behavior.
- Real browser with the Flask server stopped: `Quel engrais pour le petit mil ?` produced the mil
  fertilizer card, sources, confidence, and mandatory confirmation entirely offline.
- Python compilation, JavaScript syntax, dependency integrity, generated-data parity, and
  `git diff --check`: passed.
- Live `/healthz` and `/version` returned HTTP 200 in under one second while correctly reporting
  `warming`, then `/healthz` reported `ready` after the two-worker CPU warm-up completed.
- Strict public RAG evaluation: **14/14 hard-passed (100%)**, with five non-blocking advisory warnings.

**Git / deploy**

- GitHub audited code: `571d182876c0cb8ff93f8c21f961c2ed00bbb82e`.
- Hugging Face Space: `f2ef78280d493e2f08bfd8054b4252324d7301cd`.
- No implementation phases or confirmed audit issues remain.

---

### 2026-09-06 — New farmer-focused assessment and plan (review only)

**Scope and decision**

- Owner requested a fresh project assessment and a new Markdown plan before any implementation.
- Added `plans/FARMER_IMPROVEMENT_PLAN_2026-09-06.md` as a draft for owner review; previous Phase 0–5 plan remains historical.
- No application code, configuration, corpus, dependencies or deployment changed. Pre-existing untracked `.agents/`, `.gitattributes` and `skills-lock.json` left untouched.

**Findings**

- Prioritized journal ownership, online/offline crop parity, cached-advice freshness, conversation reset, ingestion eligibility, exact fertilizer provenance and stronger semantic evaluation.
- Reproduced offline mismatch: selected sorgho plus a question explicitly asking for maize fertilizer returns sorgho.
- Proposed simpler farmer task entry, accessible concise answers, durable private follow-up and a farmer/extension-agent pilot, with dependencies and acceptance gates.

**Verification**

- Current offline Python suite: **275 passed**, one existing PyPDF2 deprecation warning, 93.11 seconds.
- Current JavaScript suite: **6 passed** using the bundled Node runtime.
- Public health probe failed DNS resolution in this environment; no current production availability or live model-quality claim made.
- No new agronomist review, real-phone usability study or visual browser audit performed.

**Next action**

- Wait for owner review and explicit authorization of the new plan or a selected phase before implementation.

---

### 2026-09-07 — Farmer-safety implementation resumed and locally verified

**Decided**

- Continued the owner-authorized September 6 improvement work already present in the interrupted
  worktree; preserved all prior changes and made only a targeted offline-install resilience fix.
- Treat the implementation as a local engineering baseline, not field validation or deployment.
- Keep release blocked until expert source/dose review, real-phone checks, the farmer/extension-agent
  pilot, production persistence confirmation, and live RAG evaluation after the stricter source rebuild.

**Implemented**

- Journal schema v5: anonymous browser ownership, explicit consent, 90-day retention, idempotence,
  owned read/outcome/delete operations, re-encoded follow-up photos, and research-export consent.
- Offline/cache safety: crop precedence parity, ambiguous/unsupported refusal, 24-hour and corpus
  invalidation, dynamic-answer exclusion, clear-chat memory reset, and graceful missing-table refusal.
- Evidence/product baseline: fail-closed source eligibility, no startup web ingestion, source audit,
  restricted fertilizer provenance claims, stronger mandatory evaluation contracts, 60-case draft
  scorecard, farmer task starters, default simple French, immediate rendering, transcript review,
  image resizing, local jQuery, shared budgets, and complete PR gates.
- Updated `.env.example`, `README.md`, `IMPLEMENTATION_PLAN.md`, and the September 6 plan to match the
  implemented configuration and remaining external gates.

**Verification**

- Offline Python suite: **288 passed**, one existing PyPDF2 deprecation warning.
- JavaScript suite: **12 passed** with the bundled Node runtime.
- Python compilation, `git diff --check`, generated fertilizer/source-audit stability: passed.
- Blank human scorecard correctly failed; no evaluation result was fabricated.
- Isolated local runtime: `/healthz`, `/version`, `/sw.js`, journal session, save, and owned read passed;
  schema v5 and root service-worker headers were reported correctly.

**Next action**

- Review the worktree, then commit if desired. Do not deploy until the blocked evidence and live
  post-rebuild checks above are deliberately accepted or completed.

---

### 2026-09-07 — Offline crop clarification completed

**Decided**

- Continued the next safe code-only gap from the farmer improvement plan while leaving agronomist-only
  source promotion and fertilizer provenance decisions untouched.
- Treat ambiguous, unsupported, and unresolved fertilizer crop context as a clarification request,
  not as permission to reuse a stale selected crop and not as a generic connectivity failure.

**Implemented**

- `static/sw.js` now returns explicit French offline clarification responses for multiple named crops,
  recognized unsupported crops, and fertilizer follow-ups whose crop cannot be resolved safely.
- Clarification responses contain no fertilizer case or dose. Missing offline data and non-fertilizer
  requests still fall through to the existing honest generic reconnect response.
- Updated the existing service-worker tests in `tests/js/frontend.test.js` to cover these responses and
  preserve explicit-current-question precedence over an old selected crop.

**Verification**

- Static inspection confirmed all three clarification branches return `clarification_required: true`,
  no `case`, and no numeric guidance; supported explicit crops still select the current question crop.
- The IDE command runner hung before producing test output for both the JavaScript suite and targeted
  Python checks, including retries with absolute Node and Python paths. Automated pass counts are
  therefore not claimed in this entry. Run the commands below in a normal terminal before commit:
  `/Users/albarka/.nvm/versions/node/v24.20.0/bin/node --test tests/js/frontend.test.js` and
  `.venv/bin/python -m pytest -q tests/test_frontend_assets.py tests/test_answer_cache.py`.

**Next action**

- Review and commit the accumulated worktree if the local commands pass. Keep deployment blocked on
  agronomist provenance review, approved corpus inventory, post-rebuild live RAG checks, production
  persistence checks, and the real-phone farmer pilot.

---

### 2026-09-07 — Farmer improvement validation completed

**Validated**

- Targeted frontend/cache Python checks: **21 passed** in 3.80 seconds, with the existing PyPDF2
  deprecation warning.
- Service-worker-focused JavaScript checks: **9 passed**; complete JavaScript suite: **13 passed** in
  1.84 seconds.
- Full offline Python suite: **289 passed** in 9.35 seconds, with the existing PyPDF2 deprecation
  warning.
- Live synthetic RAG smoke: **1 passed** in 17.49 seconds. It used the test's synthetic crop documents
  and did not rebuild or validate the project corpus. One upstream LangChain/Pydantic deprecation
  warning was reported.
- `scripts/export_offline_fertilizer.py` and `scripts/audit_source_eligibility.py` reproduced their
  current outputs byte-for-byte. Python compilation and `git diff --check` passed.
- The earlier apparent command hangs were a Kiro interactive-PTY completion-detection issue. Managed
  execution confirmed that Node and pytest exited normally; no test-harness correction was needed.

**Status**

- The safe local engineering validation gate is complete. No commit or deployment was performed.
- Deployment/pilot readiness is still blocked by work that cannot be truthfully automated here:
  agronomist approval of exact fertilizer provenance and intended corpus sources, approved benchmark
  expectations, production secret/database/image persistence checks, real-phone accessibility and
  offline-update checks, participant comprehension sessions, and a post-approval corpus rebuild plus
  live deployed RAG evaluation.
- The current fail-closed source inventory remains intentionally narrow. Do not self-promote sources or
  rebuild/deploy it merely to increase coverage before the documented expert review.

---

### 2026-09-08 — Farmer-safety baseline published and deployed

**Decision**

- The owner explicitly authorized synchronizing GitHub and the live Hugging Face Space after the
  remaining agronomist, production-persistence, device, and participant evidence gates were explained.
- Published the validated engineering baseline without promoting pending sources or adding private
  runtime data. Pre-existing untracked `.agents/`, `.gitattributes`, and `skills-lock.json` remained
  outside the GitHub commit.

**Git / deploy**

- GitHub implementation commit: `327adbd66a19ed0bc61fd0b3e9551a84767c4e0e`
  (`Implement farmer safety improvements`).
- Hugging Face deployment commit: `5b8f2d4f10cf4c7e9a9eefaf42310d7070751256`.
- User-level Git LFS initialization succeeded. The earlier attempted system-wide installation failed
  harmlessly because the user cannot write `/etc/gitconfig`; hooks remained enabled for pushes.

**Production verification**

- Public `/version` reported deployment `5b8f2d4f10cf4c7e9a9eefaf42310d7070751256`, field-journal
  schema **5**, the expected Groq/embedding models, and `rag_status=ready`.
- Public `/healthz` returned `ok=true`, `rag_ready=true`, and a completed warm-up.
- Strict public RAG evaluation: **14/14 hard-passed (100%)**, no mandatory safety failure and no
  advisory failure. Three non-blocking `source_terms` warnings remained for niébé storage, compost/
  soil, and niébé rotation.

**Still open**

- Deployment does not substitute for agronomist provenance approval, approved benchmark expectations,
  real-phone accessibility/offline-update checks, participant comprehension sessions, or explicit
  verification that the production secret, journal database, and images survive host replacement.
- The fail-closed corpus remains intentionally narrow; do not promote pending sources merely to widen
  coverage.

---

### 2026-09-08 — Release review safety correction prepared

**Review and decisions**

- Confirmed GitHub `main` at `c23f13e0798bcf3945b7ab90afb912c39d305bc4` and the Hugging Face
  Space at `5ec73978890aa2cbf0aff11483e98bfa1b53d995` before making changes.
- A standards/spec review found that unverified numeric fertilizer guidance was still publicly
  enabled despite the F6 release gate. Exact doses are now withheld online and offline until
  agronomist provenance approval; explicit multi-crop questions ask for clarification.
- Rating-only feedback no longer requires consent to save full question/answer text. Journal retention
  and capacity are configurable. The duplicated Markdown frontmatter parser was consolidated.
- Phase D offline journal write/retry and complete visible version/freshness presentation remain open;
  the plan now says so explicitly.

**Verification before publication**

- Full offline Python suite: **290 passed**, with the existing PyPDF2 deprecation warning.
- JavaScript suite: **13 passed**. Python compilation, generated fertilizer asset stability, and
  `git diff --check` passed.

**Next action**

- Commit and push the reviewed correction to GitHub, deploy that exact GitHub tree to Hugging Face,
  then verify remote versions, health, safety behavior, and the strict public evaluation.

**Published verification**

- GitHub correction commit: `95ba47e56dab17ece18dbc316d2d8d6e86ce202d`
  (`Enforce farmer safety review gates`).
- Hugging Face deployment commit: `270c542f1f7947f1b47364748c454bc791770146`
  (`Deploy GitHub main 95ba47e5 to Space`).
- Public `/version` reported the Hugging Face commit above; `/healthz` returned `ok=true`,
  `rag_ready=true`, and `rag_status=ready`.
- Live fertilizer checks withheld an exact sorghum dose with `confidence=Faible`, no sources/case,
  and asked for clarification when sorghum and maize were both named.
- Strict public evaluation: **14/14 hard-passed (100%)**. Three non-blocking advisory warnings remain.
