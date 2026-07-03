# DakiKobo Knowledge Base Index

Lightweight index for AI assistants (ChatGPT Project, Cursor). Full PDFs stay in `Data/` locally — not uploaded to cloud assistants.

## Current Active RAG Path

The app now prefers reviewed Markdown under `Data/markdown/`, with PDF fallback
when Markdown is missing or disabled. See `DATA_SOURCES.md` for source
governance and `PROJECT_STATE.md` for the latest verification status.

Key curated Markdown additions:

| File | Topic | Crops | Zone |
|---|---|---|---|
| `Data/markdown/prosol_fertilite_sols_burkina_2020.md` | Soil fertility, compost, organic manure, CES | Mixed | Burkina Faso |
| `Data/markdown/iita_niebe_afrique_ouest_2018.md` | Niébé production, symptoms, storage | Niébé | West Africa |
| `Data/markdown/scraped_reviewed/fao_burkina_policy_data_profile_2026.md` | Policy, public expenditure, price incentives, EPA/statistics, FAO country profile | Mixed | Burkina Faso |

Firecrawl raw outputs under `Data/scraped/pending/` are not active RAG sources.

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

- Current app config uses the full `Data/` tree and recursive ingestion.
- Markdown is preferred for hosted startup and cleaner chunking.
- ChromaDB is persisted in `chroma_db/` and is generated, not committed.
- Planned: richer source-card display using document metadata.

## Priority ingestion order

1. GIZ agriculture programme
2. Household characteristics
3. Bagré growth pole (regional specificity)
4. KIT Burkina book
5. Identify and rename `needs_review_01/02`, `bl068f`, `26818`
