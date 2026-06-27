# Source-First Research Prompt for DakiKobo

Use this before any deep research model is allowed to write RAG knowledge files.

The goal is simple: **prove the source first, write advice later**. A model that
cannot verify the title, publisher, year, country, and URL must not summarize the
source as if it were trustworthy.

## Why This Exists

Previous deep research runs found some real URLs but attached wrong metadata:

- non-Burkina documents were labeled as Burkina Faso sources;
- upload or access dates were treated as publication years;
- weak pages were turned into polished agricultural advice;
- exact doses appeared without document-level proof.

For DakiKobo, that is not acceptable. The bot gives agricultural advice, so source
traceability matters more than a polished answer.

## Workflow

1. **Source discovery only**
   - Find candidate sources.
   - Do not write farmer advice.
   - Do not synthesize fertilizer doses, crop calendars, or pest treatments.

2. **Source verification**
   - Check title page, PDF metadata, publisher page, or visible citation.
   - Classify each source as Burkina-specific, West Africa regional, non-local
     comparative, pending, or rejected.

3. **Single-source extraction**
   - Convert one verified source at a time into French Markdown.
   - Keep limitations and confirmation disclaimers.

4. **Human review before ingestion**
   - Only reviewed outputs move to `Data/markdown/`.
   - Raw model output stays in `Data/research_pack/`, `Data/web/`, or archive.

## Prompt A - Source Discovery Only

Use this in iAskPro Pro Search, Gemini Deep Research, ChatGPT Deep Research,
Claude research, or any model with web search.

```text
Find sources only. Do not write agricultural advice yet.

Project: DakiKobo, a French RAG assistant for agriculture in Burkina Faso.

Topic: <ONE NARROW TOPIC>
Crops: <mil | sorgho | mais | niebe | arachide | all>
Country focus: Burkina Faso. West Africa regional sources are allowed only if
clearly labeled as regional, not Burkina-specific.

Prioritize:
- Burkina Faso agriculture ministry, INERA, extension services, national projects
- CILSS, AGRHYMET, WASCAL, CORAF, ECOWAS
- FAO, IFAD, World Bank, CGIAR, ICRISAT, IITA, CIRAD, GIZ, FEWS NET
- peer-reviewed Burkina Faso agronomy papers

Reject:
- Scribd/user-upload pages unless the original publisher is found
- blogs, SEO pages, social media, generic gardening pages
- agrochemical sales pages
- any source with unclear title, publisher, year, or country

Return only a source register table with these columns:
- status: candidate | pending | reject
- exact title shown by the source
- exact publisher shown by the source
- exact publication year shown by the source, or null
- country/region covered
- classification: Burkina-specific | West Africa regional | non-local comparative | unclear
- direct URL
- source type: PDF | webpage | dataset | report | article | manual
- crops/topics covered
- 2 short proof snippets from the title page, citation block, or source page
- risk notes
- should scrape/convert first: yes/no

Rules:
- Do not infer the year from the URL unless the document itself supports it.
- Do not treat "West Africa" as "Burkina Faso".
- Do not give exact fertilizer, pesticide, disease, or calendar advice yet.
- If metadata is uncertain, write "pending verification" instead of guessing.
```

## Prompt B - Verify A Candidate Source

Use this when you already have one URL and need a yes/no decision.

```text
Verify this source for DakiKobo before RAG ingestion.

URL: <PASTE URL>
Claimed topic: <TOPIC>
Claimed country: Burkina Faso

Return only:
1. exact title
2. exact publisher
3. publication year shown in the document/source page
4. country or region actually covered
5. whether it is Burkina-specific, West Africa regional, non-local comparative, or reject
6. 2 short proof snippets with page/section if available
7. whether it contains exact fertilizer/pesticide/calendar numbers
8. safety concerns
9. final decision: accept_candidate | pending | reject

Do not summarize agricultural advice. Do not correct missing facts by guessing.
```

## Prompt C - Convert One Verified Source To RAG Markdown

Use this only after the source has passed Prompt B.

```text
Convert this verified source into strict French Markdown for DakiKobo RAG.

Source metadata already verified:
- title: <TITLE>
- publisher: <PUBLISHER>
- year: <YEAR>
- country/region: <COUNTRY/REGION>
- classification: <Burkina-specific | West Africa regional | non-local comparative>
- URL: <URL>

Rules:
- Use only facts present in the source text below.
- Do not invent doses, dates, pesticide names, disease names, yields, or calendars.
- Preserve numbers exactly and include local-context limitations.
- If the source is regional, clearly say it is regional and not Burkina-only.
- Fertilizer advice must include: "Confirmez la dose avec un agent agricole local ou un test de sol."
- Disease/photo advice must include: "Ceci n'est pas un diagnostic définitif."
- Output only Markdown.

Required front matter:
---
title: "<French title>"
source_type: "<official_report | extension_manual | research_article | dataset | project_page | climate_bulletin | livelihood_profile | other>"
publisher: "<publisher>"
authors: "<authors or null>"
year: "<year or null>"
source_url: "<url>"
retrieved_at: "<YYYY-MM-DD>"
language_original: "<fr | en | mixed | other>"
language_output: "fr"
country: "<Burkina Faso | West Africa | other>"
regions: []
agroecological_zones: []
crops: []
topics: []
evidence_level: "<high | medium | low>"
review_status: "pending_human_review"
classification: "<Burkina-specific | West Africa regional | non-local comparative>"
limitations:
  - "<limitation>"
---

# <French title>

## Résumé utile pour DakiKobo

- <3-6 source-grounded bullets>

## Conseils pratiques

### Ce que l'on peut dire avec confiance

- <supported facts only>

### Ce qui dépend du contexte local

- <soil, rainfall, variety, region, crop stage, input access>

### Ce qu'il ne faut pas automatiser

- <unsafe or uncertain advice needing a human>

## Données structurées

| Élément | Valeur | Unité | Culture | Zone | Source |
|---|---:|---|---|---|---|

## Questions de suivi à poser à l'utilisateur

1. <question>
2. <question>
3. <question>

## Réponse courte possible pour le bot

<80-130 words in simple French, cautious, source-grounded.>

## Sources

- <Publisher> (<year>). <Title>. <URL>

## Notes de revue humaine

- <what must be checked before moving to Data/markdown/>

Source text:
<PASTE VERIFIED SOURCE TEXT OR FIRECRAWL MARKDOWN>
```

## Acceptance Checklist

A source can move toward RAG only when all are true:

- [ ] Direct source URL exists.
- [ ] Title is verified from the document or source page.
- [ ] Publisher is verified.
- [ ] Publication year is verified or explicitly `null`.
- [ ] Country/region is verified.
- [ ] Classification is correct.
- [ ] Exact doses or chemical names, if present, are source-backed and flagged for review.
- [ ] No user-upload pages are used as canonical sources.
- [ ] Final Markdown has `review_status: pending_human_review`.

## Short Topics To Run First

- `zaï, demi-lunes, cordons pierreux et fertilité des sols au Burkina Faso`
- `production du niébé en Afrique de l'Ouest avec auteurs INERA Burkina`
- `associations céréales légumineuses Burkina Faso CIRAD INERA`
- `calendrier cultural mil sorgho maïs Burkina Faso source officielle`
- `aflatoxine maïs arachide Burkina Faso stockage post-récolte`
