# Vision evaluation assets (offline / Colab)

Use this folder for **real** leaf photos and gold labels. Nothing here is
auto-loaded into production RAG.

| File | Role |
|------|------|
| `manifest_template.csv` | Copy to `reports/vision_eval_manifest.csv` and fill rows |
| `samples/` | Optional local images (gitignored if large / private) |

## Labels

Same set as `scripts/vision_eval_helpers.LABELS`:

- `healthy`
- `disease_suspected`
- `pest_damage`
- `not_a_plant`
- `blurry`
- `unknown`

## Workflow

1. Collect phone photos (consent; no faces if possible).
2. Copy `manifest_template.csv` → e.g. `reports/vision_eval_manifest.csv`.
3. Add rows (example):

```csv
case_id,image_path,crop,gold_label,gold_notes,source,split
phone_001,Data/vision_eval/samples/phone_001.jpg,mais,disease_suspected,taches jaunes,phone_photo,eval
phone_002,Data/vision_eval/samples/phone_002.jpg,sorgho,blurry,photo floue,phone_photo,eval
phone_003,Data/vision_eval/samples/phone_003.jpg,,not_a_plant,objet,phone_photo,eval
```

4. Run notebooks 01 / 03 / 04 in Colab against that manifest.
5. Ship a custom model **only** if notebook 05 gates pass vs Gemini.

Do not commit private farmer photos without consent.
