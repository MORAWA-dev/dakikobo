# Research notebooks

Colab-oriented experiments that stay **out of the production Flask path**.

| Notebook | Purpose |
|----------|---------|
| `01_disease_photo_eval.ipynb` | Build a leaf-photo eval set, score Gemini prompt variants, export a ship/no-ship report |
| `03_scold_retrieval_eval.ipynb` | SCOLD / foundation embedding retrieval scaffold with Colab `embed_image` wiring (no training; Gemini stays production) |
| `04_baseline_classifier.ipynb` | Small baseline classifier research scaffold only — compare to Gemini; do not ship for show |
| `05_export_criteria.ipynb` | Export ship/no-ship gates only — no model packaging until all gates pass |

Shared helpers (unit-tested): `scripts/vision_eval_helpers.py`
(includes pure-Python `rank_by_embedding` / `retrieval_accuracy` for notebook 03).

## Rules

- Do not put API keys in the notebook. Use Colab secrets / environment variables.
- Do not train a custom disease model just for show.
- Ship a custom model only if it beats Gemini on real phone photos **and** refuses blurry/non-plant cases safely.
- Prefer the shared label mapper in `vision_eval_helpers.classify_from_text` so Colab and pytest stay aligned.
- Phone-photo manifests: start from `Data/vision_eval/manifest_template.csv` (see `Data/vision_eval/README.md`).
