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

1. **Human validation** of MAERAH / CILSS curated Markdown license and factual details (`Data/markdown/scraped_reviewed/`).
2. **Retry Firecrawl** for WASCAL / INERA / AGRHYMET when proxy is healthy; never promote 404/502 pages (see `Data/scraped/rejected/`).
3. **Optional KB:** curated synthesis only from pending ministry/FAO scrapes if new field value; keep raw pending out of RAG.
4. **Vision lab:** wire real SCOLD encoder in Colab (`notebooks/03_scold_retrieval_eval.ipynb`); no production swap until it beats Gemini on phone photos.
5. **Local languages later:** Mooré / Dioula / Fulfulde labels only after French-simple path; no rushed generation.
6. **Notebook 4–5** only as research comparison, not demo hype.

---

## Session entries

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
