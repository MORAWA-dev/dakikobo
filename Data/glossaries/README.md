# Glossaries (labels only)

Files here support **careful** multilingual labeling for the field UI.

| File | Role |
|------|------|
| `crop_labels.json` | Crop IDs with French (primary) + optional Mooré / Dioula / Fulfulde slots |

## Rules

1. **French remains the production language** for answers and most UI.
2. Local-language fields stay **empty** until a native speaker / extension agent fills them.
3. Do **not** wire empty local names into the live chat generator.
4. `core/simple_french.py` remains the French-simple path; this folder is for labels/glossary data, not LLM translation.

## Next human step

Fill `moore` / `dioula` / `fulfulde` for the five primary crops using a verified lexicon, then add a small UI badge experiment (labels only).
