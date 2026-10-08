# DakiKobo next-work and synchronization plan

Date: 2026-10-08  
Purpose: give a fresh coding chat a small, evidence-based sequence of work while
keeping the local checkout, GitHub, and the Hugging Face Space synchronized.

## Current baseline

- GitHub `origin/main` is the canonical accepted application snapshot.
- The Hugging Face Space has a separate Git history. Its commit hash is expected
  to differ from GitHub even when the deployed files are identical.
- Before this plan was added, local `main` and `origin/main` were
  `f75c4c39085bebf3cab35a51d27a21256336b57f`; the live Space reported
  `ac35e8857a8899fe5391030f17190ce74583abaa`, `rag_status=ready`, and a healthy
  `/healthz` response.
- There were no open GitHub pull requests.
- The latest verified engineering baseline is 717 Python tests passed with one
  skip, 33 JavaScript tests passed, all four GitHub CI jobs passed, and the
  strict live RAG evaluation passed 14/14.
- Only the reviewed CILSS and MAERAH/OAPH documents are eligible RAG sources.
  Exact fertilizer figures remain withheld.
- The field-release decision remains **REPORTÉE**. Agronomist approval,
  physical-phone evidence, participant evidence, and hosting durability evidence
  are still missing.

The commit hashes above are a dated audit record. At the start of every new work
session, fetch both remotes and establish the current hashes again.

## Synchronization contract

A change is synchronized only when all of the following are true:

1. It is merged into GitHub `origin/main` after the required checks pass.
2. The shared local `main` is fast-forwarded to that exact GitHub merge commit.
3. That exact GitHub tree is copied into the separate HF deployment history,
   preserving the Space-specific `.gitattributes` file.
4. The HF deployment commit message records the GitHub SHA:
   `Deploy GitHub main <full-sha> to Space`.
5. The public `/version` endpoint reports the new HF commit and ready RAG state;
   `/healthz` reports healthy and ready.
6. The live smoke/evaluation checks pass, and the GitHub-to-HF SHA mapping and
   results are appended to `SESSION.md`.

Never declare synchronization from `git push` alone. Never compare GitHub and HF
commit IDs for equality because their histories are intentionally different.

## Standard delivery procedure

Use this procedure for every implementation phase:

1. Read `AGENTS.md`, the latest `SESSION.md` entry, this plan, and the relevant
   source/review documents.
2. Fetch `origin/main` and `hf/main`. Record the local, GitHub, HF, and live
   `/version` hashes. Preserve existing untracked and generated files.
3. Create an isolated branch/worktree from `origin/main` using the `codex/`
   branch prefix.
4. Make one focused change. Keep user-facing text in French and retain all
   grounding, fertilizer, disease, privacy, and confirmation rules.
5. Run tests appropriate to the change. For application releases, run the full
   offline Python suite, JavaScript suite, fertilizer parity check, compilation,
   and `git diff --check`.
6. Push the branch and open a pull request. Wait for regression,
   build-and-smoke, Chromium rehearsal, and journal-continuity checks. Fix any
   failure before merging.
7. Merge the green pull request and fast-forward local `main` without deleting or
   overwriting untracked files.
8. In a temporary worktree based on `hf/main`, replace the tracked tree with the
   exact `origin/main` tree, restore the HF `.gitattributes`, normalize staged
   files, inspect the staged diff, commit with the GitHub SHA, and push to
   `hf/main`. Do not copy `.git`, `.env`, virtual environments, Chroma state,
   generated audio, feedback exports, case databases, or caches.
9. Wait for the Space to finish building. Verify `/version`, `/healthz`, important
   private-path responses and security headers, then run the strict live RAG
   evaluation. Do not manufacture a pass when credentials or the provider are
   unavailable; record the exact blocker.
10. Append the evidence and the next open item to `SESSION.md`. Clean up temporary
    worktrees and local task branches.

## Prioritized improvement phases

### Phase 0 — Add synchronization guardrails

Create a small verification tool that compares a normalized manifest of the
tracked GitHub tree with the HF deployment tree, excluding only intentional
Space metadata such as `.gitattributes`. It should print the GitHub SHA, HF SHA,
live SHA, differing paths, and a clear pass/fail result. Add a documented manual
or GitHub Actions dispatch for post-deployment verification without committing
tokens. Make updating `PROJECT_STATE.md`, `README.md`, and `SESSION.md` part of
the release checklist.

Completion evidence: tests for manifest comparison, a successful local dry run,
green CI, and a live run against the deployed Space.

### Phase 1 — Improve answers through reviewed sources

The largest product limitation is source coverage. Questions about weeds,
planting practice, crop protection, and soil fertility often need an honest
refusal because the current eligible corpus is narrow.

Prepare the IITA niébé and ProSol soil/fertility candidates for agronomist review
with exact page or excerpt traceability. Add evaluation questions for
`adventices`/weeds and practical crop management before changing eligibility.
Promote only the exact documents and statements approved by the reviewer, rebuild
the vector store, and run regression and live evaluations. Do not infer approval
from the presence of a document in `Data/`.

Completion evidence: signed review records, updated source matrix/metadata,
query-to-evidence tests, evaluation comparison, and no regression in honest
fallback behavior.

### Phase 2 — Validate real phone use

Run the existing physical-phone worksheet at approximately 320 px on a real
device and a constrained connection. Cover text entry, Français simple, voice
recording, TTS playback, photo screening, source cards, journal consent/replay,
offline behavior, and recovery from errors. Record device, browser, connection,
observed result, and evidence. A desktop emulator does not satisfy this phase.

Completion evidence: completed worksheet with real observations and resolved
critical issues. Any local-language labels or comprehension changes require a
qualified reviewer.

### Phase 3 — Prove durable private storage

Confirm whether the HF Space has persistent storage. If it does, configure the
journal path there and execute `evaluation/HOSTING_VALIDATION.md`, including
replacement/rebuild/restore and privacy checks. If persistent storage is not
available, choose and implement a durable backend before promising journal
continuity.

Completion evidence: provider-level allocation/configuration evidence and a
completed hosting validation record. The local Docker bind-mount rehearsal alone
does not satisfy this phase.

### Phase 4 — Run the human pilot and make the release decision

After Phases 1–3, run the prepared farmer/extension-agent pilot. Evaluate claim
grounding of at least 90%, task success/comprehension of at least 80%, and zero
critical safety failures. Generate the release decision from recorded evidence.
Keep the result **REPORTÉE** whenever a required gate lacks evidence.

Completion evidence: anonymized pilot results, adjudicated safety findings, and
an updated release decision artifact.

### Phase 5 — Optional product improvements after the gates

Use privacy-safe operational metrics to add a source-coverage and answer-quality
view for maintainers. Consider richer reviewed weed/adventice guidance and
better field-language labels only after the relevant evidence and reviews exist.
Avoid adding crops, providers, or complex features while the release gates above
remain open.

## Human inputs that an agent cannot fabricate

- An agronomist's explicit source and dose approval.
- Physical-device test observations.
- Farmer or extension-agent consent and pilot responses.
- HF account/storage allocation or credentials that are not already configured.

An agent should complete all preparation, automation, and review materials first,
then state the single missing human action precisely.

## Definition of done for the roadmap

The roadmap is complete when the automated suites and live evaluation pass, the
approved corpus provides traceable crop guidance, phone and hosting validation
records are complete, the pilot meets its thresholds with no critical safety
failure, the release decision is updated from evidence, and local/GitHub/HF are
synchronized under the contract above.

## Prompt for a new chat

Copy and send this prompt from the DakiKobo project:

```text
Continue DakiKobo from plans/DAKIKOBO_NEXT_WORK_PLAN_2026-10-08.md.
First read AGENTS.md, the newest SESSION.md entry, PROJECT_STATE.md, and that plan.
Fetch origin/main and hf/main and verify local, GitHub, HF, and live /version and
/healthz state. Preserve all existing untracked/generated files. Execute only the
first incomplete prioritized phase, using an isolated codex/ branch and focused
changes. Run the required checks, open a PR, wait for all CI jobs, merge only when
green, fast-forward local main, deploy the exact GitHub tree to the separate HF
history, verify the live Space and strict RAG evaluation, and append the evidence
and GitHub-to-HF SHA mapping to SESSION.md. Do not claim human validation or
agronomist approval without recorded evidence. Continue until the phase is fully
finished or one specific human-only input is genuinely required.
```
