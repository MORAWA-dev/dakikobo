# DakiKobo — Kimi Light Improvement Plan

Date: 17 September 2026

Role: lightweight documentation and repository-hygiene agent

Starting point: latest GitHub `main` after PR #12

Status: ready for small, independent draft pull requests

## Objective

Reduce review effort while Kiro handles deeper work. Kimi should produce small, low-risk changes that improve traceability, documentation quality, and human-test readiness. Each task must be independently reviewable and must not change production behavior.

## Guardrails

1. Use a clean worktree based on the latest `origin/main`; leave the owner's existing checkout untouched.
2. Make one task per draft PR. Keep each PR documentation-only unless a task explicitly permits a test-only edit.
3. Do not edit application code, workflows, dependencies, schemas, source eligibility, fertilizer rules, or generated datasets.
4. Do not deploy, merge, promote sources, approve evidence, or fill human-review fields.
5. Preserve French application wording and the current safety rules.
6. Prefer links to existing canonical files over copying their content.

## Light Task L1 — Repository evidence index

### Scope

Create `evaluation/EVIDENCE_INDEX.md` as a one-page index linking the canonical artifacts for source review, browser rehearsal, journal continuity, pilot rehearsal, benchmark approval, and release decision.

### Acceptance criteria

- Every link resolves inside the repository.
- Each entry states `automated`, `human pending`, `phone pending`, `agronomist pending`, or `hosting pending`.
- The index contains no copied test results that can become stale; it points to the authoritative report or workflow instead.
- No outcome, reviewer, date, or approval is invented.

### Verification

```bash
python - <<'PY'
from pathlib import Path
import re
p = Path('evaluation/EVIDENCE_INDEX.md')
for link in re.findall(r'\[[^]]+\]\(([^)]+)\)', p.read_text()):
    if '://' not in link and not link.startswith('#'):
        assert (p.parent / link.split('#', 1)[0]).resolve().exists(), link
print('all relative links resolve')
PY
git diff --check
```

### Deliverable

Draft PR titled `Add pilot evidence index`. Report the PR URL, head SHA, linked artifact count, and unresolved evidence categories.

## Light Task L2 — Human phone-test worksheet

Start from latest `main` independently of L1.

### Scope

Create a concise printable worksheet under `evaluation/` for the five real-phone journeys already defined by the pilot materials. Reuse existing acceptance gates through links.

### Acceptance criteria

- Blank fields for device, Android/browser version, connection condition, participant code, facilitator intervention, result, and notes.
- Covers narrow viewport, keyboard navigation, microphone denial, audio failure/retry, journal save/reopen/delete, and source-scope display.
- Contains no participant identity fields and no request for question/answer transcripts.
- States that headless Chromium evidence does not replace physical-phone evidence.
- Leaves all results blank.

### Verification

```bash
git diff --check
```

### Deliverable

Draft PR titled `Add real-phone validation worksheet`. Report the PR URL, head SHA, journey count, and the human steps still required.

## Light Task L3 — French user-text inventory

Start from latest `main` independently of L1 and L2.

### Scope

Create `reports/FRENCH_UI_TEXT_AUDIT_2026-09-17.md` by scanning templates and browser JavaScript for visible text. Report suspected English leakage, internal exception leakage, and untranslated accessibility labels. This is a read-only audit report.

### Acceptance criteria

- Every finding includes file, line, visible string, trigger, and severity.
- Test fixtures, developer logs, identifiers, URLs, and code comments are excluded unless users can see them.
- Empty sections explicitly say `Aucun problème observé` rather than inventing issues.
- No application file is changed in this PR.

### Verification

```bash
git diff --check
git diff --name-only origin/main...HEAD
```

The second command must list only the new audit report and any necessary update to `SESSION.md`.

### Deliverable

Draft PR titled `Audit French user-facing text`. Report the PR URL, head SHA, finding counts by severity, and recommended follow-up tasks. Do not fix findings in the audit PR.

## Light Task L4 — Documentation link and stale-status audit

Start after L1–L3 are reviewed.

### Scope

Audit Markdown links and status language across `README.md`, `PROJECT_STATE.md`, `IMPLEMENTATION_PLAN.md`, `DEPLOYMENT.md`, `evaluation/`, `Data/reviews/`, and `plans/`. Fix broken relative links and clearly historical statements only.

### Acceptance criteria

- All changed links resolve.
- Historical test counts and commit hashes are labeled historical.
- Current claims avoid hard-coded wording that becomes false after the next merge.
- Technical, human, phone, agronomist, pilot, and hosting states remain distinct.
- Changes are documentation-only.

### Verification

```bash
git diff --check
python -m pytest -q tests --ignore=tests/test_rag.py
pnpm test:js
```

### Deliverable

Draft PR titled `Repair documentation links and status labels`. Report the PR URL, head SHA, links checked, links fixed, and CI results.

## Stop conditions

Stop and report instead of guessing when a task requires:

- agronomist judgment or source approval;
- participant results or physical-device observations;
- hosting credentials or deployment access;
- live model credentials;
- changes to application behavior, dependencies, workflows, schemas, or safety rules.

## Required report for every task

- PR URL and head SHA
- Base SHA
- Files changed
- Checks performed and exact results
- Remaining human or technical blockers
- Confirmation that the PR is a draft and nothing was merged or deployed
