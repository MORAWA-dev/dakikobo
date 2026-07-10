# Research notebooks

Colab-oriented experiments that stay **out of the production Flask path**.

| Notebook | Purpose |
|----------|---------|
| `01_disease_photo_eval.ipynb` | Build a leaf-photo eval set, score Gemini prompt variants, export a ship/no-ship report |

Shared helpers (unit-tested): `scripts/vision_eval_helpers.py`.

## Rules

- Do not put API keys in the notebook. Use Colab secrets / environment variables.
- Do not train a custom disease model just for show.
- Ship a custom model only if it beats Gemini on real phone photos **and** refuses blurry/non-plant cases safely.
- Prefer the shared label mapper in `vision_eval_helpers.classify_from_text` so Colab and pytest stay aligned.
