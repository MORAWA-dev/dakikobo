# Short iAskPro Prompts for DakiKobo Research

Use these when iAskPro rejects the long Deep Research prompt. Run one small task at a time, then save the answer for review.

---

## Difference Between Modes

Use **Pro Search** when you need sources.

- Best for finding official pages, PDFs, reports, crop calendars, and citations.
- Ask narrow questions.
- Request URLs, publisher, year, and why the source is trustworthy.
- Use it first.

Use **Deep Think** when you already have sources or notes.

- Best for comparing sources, extracting patterns, identifying contradictions, and planning structure.
- Less ideal as the first step if you need fresh URLs.
- Use it after Pro Search gives you source links.

Use **normal chat / short question** for quick clarification.

- Best for "what does this mean?" or "summarize this source."
- Not enough for building a knowledge pack.

---

## Prompt 1 - Pro Search Source Discovery

```text
Find trustworthy sources for DakiKobo, a French agricultural RAG bot for Burkina Faso.

Important: sources only. Do not write agricultural advice yet.

Topic: <PUT ONE TOPIC HERE>
Crops: <mil/sorgho/mais/niebe/arachide>

Prioritize official or high-trust sources: Burkina Faso agriculture ministry, INERA, FAO, CILSS, AGRHYMET, WASCAL, CORAF, CGIAR, ICRISAT, IITA, FEWS NET, GIZ, World Bank, IFAD.

Return only:
1. 4-8 best sources with exact title, direct URL, publisher, year shown by the document, language, and country/region covered.
2. Classification: Burkina-specific, West Africa regional, non-local comparative, unclear, or reject.
3. Two short proof snippets from the source page, title page, citation block, or visible metadata.
4. What each source contains.
5. Limitations, contradictions, or trust concerns.
6. Which 2-3 sources should be verified/scraped first.

Reject Scribd/user uploads, generic blogs, agrochemical sales pages, and any source where title, publisher, date, or country are unclear.
Do not infer a publication year from a URL unless the source itself confirms it.
Do not give pesticide, fertilizer, disease, or crop-calendar advice yet.
```

Example topics:

- `fumure du mil, sorgho et mais au Burkina Faso`
- `calendrier cultural et dates de semis au Burkina Faso`
- `maladies et ravageurs du niébé au Burkina Faso`
- `zaï, demi-lunes, cordons pierreux et conservation des eaux et sols`
- `stockage post-récolte et aflatoxine pour maïs/arachide/niébé`

---

## Prompt 2 - Deep Think Source Comparison

Paste this after Pro Search gives you sources.

```text
Compare these sources for DakiKobo, a French agricultural RAG bot for Burkina Faso.

Sources:
<PASTE 5-10 SOURCE TITLES + URLS HERE>

Task:
1. Group the sources by crop and topic.
2. Verify whether each source is Burkina-specific, West Africa regional, non-local comparative, or unclear.
3. Identify contradictions, weak evidence, and suspicious metadata.
4. Identify which sources are safe candidates for later Markdown conversion.
5. Mark anything that must be confirmed by a local agricultural agent.

Return a concise review table. Do not write final farmer advice yet. Do not invent facts beyond the sources.
```

---

## Prompt 3 - Convert One Source To RAG Markdown

Use this after you have one good source or Firecrawl Markdown.

```text
Convert the source below into strict French Markdown for DakiKobo RAG.

Rules:
- Keep facts source-grounded.
- Do not invent numbers, dates, doses, pesticides, or disease names.
- Preserve source URL, publisher, year, language, crops, topics.
- Add review_status: pending_human_review.
- If fertilizer or disease advice appears, include a confirmation disclaimer.
- Output only Markdown.

Required structure:
---
title: "<French title>"
source_type: "<official_report | extension_manual | research_article | project_page | other>"
publisher: "<publisher>"
year: "<year or null>"
source_url: "<url>"
retrieved_at: "<YYYY-MM-DD>"
language_original: "<fr | en | mixed>"
language_output: "fr"
country: "Burkina Faso"
crops: [<mil | sorgho | mais | niebe | arachide | other>]
topics: [<semis | fumure | maladie | ravageur | climat | sol | stockage | autre>]
evidence_level: "<high | medium | low>"
review_status: "pending_human_review"
limitations:
  - "<limitation>"
---

# <French title>

## Résumé utile pour DakiKobo

- <3-6 bullets>

## Conseils pratiques

### Ce que l'on peut dire avec confiance

- <supported facts>

### Ce qui dépend du contexte local

- <soil, rainfall, variety, region, crop stage, etc.>

### Ce qu'il ne faut pas automatiser

- <dangerous or uncertain advice>

## Données structurées

| Élément | Valeur | Unité | Culture | Zone | Source |
|---|---:|---|---|---|---|

## Questions de suivi à poser à l'utilisateur

1. <question>
2. <question>
3. <question>

## Réponse courte possible pour le bot

<80-130 words in simple French, cautious, with disclaimer if needed.>

## Sources

- <publisher> (<year>). <title>. <url>

## Notes de revue humaine

- <what to verify before ingestion>

Source text or Firecrawl Markdown:
<PASTE SOURCE TEXT HERE>
```

---

## Very Short Emergency Prompt

If even the prompts above are too long, use this:

```text
Find 8 trustworthy sources about <TOPIC> for a French RAG bot advising farmers in Burkina Faso. Prioritize official/credible sources: INERA, Burkina Faso agriculture ministry, FAO, CILSS, AGRHYMET, WASCAL, CGIAR, ICRISAT, IITA, FEWS NET, GIZ, World Bank. Return URL, publisher, year, crops, topics, why trustworthy, and limitations. Do not invent facts.
```
