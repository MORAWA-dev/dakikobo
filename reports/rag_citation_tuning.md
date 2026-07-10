# RAG citation tuning notes

Date: 2026-07-10  
Target: live Space `https://kimcomehome-dakikobo.hf.space`

## Live baseline (`scripts/evaluate_rag.py`)

- Health: `rag_ready=true`, warm-up finished successfully.
- Result: **8/8 passed** on the public smoke suite.
- Notable latencies: soil ~4.8s, fertilizer TTS path ~3.2s, RAG ~1.4–2.4s.

## Issues observed even on PASS cases

1. **Maïs / feuilles** sometimes cited the generic India-oriented
   *Farmer's Handbook on Basic Agriculture* instead of a Burkina/crop-specific
   document.
2. **Arachide** answers could cite broad household/zone mapping PDFs that
   mention Burkina but not groundnut agronomy.

## Tuning applied

| Change | Rationale |
|--------|-----------|
| Expand disease/leaf citation aliases (`feuille`, `tache`, `carence`…) | Better topic overlap for symptom questions |
| Demote weak generic titles in ranking (`_WEAK_SOURCE_MARKERS`, −0.10) | Prefer crop-specific sources when scores are close |
| Rank by crop-overlap then adjusted score | Crop match beats a slightly higher generic score |
| If crop named but no crop-matched source survives, cap cards to 1 and confidence ≤ Moyen | Avoid overconfident generic citations |
| Score lookup `k=6 → 8` | Slightly wider pool for secondary titles |
| Extra eval cases: compost/ProSol + field-context semis | Cover fertility docs and context form path |

Thresholds left as defaults (`SIMILARITY_THRESHOLD=0.2`,
`CITATION_SCORE_MARGIN=0.12`, `MAX_RAG_SOURCES=2`) because the live suite was
already green; tuning focuses on ranking quality, not hard cutoffs.

## Re-run

```bash
.venv/bin/python scripts/evaluate_rag.py \
  --base-url https://kimcomehome-dakikobo.hf.space \
  --output reports/rag_eval_results.md
```

After deploy, re-check maize leaf and arachide cases manually for source titles.

## Post-deploy follow-up (2026-07-10 later)

Live suite after deploy: **9/10** (SoilGrids `/soil` returned HTTP 502 — external
API cold start / timeout, not a RAG regression).

Manual maize/arachide still sometimes surface generic Burkina reports. Additional
hardening:

- Drop weak titles entirely when any non-weak source remains.
- Expand weak markers (`agrobusiness`, `comprehensive report`, …).
- Prefer crop tokens in **title** when ranking.
- Cap confidence at Moyen when the only remaining source is weak.
- SoilGrids: default timeout 18s + one retry on 5xx/timeout.
