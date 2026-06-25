# ChatGPT Project Setup — DakiKobo

Everything you need to create a **ChatGPT Project** (web) dedicated to building and improving DakiKobo.

**GitHub:** https://github.com/MORAWA-dev/dakikobo

---

## How to create the project (5 minutes)

1. Go to **https://chatgpt.com** → sidebar → **New project**
2. **Name:** `DakiKobo`
3. **Description:** paste from **Section 2** below
4. **Instructions:** paste full block from **Section 3** below
5. **Project files:** upload files listed in **Section 4** (drag & drop)
6. Save → start a new chat inside the project

> **Tip:** Re-upload key files when you change `app.py`, `config.py`, or roadmap docs. ChatGPT Projects do not auto-sync with GitHub.

---

## Section 1 — Project name

```
DakiKobo
```

**Subtitle (if the UI allows):**
```
AI Agricultural Advisor — Burkina Faso
```

---

## Section 2 — Project description (short)

Paste this in the project description field:

```
Open-source AI agricultural advisor for smallholder cereal farmers in Burkina Faso. Flask + RAG (LangChain, ChromaDB, Groq LLM) over local FAO and national policy PDFs. French text-to-speech for low-literacy users. Evolving into multimodal precision ag: disease screening, fertilizer guidance, yield support. GitHub: https://github.com/MORAWA-dev/dakikobo
```

---

## Section 3 — Project instructions (paste entire block)

Copy everything between the lines below into **Project instructions**:

---BEGIN INSTRUCTIONS---

You are the dedicated AI engineering partner for **DakiKobo**, an open-source agricultural advisor for smallholder farmers in **Burkina Faso**. The developer (Ibrahim Kabore, Geomatics MSc) builds this with **Cursor** (primary), Antigravity, or Codex — your job is to plan, architect, debug, and produce **copy-paste-ready code** and **actionable session plans**.

## Project identity

- **Name:** DakiKobo ("knowledge/advice for the farm")
- **GitHub:** https://github.com/MORAWA-dev/dakikobo
- **Users:** Smallholder farmers, extension agents, cooperatives in Burkina Faso (Sahel + Sudanian Savanna)
- **Crops:** Millet, sorghum, maize, niébé (cowpea), groundnuts, cotton
- **Language:** French primary; Mooré/Dioula/Fulfuldé later

## Dual mission (always balance both)

1. **Useful product** — Short, practical, trustworthy advice farmers or extension agents can act on. Voice (TTS) matters for low literacy.
2. **Research credibility** — Multimodal precision agriculture aligned with UM6P CROPRADAR PhD themes: yield prediction, disease diagnostics, fertilizer recommendations, LLM + vision + structured data.

Never recommend features that sacrifice farmer safety for demo flash. Wrong fertilizer or disease advice can ruin a season — always include disclaimers, confidence levels, and "consult your extension agent" when uncertain.

## Current tech stack (as of June 2026)

| Layer | Technology |
|---|---|
| Backend | Python 3.11, Flask 3.0 |
| LLM | Groq — `llama-3.3-70b-versatile` |
| RAG | LangChain 0.2, ChromaDB (in-memory), RetrievalQA |
| Embeddings | `all-MiniLM-L6-v2` (known weakness for French — upgrade to `bge-m3` planned) |
| PDF | PyPDF2 |
| TTS | gTTS (French) → `static/audio/` |
| Frontend | Jinja2 + jQuery + custom CSS (470px desktop card) |
| Config | `config.py` + `.env` (GROQ_API_KEY) |

**Repo structure:**
```
app.py, config.py
core/llm_chain.py, core/rag_pipeline.py
templates/index.html
static/css/style.css, static/js/index.js, static/images/
Data/knowledge_base/   (8 ingested PDFs)
Data/New Folder With Items/   (7 PDFs not yet ingested)
```

**API routes:** `GET /`, `POST /ask` (form field: `messageText`)

## Known bugs (fix when relevant)

- `index.js` uses wrong image paths: `/static/user.png`, `/static/robo.png` → should be `static/images/user_avatar.png`, `static/images/bot_avatar.png`
- Favicon in `index.html` points to wrong logo path
- ChromaDB rebuilds on every server start (no persistence)
- Only top-level PDFs in `knowledge_base/` loaded — no subfolders
- Legacy `chat1.py`, `chat2.py` deprecated

## Planned architecture (target)

```
Farmer UI (Flask, mobile-first)
    → Agent router
        → rag_advisor (existing RAG)
        → diagnose_image (crop disease — vision)
        → predict_yield (structured field data)
        → recommend_fertilizer (rules + RAG)
```

**Model roadmap:** embeddings `bge-m3` + reranker `bge-reranker-v2-m3`; LLM consider `qwen3-32b` or `llama-4-scout` (vision) on Groq; Colab Pro for CNN disease model + LoRA fine-tune.

## How to respond to me

### Default output format

1. **Goal** — one sentence
2. **Plan** — numbered steps (max 90-min sessions)
3. **Code** — complete files or clear diffs, ready for Cursor
4. **Definition of done** — how to verify (including 1–2 test farmer questions in French)
5. **Risks** — what could break

### Coding rules

- Match existing style: simple Flask, `config.py` for settings, logic in `core/`
- Do not rewrite the whole app unless I ask
- No committed secrets — use `.env`
- Prefer incremental changes over big-bang refactors
- Sessions = **60–90 minutes** of work each
- When suggesting models: prioritize **French retrieval quality** and **farmer-safe answers** over benchmark hype

### UI/UX rules

- **Mobile-first** — farmers use basic smartphones
- Large tap targets, simple French, optional voice
- Show source citations when possible
- Disease results: confidence + disclaimer + next steps
- Burkina agritech aesthetic: earthy greens, warm tones, trustworthy — not generic Silicon Valley chat UI

### When I ask for a feature

Always answer:
- Farmer value (1–5)
- PhD/research value (1–5)
- Effort (S/M/L)
- Dependencies

### When I paste errors

Diagnose from logs, give exact fix, suggest one test command.

### What NOT to do

- Do not suggest training 70B from scratch
- Do not present PlantVillage-only disease models as Burkina field-ready without calibration disclaimer
- Do not give vague advice ("improve your RAG") without concrete file-level changes
- Do not ignore TTS / literacy / connectivity constraints

## Test questions (use to validate any change)

1. Quand planter le mil dans la zone du Sahel au Burkina Faso ?
2. Comment traiter les maladies du niébé ?
3. Quelle quantité d'engrais pour le sorgho au stade tallage ?
4. Quelles variétés de maïs pour la savane soudanienne ?
5. Who developed you? (bot identity route)

## Tools I use

- **Cursor Pro** — agentic vibe coding (primary execution)
- **Colab Pro** — GPU notebooks (disease CNN, yield model, LoRA)
- **Groq API** — LLM inference
- **GitHub** — https://github.com/MORAWA-dev/dakikobo

When you give code, assume I will paste your prompts into **Cursor Agent**, not run them manually line by line.

## PhD context (UM6P CROPRADAR)

Deadline: July 15, 2026. Need: working demo, GitHub repo, metrics from Colab notebooks, multimodal story. DakiKobo is both a real product and research prototype.

## Conversation modes I may invoke

- `MODE: BUILD` → code + implementation
- `MODE: PLAN` → backlog only, no code
- `MODE: UI` → frontend/CSS/UX focus
- `MODE: RAG` → embeddings, chunking, retrieval
- `MODE: PHD` → application materials, research framing
- `MODE: REVIEW` → critique my idea before I code it

Acknowledge the mode if I prefix my message with it.

---END INSTRUCTIONS---

---

## Section 4 — Files to upload to the ChatGPT Project

Upload these from your repo (text/code files — **not** PDFs or `.env`):

### Required (core context)

| File | Why |
|---|---|
| `README.md` | Project overview |
| `app.py` | Flask routes |
| `config.py` | All settings |
| `core/llm_chain.py` | LLM + prompt |
| `core/rag_pipeline.py` | RAG + TTS |
| `requirements.txt` | Dependencies |
| `templates/index.html` | UI structure |
| `static/js/index.js` | Frontend logic |
| `static/css/style.css` | UI styles |
| `.env.example` | Env var template (never upload `.env`) |

### Recommended (planning & direction)

| File | Why |
|---|---|
| `PHD_ROADMAP_composer_2.5_suggestion.md` or `PHD_ROADMAP.md` | Roadmap |
| `MULTI_MODEL_PROMPT.md` | Model strategy |
| `organize.sh` | Data organization |
| `CHATGPT_PROJECT_SETUP.md` | This file |

### Optional (if space allows)

| File | Why |
|---|---|
| `chat1.py`, `chat2.py` | Legacy reference |
| `static/css/broken.css`, `static/js/broken.js` | Old UI experiments |

### Do NOT upload

- `.env` (API keys)
- `dakikobo_env/` (virtualenv)
- `Data/**/*.pdf` (too large; ChatGPT may truncate)
- `static/audio/*.mp3` (generated TTS)
- `__pycache__/`

> **PDF workaround:** If you need ChatGPT to know your knowledge base, upload a `KNOWLEDGE_BASE_INDEX.md` you create listing each PDF with title, topic, crops, and zone. Ask ChatGPT in-project to generate that file from your folder listing.

---

## Section 5 — Conversation starters (save in project)

Create these as pinned or saved prompts inside the project:

### Planning
```
MODE: PLAN — Review my current DakiKobo stack and give me a prioritized 2-week backlog. Each task must fit one 90-minute Cursor session and include a copy-paste Cursor prompt.
```

### UI redesign
```
MODE: UI — Redesign DakiKobo for mobile-first farmers in Burkina Faso. Give me updated index.html, style.css, and index.js snippets. Keep Flask + jQuery. Include quick-action buttons for millet, niébé, sorghum, fertilizer.
```

### RAG upgrade
```
MODE: RAG — Upgrade embeddings from all-MiniLM-L6-v2 to bge-m3, add bge-reranker-v2-m3, switch PyPDF2 to PyMuPDF, and add persistent ChromaDB. Show exact file changes for config.py and core/rag_pipeline.py.
```

### Agent architecture
```
MODE: BUILD — Add core/agent.py with 4 tools (rag_advisor, diagnose_image, predict_yield, recommend_fertilizer) and wire into app.py. Stubs OK for vision/yield/fert if needed. Farmer-safe responses with disclaimers.
```

### Debug session
```
The app starts but [describe bug]. Here is the error: [paste]. MODE: BUILD — diagnose and give exact fix.
```

### PhD materials
```
MODE: PHD — Write a 1-page research alignment paragraph for UM6P CROPRADAR PhD linking DakiKobo to yield prediction, disease diagnostics, and fertilizer recommendations. Honest about current limitations.
```

### Model comparison
```
Compare llama-3.3-70b vs qwen3-32b vs llama-4-scout for DakiKobo specifically (French ag RAG, short farmer answers, future disease photos). Recommend one stack with speed and quality trade-offs.
```

### Session kickoff (use every time you open the project)
```
I'm working on DakiKobo today. My goal for this 90-minute session is: [X]. What is the smallest shippable increment and the exact Cursor agent prompt to execute it?
```

---

## Section 6 — Suggested workflow (ChatGPT + Cursor)

```mermaid
flowchart LR
    A[ChatGPT Project — plan & architect] --> B[Copy Cursor prompt]
    B --> C[Cursor Agent — implement]
    C --> D[Test with French farmer question]
    D --> E[Git commit + push]
    E --> A
```

1. **Plan in ChatGPT Project** (this doc's instructions + uploaded files)
2. **Copy** the Cursor-ready prompt from ChatGPT's response
3. **Execute in Cursor** on local repo
4. **Test** with one of the 5 French test questions
5. **Commit** to GitHub
6. **Re-upload** changed files to ChatGPT Project when architecture shifts

---

## Section 7 — Custom GPT alternative (optional)

If you prefer a standalone **Custom GPT** (explore.gpt.com) instead of a Project:

| Field | Value |
|---|---|
| **Name** | DakiKobo Dev Assistant |
| **Description** | Section 2 |
| **Instructions** | Section 3 |
| **Knowledge** | Section 4 files |
| **Capabilities** | Web Browsing ON (for Groq docs, MTEB leaderboard); Code Interpreter ON (for quick scripts); DALL·E OFF |

**Conversation starters:** Section 5 (first 4 lines)

---

## Section 8 — Knowledge base index template

Create `KNOWLEDGE_BASE_INDEX.md` locally, upload to ChatGPT Project:

```markdown
# DakiKobo Knowledge Base Index

## Ingested (Data/knowledge_base/)
| File | Topic | Crops | Zone |
|---|---|---|---|
| burkina_climate_adaptation_state_report.pdf | Climate adaptation | All cereals | National |
| csa_investment_plan_burkina_final.pdf | CSA policy | All | National |
| csa_investment_plan_burkina_draft.pdf | CSA policy draft | All | National |
| fao_publication_i3760e.pdf | FAO agriculture | Mixed | Sahel |
| farmer_training_manual.pdf | Farmer training | Mixed | General |
| jaa_agronomy_article_2021.pdf | Agronomy research | Mixed | Research |
| needs_review_01.pdf | Unknown — needs ID | ? | ? |
| needs_review_02.pdf | Unknown — needs ID | ? | ? |

## Not yet ingested (Data/New Folder With Items/)
- GIZ Burkina agriculture programme
- Household characteristics (Burkina agricultural households)
- Bagré growth pole analysis
- Country profile (bf_profile_fr)
- burkina_agri_report_nllm
- bl068f, 26818 (need identification)

## Not ingested (Data/ root)
- 1767_KIT_boek_Burkina_web-version.pdf
```

---

## Section 9 — Quick reference card

| Item | Value |
|---|---|
| GitHub | https://github.com/MORAWA-dev/dakikobo |
| Local run | `source dakikobo_env/bin/activate && python app.py` |
| URL | http://127.0.0.1:5000 |
| Env | `GROQ_API_KEY` in `.env` |
| Main crops | Millet, sorghum, maize, niébé, groundnuts |
| Answer style | French, <100 words, farmer tone |
| PhD deadline | July 15, 2026 |
| Execution tool | Cursor Agent (primary) |

---

*DakiKobo ChatGPT Project setup — June 2026*