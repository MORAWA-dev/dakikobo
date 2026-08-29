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

| Item | Value |
|------|--------|
| App | French field advisor for Burkina Faso (Flask + RAG) |
| Live Space | https://kimcomehome-dakikobo.hf.space/ |
| HF Space repo | https://huggingface.co/spaces/kimcomehome/dakikobo |
| GitHub | `origin/main` (primary history) |
| HF deploy | Separate history via worktree + rsync; commit message `Deploy GitHub main <sha> to Space` |
| Entry | `app.py` |
| Product rules | French UI; no invented fertilizer doses; cautious/source-grounded; secrets in `.env` only |
| Offline tests | `.venv/bin/pytest -q tests/test_disease.py tests/test_fertilizer.py tests/test_ingestion.py tests/test_router.py` (+ route/eval tests as needed) |
| Live smoke | `.venv/bin/python scripts/evaluate_rag.py --strict --min-pass-rate 0.75` |
| Longer roadmap | `TODO.md`, `PROJECT_STATE.md`, `Agents.md` |

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
