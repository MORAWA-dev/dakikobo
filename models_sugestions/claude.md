# DakiKobo: Claude (Opus) Suggestions for Cursor Execution

**Repository:** https://github.com/MORAWA-dev/dakikobo
**Reviewed commit state:** local working tree, 2026-06-24
**Reviewer:** Claude, grounded in a direct read of `app.py`, `config.py`, `core/llm_chain.py`, `core/rag_pipeline.py`, `templates/index.html`, `static/js/index.js`, `static/css/style.css`, `Data/`, `requirements.txt`, `.gitignore`.
**Deadline driving priorities:** UM6P CROPRADAR PhD application, July 15, 2026 (~3 weeks).

> This file is one of several model responses in `models_sugestions/`. It is written to be executed task-by-task in Cursor. Open one backlog row, paste its prompt, let Cursor edit only the named files, run the verification, commit, move on.

---

## 0. What I found that your brief did not list (read this first)

Your "Known bugs & gaps" list is accurate but incomplete. I read the code and found five issues that are not in your brief and that change priorities. Confidence: high (verified in source).

1. **Your similarity threshold is silently ignored.** In `core/llm_chain.py` you call `db.as_retriever(similarity_score_threshold=SIMILARITY_THRESHOLD)`. LangChain only honors a score threshold when you also pass `search_type="similarity_score_threshold"`. Without it, the default search type is plain similarity and the `0.6` value does nothing. So your retriever returns the top-k chunks regardless of relevance, which directly causes confident answers from weakly-related context. This is a root cause of the "overconfident" anti-pattern you want to avoid, and it is a two-line fix.

2. **Source documents are already fetched, then thrown away.** In `llm_chain.py` you set `return_source_documents=True`, and in `app.py` you read only `response["result"]`. The chain is already returning `response["source_documents"]`. Citations in the UI are roughly 80% wired. You are discarding data you already pay for. This makes "source citations" a P0, not a P2.

3. **Your TTS cuts the answer off mid-sentence.** `config.py` sets `TTS_MAX_CHARS = 180`, and `text_to_speech_to_static` does `text[:TTS_MAX_CHARS]`. Your answers run to ~100 words (~550-650 characters). For a low-literacy user who depends on audio, two thirds of every answer is inaudible. Your most important accessibility feature is broken in a way a sighted developer never notices because the full text is on screen. High severity given your stated user.

4. **`DATA_FOLDER` will break the moment you leave macOS.** `config.py` sets `DATA_FOLDER = os.path.join("data", "knowledge_base")` (lowercase `data`), but the real folder is `Data/knowledge_base`. macOS APFS is case-insensitive so it works on your laptop. Colab, any Linux VM, Docker, or a teammate on Linux will load zero PDFs and the app will fall over at `initialize_vector_store`. Latent, but it will bite you exactly when you try to demo on a cloud box.

5. **`requirements.txt` is UTF-16 encoded.** The hexdump shows `23 00 20 00 ...` (a null byte after every character). `pip install -r requirements.txt` fails or misreads on many setups, and the file is unreadable in normal diffs. Anyone you ask to reproduce your environment (a PhD reviewer, a collaborator) hits this in the first five minutes. Re-save as UTF-8.

Minor, lower confidence, still worth a sweep: `fetch_website_content` returns raw unparsed HTML straight into the vector store (dormant because all `KNOWLEDGE_URLS` are commented out, but it is a trap waiting to be uncommented); generated MP3s use random names and are never cleaned up (`static/audio/` already holds 17 files); `broken.css`, `broken.js`, `chat1.py`, `chat2.py` are dead files still in the tree; `static/css/style.css` has no `@media` query at all and a hard `width: 470px`, confirming the desktop-only layout.

The rest of this document follows your requested structure.

---

## 1. Executive summary (5 bullets max)

- **Fix the trust-breaking bugs before adding any feature.** The ignored similarity threshold, the 180-char audio truncation, and discarded source documents are each a few lines and each maps directly onto your stated anti-patterns (overconfidence, broken accessibility, no citations). Do these in week 1, day 1.
- **Citations + confidence + disclaimers are your single highest-impact move for both goals.** They make the product trustworthy for extension agents and they are exactly the "honest, grounded multimodal system" signal a precision-ag PhD reviewer looks for. You already return the source docs; surface them.
- **Mobile-first is non-negotiable and currently absent.** A fixed 470px layout with zero media queries fails your real users (basic smartphones) and looks like a prototype on a reviewer's phone. One focused session converts it.
- **For the disease module, ship Gemini Vision first, not a CNN.** A custom CNN is the most seductive time sink and the least defensible by July 15 (no clean Burkina field dataset, GPU training, overfitting risk). Use Gemini Vision with a strict "this is a screening hint, not a diagnosis" wrapper now; frame the CNN as planned future work in your research statement. This protects your timeline and your honesty.
- **The PhD deliverable is a credible 3-minute demo plus an honest README and a one-page research statement,** not a finished product. Optimize the next 3 weeks for "a reviewer believes this person can build multimodal precision-ag systems," not "a farmer in Kaya is using this daily."

---

## 2. Product vision (farmer usefulness)

**Primary user for v1: the extension agent and the agronomy student, not the farmer directly.** You already identified this in your constraints and it is correct. An extension agent has a smartphone, reads French, serves 50-200 farmers, and is the realistic amplification point. Designing for the agent removes the hardest constraints (low literacy as a hard blocker, local-language requirement on day one) while keeping them on the roadmap. The farmer is the end beneficiary; the agent is the user. Write every UI label and every answer as if an agent will read it aloud or paraphrase it to a farmer.

**Three jobs DakiKobo should do better than Google or a neighbor:**

1. **Give a Burkina-specific, source-grounded answer in seconds.** Google returns generic or US/European agronomy; a neighbor returns one person's experience. DakiKobo's edge is a curated Burkinabé corpus (FAO Burkina, CSA investment plans, the KIT manual, GIZ program docs) returned with the document name attached. The job is "trustworthy local specificity," and the citation is the proof.

2. **Answer about the right crops in the right zone.** Sorghum, millet, niébé, groundnuts in Sahel vs Sudanian Savanna. Generic tools do not know that a sowing-window answer for maize in the south is wrong for millet in the north. Encode zone and crop awareness so the answer is locally actionable.

3. **Be usable hands-free and offline-tolerant.** Voice in, voice out, short answers, low bandwidth. A neighbor is free but not always present; Google needs reading and good signal. DakiKobo's job is "works on a cheap phone, on patchy 2G, while the agent's hands are dirty."

**What you should NOT build yet:** a custom disease CNN trained on scraped images; a native mobile app or Firebase backend; Mooré/Dioula/Fulfuldé generation (collect the need, do not build it); a yield model presented as field-ready; an offline/edge LLM. Each of these is months of work and none is required for a credible July 15 demo. Building any one of them well would consume your entire window.

---

## 3. UI/UX redesign proposal

**Verdict on the stack: keep Flask + jQuery. Do not migrate to React/Vue.** Strong case: your app is a single chat surface plus an image upload and a few quick-action buttons. React buys you nothing here and costs you a build toolchain, a rewrite, and a week you do not have. A reviewer does not care whether the frontend is React; they care whether it works on a phone and whether the answers are grounded. Migrating now is the "fancy architecture that breaks a working simple advisor" anti-pattern in your own brief. Spend the saved time on citations and the disease screen. (If you later want a true offline PWA with a service worker, you can add that to the existing Flask-served HTML without React.)

**Layout: mobile-first, full-viewport chat, optional PWA.** Replace the fixed 470px card with a full-height responsive column. The chat fills the screen on a phone and centers in a max-640px column on desktop. Add a real `@media` strategy (mobile base styles, desktop as the enhancement). Adding a `manifest.json` and a minimal service worker that caches the shell turns it into an installable PWA, which is a clean, honest, low-cost story for "designed for rural smartphones."

**Color, type, branding for Burkina agritech.** Move away from the generic green gradient. Suggested direction: earth and millet palette. Primary deep terracotta/laterite red-brown (`#A0522D`-ish, the color of Burkinabé soil), millet-gold accent (`#E3A52B`), grounded green for confirmations (`#3F7D3F`), warm off-white background (`#FBF7EF`), near-black text for contrast in bright sun (`#1A1A1A`). High contrast matters because users will be outdoors. Typography: one humanist sans with strong legibility at small sizes and good French diacritic support (Inter, or keep Roboto which you already load). Large base font (17-18px) and large tap targets (min 48px) for outdoor thumb use.

**New UI components needed:**

- **Source chips** under each bot answer: small pills showing the document name(s) the answer drew from, e.g. `📄 FAO i3760e` `📄 Manuel de formation`. Tappable to expand the exact snippet.
- **Confidence badge** on each answer: `Fiable` (green) / `À vérifier` (amber) / `Hors base` (grey), driven by retrieval score, not by the LLM's self-assessment.
- **Disclaimer line** that always renders on disease/fertilizer answers: "Conseil indicatif. Confirmez avec votre agent agricole avant d'agir."
- **Image upload** button with a clear "Photographier une feuille malade" affordance and a thumbnail preview.
- **Voice recording state**: the mic button must show an active/listening state (pulsing ring) and a simple waveform or animated dots while capturing; right now there is no visual feedback, so users do not know it is listening.
- **Quick-action chips** above the input for the top recurring questions: `Semis du mil`, `Maladies du niébé`, `Fertilisation du sorgho`, `Dose d'engrais`, `Stockage des céréales`. Tapping one fills and sends the question. This is huge for low-literacy and for demo polish.
- **Answer toolbar**: a 🔊 replay button per answer and a 👍/👎 "Utile ?" feedback pair.

**ASCII wireframe (mobile, ~360px):**

```
┌─────────────────────────────┐
│ ☰  DakiKobo        🌾  FR ▾  │  header: logo, lang switch
├─────────────────────────────┤
│                             │
│  ┌───────────────────────┐  │
│  │ 🤖 Pour semer le mil  │  │  bot bubble
│  │ au Sahel, attendez... │  │
│  │                       │  │
│  │ [Fiable]  🔊 replay   │  │  confidence badge + replay
│  │ 📄 FAO i3760e  📄 KIT │  │  source chips (tap to expand)
│  │ Utile ?  👍  👎       │  │  feedback
│  └───────────────────────┘  │
│                             │
│         ┌────────────────┐  │
│         │ Quand semer ?  🧑│  │  user bubble
│         └────────────────┘  │
│                             │
├─────────────────────────────┤
│ [Semis mil][Niébé][Engrais] │  quick-action chips (scroll x)
├─────────────────────────────┤
│ 📷  [ Posez votre question ] │  image btn + input
│ 🎤(•listening•)        ➤    │  mic w/ active state + send
└─────────────────────────────┘
```

**Three Cursor-ready prompts for UI work:**

> **UI-1 (mobile-first rebuild of the shell):**
> "In `static/css/style.css` and `templates/index.html`, convert the DakiKobo chat from a fixed 470px desktop card to a mobile-first responsive layout. Base styles target a 360px phone: chat fills 100vh, input bar pinned to the bottom, tap targets at least 48px, base font 17px. Add a `@media (min-width: 700px)` block that centers the chat in a max-width 640px column. Replace the green gradient with this palette: background `#FBF7EF`, primary `#A0522D`, accent `#E3A52B`, success `#3F7D3F`, text `#1A1A1A`. Do not touch app.py or the JS logic. Definition of done: opening the page in Chrome device-toolbar at 360px shows a full-height chat with no horizontal scroll and a bottom-pinned input."

> **UI-2 (quick-action chips + active mic state):**
> "In `templates/index.html`, `static/js/index.js`, and `static/css/style.css`, add a horizontally scrollable row of quick-action chips above the input with these French labels: 'Semis du mil', 'Maladies du niébé', 'Fertilisation du sorgho', 'Dose d'engrais', 'Stockage des céréales'. Tapping a chip fills `#messageText` with the corresponding full question and calls `sendMessage()`. Also give `#chatbot-form-btn-voice` a visible 'listening' state: add a CSS pulsing-ring class that JS toggles on `recognition.start()` / `onresult` / `onerror`. Definition of done: a non-technical tester can tap 'Semis du mil', see a question sent and answered, and can see the mic visibly pulse while speaking."

> **UI-3 (source chips + confidence badge + disclaimer rendering):**
> "In `static/js/index.js` and `static/css/style.css`, extend the bot message renderer to display, below each answer: (a) source chips from a `response.sources` array of `{title}` objects, styled as small pills; (b) a confidence badge from `response.confidence` ('high'|'medium'|'low') mapped to 'Fiable'/'À vérifier'/'Hors base' with green/amber/grey; (c) a fixed disclaimer line in small italic when `response.sensitive` is true. Assume the Flask `/ask` route now returns these fields. Also fix the avatar paths: replace `/static/robo.png` with `/static/images/bot_avatar.png` and `/static/user.png` with `/static/images/user_avatar.png`. Definition of done: a tester sees document names and a coloured confidence badge under each answer, and a disclaimer under fertilizer/disease answers."

---

## 4. Technical architecture improvements

### 4.1 Agent design (tools, routing, fallbacks)

Do not jump straight to LangGraph. For July 15, an intent router with three or four explicit tools is more credible and less fragile than a free-form agent that can loop or hallucinate tool calls. Recommended shape:

- A lightweight router (a single Groq call returning a JSON `intent`, or a keyword+embedding classifier) maps each query to one of: `rag_qa` (default knowledge questions), `disease_screen` (an image is attached), `fertilizer_calc` (structured fertilizer question), `yield_estimate` (yield question), `smalltalk/identity`.
- Each intent calls a dedicated handler. `rag_qa` is your existing chain. `fertilizer_calc` is a deterministic rule table, not the LLM. `disease_screen` calls Gemini Vision. `yield_estimate` returns a clearly-labeled rough estimate or a polite "not yet available."
- **Fallback discipline:** every handler must degrade to a safe message rather than guessing. If retrieval score is below threshold, return your "Hors base" answer with low-confidence badge. If Gemini fails, say so. Never let a failure become a confident wrong answer.

Frame it this way in your research statement: "DakiKobo uses a constrained tool-routing layer rather than an open-ended agent, prioritizing predictability and safety for high-stakes agronomic advice." That is a more mature claim than "I used LangGraph."

### 4.2 RAG improvements

In priority order:

1. **Turn on the threshold and pick a search type** (the silent bug from section 0): `db.as_retriever(search_type="similarity_score_threshold", search_kwargs={"score_threshold": SIMILARITY_THRESHOLD, "k": 4})`. Now `0.6` actually filters.
2. **Attach metadata at ingestion.** Right now you `Chroma.from_texts(chunks)` with no metadata, so you cannot cite anything. Switch to building `Document` objects (or pass a parallel `metadatas` list) carrying `source` (filename), and ideally `title` and `page`. This is the prerequisite for citations and for filtering by crop/zone later.
3. **Persist Chroma.** Use `Chroma(persist_directory="chroma_db", embedding_function=...)`, ingest once into it, and on startup load from disk if it exists. Re-index only when the corpus changes (gate behind an env flag or a `--reindex` check). Eliminates the slow full re-embed on every restart. `chroma_db/` is already in your `.gitignore`, so you planned for this.
4. **Recurse into subfolders and ingest the other PDFs.** `glob(os.path.join(folder, "*.pdf"))` misses subfolders. Use `glob(..., recursive=True)` with `**/*.pdf` or `os.walk`, and point ingestion at `Data/` so the KIT book, GIZ program doc, household-characteristics, Bagré, and country-profile PDFs come in. Tag the unidentified `needs_review_01/02` properly or quarantine them.
5. **Upgrade embeddings to multilingual.** `all-MiniLM-L6-v2` is English-centric and your queries and corpus are French. Move to `paraphrase-multilingual-mpnet-base-v2` or, if you want a stronger and still-free option, `BAAI/bge-m3`. This is the same call you already saw in the Gemini session-2 file; it is correct, do it. Note it forces a full re-index (different vector dimension), so do it together with the persistence change.
6. **Return citations in the response** by reading `response["source_documents"]`, de-duplicating by `source`, and sending `{title, snippet}` to the frontend. This is the backend half of UI-3.
7. **Chunking:** 500/100 is small for agronomy prose and fragments tables. Try 800-1000 chars with 150 overlap, and measure retrieval quality on a fixed question set before/after. Do not over-tune; this is a measure-twice change.

### 4.3 Multimodal pipeline (disease photo): Gemini vs CNN vs hybrid

**Recommendation: Gemini Vision now, hybrid as the research narrative, custom CNN as future work. Do not train a CNN before July 15.** Confidence: high.

Reasoning. You do not have a clean, labeled, Burkina-field crop-disease dataset. Training on PlantVillage (lab images, foreign crops, clean backgrounds) and presenting it as field-ready is precisely the anti-pattern you listed. A model trained on PlantVillage collapses on real phone photos taken in a field. Gemini Vision, prompted carefully and wrapped in hard disclaimers, gives a usable screening hint today with zero training time. The wrapper is what makes it honest and what makes it research-credible:

- Prompt Gemini to return: likely issue(s), a confidence word, what to inspect next, and an explicit "this is a preliminary screening, not a diagnosis; confirm with an extension agent" line, in French, scoped to your crops.
- Force the model to say "I cannot tell from this image" when the photo is blurry or out of scope. Test this path explicitly.
- For the PhD framing, this is your honest-limitations centerpiece: "v1 uses a general vision-language model for screening because no field-validated Burkinabé dataset exists; CROPRADAR's contribution would be to build that dataset and a domain CNN/hybrid." That is a research gap you can articulate from experience, which is far stronger than a fragile CNN demo.

If you have spare evenings, the only Colab work worth doing here is a small notebook that runs PlantVillage through a fine-tuned model to produce a confusion matrix and a written analysis of why it does not transfer to Sahel field photos. That negative result is more impressive to a reviewer than a 99% lab-accuracy number, because it shows you understand domain shift.

### 4.4 Yield + fertilizer modules: honest MVP scope

**Fertilizer: build it, as a deterministic rule tool, not an ML model.** Burkina fertilizer guidance for cereals exists in your corpus and in published FAO/INERA recommendations (typical NPK and urea split-dose guidance per crop). Encode a small lookup: crop x zone x (optional soil note) returns a recommended basal NPK dose, urea top-dressing timing, and a "confirm locally" disclaimer. This is honest (it is published agronomy, not a guess), it is genuinely useful to an agent, and it demonstrates "structured agronomic data + reasoning" cheaply. Cite the source document in the output. Definition of done: an agent asks "engrais pour sorgho" and gets a specific dose with a source and a disclaimer.

**Yield: scope it as an explicit, labeled estimate or defer it.** Do not present a yield model trained on foreign data as field-ready. Two honest options: (a) a transparent rule/lookup giving a typical yield range per crop per zone from your corpus, clearly labeled as a reference range, not a prediction; or (b) a Colab notebook that trains a yield regression on a real public Burkina/Sahel dataset (FAO crop statistics, or a remote-sensing + yield dataset that fits your geomatics background) and reports honest cross-validated error, kept as a research artifact rather than wired into the live app. Given your geomatics MSc, option (b) is your strongest PhD-alignment play because it connects to remote sensing. But it is research, not product; keep it in a notebook with an honest metrics table.

### 4.5 File/folder restructuring

Keep it light. Concrete moves:

- Delete dead files: `chat1.py`, `chat2.py`, `static/css/broken.css`, `static/js/broken.js`. Finish or delete `organize.sh`.
- Re-save `requirements.txt` as UTF-8 (it is currently UTF-16; verify with `file requirements.txt` showing ASCII/UTF-8 text afterwards).
- Fix `DATA_FOLDER` to `os.path.join("Data", "knowledge_base")` and point ingestion at `Data/` recursively.
- Add a `core/` module per tool as you build them: `core/disease.py`, `core/fertilizer.py`, `core/router.py`. Keep `app.py` thin (routing only).
- Add a real `tests/` (right now it is an empty `__init__.py`): a couple of pytest tests that assert ingestion finds N PDFs and that a known question returns a non-empty grounded answer. Tests are cheap PhD-credibility signal.
- Add `manifest.json` + a minimal `service-worker.js` for the PWA story.

---

## 5. Prioritized backlog

Ordered P0 → P3. Farmer value and PhD value are 1-5. Effort S = under 60 min, M = one 60-90 min session, L = two-plus sessions. Every task has a non-expert-verifiable definition of done embedded in its prompt.

| Priority | Task | Farmer | PhD | Effort | Cursor session prompt (copy-paste ready) |
|---|---|---|---|---|---|
| **P0** | Fix avatar + favicon paths | 3 | 1 | S | "In `static/js/index.js` replace `/static/robo.png` with `/static/images/bot_avatar.png` and `/static/user.png` with `/static/images/user_avatar.png`. In `templates/index.html` change the favicon and header logo `href`/`src` from `static/logo.png` to `static/images/logo.png`. DoD: load the page, bot and user avatars and the browser-tab icon all display, no broken-image icons." |
| **P0** | Fix ignored similarity threshold | 5 | 4 | S | "In `core/llm_chain.py`, change the retriever to `db.as_retriever(search_type='similarity_score_threshold', search_kwargs={'score_threshold': SIMILARITY_THRESHOLD, 'k': 4})`. DoD: ask an off-topic question (e.g. 'how do I fix a car engine?') and confirm DakiKobo returns the 'Hors base / Don't know' fallback instead of a confident answer." |
| **P0** | Fix TTS truncation | 5 | 1 | S | "In `config.py` raise `TTS_MAX_CHARS` to 700. In `core/rag_pipeline.py` `text_to_speech_to_static`, if text exceeds the limit, split into sentence-sized gTTS segments and concatenate, or at minimum stop cutting mid-word by truncating at the last space before the limit. DoD: ask a question whose answer is ~90 words, enable audio, and confirm the spoken audio reaches the end of the answer." |
| **P0** | Re-save requirements.txt as UTF-8 | 1 | 3 | S | "Re-encode `requirements.txt` from UTF-16 to UTF-8 without BOM, preserving the same package list. DoD: `file requirements.txt` reports ASCII/UTF-8 text, and `pip install -r requirements.txt` runs in a fresh venv without an encoding error." |
| **P0** | Fix DATA_FOLDER + recurse subfolders | 4 | 3 | S | "In `config.py` set `DATA_FOLDER = os.path.join('Data', 'knowledge_base')`. In `core/rag_pipeline.py` `load_pdfs_from_folder`, use a recursive glob (`**/*.pdf`, `recursive=True`) or `os.walk` so subfolders are included, and update `app.py` to ingest from `Data/`. DoD: on startup the console prints a PDF count of 14+ instead of 8, including the KIT book and the New Folder PDFs." |
| **P1** | Add metadata at ingestion | 4 | 5 | M | "In `core/rag_pipeline.py`, change ingestion to build LangChain `Document` objects (or pass a parallel `metadatas` list) so every chunk carries `source` = the PDF filename. DoD: after restart, programmatically retrieve a chunk and confirm its metadata contains the originating filename." |
| **P1** | Return + render citations | 5 | 5 | M | "Backend: in `app.py` `/ask`, read `response['source_documents']`, de-duplicate by `source` metadata, and return a `sources` list of `{title}` plus a `confidence` field derived from retrieval score. Frontend: render source chips and a confidence badge under each bot answer (see UI-3). DoD: a tester sees document names and a coloured 'Fiable/À vérifier' badge under every answer." |
| **P1** | Persistent Chroma | 3 | 4 | M | "In `core/rag_pipeline.py`, use `Chroma(persist_directory='chroma_db', ...)`. On startup, load the existing store if `chroma_db/` exists; only ingest+embed when it is missing or a `REINDEX=1` env var is set. DoD: start the server twice; the second start is visibly faster and prints 'loaded existing index' instead of re-embedding." |
| **P1** | Mobile-first responsive layout | 5 | 2 | M | Use prompt **UI-1** above. |
| **P1** | Quick-action chips + active mic state | 5 | 2 | M | Use prompt **UI-2** above. |
| **P2** | Multilingual embeddings upgrade | 4 | 4 | M | "In `config.py` set `EMBEDDING_MODEL = 'paraphrase-multilingual-mpnet-base-v2'`. Re-index the persistent Chroma store (it must be rebuilt because the dimension changes). DoD: ask the same French question before and after; retrieval returns more on-topic chunks (eyeball the source chips)." |
| **P2** | Deterministic fertilizer tool | 5 | 5 | M | "Create `core/fertilizer.py` with a lookup keyed by crop (sorgho, mil, maïs, niébé, arachide) and zone (Sahel, Soudano-sahélien) returning basal NPK dose, urea top-dress timing, and a French disclaimer, sourced from the corpus/FAO. Add a router branch in `app.py` so fertilizer questions hit this tool. DoD: ask 'dose d'engrais pour le sorgho' and get a specific dose with a source name and a 'confirmez avec votre agent' disclaimer." |
| **P2** | Disease screening via Gemini Vision | 5 | 5 | L | "Add `core/disease.py` calling the Gemini Vision API on an uploaded leaf photo, prompted in French to return likely issue, confidence word, next inspection step, and a mandatory 'screening, not diagnosis' disclaimer, scoped to Burkina cereal/legume crops; force an 'I cannot tell' response on blurry/out-of-scope images. Add an image-upload control (see UI components) and an `/ask_image` route. DoD: upload a leaf photo and a blurry/random photo; the first returns a hedged screening with disclaimer, the second returns 'I cannot tell, retake the photo.'" |
| **P2** | Feedback capture (Utile ?) | 3 | 4 | S | "Add 👍/👎 'Utile ?' buttons under each answer that POST `{question, answer, sources, vote}` to a `/feedback` route appending a row to a local CSV/JSONL. DoD: click 👎 on an answer and confirm a new line appears in `feedback.jsonl`." |
| **P3** | PWA shell (installable, offline shell) | 3 | 3 | M | "Add `manifest.json` and a minimal `service-worker.js` that caches the app shell (HTML/CSS/JS/icons). Register the SW in `index.html`. DoD: in Chrome, the page shows an 'Install app' prompt and the shell loads with the network throttled to offline (answers still need network, but the UI opens)." |
| **P3** | Cleanup + first tests | 2 | 4 | S | "Delete `chat1.py`, `chat2.py`, `static/css/broken.css`, `static/js/broken.js`. Add `tests/test_ingest.py` asserting ingestion finds >=14 PDFs and `tests/test_qa.py` asserting a known crop question returns a non-empty answer with at least one source. DoD: `pytest` runs green." |

---

## 6. Colab Pro notebook plan

Colab is for GPU work that genuinely needs a GPU and produces a research artifact. Three notebooks, in priority order.

**Notebook 1: Embedding/retrieval evaluation (highest value, modest GPU).**
Objective: prove your RAG retrieves the right chunks and justify the multilingual upgrade with numbers. Dataset: your own corpus plus a hand-written set of ~25 French agronomy questions with the document you expect each to hit. Metrics: retrieval hit-rate@k and MRR for `all-MiniLM` vs `paraphrase-multilingual-mpnet` vs `bge-m3`. Plug-back: pick the winning model, set it in `config.py`, re-index. This notebook becomes a figure in your research statement ("retrieval quality across embedding models on a Burkinabé agronomy corpus").

**Notebook 2: Disease-model domain-shift study (honest negative result).**
Objective: demonstrate, with evidence, why a PlantVillage-trained CNN does not transfer to Sahel field photos, justifying your Gemini-now/CNN-later decision. Dataset: PlantVillage (public) for training; a small set of real field/phone leaf photos (even 30-50 you collect or source) for testing. Metrics: train/val accuracy on PlantVillage vs accuracy on field photos, plus a confusion matrix. Plug-back: nothing goes into the live app; the result goes into your research statement as articulated future work. A documented domain-shift failure is a stronger PhD signal than a lab-accuracy brag.

**Notebook 3: Yield regression baseline (geomatics-aligned, optional).**
Objective: a transparent yield baseline that connects to your remote-sensing background. Dataset: a public Burkina/Sahel crop-yield dataset, ideally one you can pair with NDVI/climate features (FAO statistics, or a remote-sensing yield dataset). Metrics: cross-validated MAE/RMSE with an explicit statement of limitations. Plug-back: keep as a research artifact; optionally expose a clearly-labeled "reference estimate" in the app only if the error is honest enough to disclose. This is your bridge sentence into CROPRADAR's yield-prediction focus.

**What NOT to train in Colab (waste of time before July 15):** a production disease CNN you intend to ship; an LLM fine-tune (Groq's llama-3.3-70b already outperforms anything you could fine-tune in your window); embedding fine-tuning; any model whose only purpose is to look impressive in the demo. GPU time spent on a model you will not honestly deploy is time stolen from the product and the writing.

---

## 7. PhD application materials

**README (rewrite it; the current one predates this work).** Structure: one-line value proposition; a screenshot/GIF of the mobile UI with a source chip and confidence badge visible; "What it does today" (honest, working features only); "Architecture" (a small diagram: query → router → RAG/tools → grounded answer + citations + TTS); "Knowledge base" (the corpus list with provenance); "Honest limitations" (this is the section reviewers respect); "Roadmap → CROPRADAR" (how this prototype maps onto the PhD's four focus areas). Make the README readable on GitHub mobile.

**Demo video, scene by scene (target 3 minutes):**
1. (0:00-0:20) Phone screen. State the problem in one sentence: smallholder cereal farmers in Burkina lack fast, trustworthy, local agronomic advice.
2. (0:20-0:50) Type or speak a French question about millet sowing in the Sahel. Show the grounded answer appear with a source chip and a "Fiable" badge. Tap the chip to reveal the source snippet. This is your trust money-shot.
3. (0:50-1:20) Tap 🔊, let the audio play to the end (proves the TTS fix), and say one line about low-literacy access.
4. (1:20-1:50) Ask a fertilizer question; show the deterministic dose with its disclaimer. Emphasize "indicative, confirm locally."
5. (1:50-2:20) Upload a leaf photo; show Gemini's hedged screening with the "not a diagnosis" disclaimer. Then upload a blurry photo and show it correctly refusing. The refusal is the point.
6. (2:20-2:50) Ask an off-topic question; show the honest "Hors base" fallback. Demonstrating that it knows what it does not know is the single most credible 10 seconds in the video.
7. (2:50-3:00) One sentence connecting DakiKobo to CROPRADAR: this prototype is the product seed; the PhD builds the field-validated multimodal models it currently lacks.

**Research statement angle.** Lead with the gap, not the demo: field-validated multimodal precision-ag tools for Sahelian cereal systems barely exist, and the datasets to build them are missing. Position DakiKobo as evidence you can build the LLM + RAG + tool-routing + multimodal scaffolding end to end, and position CROPRADAR's contribution as the missing pieces you have personally hit (a Burkina field disease dataset, a transfer-honest yield model, fertilizer recommendation grounded in local agronomy). Your geomatics MSc is the differentiator: tie yield prediction to remote sensing explicitly.

**Honest limitations to acknowledge (state them, do not hide them).** Disease screening uses a general VLM, not a field-validated model. Knowledge base is small (~14 PDFs) and French-only. No local-language generation yet. Yield is a reference range, not a validated prediction. In-app evaluation is qualitative; quantitative retrieval metrics live in a notebook. Reviewers trust applicants who name their limitations precisely far more than those who oversell.

---

## 8. Risks & realism check

**What fails if you try to do everything:** you will sink the window into the custom disease CNN, produce a fragile model, and arrive at July 15 with no citations, a broken mobile layout, and a demo that contradicts your own "no foreign-data models" principle. The second failure mode is a React migration that eats a week and changes nothing a reviewer values. The third is local-language generation, which is a research project, not a feature.

**Minimum viable credible demo by July 15 (the bar to clear):**
- The P0 bug fixes done (threshold, TTS, paths, encoding, ingestion). Non-negotiable; they are hours, not days, and each removes an embarrassment.
- Citations + confidence badge + disclaimer rendering live. This is the trust story and it is mostly wiring you already have.
- Mobile-first layout that looks intentional on a phone.
- Gemini Vision disease screening with hard disclaimers and a working refusal path.
- A deterministic fertilizer tool with sources.
- Notebook 1 (retrieval eval) and Notebook 2 (domain-shift study) done as research artifacts.
- A rewritten README and a 3-minute demo video.

That set is achievable by one developer vibe-coding in 3 weeks and it tells a coherent, honest story for both goals. Everything else is upside.

---

## 9. Suggested 3-week calendar

Product first, research second. Each day is one or two 60-90 min sessions.

**Week 1: Stop the bleeding, build trust (product).**
- Day 1: P0 path fixes, favicon, threshold fix, TTS fix. (Two short sessions.) Commit each.
- Day 2: P0 requirements.txt re-encode + DATA_FOLDER fix + recursive ingestion. Confirm 14+ PDFs load.
- Day 3: Metadata at ingestion + persistent Chroma. Verify faster restart.
- Day 4: Backend citations + confidence field in `/ask`.
- Day 5: Frontend source chips + confidence badge + disclaimer rendering (UI-3). End of week: trustworthy, grounded, cited answers.
- Weekend (optional): start Notebook 1 (retrieval eval) on Colab.

**Week 2: Make it usable and multimodal (product + first research).**
- Day 6: Mobile-first layout (UI-1).
- Day 7: Quick-action chips + active mic state (UI-2).
- Day 8: Multilingual embeddings upgrade + re-index; eyeball improvement.
- Day 9: Deterministic fertilizer tool + router branch.
- Day 10: Gemini Vision disease screening backend + refusal path. Finish Notebook 1.
- Weekend: image-upload UI + thumbnail; wire disease screen end to end.

**Week 3: Polish, prove, package (research + submission).**
- Day 11: Feedback capture; cleanup dead files; first pytest tests.
- Day 12: Notebook 2 (domain-shift study), produce the confusion matrix and write-up.
- Day 13: Rewrite README with screenshots and honest-limitations section.
- Day 14: Record and edit the 3-minute demo video (script in section 7).
- Day 15: Research statement draft tying DakiKobo → CROPRADAR; link the notebooks as artifacts.
- Days 16-18: Buffer for overruns, dry-run the demo on a real phone on throttled network, proofread the application. Submit before July 15, not on it.
- (Notebook 3 / yield only if Days 16-18 are genuinely free.)

---

## 10. One thing you would cut

**Cut the custom disease CNN for v1.** You are overestimating its value and underestimating its cost. Without a field-validated Burkina dataset it will either overfit lab images or underperform on phone photos, and shipping it would violate your own "no foreign-data models presented as field-ready" rule. It is the highest-risk, lowest-payoff item before July 15.

**Do instead:** ship Gemini Vision screening wrapped in hard "not a diagnosis" disclaimers and a working refusal path for bad images, and turn the CNN into your strongest research artifact via Notebook 2's honest domain-shift study. You convert a fragile demo liability into a credible research argument, and you free roughly two sessions for citations and mobile polish, which are what actually move both goals.

---

## Bonus

**Alternative name + subtitle:** **DakiKobo, Conseil agricole pour le Sahel** ("Farm advice for the Sahel"). Keeps your existing brand and adds an instantly legible subtitle for both audiences.

**Landing-page sentence (works for farmers and PhD reviewers):**
"DakiKobo gives Burkinabè cereal farmers fast, voice-first agronomic advice grounded in local sources and honest about what it does not yet know, and serves as a research prototype for multimodal precision agriculture in the Sahel."

---

*Prepared by Claude (Opus). Every code-level claim in section 0 and section 4 was verified against the current source tree, not assumed. Where I recommend deferring work (CNN, React, local-language generation), the reasoning is timeline and honesty, not capability.*
