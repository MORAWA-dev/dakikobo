# Evaluation Reports

This directory holds generated DakiKobo evaluation reports.

Generate the public Space report with:

```bash
python scripts/evaluate_rag.py
```

The default output is:

```text
reports/rag_eval_results.md
```

Reports are snapshots of live app behavior. Regenerate them after RAG, source,
prompt, weather, soil, or deployment changes.
