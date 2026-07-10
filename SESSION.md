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

1. **When climate hosts UP:** health probe + refresh (skips DOWN URLs).
2. **Optional KB:** curated pending only if new field value.
3. **Vision (Colab):** run 03/04 on phone photos; export only if notebook 05 gates pass.
4. **Fill** local crop labels in `Data/glossaries/crop_labels.json` with human review.
5. Optional: local agent review of French field phrasing.

---

## Session entries

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

- (filled at commit)

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
