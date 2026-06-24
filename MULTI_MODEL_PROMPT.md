# Multi-Model Prompt — DakiKobo Improvement Suggestions

Copy everything inside the **"START PROMPT"** / **"END PROMPT"** block below and paste it into Claude, GPT, Gemini, Groq, or any other model.  
Use the same prompt everywhere so you can compare answers side by side.

**Tip:** After each model responds, save the answer in a folder like `suggestions/gpt.md`, `suggestions/claude.md`, etc.

---

## START PROMPT

You are a senior AI + agritech product architect. I will use your suggestions to **vibe-code** improvements in **Cursor** (primary), **Antigravity**, or **Codex** — so every recommendation must be **concrete, prioritized, and executable** in small coding sessions (60–90 min each).

Do **not** give generic advice. Ground everything in my actual project state below.

---

### PROJECT: DakiKobo

**What it is:** An AI-powered agricultural advisor for smallholder cereal farmers in **Burkina Faso** (Sahel + Sudanian Savanna). Named for local-language notions of "knowledge/advice for the farm."

**My background:** Geomatics MSc. Building this as my own useful product **and** as portfolio for a PhD application.

**Dual goal (both matter equally):**
1. **Useful product** — Real farmers or extension agents should get short, practical, trustworthy advice (voice + text).
2. **Research credibility** — Show I can build multimodal precision-ag systems, not just a chatbot demo.

**Anti-patterns to avoid:**
- Overconfident disease IDs without disclaimers
- Yield models trained on foreign data presented as field-ready
- Fancy architecture that breaks a working simple advisor
- UI that only looks good on desktop

---

### PHD TARGET

**Position:** PhD at School of Collective Intelligence, **UM6P** (Mohammed VI Polytechnic University)  
**Project:** **CROPRADAR** — Multimodal AI for Precision Agriculture  
**Focus areas:**
- Yield prediction
- Disease diagnostics
- Intelligent fertilizer recommendations
- Combining: image models + structured agronomic data + deep learning + LLM reasoning
- Cereal farming systems

**Application deadline:** July 15, 2026 (~3 weeks from now)  
**Application link:** https://lnkd.in/ehPz3hGj

I need suggestions that strengthen **both** farmer utility **and** PhD alignment without pretending the product is production-ready.

---

### CURRENT TECH STACK

| Layer | Technology |
|---|---|
| Backend | Python 3.11, Flask 3.0 |
| LLM | Groq — `llama-3.3-70b-versatile` via `langchain-groq` |
| RAG | LangChain 0.2, ChromaDB 0.5, `all-MiniLM-L6-v2` embeddings |
| PDF extraction | PyPDF2 |
| TTS | gTTS (French) → MP3 in `static/audio/` |
| Frontend | Jinja2 template + jQuery + custom CSS (no React/Vue) |
| Config | `config.py` + `.env` (GROQ_API_KEY) |
| Legacy | `chat1.py`, `chat2.py` deprecated (replaced by `core/`) |

**Available to me (not yet wired in):**
- Cursor Pro (agentic vibe coding)
- Colab Pro (GPU for training notebooks)
- Gemini API (vision + translation — planned)
- OpenAI API (optional)
- Firebase (planned, not implemented)

---

### REPOSITORY STRUCTURE

```
dakikobo/
├── app.py                  # Flask entry — / and /ask routes only
├── config.py               # All tuneable settings
├── core/
│   ├── llm_chain.py        # Groq LLM + RetrievalQA prompt (Burkina-focused)
│   └── rag_pipeline.py     # PDF load, chunk, Chroma, gTTS
├── templates/index.html    # Chat UI
├── static/
│   ├── css/style.css       # Green gradient theme, 470×650px chat box
│   ├── js/index.js         # jQuery AJAX chat + voice input (webkitSpeechRecognition)
│   ├── images/             # logo, bot_avatar, user_avatar
│   └── audio/              # Generated TTS mp3 files
├── Data/
│   ├── knowledge_base/     # 8 cleaned PDFs (ingested)
│   └── New Folder With Items/  # 7 more PDFs NOT yet ingested
├── organize.sh             # One-time PDF rename/move script (partially run)
├── requirements.txt
├── .env.example
├── PHD_ROADMAP.md          # My internal roadmap (useful + PhD dual track)
└── README.md
```

---

### WHAT WORKS TODAY

- Flask app starts and serves chat at `http://127.0.0.1:5000`
- RAG pipeline: loads PDFs → chunks (500 chars, 100 overlap) → ChromaDB in-memory → RetrievalQA
- System prompt targets Burkina crops: sorghum, millet, maize, cotton, niébé, groundnuts
- Answers capped at ~100 words, farmer tone, "don't know" fallback
- French TTS on every answer (checkbox to play audio)
- Browser speech-to-text for French voice input (`fr-FR`)
- Typing animation for bot messages
- 8 PDFs in knowledge base: FAO, CSA investment plans, climate adaptation, farmer training manual, agronomy article, 2 unidentified (`needs_review_01/02`)

---

### KNOWN BUGS & GAPS

**Bugs:**
- `static/js/index.js` references broken paths: `/static/user.png`, `/static/robo.png` (actual files: `static/images/user_avatar.png`, `static/images/bot_avatar.png`)
- `templates/index.html` favicon points to `static/logo.png` (actual: `static/images/logo.png`)
- ChromaDB is **in-memory only** — full re-index on every server restart (slow)
- Only PDFs directly in `knowledge_base/` are loaded — **no subfolder recursion**, 7 PDFs not ingested
- `organize.sh` not fully executed; legacy `chat1.py` / `chat2.py` still present

**Missing features (planned, not built):**
- Image upload / crop disease screening
- Agent router (LangGraph or tool-calling)
- Yield prediction module
- Structured fertilizer recommendation tool
- Multilingual (Mooré, Dioula, Fulfuldé)
- Source citations shown in UI
- Mobile-first responsive layout (current UI is fixed 470px width)
- Offline / edge inference
- Firebase backend / mobile app
- Persistent vector store
- User feedback ("was this helpful?")
- Any automated tests (only empty `tests/__init__.py`)

**UI state:**
- Desktop-centric card layout, green gradient background
- Functional but dated — looks like early prototype
- No image upload, no structured forms, no source display
- Voice button exists but no visual recording state

---

### KNOWLEDGE BASE (16 PDFs total, 8 ingested)

**Ingested (`Data/knowledge_base/`):**
- `burkina_climate_adaptation_state_report.pdf`
- `csa_investment_plan_burkina_final.pdf` / `_draft.pdf`
- `fao_publication_i3760e.pdf`
- `farmer_training_manual.pdf`
- `jaa_agronomy_article_2021.pdf`
- `needs_review_01.pdf` / `needs_review_02.pdf`

**Not ingested yet:**
- `Data/1767_KIT_boek_Burkina_web-version.pdf`
- `Data/New Folder With Items/` — GIZ agriculture program, household characteristics, Bagré growth pole, country profile, agri report, etc.

---

### REAL-WORLD CONSTRAINTS (design for these)

- Many users have **low literacy** → TTS is essential, not optional
- **French** is primary; local languages (Mooré, Dioula, Fulfuldé) needed later
- **Patchy internet** in rural Burkina → short answers, low bandwidth, offline is long-term goal
- **Basic smartphones** → must work in mobile browser
- **Trust** → wrong advice on fertilizer or disease can ruin a season → disclaimers, confidence levels, cite sources
- Realistic first users: **extension agents, agronomy students, cooperatives** — not every farmer directly yet

---

### WHAT I WILL DO WITH YOUR ANSWER

I will:
1. Compare responses from multiple models
2. Pick the best ideas
3. Execute them in **90-minute Cursor sessions** using agentic coding
4. Use **Colab Pro** only for GPU training notebooks (disease CNN, yield model)

---

### YOUR TASK — OUTPUT FORMAT (STRICT)

Respond in **exactly** these sections:

#### 1. Executive summary (5 bullets max)
What matters most for me in the next 3 weeks?

#### 2. Product vision (farmer usefulness)
- Who is the primary user for v1?
- What 3 jobs should DakiKobo do better than Google or asking a neighbor?
- What should I **not** build yet?

#### 3. UI/UX redesign proposal
Be specific. Include:
- Layout changes (mobile-first? full-screen? PWA?)
- Color/typography/branding direction for Burkina agritech
- New UI components needed (image upload, source chips, confidence badges, voice waveform, quick-action buttons for common questions like "planting millet", "niébé diseases", "fertilizer sorghum")
- Wireframe description or ASCII mockup
- Whether to keep Flask+jQuery or migrate frontend (and why)
- **3 Cursor-ready prompts** specifically for UI work I can paste into Cursor

#### 4. Technical architecture improvements
- Agent design (tools, routing, fallbacks)
- RAG improvements (chunking, metadata, persistent Chroma, citations in response)
- Multimodal pipeline (disease photo — Gemini vs custom CNN vs hybrid)
- Yield + fertilizer modules — honest MVP scope
- File/folder restructuring if needed

#### 5. Prioritized backlog (table)

| Priority | Task | Farmer value (1-5) | PhD value (1-5) | Effort (S/M/L) | Cursor session prompt (copy-paste ready) |
|---|---|---|---|---|---|

Include **at least 12 tasks**, ordered P0 → P3.

#### 6. Colab Pro notebook plan
- Notebook 1, 2, 3: objective, dataset, metrics, how results plug back into Flask app
- What **not** to train in Colab (waste of time)

#### 7. PhD application materials
What to show reviewers in: README, demo video (scene-by-scene), research statement angle, honest limitations to acknowledge

#### 8. Risks & realism check
What will fail if I try to do everything? What is the **minimum viable credible demo** by July 15?

#### 9. Suggested 3-week calendar
Day-by-day or week-by-week, **useful product first**, research modules second.

#### 10. One thing you would cut
Name one feature I am probably overestimating — and what to do instead.

---

### CONSTRAINTS ON YOUR SUGGESTIONS

- Sessions are **60–90 minutes** — tasks must be splittable
- I am **one developer** vibe-coding with AI assistants
- Budget: API keys for Groq/Gemini are OK; no expensive cloud infra
- Prefer **incremental** changes over full rewrite unless you make a strong case
- Every task needs a **definition of done** a non-expert farmer-facing tester could verify
- Suggestions must work for **Burkina Faso cereal systems** (millet, sorghum, maize, niébé, groundnuts) — not generic US corn farming

---

### BONUS (if you have capacity)

Give me **one alternative product name/subtitle** and **one sentence** I can put on the landing page that works for both farmers and PhD reviewers.

---

## END PROMPT

---

## Optional follow-up prompts (after first response)

Use these to go deeper with the same model:

### UI deep-dive
```
Based on your previous DakiKobo suggestions, give me a complete mobile-first UI spec: HTML structure changes for templates/index.html, CSS design tokens (colors, spacing, fonts), and every new JS interaction. Assume Flask + jQuery stay. Output code-ready snippets.
```

### Architecture deep-dive
```
Design the DakiKobo agent layer in detail: tool schemas, router logic, error handling, and how each tool returns farmer-safe responses with disclaimers. Prefer LangGraph if justified, or a simpler Flask-native approach if not. Include file names and function signatures.
```

### PhD-only lens
```
Review DakiKobo only through the UM6P CROPRADAR PhD lens. What 3 experiments with metrics would most strengthen my application? What gap in my current repo would supervisors notice immediately?
```

### Farmer-only lens
```
Ignore the PhD completely. You are an extension agent in Koudougou. What would make you open DakiKobo on your phone in the field? What would make you distrust it?
```

### Compare mode (paste two model outputs)
```
Here are suggestions from Model A and Model B pasted below. Merge them into one prioritized plan, flag contradictions, and pick a winner for each disagreement.

[Paste Model A]

[Paste Model B]
```

---

## How to use across models

| Model | Suggested use |
|---|---|
| **Claude** | Architecture, farmer-safety, nuanced product thinking |
| **GPT-4o / o3** | Structured backlog, Cursor prompts, UI wireframes |
| **Gemini** | Vision/multimodal pipeline, French/African language angle |
| **Grok** | Fast iteration prompts, skepticism / cut scope |
| **DeepSeek** | Technical RAG + agent implementation detail |

Save each response → compare section 5 (backlog tables) → execute top P0 items in Cursor first.

---

*DakiKobo multi-model prompt — June 2026*