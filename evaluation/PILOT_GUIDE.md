# Farmer pilot and expert review — not yet conducted

Use `farmer_benchmark.json` as a **draft**, not as agronomic truth. An extension agent must approve expected observations before any live model benchmark. The 60 cases contain 20 ordinary agronomy, 10 context, 10 safety, 10 connectivity and 10 input scenarios. The split is 40 development / 20 held-out. Keep held-out examples out of prompt tuning.

## Before pilot release

1. Review `Data/reviews/SOURCE_ELIGIBILITY_2026-09-06.md`. Pending guides currently cannot enter the index. Do not set a review flag just to restore coverage.
2. Resolve the exact source/article/page, crop, zone, planting density, formulation and timing for every fertilizer figure. Millet microdose equivalents have been withheld; other figures retain a visible pending-reference limitation. No numeric calculator is enabled.
3. Back up runtime data and document the deployed commit, corpus hash, provider/model settings and dates. Passing local tests does not satisfy the expert or pilot gates.
4. Verify production persistence for the anonymous session secret and journal. Without persistent storage, host restarts may lose these records. Explain that clearing cookies loses access; do not offer account recovery that does not exist.

## Run the sessions

Recruit 8–12 farmers and 2–3 extension agents with consent, including participants with limited reading confidence and shared/older Android phones. These are formative observations, not representative yield evidence. Do not collect names, precise farm coordinates or private photos unnecessarily.

Give five tasks: ask about sowing, clarify a crop problem, understand fertilizer guidance, retrieve an answer offline, and return to a saved case. Record device, network conditions, task time, help needed, misunderstandings and whether the participant can explain the intended next action and limitation. Treat local language/audio quality as unvalidated until native-speaker checks are available.

For each substantive answer, record its claims, exact supporting source excerpts/page references, and the expert's grounding judgement. Measure the 90% grounding target at the **claim** level. Track at least 80% independent task completion and next-action comprehension at the **participant/task** level. The scenario scorecard is a screening aid, not a substitute for these denominators.

Use the due follow-up date as an in-app prompt when the user returns. No notifications are sent. Separate immediate usefulness from later field outcomes and distinguish not applied, not yet observable, unchanged, improved and worse. Never infer a yield gain from a rating.

## Scorecard

```bash
.venv/bin/python scripts/farmer_evaluation.py --prepare /tmp/farmer-scorecard.csv
.venv/bin/python scripts/farmer_evaluation.py --assess /tmp/farmer-scorecard.csv
```

Blank or incomplete reviews fail. Critical safety failures block release regardless of the overall score. The tool accepts explicitly entered human scores; it cannot verify expertise or prove that a session happened. Use non-identifying reviewer codes and keep filled scorecards private. Preserve observations and failed examples to prioritize the next iteration.

## Release decision

Publish a report with achieved scores, failures, source gaps, tested devices and sample limitations. Do not claim production readiness while ownership/safety regressions fail or agronomic evidence remains unresolved. Do not publish farmer records, photo attachments or filled evaluation exports.
