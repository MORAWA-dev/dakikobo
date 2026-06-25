# Cursor prompt: plan and implement DakiKobo improvements, easy to hard

Paste the block below into Cursor (Composer/Agent) with the repo open.

---

> You are working in the DakiKobo repository (Flask + LangChain RAG agricultural advisor for Burkina Faso). Before writing any code, do this:
>
> **1. Walk the project.** Read `app.py`, `config.py`, `core/llm_chain.py`, `core/rag_pipeline.py`, `templates/index.html`, `static/js/index.js`, `static/css/style.css`, `requirements.txt`, `.gitignore`, and the folder layout under `Data/`. Build an accurate mental model of how a request flows from the browser to the LLM and back. Do not assume; confirm by reading.
>
> **2. Skim the model suggestions.** Read every file in the `models_sugestions/` subfolder (note the spelling: `models_sugestions`), including `claude.md`, `chatgptsuggestions.md`, and the Gemini files. These are recommendations from different models. Treat them as input, not orders. Where they overlap, that signals high confidence. Where they conflict, use your own read of the code to decide.
>
> **3. Produce a single implementation plan** and save it as `IMPLEMENTATION_PLAN.md` in the repo root. The plan must:
>    - Merge and de-duplicate the suggestions into one ordered list of concrete tasks.
>    - Order tasks strictly from easiest/lowest-risk to hardest/highest-risk. Quick bug fixes and path corrections first; new modules (disease screening, agent routing, yield) last.
>    - For each task give: a short title, the exact files it touches, a one-line "definition of done" that a non-developer could verify, an effort tag (S/M/L), and a **model tier** (CHEAP / MID / FRONTIER) following the routing rule below.
>    - Put genuinely unrealistic or long-shot items (custom CNN training, native mobile app, offline edge inference, local-language generation) in a separate "Later / parked" section at the bottom with one sentence on why they are deferred. Do not attempt them now.
>    - Mark each task with a status checkbox: `[ ]` todo, `[x]` done.
>
> **Model routing rule** (to save tokens; I drive an expensive model by default):
>    - **CHEAP** = mechanical, single-file, no judgment: path/string fixes, file encoding, config value changes, deleting dead files, simple CSS tweaks. These need a fast cheap model, not a reasoning model.
>    - **MID** = small logic across one or two files with a clear spec: wiring source documents into the response, a quick endpoint, a self-contained function with tests.
>    - **FRONTIER** = real design or cross-file reasoning: agent routing, RAG re-architecture (persistent store, header-aware chunking), the disease pipeline, anything touching multiple modules or requiring trade-off decisions.
>    - In `IMPLEMENTATION_PLAN.md`, tag every task with its tier so I know which model to select in Cursor's picker before pasting it. Most easy wins should be CHEAP. Do not over-assign FRONTIER; if a task only needs careful editing, it is MID at most.
>
> **4. Implement one task at a time, starting today with the easiest.** For each task, in order:
>    - State which task you are starting, and remind me of its model tier so I can switch the Cursor model if needed before you run.
>    - Make the smallest change that satisfies it. Edit only the files that task names.
>    - Test it: run the app or the relevant code, or write a quick check, and show me the result proving the definition of done is met. For UI tasks, describe exactly what to click and what should appear.
>    - If it works, update the checkbox to `[x]` in `IMPLEMENTATION_PLAN.md` and tell me the suggested commit message. Then stop and wait for my go-ahead before the next task.
>    - If it breaks something, fix it before moving on. Never leave the app in a non-starting state.
>
> **Rules.**
> - One task per step. Do not batch multiple tasks. Do not refactor unrelated code.
> - Prefer incremental edits over rewrites. Keep the working simple advisor working at every step.
> - If a task turns out bigger or riskier than expected, pause and tell me; propose splitting it rather than pushing through.
> - This project serves smallholder farmers in Burkina Faso (millet, sorghum, maize, niébé, groundnuts). Keep answers, labels, and TTS in French. Keep changes mobile-friendly.
>
> Start now: do steps 1 to 3, show me `IMPLEMENTATION_PLAN.md`, then begin the first (easiest) task and stop after its test passes.

---

## How to map tiers to Cursor models

Cursor lets you pick the model per message. Map the tiers to whatever your model picker currently lists:

- **CHEAP** -> a fast budget model (Cursor "Auto", or a small/fast tier like a mini/flash/haiku-class model). Use for the mechanical fixes; do not spend Opus tokens here.
- **MID** -> a solid mid model (a Sonnet-class or GPT mid-tier).
- **FRONTIER** -> your default Opus 4.8 (or the strongest model available) for the design-heavy tasks only.

Practical flow: do all CHEAP tasks in one sitting on a budget model, commit each, then switch to Opus only when you reach the FRONTIER block. The exact model names in Cursor change over time, so match by capability tier, not by a fixed name.

## Optional: seed the easy wins

If you want to point Cursor at the safest starting batch explicitly, add this line to the prompt: "For the first few tasks, prioritize: fix the broken avatar/favicon image paths, re-save `requirements.txt` as UTF-8, fix the `DATA_FOLDER` casing, raise `TTS_MAX_CHARS`, and turn on the retriever score threshold. These are low-risk and independently testable." (All five are detailed in `models_sugestions/claude.md`, section 0 and the P0 backlog rows.)
