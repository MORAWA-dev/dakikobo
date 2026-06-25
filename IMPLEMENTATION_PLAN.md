# DakiKobo — Implementation Plan

Single, merged, de-duplicated backlog built from `models_sugestions/` (Claude, ChatGPT, Gemini
sessions 1–2) **plus** a direct read of the source tree. Tasks are ordered **easiest / lowest-risk
first**, hardest / highest-risk last. Each task lists the exact files it touches, a one-line
definition of done a non-developer can verify, and an effort tag: **S** (<60 min), **M** (one
session), **L** (two+ sessions).

Rules of engagement: one task per step, smallest change that works, test before commit, never leave
the app unable to start. Answers, labels, and TTS stay in **French**. Keep everything mobile-friendly.

Status legend: `[ ]` todo · `[x]` done.

---

## Tier 1 — Quick bug & path fixes (do first)

- [x] **1b. Force French answers + French fallback** — `core/llm_chain.py`
  - *Done when:* asking a question (even one phrased in English) returns the answer — and the
    "I don't know" fallback — in French. **(S)**

- [x] **1. Fix broken avatar + favicon/logo paths** — `static/js/index.js`, `templates/index.html`
  - *Done when:* the page loads with the DakiKobo logo, bot avatar, user avatar, and browser-tab
    icon all visible — no broken-image icons. **(S)**

- [x] **2. Re-encode `requirements.txt` as UTF-8** — `requirements.txt`
  - *Done when:* `file requirements.txt` reports ASCII/UTF-8 text (not "data"), with the same
    package list. **(S)**

- [x] **3. Fix `DATA_FOLDER` casing** — `config.py`
  - *Done when:* `DATA_FOLDER` points at `Data/knowledge_base`; startup log shows PDFs found
    (works on Linux/Colab, not just macOS). **(S)**

- [x] **4. Fix TTS truncation** — `config.py`, `core/rag_pipeline.py`
  - *Done when:* enabling audio on a ~90-word French answer plays speech that reaches the end of
    the sentence instead of cutting off mid-word. **(S)**

- [ ] **5. Enable the similarity-score threshold** — `core/llm_chain.py`
  - *Done when:* asking an off-topic question (e.g. "comment réparer un moteur de voiture ?")
    returns the "information not available" fallback instead of a confident answer. **(S)**

- [ ] **6. Recursive PDF ingestion** — `core/rag_pipeline.py`
  - *Done when:* the startup log prints a higher PDF count than before (subfolders included), and
    one unreadable PDF does not crash startup. **(S)**

- [ ] **7. Remove dead files** — delete `chat1.py`, `chat2.py`, `static/css/broken.css`, `static/js/broken.js`
  - *Done when:* those files are gone and `python app.py` still starts normally. **(S)**

---

## Tier 2 — RAG quality & trust (medium)

- [ ] **8. Attach source metadata at ingestion** — `core/rag_pipeline.py`
  - *Done when:* a retrieved chunk carries its originating PDF filename in `metadata["source"]`
    (verified by a quick print/check). **(M)**

- [ ] **9. Return + render source citations** — `app.py`, `static/js/index.js`, `static/css/style.css`
  - *Done when:* under each bot answer the UI shows the document name(s) the answer drew from;
    answers with no retrieved source show none. **(M)**

- [ ] **10. Persistent Chroma vector store** — `config.py`, `core/rag_pipeline.py`, `app.py`
  - *Done when:* the second `python app.py` starts noticeably faster and logs "loading existing
    index" instead of re-embedding (rebuild only when `REBUILD_VECTORSTORE=true`). **(M)**

- [ ] **11. Multilingual embeddings upgrade** — `config.py` (+ one-time reindex)
  - *Done when:* after rebuilding the index with `paraphrase-multilingual-mpnet-base-v2`, the same
    French question returns visibly more on-topic source chips. **(M)**

---

## Tier 3 — Mobile UX (medium)

- [ ] **12. Mobile-first responsive layout** — `templates/index.html`, `static/css/style.css`
  - *Done when:* at 360px width (Chrome device toolbar) the chat fills the screen, the input bar
    is pinned to the bottom, and there is no horizontal scroll. **(M)**

- [ ] **13. Quick-action chips + active mic state** — `templates/index.html`, `static/js/index.js`, `static/css/style.css`
  - *Done when:* tapping a French chip (e.g. "Semis du mil") sends that question and gets an
    answer, and the mic button visibly pulses while listening. **(M)**

- [ ] **14. Feedback capture (👍 / 👎)** — `app.py`, `static/js/index.js`, `static/css/style.css`
  - *Done when:* clicking 👎 under an answer appends a new row to `data/feedback.csv`
    (no database). **(M)**

---

## Tier 4 — Docs & tests (medium, low-risk)

- [ ] **15. Rewrite `README.md`** — `README.md`
  - *Done when:* the README matches the current stack (Flask, Groq `llama-3.3-70b`, LangChain,
    Chroma, French TTS), uses `.env`, and contains no instruction to put API keys in source. **(M)**

- [ ] **16. First pytest smoke tests** — `tests/`
  - *Done when:* `pytest` passes a test asserting ingestion finds the expected PDFs and a known
    French crop question returns a non-empty answer. **(S)**

---

## Tier 5 — New modules (hardest / highest-risk, do last)

- [ ] **17. Deterministic fertilizer tool + keyword branch** — `core/fertilizer.py`, `app.py`
  - *Done when:* asking "dose d'engrais pour le sorgho" returns a specific source-grounded dose
    with a French "confirmez avec votre agent" disclaimer (no invented numbers). **(L)**

- [ ] **18. Intent router** — `core/router.py`, `app.py`
  - *Done when:* fertilizer questions hit the fertilizer tool, everything else hits RAG, and
    normal Q&A is unchanged. **(M)**

- [ ] **19. Disease screening via Gemini Vision + image upload** — `core/disease.py`, `app.py`, `templates/index.html`, `static/js/index.js`
  - *Done when:* uploading a leaf photo returns a hedged French screening with a "ceci n'est pas
    un diagnostic" disclaimer, and a blurry/random photo returns a polite "je ne peux pas dire,
    reprenez la photo". **(L)**

---

## Later / parked (do **not** attempt now)

- **Custom disease CNN training** — no field-validated Burkina dataset; PlantVillage models collapse
  on real phone photos. Better as an honest Colab "domain-shift" research artifact.
- **Real yield-prediction model** — needs local plot-level data; false precision harms trust. Keep
  to a clearly-labeled reference range or a research notebook.
- **Native mobile app (Flutter/Android)** — months of work; the responsive web app covers the demo.
- **Offline / edge inference (local LLM)** — out of scope for the deadline and the hardware.
- **Local-language generation (Mooré / Dioula / Fulfuldé)** — a research project, not a feature;
  French first.
- **PWA install + service worker** — nice-to-have; deferred until the core trust features land.
- **Firebase / user accounts / admin dashboard** — unnecessary backend complexity for v1.

---

*Conflicts resolved by reading the code: embeddings → `paraphrase-multilingual-mpnet-base-v2`
(lighter than `bge-m3` for a laptop on a 3-week timeline); persist dir → `chroma_db/` (already
git-ignored); Gemini's session-2 source-chip JS diff has a string-concatenation bug, so task 9 is
hand-written rather than pasted.*
