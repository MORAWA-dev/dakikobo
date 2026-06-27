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

- [x] **1c. Translate UI strings to French** — `static/js/index.js`, `app.py`
  - *Done when:* the welcome message, the bot self-identity reply (also triggered by French
    phrasing), and the error message all appear in French. **(S)**

- [x] **1. Fix broken avatar + favicon/logo paths** — `static/js/index.js`, `templates/index.html`
  - *Done when:* the page loads with the DakiKobo logo, bot avatar, user avatar, and browser-tab
    icon all visible — no broken-image icons. **(S)**

- [x] **2. Re-encode `requirements.txt` as UTF-8** — `requirements.txt`
  - *Done when:* `file requirements.txt` reports ASCII/UTF-8 text (not "data"), with the same
    package list. **(S)**

- [x] **3. Fix `DATA_FOLDER` casing** — `config.py`
  - *Done when:* `DATA_FOLDER` points at the correctly-cased `Data` tree; startup log shows PDFs
    found recursively (works on Linux/Colab, not just macOS). **(S)**

- [x] **4. Fix TTS truncation** — `config.py`, `core/rag_pipeline.py`
  - *Done when:* enabling audio on a ~90-word French answer plays speech that reaches the end of
    the sentence instead of cutting off mid-word. **(S)**

- [x] **5. Enable the similarity-score threshold** — `core/llm_chain.py`, `config.py`
  - *Done when:* asking an off-topic question (e.g. "comment réparer un moteur de voiture ?")
    returns the "information not available" fallback instead of a confident answer. **(S)**

- [x] **6. Recursive PDF ingestion** — `core/rag_pipeline.py`, `config.py`
  - *Done when:* the startup log prints a higher PDF count than before (subfolders included), and
    one unreadable PDF does not crash startup. **(S)**

- [x] **7. Remove dead files** — delete `chat1.py`, `chat2.py`, `static/css/broken.css`, `static/js/broken.js`
  - *Done when:* those files are gone and `python app.py` still starts normally. **(S)**

---

## Tier 2 — RAG quality & trust (medium)

- [x] **8. Attach source metadata at ingestion** — `core/rag_pipeline.py`, `app.py`
  - *Done when:* a retrieved chunk carries its originating PDF filename in `metadata["source"]`
    (verified by a quick print/check). **(M)**

- [x] **9. Return + render source citations** — `app.py`, `static/js/index.js`, `static/css/style.css`
  - *Done when:* under each bot answer the UI shows the document name(s) the answer drew from;
    answers with no retrieved source show none. **(M)**

- [x] **10. Persistent Chroma vector store** — `config.py`, `core/rag_pipeline.py`, `app.py`
  - *Done when:* the second `python app.py` starts noticeably faster and logs "loading existing
    index" instead of re-embedding (rebuild only when `REBUILD_VECTORSTORE=true`). **(M)**

- [x] **11. Multilingual embeddings upgrade** — `config.py`, `core/rag_pipeline.py` (+ one-time reindex)
  - *Done when:* after rebuilding the index with a multilingual model, the same French question
    returns on-topic source chips while off-topic queries still hit the fallback. **(M)**
  - Switched `EMBEDDING_MODEL` to `paraphrase-multilingual-MiniLM-L12-v2` (chosen over heavier
    multilingual alternatives because it is faster to embed on CPU while still good for French).
  - Switching the model changed the relevance-score scale (Chroma's default L2 produced large
    negative scores → the 0.2 threshold rejected everything). Fixed by setting the Chroma collection
    to **cosine** space (`collection_metadata={"hnsw:space": "cosine"}`), which normalizes scores so
    the existing `SIMILARITY_THRESHOLD = 0.2` keeps working across models.
  - Verified end-to-end on the real code path (build → persist → load → threshold retriever):
    on-topic French queries return source docs; off-topic ("moteur de voiture", "capital of France")
    return 0 → fallback. Cosine scores: on-topic top ~0.32–0.53, off-topic top ~0.03–0.11.
  - **Requires a one-time reindex:** no `chroma_db/` existed, so the next `python app.py` builds fresh
    with the new model (slower first build on CPU, then fast loads via the Task 10 persistence). If a
    stale index ever exists after a future model change, delete `chroma_db/` or set
    `REBUILD_VECTORSTORE=true`.

---

## Tier 3 — Mobile UX (medium)

- [x] **12. Mobile-first responsive layout** — `templates/index.html`, `static/css/style.css`
  - *Done when:* at 360px width (Chrome device toolbar) the chat fills the screen, the input bar
    is pinned to the bottom, and there is no horizontal scroll. **(M)**
  - Added global `box-sizing: border-box` so padding can't cause overflow; made `.chat-container`
    responsive (`max-width: 100%`, `max-height: 100%`) and switched body height to `100dvh` for
    correct sizing under mobile browser chrome.
  - Added a `@media (max-width: 480px)` block: container goes full-screen (`width: 100%`,
    `height: 100dvh`, square corners), tightened header/messages/input/footer padding, widened
    message bubbles to 90%, and let the footer wrap so the clear button + voice toggle never overflow.
  - Input bar stays pinned to the bottom via the existing flex column (`.chat-messages { flex: 1 }`)
    now that the container fills the viewport height. Long source filenames already wrap
    (`word-break`), so no horizontal scroll at 360px.
  - Also set `<html lang="fr">` (was `en`) to match the app's French UI.

- [x] **13. Quick-action chips + active mic state** — `templates/index.html`, `static/js/index.js`, `static/css/style.css`
  - *Done when:* tapping a French chip (e.g. "Semis du mil") sends that question and gets an
    answer, and the mic button visibly pulses while listening. **(M)**
  - Added a horizontal, scrollable `.quick-chips` row above the input with 5 French crop chips
    (Semis du mil, Fertiliser le sorgho, Maladies du niébé, Culture du maïs, Rotation des cultures);
    each carries the full question in `data-question`.
  - JS delegates `.chip` clicks: sets `#messageText` to the question and calls `sendMessage()`
    (guarded by `isProcessing`).
  - Mic button now pulses while listening: `recognition.onstart` adds a `.listening` class
    (red pulsing `box-shadow` animation), `onend`/error removes it. Also localized the STT failure
    alert to French.

- [x] **14. Feedback capture (👍 / 👎)** — `app.py`, `static/js/index.js`, `static/css/style.css`
  - *Done when:* clicking 👎 under an answer appends a new row to `data/feedback.csv`
    (no database). **(M)**
  - Added a `POST /feedback` route that appends `timestamp,rating,question,answer` to
    `data/feedback.csv` (creates the file + header on first write; validates rating ∈ {up,down}).
  - Frontend renders 👍/👎 buttons under each bot answer (after typing); clicking posts the
    rating with the originating question + answer, disables the buttons, and shows "Merci !".
  - Verified with Flask's test client: invalid rating → 400; up/down → rows appended with header.
  - Added `data/feedback.csv` to `.gitignore` (runtime-generated, not committed).

---

## Tier 4 — Docs & tests (medium, low-risk)

- [x] **15. Rewrite `README.md`** — `README.md`
  - *Done when:* the README matches the current stack (Flask, Groq `llama-3.3-70b`, LangChain,
    Chroma, French TTS), uses `.env`, and contains no instruction to put API keys in source. **(M)**
  - Full rewrite: accurate stack (Groq `llama-3.3-70b-versatile`, multilingual MiniLM embeddings,
    persistent Chroma), `uv`/`.env` setup workflow (cp `.env.example` → `.env`), features list
    (sources, TTS/STT, quick chips, feedback, mobile UI), config reference table, project layout,
    and a first-run/rebuild note. Removed the old insecure "put your key in chat2.py" instruction
    and the stale Mixtral references.

- [x] **16. First pytest smoke tests** — `tests/`
  - *Done when:* `pytest` passes a test asserting ingestion finds the expected PDFs and a known
    French crop question returns a non-empty answer. **(S)**
  - `tests/test_ingestion.py`: asserts expected PDFs are discoverable under `Data/` and that
    `load_pdfs_from_folder` returns non-empty `Document`s with `source` metadata.
  - `tests/test_rag.py`: live smoke test — builds a tiny in-memory Chroma (cosine), runs the
    real `RetrievalQA` chain on "Quand semer le mil ?", asserts a non-empty answer. Auto-skips
    when `GROQ_API_KEY` is unset (so CI without a key still passes).
  - Added `pytest` to `requirements.txt` and `.pytest_cache/` to `.gitignore`.
  - Result: `3 passed` (all three ran locally with the `.env` key present).

---

## Tier 5 — New modules (hardest / highest-risk, do last)

- [x] **17. Deterministic fertilizer tool + keyword branch** — `core/fertilizer.py`, `app.py`
  - *Done when:* asking "dose d'engrais pour le sorgho" returns a specific source-grounded dose
    with a French "confirmez avec votre agent" disclaimer (no invented numbers). **(L)**
  - **Data check first:** the existing PDF corpus has NO per-crop dose tables (its `kg/ha` figures
    are yields, plus one anecdotal maize line; `farmer_training_manual.pdf` is a generic India-
    oriented handbook). So doses were sourced from **published Burkina/INERA research** (verified
    via web search) rather than invented or pulled from anecdotes.
  - `core/fertilizer.py`: fixed, cited per-crop doses for sorgho, mil, maïs, niébé, arachide
    (e.g. cereals = 100 kg/ha NPK 14-23-14 + 50 kg/ha urée; maïs = 150 + 100; niébé = 100 NPK only;
    arachide = légumineuse, ~14 kg N/ha + fumure organique). Includes microdose alternatives for
    cereals. Every answer carries the "Confirmez toujours avec votre agent agricole" disclaimer and
    cites its source(s). `is_fertilizer_query()` detects intent; `get_fertilizer_advice()` returns
    `None` (→ RAG) when no supported crop is named.
  - `app.py`: deterministic keyword branch in `/ask` runs before the LLM, so fertilizer questions
    get grounded numbers (with TTS + source chips) and never hit the model's invention risk.
  - Added `tests/test_fertilizer.py` (4 tests, no network): intent detection, grounded sorgho dose
    + disclaimer, all 5 crops covered, and deferral to RAG when no crop is named. All pass.

- [x] **18. Intent router** — `core/router.py`, `app.py`
  - *Done when:* fertilizer questions hit the fertilizer tool, everything else hits RAG, and
    normal Q&A is unchanged. **(M)**
  - `core/router.py`: `classify(query)` returns `INTENT_FERTILIZER` only when the question is a
    fertilizer query AND names a supported crop; otherwise `INTENT_RAG`. Centralizes dispatch so a
    future "disease" intent can be added without touching the route.
  - `app.py`: `/ask` now dispatches via `classify()` (replacing the inline keyword branch). The RAG
    path is untouched, so normal Q&A behaves exactly as before.
  - Added `tests/test_router.py` (3 tests): fertilizer+crop → tool, fertilizer-without-crop → RAG,
    normal/other questions → RAG. All pass.

- [x] **19. Disease screening via Gemini Vision + image upload** — `core/disease.py`, `app.py`, `templates/index.html`, `static/js/index.js`
  - *Done when:* uploading a leaf photo returns a hedged French screening with a "ceci n'est pas
    un diagnostic" disclaimer, and a blurry/random photo returns a polite "je ne peux pas dire,
    reprenez la photo". **(L)**
  - `core/disease.py`: calls Gemini Vision via the **REST API using `requests`** (no SDK dependency —
    the `google-genai` install tried to compile a Rust wheel and hung). Prompt forces a hedged French
    screening ("il pourrait s'agir de…") and returns a sentinel for unusable photos → polite
    "reprenez la photo" message. Code guarantees the "Ceci n'est pas un diagnostic" disclaimer, and
    gracefully handles missing key / network errors / 429 quota.
  - `config.py`: `GEMINI_API_KEY`, `GEMINI_MODEL` (default `gemini-2.5-flash`).
  - `app.py`: `POST /screen` accepts an uploaded image, returns French screening + TTS.
  - UI: camera button in the input bar (`accept="image/*" capture="environment"`), JS shows the
    user's photo bubble, posts multipart to `/screen`, renders the answer (with optional voice).
  - Added `scripts/test_gemini.py` — reusable key checker (`python scripts/test_gemini.py`).
  - Tests: `tests/test_disease.py` (5, HTTP mocked) cover unclear photo, disclaimer append/no-dup,
    429, and missing-key paths. Live wiring confirmed end-to-end (reached Gemini; returned the
    friendly 429 message).
  - **Live confirmed working:** the earlier 429 was model-specific — `gemini-2.0-flash` had no free
    quota, but `gemini-2.5-flash` works. Default model switched to `gemini-2.5-flash`; a live vision
    call returned the correct "unclear photo" response for a blank image. `scripts/test_gemini.py`
    now tests the app's configured model and reports ✅.

- [x] **20. Public demo guardrails** — `config.py`, `app.py`, `tests/test_app_routes.py`
  - *Done when:* repeated expensive requests are slowed per session, oversized image uploads are
    rejected before Gemini, and users receive clear French errors. **(S)**
  - `config.py`: added `REQUEST_COOLDOWN_SECONDS` (2s), `IMAGE_COOLDOWN_SECONDS` (6s), and
    `MAX_IMAGE_UPLOAD_MB` (5 MB), all overridable via environment variables.
  - `app.py`: `/ask` and `/screen` now return HTTP 429 with `retry_after` for rapid repeats; image
    uploads over the configured limit return HTTP 413 before vision processing.
  - Tests cover text cooldown, image cooldown, and oversized upload responses.

- [x] **21. Quota-safe public examples** — `core/examples.py`, `app.py`, `templates/index.html`, `static/js/index.js`
  - *Done when:* visitors can run 3 text examples, 1 fertilizer example, and 1 image-case example
    without invoking Groq, Gemini, or TTS. **(S)**
  - Added `/examples/<example_id>` with canned French demo responses using the same `answer`,
    `sources`, `confidence`, and `case` JSON shape as live routes.
  - Replaced quick chips with a compact examples panel that renders normal answers and case cards
    through the existing chat UI.
  - Tests cover text, fertilizer, image-case, missing-example, and index markup paths.

- [x] **22. Weather-aware advice card** — `core/weather.py`, `app.py`, `templates/index.html`, `static/js/index.js`
  - *Done when:* users can choose a Burkina Faso location and see a compact weather card with
    rainfall, ET0, soil moisture signal, sowing-window guidance, and urea-before-rain warning. **(M)**
  - `core/weather.py`: uses Open-Meteo forecast data for selected locations, derives four cautious
    agronomic signals, and caches responses by location/date to protect the free Space.
  - `app.py`: added `/weather/locations` and `/weather`, returning structured weather JSON plus
    French error responses.
  - UI: added a `Météo agricole` selector and a compact card renderer instead of a long paragraph.
  - Tests cover API parsing/cache behavior, route success/failure paths, and page markup.

- [x] **23. Soil-aware fertilizer context** — `core/soil.py`, `app.py`, `templates/index.html`, `static/js/index.js`
  - *Done when:* users can choose crop + location and see SoilGrids-derived explanatory indicators
    beside deterministic fertilizer guidance, with clear soil-test confirmation language. **(M)**
  - `core/soil.py`: queries SoilGrids for clay, sand, organic carbon, pH, and CEC at 0-5 cm; converts
    them into classes for texture tendency, organic carbon, pH, and nutrient-retention risk.
  - `app.py`: added `/soil/locations` and `/soil`; `/soil` combines the soil context with the existing
    deterministic fertilizer tool rather than asking the LLM for doses.
  - UI: added a `Sol + engrais` selector and compact card renderer with metrics, indicators,
    fertilizer text, source cards, and the required local-test disclaimer.
  - Tests cover SoilGrids parsing/cache behavior, route success/failure paths, and page markup.

- [x] **24. TTS timeout fallback** — `config.py`, `core/rag_pipeline.py`, `tests/test_tts.py`
  - *Done when:* a slow or failing gTTS request returns the answer with `audio_url: ""` instead of
    blocking the Flask worker. **(S)**
  - `config.py`: added `TTS_TIMEOUT_SECONDS` (default 8s).
  - `core/rag_pipeline.py`: passes the timeout to `gTTS` and treats audio generation as optional.
  - Tests cover timeout propagation, failure fallback, and sentence-boundary truncation.

- [x] **25. Credible mobile UX pass** — `templates/index.html`, `static/css/style.css`, `static/js/index.js`
  - *Done when:* the first screen prioritizes the conversation, tools are available without crowding
    the chat, and icon controls are understandable on phones. **(S)**
  - Moved weather and soil selectors behind one `Outils` drawer beside the input.
  - Replaced the cartoon bot avatar with the neutral DakiKobo logo in all bot messages.
  - Added compact wrapped examples, higher-contrast section labels, and clearer labels/tooltips for
    send, voice input, image screening, and tools.
  - Tests cover the index markup hooks for the drawer and existing tool controls.

- [x] **26. Per-answer audio replay** — `static/js/index.js`, `static/css/style.css`
  - *Done when:* generated audio can be replayed from its answer bubble, while the footer checkbox
    remains the single global auto-play toggle. **(S)**
  - Added a `Réécouter` button for normal RAG answers and image screening answers when `audio_url`
    is present.
  - Centralized browser audio playback so starting a new answer stops the previous audio, and turning
    off the global voice checkbox stops current playback.

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

*Conflicts resolved by reading the code: embeddings → `paraphrase-multilingual-MiniLM-L12-v2`
(lighter than `bge-m3` for a laptop on a 3-week timeline); persist dir → `chroma_db/` (already
git-ignored); Gemini's session-2 source-chip JS diff has a string-concatenation bug, so task 9 is
hand-written rather than pasted.*
