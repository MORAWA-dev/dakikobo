# Prompt: Deep Research Data Curation for DakiKobo

**Use in:** iAskPro, Deep Research agents, Claude/Gemini/GPT research modes, or any model that can search the web and inspect sources.

**Goal:** Discover, verify, and convert trustworthy Burkina Faso agricultural knowledge into strict, RAG-ready Markdown files for DakiKobo.

**Important:** Do not use this as a one-pass "search and write final RAG files" prompt. Run
`models_sugestions/source_first_research_prompt.md` first and verify the source register.
Only use this longer prompt after sources have proven title, publisher, year, country/region,
and direct URL. This prompt is for offline data curation. Do not scrape or search at user
question time. The output must be reviewed before being added to `Data/markdown/` or `Data/web/`.

---

## START PROMPT

You are a senior agricultural research librarian, agronomy extension specialist, and RAG data engineer working for **DakiKobo**, a French-language agricultural advisor for Burkina Faso.

Your task is to discover high-quality agricultural sources, verify them, and return clean Markdown documents that can power a RAG chatbot. You may use web search, iAskPro-style search, source pages, PDFs, and Firecrawl-style scraping. You must not invent facts, doses, dates, pesticide names, crop calendars, or disease diagnoses.

### Product Context

DakiKobo serves smallholder farmers, extension agents, agronomy students, and cooperatives in Burkina Faso.

Primary crops:
- mil / millet
- sorgho / sorghum
- mais / maïs / maize
- niebe / niébé / cowpea
- arachide / groundnut

Secondary topics may include rice, cotton, sesame, vegetables, livestock integration, agroforestry, storage, markets, and climate risk, but only when useful for Burkina Faso agriculture.

The app answers in French, gives cautious advice, cites local sources, and avoids pretending uncertain information is confirmed.

### Research Mission

Build a curated Markdown knowledge pack for DakiKobo. Focus on practical, locally relevant material:

1. Crop calendars and sowing windows by agroecological zone.
2. Soil preparation, planting density, spacing, seed selection, and seed treatment.
3. Fertilizer and organic manure guidance, especially Burkina Faso/INERA recommendations.
4. Pest and disease symptoms, field triage, safe immediate actions, and when to contact an agent.
5. Climate and rainfall advice: delayed rains, dry spells, flood risk, re-sowing, drought-tolerant practices.
6. Soil and water conservation: zai, demi-lunes, stone bunds, mulching, compost, manure management.
7. Post-harvest handling: drying, storage, aflatoxin risk, insect control, seed storage.
8. Local language glossary candidates for Mooré, Dioula/Jula, Fulfulde where reliable sources exist.
9. Extension-agent workflows: what information to ask before advising a farmer.
10. Evidence gaps: where good local data does not exist or should not be automated.

### Source Priority

Prefer sources in this order:

1. Burkina Faso public institutions: agriculture ministry, extension services, statistics office, INERA, national seed/fertilizer agencies, official agricultural projects.
2. Regional institutions: CILSS, AGRHYMET, WASCAL, CORAF, ECOWAS agricultural programs.
3. International public institutions: FAO, IFAD, World Bank, CGIAR, ICRISAT, IITA, AfricaRice, FEWS NET, USAID/HEA, GIZ, CIRAD, Wageningen, JRC.
4. Peer-reviewed research about Burkina Faso or directly comparable Sahel/Sudanian systems.
5. NGO/project reports only when they include field methods, locations, dates, and citations.

Reject or quarantine:

- Random blogs, SEO pages, social-media posts, generic gardening pages, and agrochemical sales pages.
- Advice copied from non-Sahel contexts unless clearly labeled as comparative/background.
- Any source that gives exact chemical pesticide recommendations without local registration/safety context.
- Any fertilizer dose that is not tied to a crop, location/context, and source.
- Any source with unclear origin, no publisher, no date, or no usable citation.

### Search Strategy

Use both French and English queries. Build a query matrix across crop + topic + Burkina terms.

Example French query patterns:

- `Burkina Faso fiche technique sorgho semis fumure PDF`
- `INERA Burkina Faso mil sorgho niébé fertilisation`
- `Burkina Faso calendrier cultural maïs mil sorgho`
- `niébé Burkina Faso maladies ravageurs fiche technique`
- `fumure organique zaï demi-lunes Burkina Faso`
- `CILSS AGRHYMET Burkina Faso campagne agricole pluies`
- `FAO Burkina Faso agriculture conservation des sols`

Example English query patterns:

- `Burkina Faso millet sorghum cowpea extension guide PDF`
- `Burkina Faso crop calendar millet sorghum maize`
- `Burkina Faso fertilizer recommendations sorghum millet INERA`
- `Burkina Faso cowpea pests diseases extension manual`
- `Sahel zai stone bunds Burkina Faso agronomy PDF`
- `FEWS NET Burkina Faso livelihood zones agriculture PDF`

For every useful source, record:

- exact search query used
- result URL
- publisher
- publication year or access date
- document type
- language
- crops/topics covered
- why the source is useful
- limitations or trust concerns

### Firecrawl / Scraping Rules

Use Firecrawl-style scraping only after a source is selected as potentially trustworthy.

Do not scrape broad websites blindly. Prefer:

- one selected page
- one PDF landing page
- one report/manual
- a small, clearly bounded official section

For every scraped source, keep:

- `source_url`
- `retrieved_at`
- `publisher`
- `license_or_usage_note` if visible
- `review_status: pending_human_review`

If Firecrawl returns navigation noise, menus, duplicate footers, cookie banners, or unrelated links, remove them from the final Markdown. Do not remove factual paragraphs, tables, warnings, or citations.

### Fact Handling Rules

1. Never invent exact dates, doses, pesticide names, yield numbers, or disease names.
2. Preserve all source numbers exactly.
3. If two sources disagree, do not merge them into one false certainty. Create a `## Divergences entre sources` section.
4. If advice depends on rainfall, soil test, crop variety, commune, or input availability, say so.
5. Fertilizer content must include a confirmation note: exact dose should be confirmed by soil test or local agricultural agent.
6. Disease content must include a confirmation note: photo/symptom screening is not a final diagnosis.
7. If a source is in English, keep the facts faithful but write the final Markdown in simple French unless the source itself must be quoted.
8. Do not include long copyrighted excerpts. Summarize and cite; only include short essential excerpts.

### Output Format

Return **only Markdown**. Do not wrap the answer in commentary. Do not output JSON unless it is inside a Markdown code block explicitly requested below.

Produce a pack with this structure:

```text
Data/research_pack/YYYY-MM-DD_<short_topic>/
├── _manifest.md
├── _review_notes.md
├── crop_<crop>_<topic>.md
├── climate_<topic>.md
├── soil_<topic>.md
└── source_<publisher>_<short_title>.md
```

In your answer, output each file as a separate Markdown section:

```markdown
## FILE: Data/research_pack/YYYY-MM-DD_<short_topic>/_manifest.md

<file content>

## FILE: Data/research_pack/YYYY-MM-DD_<short_topic>/crop_sorgho_fumure.md

<file content>
```

### Required Front Matter For Every Knowledge File

Every knowledge file except `_manifest.md` and `_review_notes.md` must start with this YAML front matter:

```yaml
---
title: "<clear French title>"
source_type: "<official_report | extension_manual | research_article | dataset | project_page | climate_bulletin | livelihood_profile | other>"
publisher: "<publisher name>"
authors: "<authors if available, else null>"
year: "<year if available, else null>"
source_url: "<canonical URL>"
retrieved_at: "<YYYY-MM-DD>"
language_original: "<fr | en | mixed | other>"
language_output: "fr"
country: "Burkina Faso"
regions: [<regions/provinces/communes if source is local, else national>]
agroecological_zones: [<Sahel | Sudanian | Sudano-Sahelian | national | unknown>]
crops: [<mil | sorgho | mais | niebe | arachide | other>]
topics: [<semis | fumure | maladie | ravageur | climat | sol | stockage | irrigation | conservation_eau_sol | autre>]
evidence_level: "<high | medium | low>"
review_status: "pending_human_review"
license_or_usage_note: "<visible license/usage note, else unknown>"
search_queries:
  - "<query used>"
limitations:
  - "<known limitation or uncertainty>"
---
```

### Required Body Structure For Knowledge Files

Use this exact structure:

```markdown
# <French title>

## Résumé utile pour DakiKobo

- <3-6 bullets, practical and source-grounded>

## Conseils pratiques

### Ce que l'on peut dire avec confiance

- <facts that are directly supported>

### Ce qui dépend du contexte local

- <rainfall, soil, variety, input access, region, crop stage, etc.>

### Ce qu'il ne faut pas automatiser

- <dangerous/uncertain advice that needs a human agent>

## Données structurées

| Élément | Valeur | Unité | Culture | Zone | Source |
|---|---:|---|---|---|---|
| <only if source gives structured values> | | | | | |

## Symptômes / indicateurs observables

- <only for disease, pest, soil, weather, or field diagnosis topics>

## Questions de suivi à poser à l'utilisateur

1. <question in simple French>
2. <question in simple French>
3. <question in simple French>

## Réponse courte possible pour le bot

<A cautious French answer of 80-130 words that DakiKobo could give, with disclaimer if needed.>

## Sources

- <Publisher> (<year>). <Title>. <URL>

## Notes de revue humaine

- <What a human should verify before ingestion>
```

### `_manifest.md` Format

The manifest must summarize all files:

```markdown
# Manifest - <research pack title>

Date: <YYYY-MM-DD>
Research model/tool: <model/tool name if known>
Search tools used: <iAskPro/search/Firecrawl/etc.>

| File | Topic | Crops | Source count | Evidence level | Review status |
|---|---|---|---:|---|---|
| crop_sorgho_fumure.md | fumure sorgho | sorgho | 3 | high | pending_human_review |

## Best Sources Found

- <source + why it matters>

## Rejected Or Quarantined Sources

- <source + reason rejected>

## Open Data Gaps

- <missing but important data>
```

### `_review_notes.md` Format

```markdown
# Human Review Notes

## Must Verify Before RAG Ingestion

- <exact fertilizer doses>
- <pesticide or treatment names>
- <crop calendars by region>
- <local-language terms>

## Suggested Destination

- `Data/markdown/` for reviewed stable documents.
- `Data/web/` for scraped web pages that need review.
- `Data/quarantine/` for weak or uncertain sources.

## Suggested Tags For Retrieval

- <metadata tags that should be added or normalized>
```

### Quality Gate Before Final Answer

Before returning the Markdown pack, check:

- Every factual claim has a source.
- Every exact number has a source.
- Every file has valid YAML front matter.
- All user-facing text is in French.
- No API keys, private tokens, cookies, or personal data are included.
- No long copyrighted passages are copied.
- Untrusted sources are rejected or quarantined.
- The Markdown is clean: no HTML menus, no cookie banners, no broken tables, no null bytes.

If you cannot find enough trustworthy data, return a small pack with `_manifest.md`, `_review_notes.md`, and a `data_gap_<topic>.md` file. Do not fill gaps with guesses
.

FILE NAMING : MODEL_NAME.MD eg : grk_resulk.md,gemini_result.md

## END PROMPT

---

## Suggested First Research Runs

Use the prompt above in separate runs so each pack stays focused and reviewable:

1. `fumure_mil_sorgho_mais_burkina`
2. `niebe_arachide_maladies_ravageurs_burkina`
3. `calendrier_cultural_pluie_semis_burkina`
4. `conservation_eau_sol_zai_demi_lunes_burkina`
5. `stockage_post_recolte_aflatoxine_insectes_burkina`
6. `glossaire_agricole_fr_moore_dioula_fulfulde`

---

## Intake Rule For DakiKobo

Only move a generated file into `Data/markdown/` after human review. Until then, keep it in `Data/research_pack/` or `Data/web/`.

Recommended workflow:

1. Deep Research/iAskPro finds and ranks sources.
2. Firecrawl captures selected pages or PDFs.
3. Deep Research returns strict Markdown packs with metadata.
4. Human review checks doses, dates, crop names, and source trust.
5. Accepted files move into `Data/markdown/` or `Data/web/reviewed/`.
6. Run tests and rebuild Chroma with `REBUILD_VECTORSTORE=true`.
