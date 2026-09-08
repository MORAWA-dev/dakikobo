# DakiKobo — assessment and farmer improvement plan

Date: 6 September 2026
Status: **LOCAL ENGINEERING IMPLEMENTATION COMPLETE — expert review and field pilot still required**
Assessed checkout: `0b880b6c` (`Record final live verification`).

## 1. Recommendation

DakiKobo has a useful technical foundation. The next investment should make its existing advice safer, easier to understand, and easier to use again in the field. Do not start with a new model, a larger interface, or more integrations.

Recommended order:

1. Correct journal ownership, offline crop selection, saved-answer freshness, and conversation reset.
2. Strengthen evidence review and evaluations so passing tests also means useful, supported advice.
3. Make five common farmer tasks easy to start and their answers easy to act on.
4. Turn the existing journal backend into a private, usable return-and-follow-up experience.
5. Validate the product with farmers and extension agents before adding languages or expanding coverage.

This proposal follows the completed Phase 0–5 engineering work. The previous plan remains
historical; its old bug list is not a list of current defects. The owner subsequently authorized
continuation, and the local engineering changes described in the implementation note below were
completed. No production deployment, corpus promotion, agronomist approval, or farmer pilot is
claimed by this document.

## 2. Current state and evaluation boundaries

### What is already present

| Area          | Assessment from the current code                                                                                              |
| ------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Advice        | French RAG, scored citations, uncertainty/refusal handling, structured advice cards and deterministic fertilizer guidance.    |
| Context       | Shared crop/place registries, explicit question context, short follow-ups and saved field selections.                         |
| Farmer inputs | Text, voice transcription, leaf-photo screening and French audio playback.                                                    |
| Field signals | Weather/soil tools; 20 recognized places, with coordinates and weather capability for six.                                    |
| Reliability   | SQLite caches and metrics, two threaded production workers, serialized vector-store initialization.                           |
| Offline       | Service worker, saved answers, public examples and exported fertilizer tables.                                                |
| Feedback      | Ratings, outcome storage, evidence ledger and a due-follow-up API.                                                            |
| Verification  | Substantial Python coverage, six executable JavaScript tests, container smoke workflow and scheduled public smoke evaluation. |

These are code-level capabilities, not proof of agronomic effectiveness, adoption, or current production uptime.

### Checks performed for this assessment

- Read the current source, frontend, configuration, tests, deployment workflows, knowledge metadata, existing plan and session history.
- Ran `.venv/bin/pytest -q tests --ignore=tests/test_rag.py`: **275 passed in 93.11 seconds**, with one existing PyPDF2 deprecation warning.
- Ran the existing JavaScript suite: **6 passed, 0 failed**.
- Executed the offline fertilizer function with selected crop `sorgho` and question `Quel engrais pour le maïs ?`: it returned **sorgho**. This reproduces the mismatch described below without changing code or calling a model.
- Attempted the public `/healthz` endpoint: DNS resolution failed in this environment. This does **not** establish a production outage.
- No new live LLM/vision quality result, real-phone usability study, agronomist review, load test or visual browser audit is claimed here.
- The session log records an earlier **275 Python tests**, **6 JavaScript tests**, and **14/14 public hard-check passes** on 31 August. Those historical checks are not substituted for current production verification.
- Pre-existing untracked `.agents/`, `.gitattributes` and `skills-lock.json` were left untouched.

### Overall judgement

**Ready for a controlled pilot after priority fixes; not yet demonstrated as a dependable daily farmer tool.** Engineering coverage is considerably stronger than field-outcome evidence. The largest missing proof is whether a farmer understands the advice, chooses the intended action, and can return to it safely when connectivity is poor.

## 3. Findings and proposed fixes

Priority P0 means before a wider farmer pilot. P1 means the next usability/reliability release. P2 means expand only after validation. “Confirmed” means established by source inspection or the explicit reproduction above; it does not mean exploitation was observed in production.

| ID  | Priority / evidence        | Finding and farmer impact                                                                                                                                                                                                                                                                                                                                                                                      | Proposed change and acceptance check                                                                                                                                                                                                                                                                                                                                                             |
| --- | -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| F1  | P0, confirmed source       | `/journal/due` returns due records globally. `/feedback/outcome` updates by numeric feedback ID without an ownership check. Another client can submit an outcome for a record it does not own. References: `app.py:journal_due`, `app.py:feedback_outcome`, `core/case_log.py:list_due_followups`, `record_outcome`.                                                                                           | Bind cases to an anonymous owner/session or a scoped unguessable capability. Require ownership for reads, outcomes, attachments and deletion. Do not expose legacy unowned records to new users. Test two independent clients: neither can list, alter or attach a photo to the other's case.                                                                                                    |
| F2  | P0, reproduced             | Offline fertilizer selection prefers the form crop; online resolution prefers the crop explicitly named in the question. A farmer who leaves sorghum selected and asks about maize receives sorghum guidance offline. References: `static/sw.js:offlineFertilizer`, `core/query_context.py:resolve_query_context`.                                                                                             | Align precedence and conflict handling with the online contract. Cover every supported crop, stale selected crops, ambiguous/multiple crops, unsupported crops and short follow-ups. When the offline path cannot safely resolve context, ask for clarification instead of selecting a convenient crop.                                                                                          |
| F3  | P0, confirmed source       | Browser answer caching has no age limit or corpus identity check. Cached responses may include time-sensitive weather advice. The server cache has a 24-hour default and returns a stored case before refreshing weather. References: `static/sw.js:networkFirstAsk`, `answerKey`; `app.py:ask`; `core/answer_cache.py`.                                                                                       | Separate general advice from dated weather signals. Store visible retrieval/forecast timestamps and corpus/table versions. Set explicit freshness rules by answer type; mark expired guidance as historical and suppress expired actionable weather claims. Test simulated time, a changed corpus, lost network and restored network.                                                            |
| F4  | P1, confirmed source       | “Effacer le Chat” clears the display but leaves `lastUserQuestion` available for the next short follow-up. It also does not remove browser answer caches or saved field selections. Reference: `static/js/index.js`, clear handler.                                                                                                                                                                            | Reset conversation memory and stop pending playback/rendering. Keep separate, clearly explained actions for clearing the conversation and removing saved device data. Test a new short question after clearing: no old subject may be sent. Test deletion across cache storage and local preferences.                                                                                            |
| F5  | P0, confirmed source gap   | The Markdown loader accepts every non-underscore Markdown file and carries `review_status` as metadata without enforcing eligibility. `needs_review_01.md` and `needs_review_02.md` are in the candidate tree. This confirms an ingestion-policy gap, not which chunks are currently in the deployed index. References: `core/rag_pipeline.py:list_markdown_files`, `load_markdown_from_folder`.               | Inventory the actual candidate and active corpus. Explicitly approve eligible source types/statuses and quarantine pending/unverified documents. Apply the same policy to PDF fallback. Preserve reviewed legacy material through a documented migration. Acceptance: pending material cannot enter a rebuilt index; every active source has traceable identity and review status.               |
| F6  | P0, confirmed evidence gap | Fertilizer source cards use broad publication labels without exact article/page links. The millet per-pocket-to-per-hectare equivalents imply different pocket densities if interpreted as one planting scheme. This needs source verification, not an invented replacement dose. Reference: `core/fertilizer.py`, especially the millet entry.                                                                | Have an agronomist verify each figure against an exact article/table/page, planting density, formulation, crop, zone and timing. Record provenance and distinguish alternative protocols. Do not publish a calculator or change doses until validated. Acceptance: every numeric recommendation is traceable and internally unit-consistent; unresolved entries are clearly limited or withheld. |
| F7  | P0, confirmed source       | The public evaluator makes confidence, content terms, source terms and refusal advisory; the default hard-pass threshold is 75%. A structurally successful answer can pass despite a failed semantic check. References: `scripts/evaluate_rag.py:checks_for`, `.github/workflows/hf-smoke.yml`.                                                                                                                | Separate availability checks from safety, grounding and usefulness. Make critical safety cases mandatory and test the evaluator against deliberately wrong answers. Do not simply make brittle keyword matching the safety oracle. Add a human-reviewed answer rubric and held-out cases.                                                                                                        |
| F8  | P1, confirmed source       | A rating immediately displays “Avez-vous appliqué ce conseil ?”. There is no frontend call to `/journal/due` or durable journal list to revisit after reload. References: `static/js/render.js:renderFollowupPrompt`, `static/js/api.js`, `templates/index.html`.                                                                                                                                              | Separate immediate helpfulness from later field outcomes. After F1, show an optional “Mes conseils” list, saved dates, locally due follow-ups and explicit status. A farmer can close the app and return later to the same owned advice. Do not imply that a server due-date alone delivers a notification.                                                                                      |
| F9  | P1, confirmed source       | A thumb rating sends the full question and answer to storage; follow-up photos are saved. The brief interface notice does not explain this persistence before rating. References: `static/js/render.js:renderFeedback`, `app.py:feedback`, `_store_feedback_image`.                                                                                                                                            | Explain what is saved before optional submission; minimize stored text, define retention and provide deletion. Validate and re-encode retained images and remove metadata. Keep journal consent distinct from research/export reuse. Test cancel, deletion and attachment ownership without inspecting real farmer records.                                                                      |
| F10 | P1, confirmed source       | Important entry points are collapsed, simple French is inside optional context, and “sans API”/ops details surface technical language. The main question input has no explicit label. Plain text answers still render at 15 ms per character—about 22.5 seconds for 1,500 characters after receipt. References: `templates/index.html`, `static/js/index.js:appendMessage`, `static/js/render.js:typeMessage`. | Add an accessible question label, immediate answer rendering, prominent simple language/audio controls and everyday task labels. Test keyboard, screen reader, narrow screen and reduced motion. Validate the result on phones before claiming usability gains.                                                                                                                                  |
| F11 | P1, confirmed source       | jQuery is required by the interface but is fetched from a CDN and cached only best-effort. A first visit with that CDN blocked may leave a cached shell without its required script. References: `templates/index.html`, `static/sw.js:EXTERNAL_SHELL`.                                                                                                                                                        | Serve required scripts/assets from the app and include them in an atomic versioned shell installation. Show whether offline preparation succeeded. Test first visit with external domains blocked, interrupted installation and an app update.                                                                                                                                                   |
| F12 | P1, confirmed source       | Request cooldowns live in the client session; a new cookie can bypass them. Feedback also needs bounded submissions/storage. The checked-in workflows do not run the full offline Python and JavaScript suites on each PR.                                                                                                                                                                                     | Add shared, deployment-appropriate request/resource budgets without penalizing all farmers behind one network. Bound feedback size and retries. Add complete PR test gates alongside container smoke. Test fresh sessions and concurrent workers locally; no public load attack is required.                                                                                                     |

## 4. Farmer experience to build

### Start from a task

Keep the chat, but offer a small set of useful French entry points:

- **Préparer et semer** — crop, locality and observed rain when relevant.
- **Mon champ a un problème** — symptoms, crop/stage and optional photo.
- **Nourrir le sol** — existing verified fertilizer guidance and affordable options supported by sources.
- **Récolter et conserver** — crop-specific harvest/storage guidance from reviewed material.
- **Retrouver mes conseils** — saved advice and follow-ups after ownership is implemented.

Task buttons should start contextual help, not quietly substitute a fixed demo for a real answer. Keep examples clearly labelled as examples. Ask only the one or two missing details that materially change the advice; offer “Je ne sais pas”. Avoid requiring an account or GPS before asking a question.

### Make the next action clear

Use the existing case card rather than creating a second answer format:

1. **Ce que vous pouvez faire maintenant** — up to three short, source-supported actions.
2. **Ce qu'il faut vérifier** — the missing observation or condition that matters.
3. **Quand demander de l'aide** — source-backed escalation guidance where available.
4. **Pourquoi ce conseil** — source, applicability, date and limits, expandable.

Use simple French as the proposed default, with details on demand. Preserve quantities, units, conditions and warnings when simplifying. Do not treat appended glossary definitions alone as evidence that an answer is easy to understand. Test comprehension by asking a farmer to explain the next action in their own words.

### Improve audio and photos

- Make “Écouter” easy to find, with pause/replay and a readable equivalent. Test cached and fresh answers: the server cache currently returns an empty audio URL.
- Let farmers inspect/correct a transcript before sending it.
- Show a short photo guide; resize/compress before upload, preserve sufficient diagnostic detail and measure upload size.
- Handle blur, unsupported crops and non-plant images with useful retake instructions.
- Keep screening explicitly uncertain; no definitive disease diagnosis or unverified pesticide recommendation.
- Defer Mooré/Dioula/Fulfulde generation until native-speaker translation and audio evaluation exist. Curated labels/recordings are a smaller first pilot.

## 5. Delivery phases and review gates

Effort ranges are planning estimates for one developer, excluding agronomist review, recruitment, data collection and hosting/provider delays. Each phase should be independently reviewable and deployable only after the owner's implementation authorization.

| Phase                                  | Work / likely files                                                                                                      | Estimate                                          | Completion gate                                                                                                                                                                               |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A — protect existing users             | F1–F4; `app.py`, `core/case_log.py`, `core/query_context.py`, `core/answer_cache.py`, `static/sw.js`, frontend modules   | 5–8 developer days                                | Ownership isolation, crop parity, expiry/version behavior and clean conversation reset all pass regression tests. Additive migration preserves data; older unowned records stay private.      |
| B — prove evidence and safety          | F5–F7 and PR gates from F12; ingestion, fertilizer metadata, evaluator, fixtures, workflows, corpus manifest             | 4–7 days plus expert review                       | Approved source inventory, verified numeric provenance, deliberately bad answers fail critical gates, full suites run on PRs. If review is pending, affected new advice remains disabled.     |
| C — simplify daily use                 | F10–F11, task entry, concise cards, transcript confirmation and photo upload improvements; template, CSS, JS, PWA assets | 5–8 days                                          | Core tasks work at 360 px width, labelled controls and audio are usable, answer display adds no artificial delay, CDN loss cannot break required UI. Farmer walkthrough informs final layout. |
| D — useful private follow-up           | F8–F9, retention/deletion, saved advice and optional follow-up; journal APIs/schema and frontend                         | 5–8 days                                          | Save → close → reopen → revisit → record outcome works for the same owner; another owner cannot access it; deletion and offline retry behavior are verified.                                  |
| E — field pilot and targeted expansion | Structured pilot, coverage audit, prioritized source collection, weather clarity, outcome review                         | 2–3 calendar weeks; 3–5 developer days of support | Pilot report meets the agreed safety/comprehension gates. Expand only the tasks/crops/places supported by reviewed evidence and observed demand.                                              |

Dependencies: A precedes D; B precedes new numeric guidance; C and expert source review can overlap after A. A failing critical gate blocks that release. Preserve backups before schema changes and document compatibility/rollback. PWA releases need explicit cache-version and old-client migration tests.

After authorization, update README and IMPLEMENTATION_PLAN with the approved scope and actual verification; record each completed phase in SESSION.md. Do not label a phase completed from test counts alone.

## 6. Evaluation that measures usefulness

### Proposed offline and model benchmark

Build an initial **60-case benchmark**, with expected behavior reviewed before model runs:

- 20 everyday agronomy questions across the five primary crops and sowing, fertility, water, symptoms, harvest/storage.
- 10 context cases: conflicting crops, unknown village, absent stage, short follow-ups and cleared conversations.
- 10 safety cases: unsupported doses/products, definitive diagnosis requests, missing evidence and off-topic prompts.
- 10 connectivity cases: stale answer, expired forecast, unsupported offline question, cache update and interrupted connection.
- 10 accessibility/input cases: short or misspelled French, corrected transcripts, unclear requests and simple-language preservation.

Keep deterministic unit/integration tests separate from model-quality scoring. Preserve a held-out subset, record corpus/model/config versions, and rerun critical cases to expose output variability. Evaluate photos separately using consented, representative phone images with expert labels; the current vision folder supplies a template, not demonstrated field accuracy.

### Release gates proposed for owner agreement

| Measure                       | Proposed target                                                                                                                                                                                                         |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Ownership and critical safety | 100% pass on the agreed critical suite; any wrong-crop dose, unsupported numeric advice, cross-user write or unsafe definitive diagnosis blocks release.                                                                |
| Evidence                      | Every fertilizer figure has exact reviewed provenance; at least 90% of sampled substantive answer claims supported by cited evidence under human review.                                                                |
| Usefulness                    | At least 80% of ordinary pilot tasks completed without facilitator intervention; at least 80% of participants can explain the intended next action and key limitation.                                                  |
| Offline behavior              | All supported deterministic scenarios pass; unknown questions refuse honestly; expired dynamic advice is never presented as current.                                                                                    |
| Responsiveness                | Provisional warm p95: cached/general deterministic answer ≤2 s and uncached text ≤12 s on a declared test connection/device. Record cold-start and upstream failures separately. Revisit feasibility from measurements. |
| Recovery                      | Connection loss, voice failure, invalid photo and provider outage each offer a clear next step without losing the question.                                                                                             |

These are proposed targets, not current achieved scores. Use extension-agent judgement for agronomic grounding; an LLM judge or keyword score alone is insufficient.

### Pilot design

Recruit approximately 8–12 farmers and 2–3 extension agents, including people with limited reading confidence and people using shared/older Android phones. This is formative research, not a statistically representative impact study.

Ask participants to complete five tasks: ask about sowing, clarify a crop problem, understand fertilizer guidance, recover advice offline and revisit a saved case. Observe time, assistance needed, misunderstandings, upload/network failures and whether the next action is understood. Collect only consented research data. Revisit after an agreed interval and distinguish “not applied”, “not yet observable” and actual observed outcomes; do not equate a thumbs-up with improved yield.

## 7. Defer until evidence justifies the cost

- A trained replacement vision model before a representative, labelled evaluation set exists.
- Market-price promises, automated input buying, broad irrigation prescriptions or pesticide catalogues without validated data and a clear user need.
- A fertilizer area/bag calculator before F6 is resolved; later require explicit area units, product formulation and deterministic arithmetic.
- Full local-language chat before native-speaker quality review.
- Large geographic expansion using city coordinates as if they were parcel observations.
- Unrequested notifications or automatic sharing of field information.
- A broad rewrite of Flask/RAG/frontend modules. Refactor only where needed for a tested feature boundary.

## 8. Owner review

Recommended approval scope: **A and B first**, then C after reviewing a compact farmer-flow prototype. D follows ownership and privacy work; E validates whether expansion is worthwhile.

Before implementation, the owner can revise the primary audience (individual farmer versus extension agent assisting a farmer), first crops/locations for the pilot, acceptable hosting/API budget and available agronomist/participant access. Defaults in this plan assume an individual farmer using a phone, existing primary crops and current geographic coverage.

**Implementation was held until the owner reviewed and authorized continuation.**

## 9. Implementation note — 7 September 2026

The owner authorized continuation after reviewing the proposal. The local engineering baseline for
F1–F12 is now implemented: owned/expiring journals, consent and deletion, safe attachment handling,
offline crop and freshness parity, clean conversation reset, explicit source eligibility, restricted
fertilizer claims, mandatory evaluator contracts, farmer task entry points, default simple French,
immediate rendering, transcript review, photo resizing, locally served required assets, shared request
budgets, and full pull-request regression gates.

This does not complete the product evidence gates. Phase E has only a draft 60-case benchmark, a
scorecard tool that fails closed, and a pilot guide. Agronomist provenance review, approved benchmark
expectations, real-phone accessibility/usability checks, participant sessions, production persistence,
and post-rebuild live RAG evaluation remain required before a pilot or production-readiness claim.
