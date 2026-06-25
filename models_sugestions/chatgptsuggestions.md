# DakiKobo — ChatGPT Suggestions for Cursor Execution

**Repository:** https://github.com/MORAWA-dev/dakikobo  
**Date:** 2026-06-24  
**Context:** Local Flask + RAG agricultural advisor for Burkina Faso, synced with GitHub.  
**Primary deadline:** UM6P CROPRADAR PhD application, July 15, 2026.  

---

## How to use this file in Cursor

Use this file as the execution reference. Do not ask Cursor to implement everything at once.

Recommended Cursor flow:

1. Open one task from the backlog.
2. Paste the task prompt into Cursor Agent.
3. Let Cursor edit only the named files.
4. Run the listed verification test.
5. Commit.
6. Move to the next task.

Suggested branch naming:

```bash
git checkout -b chore/p0-rag-persistence
```

Suggested commit style:

```bash
git add .
git commit -m "Add persistent Chroma vector store"
git push origin chore/p0-rag-persistence
```

Core rule: one 60–90 minute session should produce one farmer-visible improvement or one PhD-visible proof point.

---

## 1. Executive summary

- The next 3 weeks should focus on trust, mobile use, citations, and one working multimodal feature.
- Do not rewrite the app. Keep Flask, Jinja2, jQuery, Groq, LangChain, and Chroma for now.
- Highest-priority fixes: broken static paths, recursive PDF ingestion, persistent Chroma, source citations, mobile-first UI.
- Disease screening should start with Gemini Vision plus safety language. A custom CNN belongs in Colab as evidence, not as the main product path before July 15.
- Cut Firebase, full mobile app, local languages, offline mode, and complex agent frameworks until after the PhD application.

---

## 2. Current project diagnosis

### What works

- Flask app serves the chat UI.
- `/ask` route accepts text input.
- Groq LLM is already wired through LangChain.
- RAG loads PDF text into Chroma.
- gTTS creates French MP3 audio responses.
- Browser speech-to-text exists for French input.
- Current app is simple enough to improve quickly.

### Main weaknesses

| Area | Problem | Why it matters |
|---|---|---|
| UI | Fixed desktop-style chat card | Farmers and extension agents will test on phones |
| Static files | Wrong avatar and favicon paths | Demo looks broken |
| RAG | Chroma rebuilt on every server start | Slow and weak demo reliability |
| RAG | Only direct PDFs loaded | 7+ documents remain unused |
| RAG | No source display in UI | Trust is weak |
| RAG | No metadata per chunk | Hard to filter by crop, zone, source |
| Embeddings | `all-MiniLM-L6-v2` weak for French | Retrieval may miss French agronomic content |
| Product | No image upload | Missing CROPRADAR multimodal signal |
| Product | No fertilizer tool | Misses a high-value farmer question |
| Research | No metrics | PhD reviewers need evidence, not only demo claims |

### Repo-specific notes

- `chat1.py` and `chat2.py` are deprecated. Do not add code there.
- `core/rag_pipeline.py` and `core/llm_chain.py` are the right places for backend logic.
- `app.py` should stay small: routes, app init, request handling.
- `config.py` should hold tunable settings and env-based secrets.
- Keep generated audio in `static/audio/`.
- Keep knowledge documents under `Data/knowledge_base/` or normalize the repo to `data/knowledge_base/`. Pick one case and use it everywhere.

---

## 3. Product vision

### Primary v1 user

The primary v1 user is not every farmer directly.

The realistic v1 user is:

- extension agent
- agronomy student
- cooperative leader
- NGO field worker
- technically literate farmer

These people can validate advice before it reaches farmers with low literacy or limited agronomic training.

### Three jobs DakiKobo should do better than Google or a neighbor

#### Job 1 — Burkina-specific agronomic Q&A

Example questions:

- `Quand planter le mil dans la zone du Sahel au Burkina Faso ?`
- `Quelles variétés de maïs pour la savane soudanienne ?`
- `Comment gérer le niébé pendant une saison sèche ?`

Expected answer style:

- short
- in French
- crop-specific
- zone-aware
- with source chips
- with uncertainty when needed

#### Job 2 — Farmer-safe fertilizer guidance

Example:

- `Quelle quantité d'engrais pour le sorgho au stade tallage ?`

Expected answer style:

- identify crop and growth stage
- give ranges, not false precision
- explain timing
- warn when soil test data is missing
- cite source documents when available

#### Job 3 — First-pass disease triage from photo

Example:

- farmer uploads a maize or niébé leaf photo

Expected answer style:

- possible issue, not final diagnosis
- confidence label: high, medium, low
- 2–3 practical next steps
- clear warning against blind pesticide spraying
- advise extension-agent confirmation

### What not to build before July 15

Do not build these yet:

- Firebase backend
- user accounts
- Flutter app
- Android app
- offline inference
- Mooré, Dioula, Fulfuldé production support
- complex LangGraph setup
- full custom disease-model serving
- real yield prediction claims without local data

They are good later. They are bad now.

---

## 4. UI/UX redesign proposal

### Direction

Move from a desktop chat card to a mobile-first field assistant.

Current direction:

- fixed width
- centered desktop box
- dated gradient
- no source display
- no image upload
- no visible recording state

Target direction:

- full-height mobile web app
- large touch targets
- simple French labels
- source chips
- confidence badges
- camera upload
- quick-action questions
- voice-first interaction

### Layout

Use this structure:

```text
+----------------------------------+
| DakiKobo 🌾                      |
| Conseiller agricole Burkina      |
| [Audio: ON/OFF]                  |
+----------------------------------+
| [🌾 Planter le mil]              |
| [🌱 Engrais sorgho]              |
| [🫘 Maladies du niébé]           |
| [🌧️ Saison des pluies]           |
+----------------------------------+
|                                  |
| BOT: Bonjour. Posez une question |
|      ou ajoutez une photo.       |
|      [Source: Manuel]            |
|                                  |
| USER: Quand planter le mil ?     |
|                                  |
| BOT: Réponse courte...           |
|      Confiance: Moyenne          |
|      [Source: FAO] [Source: CSA] |
|      [👍 Utile] [👎 Pas utile]    |
|                                  |
+----------------------------------+
| [📷] [Message...] [🎤] [➤]       |
+----------------------------------+
```

### Color and brand direction

Use Burkina agritech colors, not a generic neon tech palette.

| Token | Color | Use |
|---|---|---|
| `--green-primary` | `#4F7C3A` | header, send button |
| `--green-soft` | `#DDEBD1` | bot message tint |
| `--earth` | `#8A5A32` | accents |
| `--sun` | `#C98A2E` | warning and CTA highlights |
| `--sand` | `#F8F1E4` | page background |
| `--ink` | `#243224` | text |
| `--danger` | `#B23B3B` | error and low confidence |

Typography:

- Use system fonts or Inter/Noto Sans.
- Body: 16px minimum.
- Buttons: 44px minimum height.
- Avoid tiny labels.

### Components to add

#### 1. Quick-action chips

Four default chips:

- `🌾 Planter le mil`
- `🌱 Engrais sorgho`
- `🫘 Maladies du niébé`
- `🌧️ S'adapter aux pluies`

Each chip submits a predefined question through the same AJAX flow.

#### 2. Source chips

Show below bot messages:

```text
Sources: [farmer_training_manual.pdf] [fao_publication_i3760e.pdf]
```

#### 3. Confidence badges

Required for:

- disease screening
- fertilizer advice
- yield estimates

Badge text:

- `Confiance élevée`
- `Confiance moyenne`
- `Confiance faible`

#### 4. Voice state

When listening:

```text
🎤 En écoute...
```

Add pulsing class:

```css
.is-recording { animation: pulse 1s infinite; }
```

#### 5. Image upload

Add camera/file input:

```html
<input id="imageInput" type="file" accept="image/*" capture="environment" hidden>
<button type="button" id="imageUploadBtn">📷</button>
```

#### 6. Feedback buttons

Add after bot response:

```text
[👍 Utile] [👎 Pas utile]
```

Start by logging to CSV. Do not add Firebase yet.

### Keep Flask + jQuery?

Yes.

Reason:

- deadline is short
- current stack works
- UI problems can be solved with HTML/CSS/jQuery
- adding React creates new build tooling and failure modes

Frontend migration can wait.

### UI Cursor prompts

#### UI Prompt 1 — Mobile-first layout

```text
You are editing DakiKobo. Keep Flask, Jinja2, and jQuery. Update templates/index.html and static/css/style.css to convert the current fixed-width desktop chat card into a mobile-first full-height chat interface. Requirements: 100dvh layout, max-width 760px on large screens, no fixed 470px box, large 44px touch buttons, readable French labels, Burkina agritech palette, and responsive behavior down to 360px width. Do not change backend routes.
```

Definition of done:

- Open `http://127.0.0.1:5000`.
- Resize browser to phone width.
- Chat fills the screen.
- Input stays visible at bottom.
- Header, messages, and footer do not overlap.

#### UI Prompt 2 — Quick actions and voice state

```text
Add quick-action chips above the message panel in templates/index.html and static/js/index.js. Chips: "🌾 Planter le mil", "🌱 Engrais sorgho", "🫘 Maladies du niébé", "🌧️ Saison des pluies". Each chip should submit a predefined French question through the existing AJAX chat function. Also add a visual recording state to the microphone button: while webkitSpeechRecognition is active, the mic button should show "En écoute" or a pulsing style, and return to normal when recognition ends.
```

Definition of done:

- Clicking `Planter le mil` sends a farmer question.
- Mic button visibly changes while listening.
- Existing text chat still works.

#### UI Prompt 3 — Source chips, confidence badges, feedback buttons

```text
Prepare the frontend to display richer bot responses. Update static/js/index.js so bot messages can render optional fields from the backend: sources array, confidence string, and response_type string. Render source chips below the answer, a confidence badge when present, and thumbs up/down buttons after each bot response. If the backend does not provide these fields, keep current behavior unchanged.
```

Definition of done:

- Current `/ask` response still renders normally.
- A mock JSON response with `sources` and `confidence` renders chips and badge.
- Thumbs up/down buttons appear after bot answers.

---

## 5. Technical architecture improvements

### 5.1 Recommended target architecture before July 15

Keep it simple:

```text
Flask UI
  ↓
POST /ask or POST /diagnose
  ↓
Simple router
  ↓
Tools:
  - rag_advisor
  - diagnose_image
  - recommend_fertilizer
  - estimate_yield
  ↓
Farmer-safe response schema
  ↓
JSON returned to frontend
```

### 5.2 Response schema

Use one common response shape for all tools.

```json
{
  "answer": "short French response",
  "audio_url": "/static/audio/file.mp3",
  "response_type": "rag|disease|fertilizer|yield|identity|error",
  "confidence": "high|medium|low|null",
  "sources": [
    {
      "title": "farmer_training_manual.pdf",
      "page": null,
      "snippet": "optional short snippet"
    }
  ],
  "warnings": [
    "Vérifiez avec un agent agricole si la situation est grave."
  ]
}
```

Do not overcomplicate the schema. The frontend should handle missing fields.

### 5.3 Agent/router design

Do not start with LangGraph.

Create:

```text
core/agents/router.py
core/agents/rag_agent.py
core/agents/disease_agent.py
core/agents/fertilizer_agent.py
core/agents/yield_agent.py
```

Router logic:

```python
def route_request(message: str, image_file=None) -> dict:
    if image_file is not None:
        return diagnose_image(image_file, message)

    text = message.lower()

    if any(word in text for word in ["engrais", "urée", "npk", "fertilisation", "fumure"]):
        return recommend_fertilizer(message)

    if any(word in text for word in ["rendement", "production", "récolte prévue", "estimer"]):
        return estimate_yield(message)

    return rag_advisor(message)
```

Fallbacks:

- If Gemini fails, return safe image-analysis fallback.
- If RAG has no source documents, say information is not yet available.
- If fertilizer input is incomplete, ask for crop and stage.
- If yield input is incomplete, ask for zone, crop, rainfall/planting date.

### 5.4 RAG improvements

#### Current problem

PDFs are converted to plain strings. Chunks have no source metadata. Chroma is in memory. Retrieval can return text but the UI cannot show citations.

#### Target

Use LangChain `Document` objects with metadata.

Example metadata:

```python
{
    "source": "farmer_training_manual.pdf",
    "path": "Data/knowledge_base/farmer_training_manual.pdf",
    "doc_type": "manual",
    "crop": "mixed",
    "zone": "general",
    "language": "fr"
}
```

#### Recursive loading

Use:

```python
pdf_files = glob.glob(os.path.join(folder_path, "**", "*.pdf"), recursive=True)
```

#### Persistent Chroma

Add config:

```python
VECTORSTORE_DIR = os.getenv("VECTORSTORE_DIR", "vectorstore/chroma")
REBUILD_VECTORSTORE = os.getenv("REBUILD_VECTORSTORE", "false").lower() == "true"
```

Use:

```python
Chroma.from_documents(
    documents=chunks,
    embedding=embedding_fn,
    persist_directory=VECTORSTORE_DIR,
    collection_name="dakikobo_knowledge"
)
```

On startup:

- If vector store exists and rebuild is false, load it.
- If missing or rebuild is true, rebuild.

#### Citations

`RetrievalQA` already has `return_source_documents=True`. Update `/ask` so it extracts `response["source_documents"]` and returns source names to the frontend.

### 5.5 Embedding upgrade

Current:

```python
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
```

Recommended after P0 fixes:

```python
EMBEDDING_MODEL = "BAAI/bge-m3"
```

Reason:

- better multilingual retrieval
- stronger French handling
- relevant for mixed French and technical agronomic text

Risk:

- heavier local model
- slower first startup
- may need more memory

Do it after persistent vector store and citations.

### 5.6 Disease photo pipeline

Recommended MVP:

```text
Image upload
  ↓
Gemini Vision prompt
  ↓
Candidate disease or symptom description
  ↓
RAG lookup for crop/disease context
  ↓
Farmer-safe answer
```

Gemini response should never be shown raw.

Use a safety wrapper:

```text
Résultat possible, pas un diagnostic certain.
Confiance: faible/moyenne/élevée.
Avant traitement chimique, vérifiez avec un agent agricole.
```

Return:

```json
{
  "response_type": "disease",
  "confidence": "medium",
  "answer": "La photo montre peut-être ...",
  "warnings": ["Ne pulvérisez pas sans confirmation."],
  "sources": []
}
```

Do not claim local field accuracy from PlantVillage.

### 5.7 Fertilizer MVP

Build a structured tool, not a free-form answer only.

Inputs:

```json
{
  "crop": "sorgho",
  "stage": "tallage",
  "zone": "Sahel",
  "soil_test": "unknown"
}
```

If inputs are missing, ask one short follow-up.

Output:

```text
Pour le sorgho au tallage, l'apport dépend du sol et de la pluie. Sans analyse de sol, utilisez une fourchette prudente tirée des documents disponibles. Appliquez après une pluie utile et évitez l'épandage avant sécheresse. Consultez un agent local si le champ est pauvre ou sableux.

Confiance: moyenne
Sources: [farmer_training_manual.pdf]
```

Do not give fake exact doses unless the source documents support them.

### 5.8 Yield MVP

Call it `estimate_yield`, not `predict_yield` in user-facing UI.

Input:

- crop
- zone
- sowing date
- rainfall condition
- field size
- variety if known

Output:

- estimate range
- confidence
- assumptions
- warning that it is not a guarantee

Best July version:

- simple rules or placeholder model
- one Colab notebook with public data
- no production claims

### 5.9 File and folder changes

Recommended incremental structure:

```text
core/
  agents/
    __init__.py
    router.py
    rag_agent.py
    disease_agent.py
    fertilizer_agent.py
    yield_agent.py
  retrieval/
    __init__.py
    loaders.py
    vectorstore.py
    citations.py
  vision/
    __init__.py
    gemini_client.py
  safety/
    __init__.py
    response_schema.py
    disclaimers.py
notebooks/
  01_disease_screening_colab.ipynb
  02_yield_estimation_colab.ipynb
  03_rag_evaluation.ipynb
tests/
  test_routes.py
  test_router.py
```

Do not move everything in one session. Add folders only when needed.

---

## 6. Prioritized backlog

### Priority scale

- **P0:** Must finish for credible demo.
- **P1:** Strongly recommended before July 15.
- **P2:** Useful if P0/P1 are stable.
- **P3:** Good later, not required for application.

### Backlog table

| Priority | Task | Farmer value | PhD value | Effort | Definition of done | Cursor session prompt |
|---|---:|---:|---:|---|---|---|
| P0 | Fix static image paths | 2 | 1 | S | Avatars and favicon load without 404s. | `Fix DakiKobo static asset paths. In static/js/index.js replace broken avatar paths /static/user.png and /static/robo.png with url paths pointing to /static/images/user_avatar.png and /static/images/bot_avatar.png. In templates/index.html update favicon and logo references to static/images/logo.png. Do not change backend behavior.` |
| P0 | Normalize `Data` vs `data` path | 4 | 3 | S | App loads PDFs on case-sensitive and case-insensitive systems. | `Audit config.py, app.py, organize.sh, and README for Data/data path mismatch. Pick one canonical path, preferably Data/knowledge_base if that is the actual repo folder. Update config and docs so local startup finds PDFs reliably.` |
| P0 | Recursive PDF ingestion | 5 | 4 | S | App finds PDFs in subfolders and prints total count. | `Update core/rag_pipeline.py so load_pdfs_from_folder recursively loads all PDFs under DATA_FOLDER using glob **/*.pdf. Print each loaded filename and return content with source metadata support if possible. Keep function compatibility with app.py.` |
| P0 | Persistent ChromaDB | 5 | 5 | M | Restarting Flask does not rebuild vectors unless REBUILD_VECTORSTORE=true. | `Add persistent ChromaDB support. Add VECTORSTORE_DIR and REBUILD_VECTORSTORE to config.py. Update initialize_vector_store in core/rag_pipeline.py so it loads an existing Chroma collection when present and rebuilds only when needed. Keep current app.py interface working.` |
| P0 | Source citations in API | 5 | 5 | M | `/ask` returns `sources` array and UI can render it. | `Update app.py /ask route to extract source_documents from the RetrievalQA response and return a JSON field named sources. Each source should include title, path if available, and short snippet. Do not break audio_url or answer.` |
| P0 | Source chips in frontend | 5 | 4 | M | Bot messages show source chips below answer. | `Update static/js/index.js and static/css/style.css to render optional sources from the /ask JSON response as small source chips below bot answers. If sources is missing or empty, keep current display unchanged.` |
| P0 | Mobile-first UI | 5 | 4 | M | Works on 360px phone screen, no horizontal scroll. | `Redesign templates/index.html and static/css/style.css for mobile-first full-screen chat. Keep Flask and jQuery. Remove fixed 470px width and 650px height. Use 100dvh, sticky input area, large buttons, readable font sizes, and Burkina agritech colors.` |
| P0 | Update README | 2 | 5 | M | README matches current stack and demo goals. | `Rewrite README.md to match the current DakiKobo app: Flask 3, Groq llama-3.3-70b-versatile, LangChain, Chroma, French TTS, Burkina Faso crops, current file structure, .env usage, and PhD-oriented roadmap. Remove old instruction saying to edit chat2.py with API key.` |
| P1 | Quick-action farmer questions | 4 | 2 | S | Four chips send real French questions. | `Add quick-action chips for millet planting, sorghum fertilizer, niébé diseases, and rainy-season adaptation. Clicking a chip submits a predefined French question through the existing chat AJAX path.` |
| P1 | Voice recording state | 4 | 2 | S | Mic visibly shows listening state. | `Improve the webkitSpeechRecognition UX in static/js/index.js. Add CSS class is-recording while listening, change mic button label or icon, and remove the state when recognition ends or errors.` |
| P1 | Feedback logging | 3 | 3 | M | Clicking feedback stores timestamp, question hash/text, answer, rating. | `Add thumbs-up/down feedback buttons after each bot answer. Create POST /feedback in app.py that appends feedback to data/feedback.csv. Keep it simple, no database. Return JSON success.` |
| P1 | Farmer-safe response schema | 5 | 4 | M | All routes can return answer, confidence, sources, warnings. | `Create a simple response schema helper in core/safety/response_schema.py. It should build dictionaries with answer, audio_url, response_type, confidence, sources, and warnings. Update app.py /ask to use it without changing frontend behavior.` |
| P1 | Gemini disease route | 5 | 5 | M | User uploads image and gets cautious disease triage. | `Add a POST /diagnose route that accepts an uploaded crop image and optional message. Use GEMINI_API_KEY from .env. Send the image to Gemini Vision with a farmer-safe prompt. Return possible issue, confidence, next steps, and warning that this is not a confirmed diagnosis. Do not remove existing /ask.` |
| P1 | Image upload UI | 5 | 5 | M | Phone camera upload works. | `Add image upload support to the chat UI. Add a camera button using input type=file accept=image/* capture=environment. When an image is selected, show a preview and submit it to /diagnose with FormData. Render the disease response as a bot message with confidence and warning.` |
| P1 | Simple router | 4 | 5 | M | Fertilizer/yield/image/RAG route selection works. | `Create core/agents/router.py with route_request(message, image_file=None). Route image requests to diagnose_image, fertilizer keywords to recommend_fertilizer, yield keywords to estimate_yield, and everything else to rag_advisor. Keep implementation simple and testable.` |
| P2 | Fertilizer recommendation tool | 5 | 5 | M | Sorghum/tallage query returns structured, sourced, cautious answer. | `Create core/agents/fertilizer_agent.py. It should parse crop and stage from French text, retrieve relevant RAG context, and return a structured response with crop, stage, recommendation range only if source-supported, timing, confidence, warnings, and sources. If crop or stage is missing, ask one short follow-up question.` |
| P2 | BGE-M3 embedding upgrade | 4 | 5 | M | Retrieval quality improves on French test set or at least remains stable. | `Make the embedding model configurable through .env. Add support for BAAI/bge-m3 as EMBEDDING_MODEL. Update requirements if needed. Add a note that vectorstore must be rebuilt when the embedding model changes.` |
| P2 | RAG evaluation script | 3 | 5 | M | Script tests 10 known questions and prints retrieved sources. | `Create scripts/evaluate_rag.py. It should run 10 French Burkina crop questions through the retriever, print top-k source filenames and snippets, and save results to reports/rag_eval_results.md. Include questions for millet, sorghum, maize, niébé, groundnuts, and climate adaptation.` |
| P2 | Colab disease notebook | 3 | 5 | L | Notebook reports accuracy/F1/confusion matrix and limitations. | `Create notebooks/01_disease_screening_colab.ipynb outline or README plan. Use PlantVillage or a public dataset for prototype disease classification. Include train/val/test split, metrics, confusion matrix, and a section explaining why this is not yet Burkina field-ready.` |
| P2 | Exploratory yield estimator | 3 | 5 | L | App returns range + assumptions, not fake certainty. | `Create core/agents/yield_agent.py with an exploratory estimate_yield function. It should parse crop, zone, rainfall condition, and planting date if present. Return a cautious estimate format with assumptions, missing inputs, confidence low/medium, and warning that it is not a guarantee. Do not claim field validation.` |
| P3 | PWA shell | 2 | 2 | M | App can be installed, but offline advisor is not claimed. | `Add a basic manifest.json and service worker for app shell caching only. Do not cache AI answers. Add install-friendly icons if available. Make clear in README that offline AI is future work.` |
| P3 | Local-language prototype | 3 | 4 | L | One demo path translates a short answer, clearly labeled experimental. | `Add an experimental translation helper for Mooré/Dioula/Fulfuldé labels only. Do not present it as production translation. Keep French as the main language.` |
| P3 | Admin review page | 2 | 3 | M | Local page shows feedback CSV and top questions. | `Add a simple protected-by-env admin route /admin/feedback that reads data/feedback.csv and displays counts of useful/not useful and recent questions. Keep it local-demo friendly. No user accounts.` |

---

## 7. Recommended 60–90 minute Cursor sessions

### Session 1 — Make the repo demo clean

Goal: remove visible brokenness.

Tasks:

- fix avatars
- fix favicon/logo path
- normalize static image paths
- run the app

Prompt:

```text
Fix all visible broken static assets in DakiKobo. Update templates/index.html and static/js/index.js so favicon, logo, user avatar, and bot avatar all load from static/images. Keep the existing Flask routes and AJAX behavior. After changes, list exactly what files changed and how to verify in the browser.
```

Test:

```bash
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

Farmer-facing verification:

- UI has logo and avatars.
- No broken image icons.

---

### Session 2 — Ingest all PDFs recursively

Goal: no important local PDFs ignored.

Prompt:

```text
Update DakiKobo PDF ingestion to recursively load all PDFs from the configured DATA_FOLDER, including subfolders. Print the number of PDFs found and each source filename during startup. Keep current function names if possible. Add simple error handling so one bad PDF does not crash the app.
```

Test:

```bash
python app.py
```

Farmer-facing verification:

Ask:

```text
Quels documents connais-tu sur l'agriculture au Burkina Faso ?
```

Expected:

- App responds normally.
- Server logs show all expected PDFs.

---

### Session 3 — Persistent Chroma

Goal: stop re-indexing on every restart.

Prompt:

```text
Add persistent ChromaDB to DakiKobo. Add VECTORSTORE_DIR and REBUILD_VECTORSTORE to config.py. Update initialize_vector_store so it loads existing persisted Chroma when available and rebuilds only when REBUILD_VECTORSTORE=true or when no index exists. Keep the /ask route behavior unchanged. Include clear startup logs: loading existing vectorstore vs rebuilding.
```

Test:

```bash
python app.py
# stop server
python app.py
```

Expected:

- First run builds.
- Second run loads existing vector store.

---

### Session 4 — Citations in API and UI

Goal: make answers more trustworthy.

Prompt:

```text
DakiKobo already uses RetrievalQA with return_source_documents=True. Update app.py so /ask returns a sources array with filename/title and short snippet. Update static/js/index.js and style.css to render sources as chips below bot answers. Do not break answer or audio_url fields. If no source exists, do not show source chips.
```

Test questions:

```text
Quand planter le mil dans la zone du Sahel au Burkina Faso ?
Comment traiter les maladies du niébé ?
```

Expected:

- Answer appears.
- MP3 still works if voice reading enabled.
- Source chips appear when documents are retrieved.

---

### Session 5 — Mobile-first UI

Goal: make the demo credible on phone.

Prompt:

```text
Redesign the DakiKobo frontend for mobile-first use. Keep Flask/Jinja/jQuery. Replace fixed desktop card layout with a full-height responsive chat layout. Use large touch targets, sticky input bar, readable fonts, earthy Burkina agritech colors, and no horizontal scroll on 360px width. Preserve existing element IDs used by index.js unless you update JS safely.
```

Test:

- Chrome dev tools, iPhone/Android width.
- Send a question.
- Use voice toggle.

---

### Session 6 — Quick actions + mic state

Goal: make the app easy for non-technical testers.

Prompt:

```text
Add four quick-action chips above the chat in DakiKobo: Planter le mil, Engrais sorgho, Maladies du niébé, Saison des pluies. Each chip sends a French question through the same AJAX function used by the text input. Also add a visual recording state for the microphone button while speech recognition is active.
```

Test:

- Click each chip.
- Start voice input.
- Confirm mic state changes.

---

### Session 7 — Gemini disease screening route

Goal: add CROPRADAR multimodal signal safely.

Prompt:

```text
Add a farmer-safe image disease screening MVP to DakiKobo. Add GEMINI_API_KEY to config.py from environment. Create core/agents/disease_agent.py with diagnose_image(image_file, user_message=''). Add POST /diagnose in app.py accepting multipart image upload. The response must include possible issue, confidence, 3 practical next steps, and a clear warning that this is not a confirmed diagnosis. Do not recommend pesticide spraying unless source context supports it. Keep /ask unchanged.
```

Test:

- Upload a plant leaf photo.
- Response includes confidence and warning.

---

### Session 8 — Image upload UI

Goal: make disease route usable from phone.

Prompt:

```text
Add image upload to the DakiKobo chat UI. Add a camera button beside the text input. It should use input type=file accept=image/* capture=environment. Show a small preview after selection, submit FormData to POST /diagnose, show a typing indicator while processing, and render the response with confidence and warnings.
```

Test:

- Use phone or browser file picker.
- Image preview appears.
- `/diagnose` response appears in chat.

---

### Session 9 — Fertilizer tool

Goal: answer one high-value farmer decision type with caution.

Prompt:

```text
Create a structured fertilizer recommendation tool for DakiKobo. Add core/agents/fertilizer_agent.py. It should parse French crop and growth stage terms such as sorgho, mil, maïs, niébé, tallage, semis, floraison. It should retrieve relevant RAG context, return a short recommendation, confidence, warnings, and sources. If required details are missing, ask one short follow-up. Do not invent exact fertilizer quantities if no source supports them.
```

Test:

```text
Quelle quantité d'engrais pour le sorgho au stade tallage ?
```

Expected:

- identifies sorghum and tillering
- gives cautious advice
- mentions missing soil test if relevant
- cites sources

---

### Session 10 — Simple router

Goal: make one interface call the right tool.

Prompt:

```text
Create a simple DakiKobo router in core/agents/router.py. It should route image requests to diagnose_image, fertilizer keywords to recommend_fertilizer, yield keywords to estimate_yield if available, and all other messages to the existing RAG advisor. Wire /ask to use the router for text. Keep behavior stable and add basic tests for routing decisions.
```

Test:

```text
Quand planter le mil dans le Sahel ?
Quelle quantité d'engrais pour le sorgho au tallage ?
Estime le rendement de mon maïs
```

Expected:

- routes to RAG, fertilizer, yield fallback.

---

### Session 11 — RAG evaluation script

Goal: get PhD-visible metrics.

Prompt:

```text
Create scripts/evaluate_rag.py for DakiKobo. It should load the same vector store as the app, run at least 10 French Burkina Faso crop questions, print top-3 retrieved sources and snippets, and save a Markdown report to reports/rag_eval_results.md. Include questions about millet planting, sorghum fertilizer, maize varieties, niébé disease, groundnuts, climate adaptation, and rainfall risk.
```

Test:

```bash
python scripts/evaluate_rag.py
```

Expected:

- Markdown report created.
- Top sources visible.

---

### Session 12 — README for application reviewers

Goal: make GitHub explain the project well.

Prompt:

```text
Rewrite README.md for DakiKobo as a serious open-source agritech and PhD portfolio project. Include: what it does, why Burkina Faso cereal systems matter, current features, architecture diagram in Mermaid, setup instructions using .env, known limitations, farmer-safety principles, roadmap to CROPRADAR modules, and demo test questions. Remove outdated Mixtral/chat2.py instructions.
```

Definition of done:

- README matches current files.
- No instruction tells users to put API keys in source code.
- Reviewer can understand product and research value in 2 minutes.

---

## 8. Colab Pro notebook plan

### Notebook 1 — Disease screening prototype

Filename:

```text
notebooks/01_disease_screening_colab.ipynb
```

Objective:

Build a prototype plant disease classifier to show computer-vision competence.

Dataset:

- PlantVillage or another public crop leaf dataset.
- Focus first on maize and general leaf disease classes.
- Treat sorghum, millet, and niébé as future local-data targets if public data is weak.

Metrics:

- accuracy
- macro F1
- confusion matrix
- per-class recall

Output:

- model file optional
- metrics table
- confusion matrix image
- limitation statement

How it plugs into Flask:

- Not required for July product path.
- Use it in README and demo as research evidence.
- Production disease route should remain Gemini Vision first until local field images exist.

Honest limitation text:

```text
This model is trained on public leaf-image data and is not field-validated for Burkina Faso. It demonstrates the planned computer-vision pipeline and must be calibrated with local images before farmer-facing diagnosis.
```

### Notebook 2 — Exploratory yield estimation

Filename:

```text
notebooks/02_yield_estimation_colab.ipynb
```

Objective:

Show ability to model yield from structured agronomic and climate variables.

Dataset:

- public crop yield dataset
- FAOSTAT-style district/national data if available
- rainfall/climate proxy if available

Metrics:

- MAE
- RMSE
- R²
- residual plot

Output:

- baseline model: RandomForestRegressor or XGBoost if available
- feature importance
- limitation statement

How it plugs into Flask:

- Export a simple model only if stable.
- Otherwise implement a cautious rule-based `estimate_yield` and present notebook as research groundwork.

Honest limitation text:

```text
Yield results are exploratory and depend on public proxy data. They are not field-level predictions for Burkina Faso farms without local calibration and validation.
```

### Notebook 3 — RAG evaluation

Filename:

```text
notebooks/03_rag_evaluation.ipynb
```

Objective:

Measure whether DakiKobo retrieves the right documents for Burkina Faso farmer questions.

Dataset:

- your own PDF knowledge base
- 20 manually written French questions
- expected source labels

Metrics:

- Recall@3
- Recall@5
- source match rate
- answer groundedness score by manual review

Output:

- table of test questions
- top retrieved sources
- pass/fail per question
- recommendations for chunk size and embedding model

How it plugs into Flask:

- directly improves RAG settings
- gives PhD reviewers concrete evaluation evidence

### What not to train in Colab

Do not train:

- a custom LLM
- a 70B model
- fertilizer neural network
- full multimodal model
- production disease model from PlantVillage alone
- yield model claiming local field validity

These would waste time or create misleading claims.

---

## 9. PhD application materials

### GitHub README should show

Add these sections:

1. Problem: limited access to trusted agricultural advice in Burkina Faso.
2. Product: French voice + text advisor for cereal systems.
3. Current demo: RAG + TTS + mobile chat.
4. Research extension: vision, yield, fertilizer tools.
5. Architecture diagram.
6. Screenshots.
7. Evaluation metrics from notebooks.
8. Safety principles.
9. Known limitations.
10. Roadmap.

Suggested README headline:

```text
DakiKobo — Farmer-safe multimodal agricultural advisor for Burkina Faso cereal systems
```

### Demo video plan

Length: 2–3 minutes.

#### Scene 1 — Problem framing, 10 seconds

Show text slide:

```text
Smallholder farmers and extension agents need short, local, trusted advice for millet, sorghum, maize, niébé, and groundnuts.
```

#### Scene 2 — Core RAG, 25 seconds

Ask:

```text
Quand planter le mil dans la zone du Sahel au Burkina Faso ?
```

Show:

- short answer
- source chips
- audio playback

#### Scene 3 — Fertilizer, 25 seconds

Ask:

```text
Quelle quantité d'engrais pour le sorgho au stade tallage ?
```

Show:

- structured answer
- caution about soil test/rain
- source chips

#### Scene 4 — Disease photo, 30 seconds

Upload leaf photo.

Show:

- possible issue
- confidence
- next steps
- warning that this is not confirmed diagnosis

#### Scene 5 — Research architecture, 30 seconds

Show diagram:

```text
Mobile UI + TTS
    ↓
Router
    ↓
RAG advisor | Disease screening | Fertilizer tool | Yield estimator
    ↓
Farmer-safe response schema
```

#### Scene 6 — Limitations and PhD fit, 20 seconds

Say:

```text
The current system is a prototype. The PhD work would focus on local calibration, multimodal evaluation, field validation, and safer decision support for cereal systems.
```

### Research statement angle

Use this framing:

```text
DakiKobo explores farmer-safe multimodal advisory systems for cereal production under data scarcity. The prototype combines retrieval from local agronomic documents, French voice interaction, image-based disease triage, and structured fertilizer/yield modules. The PhD would formalize local calibration, multimodal fusion, uncertainty communication, and field validation for Sahel and Sudanian Savanna farming systems.
```

### Honest limitations to acknowledge

- Current disease screening is not field-validated.
- Yield module is exploratory without local plot-level data.
- RAG quality depends on PDF extraction and knowledge-base coverage.
- French works first; local languages are future work.
- TTS depends on internet unless replaced later.
- The system is intended first for extension agents and cooperatives, not unsupervised high-risk farmer decisions.

---

## 10. Risks and realism check

### Main risk

Trying to build every planned feature will make the core app unstable.

The highest-risk distractions:

- Firebase
- full mobile app
- offline mode
- complex agent framework
- local-language support
- serving a custom CNN before proper validation

### Minimum viable credible demo by July 15

This is the smallest strong version:

1. Mobile-first UI.
2. French text Q&A.
3. French TTS.
4. All PDFs ingested.
5. Persistent Chroma.
6. Source citations.
7. Disease image upload with Gemini Vision and safety wrapper.
8. Fertilizer tool with source-grounded caution.
9. One RAG evaluation report.
10. One Colab notebook with disease or yield metrics.
11. Updated README.
12. Two-minute demo video.

### Confidence

High confidence that this scope is enough for a strong PhD portfolio demo.

Moderate confidence that disease upload and fertilizer routing can be stable within the deadline if P0 is completed first.

Low confidence that a real yield model can be useful before July 15 without local data.

---

## 11. Suggested 3-week calendar

### Week 1 — Make the advisor trustworthy

Goal: a mobile-friendly, cited, faster RAG advisor.

| Day | Focus | Output |
|---:|---|---|
| 1 | Fix static paths and repo cleanup | No broken images; README notes updated later |
| 2 | Normalize Data path and recursive PDF ingestion | All PDFs found at startup |
| 3 | Persistent Chroma | No rebuild on every restart |
| 4 | Source extraction from RetrievalQA | `/ask` returns sources |
| 5 | Source chips in UI | Farmer-facing citations visible |
| 6 | Mobile-first UI | Phone-ready demo |
| 7 | Manual evaluation | 10 test questions documented |

Week 1 test questions:

```text
Quand planter le mil dans la zone du Sahel au Burkina Faso ?
Comment traiter les maladies du niébé ?
Quelle quantité d'engrais pour le sorgho au stade tallage ?
Quelles variétés de maïs pour la savane soudanienne ?
Who developed you?
```

### Week 2 — Add multimodal and structured tools

Goal: one image feature and one fertilizer feature.

| Day | Focus | Output |
|---:|---|---|
| 8 | Gemini config and disease agent | Backend disease triage works |
| 9 | Image upload UI | Mobile image upload works |
| 10 | Disease safety response | Confidence + warning + next steps |
| 11 | Fertilizer agent | Sorghum/tallage question handled |
| 12 | Simple router | `/ask` routes fertilizer/yield/RAG |
| 13 | Feedback buttons | CSV feedback capture |
| 14 | Stabilization | Test full demo script |

Week 2 test questions:

```text
Voici une photo de mon maïs, que vois-tu ?
Quelle quantité d'engrais pour le sorgho au stade tallage ?
Mon niébé a des taches sur les feuilles, que faire ?
```

### Week 3 — Research proof and application polish

Goal: reviewers understand the product and research path.

| Day | Focus | Output |
|---:|---|---|
| 15 | RAG evaluation script/notebook | `reports/rag_eval_results.md` |
| 16 | Disease Colab notebook | metrics + limitation statement |
| 17 | Yield notebook or exploratory estimator | honest research prototype |
| 18 | README rewrite | clear GitHub project story |
| 19 | Screenshots and architecture diagram | reviewer-ready visuals |
| 20 | Demo video recording | 2–3 minute demo |
| 21 | Final application package | submit before deadline |

---

## 12. Farmer-facing test pack

Use these after every major session.

### Core RAG tests

```text
Quand planter le mil dans la zone du Sahel au Burkina Faso ?
Comment traiter les maladies du niébé ?
Quelles variétés de maïs pour la savane soudanienne ?
Comment protéger le sorgho pendant une saison de pluie irrégulière ?
Quels conseils pour l'arachide dans une zone sèche ?
```

Pass criteria:

- French answer.
- Under 120 words.
- Practical.
- Source chips shown when available.
- No overconfident claim.

### Fertilizer tests

```text
Quelle quantité d'engrais pour le sorgho au stade tallage ?
Quel engrais pour le maïs après la levée ?
Je n'ai pas d'analyse de sol, que faire pour fertiliser le mil ?
```

Pass criteria:

- Identifies missing soil data.
- Does not invent exact dose if not sourced.
- Mentions rain/timing when relevant.
- Advises local extension confirmation for high-risk decisions.

### Disease tests

```text
Mon niébé a des taches sur les feuilles, que faire ?
Voici une photo de mon maïs malade.
Peux-tu confirmer cette maladie ?
```

Pass criteria:

- Says possible issue, not guaranteed diagnosis.
- Shows confidence.
- Gives 2–3 next steps.
- Warns against blind pesticide use.

### Identity test

```text
Who developed you?
```

Pass criteria:

- Responds with the configured bot identity.
- Does not call LLM unnecessarily.

---

## 13. Suggested GitHub issues to create

Create these issues manually or paste them into GitHub.

### Issue 1 — Fix static paths and favicon

```markdown
## Goal
Fix broken avatar and favicon references in DakiKobo UI.

## Files
- templates/index.html
- static/js/index.js

## Done when
- No broken images in browser.
- Logo, user avatar, bot avatar all load from static/images.
```

### Issue 2 — Add recursive PDF ingestion

```markdown
## Goal
Load all PDFs under the knowledge base folder, including subfolders.

## Files
- core/rag_pipeline.py
- config.py

## Done when
- Startup logs show all PDFs found.
- One bad PDF does not crash the app.
```

### Issue 3 — Add persistent Chroma

```markdown
## Goal
Avoid rebuilding vector store on every Flask restart.

## Done when
- First run builds vector store.
- Second run loads existing index.
- REBUILD_VECTORSTORE=true forces rebuild.
```

### Issue 4 — Show citations

```markdown
## Goal
Return and display source documents for RAG answers.

## Done when
- /ask JSON includes sources.
- UI renders source chips.
```

### Issue 5 — Mobile-first UI

```markdown
## Goal
Make DakiKobo usable on basic smartphones.

## Done when
- No horizontal scroll at 360px width.
- Input remains reachable.
- Buttons are easy to tap.
```

### Issue 6 — Disease image upload

```markdown
## Goal
Add cautious crop disease screening from uploaded photo.

## Done when
- User can upload image.
- Response includes confidence, next steps, and disclaimer.
```

---

## 14. One thing to cut

Cut major investment in yield prediction before July 15.

Reason:

- without local plot-level data, it will be weak
- false yield certainty can harm trust
- it can absorb many sessions
- it is harder to demo safely than RAG, disease triage, and fertilizer guidance

Do instead:

- build an exploratory `estimate_yield` module
- show one Colab notebook with public-data metrics
- clearly state that local calibration is PhD work

This is a stronger and more honest research story.

---

## 15. Alternative product name and landing sentence

### Name/subtitle option

```text
DakiKobo — Conseils agricoles fiables pour les céréales du Burkina Faso
```

### Landing sentence

```text
DakiKobo aide les producteurs, conseillers agricoles et coopératives à obtenir des réponses courtes, vocales et sourcées pour les cultures de mil, sorgho, maïs, niébé et arachide au Burkina Faso.
```

---

## 16. Final execution priority

If time gets tight, finish only this sequence:

1. Fix static paths.
2. Recursive PDF ingestion.
3. Persistent Chroma.
4. Source citations.
5. Mobile-first UI.
6. Gemini disease upload.
7. Fertilizer tool.
8. RAG evaluation report.
9. README rewrite.
10. Demo video.

Everything else is optional.

