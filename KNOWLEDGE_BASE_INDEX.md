# DakiKobo Knowledge Base Index

Lightweight index for AI assistants (ChatGPT Project, Cursor). Full PDFs stay in `Data/` locally — not uploaded to cloud assistants.

## Ingested (`Data/knowledge_base/`)

| File | Topic | Crops | Zone |
|---|---|---|---|
| `burkina_climate_adaptation_state_report.pdf` | Climate adaptation & mitigation | All cereals | National |
| `csa_investment_plan_burkina_final.pdf` | Climate-Smart Agriculture investment plan (final) | All | National |
| `csa_investment_plan_burkina_draft.pdf` | CSA investment plan (draft) | All | National |
| `fao_publication_i3760e.pdf` | FAO agricultural publication | Mixed | Sahel |
| `farmer_training_manual.pdf` | Farmer training manual | Mixed | General |
| `jaa_agronomy_article_2021.pdf` | Agronomy journal article (2021) | Mixed | Research |
| `needs_review_01.pdf` | Unidentified — rename after review | ? | ? |
| `needs_review_02.pdf` | Unidentified — rename after review | ? | ? |

## Not yet ingested (`Data/New Folder With Items/`)

| File | Likely topic |
|---|---|
| `giz2023-fr-burkina-faso-programme-développement-de-l'agriculture.pdf` | GIZ agriculture development programme |
| `Caractéristiques des ménages agricoles au Burkina Faso_0.pdf` | Agricultural household characteristics |
| `The_Growth_Pole_of_Bagre_An_Analysis_of_the_Commun.pdf` | Bagré growth pole regional analysis |
| `bf_profile_fr.pdf` | Burkina Faso country profile (French) |
| `burkina_agri_report_nllm.pdf` | Burkina agriculture report |
| `bl068f.pdf` | Needs identification |
| `26818.pdf` | Needs identification |

## Not ingested (`Data/` root)

| File | Likely topic |
|---|---|
| `1767_KIT_boek_Burkina_web-version.pdf` | KIT Burkina agriculture book |

## Ingestion notes

- `app.py` loads only `*.pdf` directly in `knowledge_base/` (no subfolders)
- `config.py` → `DATA_FOLDER = data/knowledge_base` (macOS case-insensitive → `Data/knowledge_base`)
- ChromaDB is in-memory — re-indexes on every server restart
- Planned: metadata tags (`crop`, `zone`, `doc_type`), persistent Chroma, PyMuPDF extraction

## Priority ingestion order

1. GIZ agriculture programme
2. Household characteristics
3. Bagré growth pole (regional specificity)
4. KIT Burkina book
5. Identify and rename `needs_review_01/02`, `bl068f`, `26818`