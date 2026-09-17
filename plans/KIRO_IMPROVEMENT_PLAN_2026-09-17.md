# DakiKobo — Kiro Improvement Plan

Date: 17 September 2026

Role: primary implementation agent

Starting point: GitHub `main` after PR #12 (`059cee2bf3f8b7d442f3a080a3ba9c355bb210f2`)

Status: ready to execute as separate draft pull requests

## Objective

Move DakiKobo from a technically complete pilot candidate to a reviewable field-release candidate. Concentrate on source coverage, reproducible evaluation, and deployability. Preserve the product's cautious French advice, deterministic fertilizer rules, private journal ownership, and fail-closed source policy.

## Operating rules

1. Fetch the latest `origin/main` before every task and use a clean worktree. The owner's shared checkout contains unrelated local files and must remain untouched.
2. Create one focused branch and one draft PR per task. Do not merge PRs.
3. Read `AGENTS.md`, `PROJECT_STATE.md`, `IMPLEMENTATION_PLAN.md`, and `SESSION.md` before editing.
4. Keep user-facing application text in French. Keep secrets in process environment settings.
5. Treat human review as evidence: blank fields stay blank, pending decisions stay pending, and missing evidence keeps the release decision at `REPORTÉ`.
6. Never enable numeric fertilizer guidance or promote a source without documented agronomist approval.
7. Preserve existing safety behavior and refusals for unsupported questions.

## Task K1 — Complete the source-review candidate packet

### Scope

Improve the Ticket 05 review material so an agronomist can decide every pilot-scope cell without searching the repository. Work only with sources already present or independently retrievable from their recorded authoritative locations.

### Steps

1. Reconcile `Data/reviews/CROP_COVERAGE_MATRIX_2026-09-09.md`, `Data/reviews/AGRONOMIST_REVIEW_PACKET_2026-09-12.md`, and `Data/reviews/SOURCE_ELIGIBILITY_2026-09-12.md`.
2. For every pilot-scope matrix cell, record one of:
   - candidate excerpt with source, physical PDF page, printed page when present, crop, zone, and `pending_human_review`; or
   - explicit `no verified candidate` with the searched sources listed.
3. Verify every quoted excerpt against the original page. Mark paraphrases and interpretations as such.
4. Regenerate the eligibility audit from repository state.
5. Keep all newly prepared candidates ineligible until a human signs them.

### Acceptance criteria

- Every pilot-scope cell has a candidate or an explicit documented gap.
- Every candidate traces to an original file and page.
- Rights uncertainty and fidelity uncertainty remain visible.
- No reviewer, approval, date, signature, dose, or field result is invented.
- `NUMERIC_GUIDANCE_VERIFIED` remains `False` unless the repository contains new, explicit human approval supplied by the owner.

### Verification

```bash
.venv/bin/pytest -q tests/test_source_policy.py tests/test_ingestion.py
.venv/bin/pytest -q tests --ignore=tests/test_rag.py
pnpm test:js
.venv/bin/python scripts/export_offline_fertilizer.py
git diff --exit-code -- static/data/fertilizer.json
git diff --check
```

### Deliverable

Draft PR titled `Prepare complete Ticket 05 agronomist review packet`. Report covered cells, unresolved cells, candidate status counts, test results, CI results, and exact human blockers.

## Task K2 — Make the release evaluation reproducible

Start after K1 is open or merged. Base the branch on the latest `main`, not on K1 unless the task genuinely requires K1 files.

### Scope

Make the Ticket 09 offline evaluation produce a complete, deterministic evidence scaffold while keeping all human and live gates pending.

### Steps

1. Audit the development/held-out split, claim ledger, participant-task ledger, and release-decision generator.
2. Add tests for missing evidence, duplicate identifiers, denominator calculations, threshold boundaries, and fail-closed release decisions.
3. Generate a dated decision scaffold containing commit, corpus identity, model configuration, policy revision, and each unresolved gate.
4. Document the live command for an authorized target without embedding credentials or claiming that it ran.

### Acceptance criteria

- Development and held-out cases cannot be mixed silently.
- Claim grounding uses claims as the denominator and requires at least 90% expert-adjudicated grounding.
- Pilot success and comprehension use participant-task observations and each require at least 80%.
- Missing evidence always produces `REPORTÉ`.
- The generated scaffold contains no fabricated reviewer or participant data.

### Verification

```bash
.venv/bin/pytest -q tests/test_farmer_evaluation.py tests/test_evidence_ledger.py tests/test_evaluate_rag.py
.venv/bin/pytest -q tests --ignore=tests/test_rag.py
pnpm test:js
git diff --check
```

### Deliverable

Draft PR titled `Harden reproducible release-evaluation evidence`. Report the generated scaffold path, test counts, CI results, and the commands a human must run for live evaluation.

## Task K3 — Prepare production durability verification

Start after K2. This task prepares and automates safe checks; it does not claim provider durability without running on the provider.

### Scope

Turn the existing local Docker journal rehearsal into a provider-neutral deployment verification procedure for the authorized hosting target.

### Steps

1. Define preflight checks for a durable mount, stable secret, private data paths, security headers, `/healthz`, and `/version`.
2. Add a dry-run or local-fixture mode where useful, without weakening production checks.
3. Document backup, restore, container replacement, host rebuild, and rollback evidence fields.
4. Ensure evidence output excludes questions, answers, photos, recordings, cookies, tokens, and secrets.

### Acceptance criteria

- A human can execute the procedure on the target without editing source code.
- Each step records pass/fail, timestamp, target revision, and non-sensitive evidence.
- A failed persistence, ownership, header, or private-path check stops the release decision.
- Local rehearsal remains clearly distinguished from provider verification.

### Verification

```bash
.venv/bin/pytest -q tests/test_docker_journal_rehearsal.py tests/test_recovery.py
.venv/bin/pytest -q tests --ignore=tests/test_rag.py
pnpm test:js
git diff --check
```

### Deliverable

Draft PR titled `Prepare provider durability verification`. Report automated coverage, human-only target steps, test results, CI results, and deployment blockers.

## Task K4 — Close stale documentation after accepted changes

Start only after K1–K3 are reviewed. Update status documents to match accepted work. Record preparation as preparation and external proof only after the owner supplies it.

### Acceptance criteria

- `README.md`, `IMPLEMENTATION_PLAN.md`, and `PROJECT_STATE.md` agree.
- Historical sections are labeled historical.
- No fixed commit is described as permanently current.
- Physical-phone, agronomist, pilot, live-model, and hosting evidence remains pending unless supplied and traceable.

### Verification

```bash
git diff --check
python -m pytest -q tests --ignore=tests/test_rag.py
pnpm test:js
```

## Parked work

- Agent hand-off sheet: begin only if the pilot confirms the need.
- New crops or languages: begin only with reviewed sources and qualified language review.
- Custom disease model: begin only with a labeled, consented image dataset and evaluation protocol.
- Fertilizer-dose enablement: begin only after explicit agronomist approval and deterministic-rule updates.

## Required report for every task

- PR URL and head SHA
- Base SHA
- Files changed
- Acceptance criteria satisfied
- Exact Python and JavaScript test totals
- GitHub check results
- Remaining blockers and who can resolve them
- Confirmation that nothing was deployed or merged
