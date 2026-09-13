# DakiKobo — Independent Review & Improvement Plan (Kimi)

Date: 12 September 2026
Status: review complete; plan proposed for owner authorization. No code was edited for this document.
Scope: `plans/dakikobo_assessment_and_plan.md`, `plans/FARMER_IMPROVEMENT_PLAN_2026-09-06.md`,
`plans/IMPLEMENTATION_STATUS_2026-09-09.md`, `PROJECT_STATE.md`, `TODO.md`, `SESSION.md`,
git state, `core/`, and a fresh run of both offline test suites.

---

## 1. What I verified myself (not taken from the docs)

| Check | Result |
|---|---|
| `pytest -q tests --ignore=tests/test_rag.py` | **640 passed**, 1 PyPDF2 deprecation warning (47 s). Matches the status doc's claim exactly. |
| `node --test tests/js/*.test.js` | **27 passed**, 0 failed. Matches the status doc. |
| Git state | `main` at `40bb8a85`; **28 modified files uncommitted (+921/−81)**; stash `codex-plan-integration-20260909` still present. |
| Plan Phases 0–5 (original engineering plan) | All landed: `core/places.py`, `core/crops.py`, `core/retrieval.py`, `core/answer_cache.py`, `core/cache.py`, `core/journal.py`, `core/source_policy.py`, `core/rate_budget.py`, `core/answer_safety.py` all exist. |
| Fertilizer doses | Confirmed withheld pending F6 agronomist provenance (`core/fertilizer.py:125`). |
| Source eligibility | `core/source_policy.py` exists; per `PROJECT_STATE.md` only **2 sources are currently eligible** (CILSS, MAERAH/OAPH). |
| Benchmark | `evaluation/farmer_benchmark.json` is `version: 1`, `draft_pending_agronomist_and_farmer_review`. |

The docs' claims about test counts and implemented phases are accurate. This is unusually
honest status reporting — the plan docs distinguish "tested" from "proven in the field"
throughout, and that discipline should be kept.

## 2. Assessment of the existing work

**Strong:**
- The failure-mode-audit style of `dakikobo_assessment_and_plan.md` (§7) is the right
  method for this codebase, and it worked: the three live frontend defects (B1–B3) are
  fixed and the missing abstractions (A1–A3) now exist as real modules.
- The safety posture is genuinely conservative: doses withheld rather than guessed,
  source eligibility enforced at ingestion, offline/online crop precedence aligned,
  ownership checks on the journal.
- Test coverage tripled (212 → 640) while the plan executed.

**Risks and gaps the current docs under-weight:**

- **R1 — A month of work is uncommitted.** 921 insertions across 28 files plus an
  integration stash, sitting only on this laptop. One disk failure or one bad
  `git checkout .` loses the security hardening, tests, and doc sync. This is the
  single highest-severity finding in this review and it is operational, not technical.
- **R2 — The corpus is the real bottleneck, not the code.** Only 2 sources pass
  `source_policy`. The 20-cell coverage matrix exists but every cell awaits agronomic
  approval, and two candidate extracts already failed fidelity checks (IITA I3 not
  found in the guide; ProSol P1 is interpretive). RAG quality cannot improve until
  eligible material grows.
- **R3 — The critical path is human, and nothing is scheduled.** F6 agronomist review,
  benchmark expectation approval, and the field pilot are all "required" with no
  owner, date, or prepared packet. Engineering is ready and waiting on a meeting.
- **R4 — Live state is unverified since the corpus policy tightened.** No rebuild of
  the hosted vector store against the 2-eligible-source corpus, no post-rebuild live
  RAG evaluation, and HF target persistence is still unproven. `/healthz` was last
  verified live on 2026-07-10.
- **R5 — Small debt items:** PyPDF2 deprecation (move to `pypdf`), `langchain==0.2.0`
  `RetrievalQA` still deprecated (parked by design, keep parked), WASCAL/INERA/AGRHYMET
  still unreachable, no full privacy-policy page.

## 3. Improvement plan

Phases are ordered by risk-reduction per effort. K0 and K1 require no agronomist and
no pilot. K2–K4 prepare the human gates. K5 is the gate itself.

### Phase K0 — Protect the existing work (half a day)

1. Commit the 28 modified files as one reviewed "security hardening + ticket 02–07
   verification" changeset, after `git diff --check` and one more full-suite run.
   The repo convention of leaving work unindexed made sense during the integration
   window; that window has passed.
2. Drop or document the stash `codex-plan-integration-20260909` (it was already
   restored per the status log; keeping an ambiguous stash invites a future mistake).
3. Push to `origin/main` (or open a PR per the repo's PR-based history).

Done when: `git status` is clean except intentionally-untracked files, and the stash
list is empty or renamed with a README note.

### Phase K1 — Verify the live system end-to-end (1 day, needs network)

1. Rebuild the vector store against the current 2-source eligible corpus and confirm
   the manifest guard behaves as designed.
2. Run `scripts/evaluate_rag.py` against the live Space; record results in
   `reports/rag_eval_results.md`. Verify `/healthz`, `/version`, and one TTS round-trip.
3. Check that answers still degrade honestly with a thinner corpus (expect more
   « Faible » confidence and more honest refusals — that is correct behavior, not a
   regression to fix by loosening policy).

Done when: a dated live-eval report exists and the served corpus identity is recorded.

### Phase K2 — Grow the eligible corpus (3–5 days + human review)

This is the highest-leverage engineering work remaining.

1. Retry WASCAL, INERA, and AGRHYMET reachability (`scripts/check_trusted_sources.py`);
   record outcomes in `reports/trusted_source_health.md`.
2. For each of the 20 matrix cells with an approved-quality candidate, run the existing
   offline scrape → pending → review → promote workflow. Target: **at least 2 more
   eligible sources** (IITA cowpea guide and ProSol are closest — pages are already
   verified and hashed).
3. Add document-level metadata during ingestion (open TODO item) so source cards can
   carry zone/scope for the new documents.
4. Quarantine any source with unclear rights (open TODO item).

Done when: `audit_source_eligibility.py` reports ≥4 eligible sources and every active
chunk traces to a reviewed file.

### Phase K3 — Make the agronomist review cheap to run (1 day)

The review keeps not happening because it is unbounded. Make it a 2-hour appointment:

1. Produce a single review packet: the 20-cell matrix + the two verified PDF page
   extracts + a one-page sign-off form (approve / correct / reject per cell).
2. Produce the benchmark approval sheet: the 60 cases in
   `evaluation/farmer_benchmark.json` with expected behavior, marked dev vs held-out.
3. Define the unblock rule explicitly: cells the agronomist does not reach stay
   ineligible; nothing is approved by silence.

Done when: both packets exist as printable Markdown/PDF and the owner has a named
reviewer and a date.

### Phase K4 — Pilot readiness sprint (3–4 days, after K1)

1. Finish the Phase D leftovers the farmer plan flags as incomplete: visible
   version/freshness presentation on cached answers, and real-phone browser cycle
   (the Chromium check covers 320 px headless, not a physical low-end Android).
2. Run `evaluation/PILOT_GUIDE.md` as a rehearsal with 1–2 non-farmer testers on a
   real phone over a throttled connection; fix what breaks before recruiting farmers.
3. Privacy policy page (open TODO item) — one static French page, linked from the
   existing privacy note.

Done when: the five pilot tasks run start-to-finish on a physical phone with no
facilitator workaround.

### Phase K5 — The human gates (calendar-bound, not effort-bound)

1. Agronomist session (K3 packet) → unblocks F6 doses and matrix promotions.
2. Benchmark expectations approved → benchmark runs become release gates.
3. Field pilot per the farmer plan's design (8–12 farmers, 2–3 agents) → decides
   expansion. Only after this should local-language labels, vision-model evaluation,
   or new crops be reconsidered.

### Parked (explicitly not in this plan)

- LCEL rewrite of the RAG chain (parked by the original plan; still correct).
- Custom vision model (gated on labelled real-phone data).
- Mooré/Dioula/Fulfulde generation (gated on native-speaker review).
- PyPDF2 → `pypdf` migration: fold into K2 only if ingestion code is touched anyway;
  otherwise defer. A deprecation warning is not a defect.

## 4. Difference from the existing plans

The two existing plans are strong on *what to build* and already executed it. This
plan is deliberately narrower: it assumes the engineering baseline is done and attacks
the three things the docs themselves admit are missing — **uncommitted work (R1),
thin eligible corpus (R2), and unscheduled human gates (R3)**. If only one thing
happens next: **K0**. If two: K0 + K3, because K3 is what finally moves the critical
path off the engineering team and onto the calendar.

---

## Addendum — implementation status, 12 September 2026 (second pass)

Status wording follows the review rule: a phase is *complete* only with
committed, reproducible evidence.

| Phase | Status | Evidence / remaining action |
|---|---|---|
| K0 | **Complete** | Commits `38cfbb19` and `66d15593` on `chore/security-hardening-and-verification`. The stash `codex-plan-integration-20260909` was verified redundant (distinctive strings confirmed present in HEAD; content captured by `38cfbb19`) and dropped on 2026-09-12. |
| K1 | **Complete** | Committed evidence: `reports/live_verification_2026-09-12.md` (current-head section) and `reports/rag_eval_results.md`. The Space was redeployed at commit `a2798eb3`; `/healthz` ok, `/version` commit matches, `x-dakikobo-corpus: 11391cefa86f9f32` matches the local post-K2 rebuild, a full TTS MP3 (174336 bytes) was fetched, and the live evaluator passed 14/14 (3 advisory warnings). Deployed tree vs branch head differs only in docs/evidence files and the audit-script default path — no runtime behavior change. |
| K2 | **Partial / blocked by human approval** | Done: `scope` document metadata in ingestion, explicit quarantine (`rights_unclear` / `_quarantine/`, quarantine always wins), FAO synthesis formally quarantined, dated eligibility audit `Data/reviews/SOURCE_ELIGIBILITY_2026-09-12.md`, `DATA_SOURCES.md` drift corrected, reachability results committed in `reports/trusted_source_health.md`. **Not done:** the 4-source target. Remaining exact actions: (1) agronomist signs packet cells (K3), (2) FAO reuse terms confirmed, (3) only then pending → review → promote. |
| K3 | **Ready for human review** | `Data/reviews/AGRONOMIST_REVIEW_PACKET_2026-09-12.md` now includes verbatim source-page annexes with source name, SHA-256, physical/printed pages and fidelity notes; I3 explicitly flagged as not present in the original. Reviewer name, date, decisions and signature remain blank. Not complete until a real reviewer signs. |
| K4 | **Blocked / partial** | No physical-phone test was performed; headless Chromium (`reports/browser_replay_check/`) is not represented as one. Remaining exact action: `evaluation/PILOT_REHEARSAL_CHECKLIST_2026-09-12.md` executed on a real low-end Android phone with 1–2 non-farmer testers. |
| K5 | **Not started** | Human gates (agronomist session, benchmark approval, field pilot) unchanged. |
