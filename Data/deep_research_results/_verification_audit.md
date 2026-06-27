# Verification Audit - Deep Research Results

Date: 2026-06-27  
Scope: `Data/deep_research_results/*.md`  
Purpose: prevent false dates, false publishers, non-local sources, and unsupported exact recommendations from entering the DakiKobo RAG knowledge base.

Update: the rejected raw model outputs were moved to `Data/_archive/rejected_deep_research_2026-06-27/` so they are not mistaken for active research inputs.

## Environment Check

The local `.env` check found:

| Variable | Status |
|---|---|
| `IASKPRO_API_KEY` | missing |
| `IASK_API_KEY` | missing |
| `IASKPRO_KEY` | missing |
| `FIRECRAWL_API_KEY` | present |

No API keys were printed. Because no iAsk key was found under the checked names, this audit used direct source checks and temporary PDF extraction instead of iAskPro API calls.

## Current Ingestion Risk

The app currently prefers reviewed Markdown from `Data/markdown/` via `MARKDOWN_FOLDER`. The new deep-research files are in `Data/deep_research_results/`, so they are not part of the normal reviewed Markdown ingestion path.

Do not move any file from `Data/deep_research_results/` into `Data/markdown/` until it has been split, corrected, cited, and reviewed.

## File-Level Verdicts

| File | Verdict | Why | Action |
|---|---|---|---|
| `deep_research_result_by_chatgpt_dakikobo.md` | Reject for RAG | Off-topic generic research agenda about AI education, heat, and energy grids; not a Burkina Faso agriculture pack. | Keep only as failed-run record or delete later. Do not ingest. |
| `iaskpro.md` | Reject for RAG as written | Claims a 2026 Burkina Faso ministry/INERA guide but gives only the ministry homepage as `source_url`; includes exact fertilizer, pest, storage, and soil claims without document-level citations. | Use as a topic checklist only. Re-run as short source-finding prompts, not as final knowledge. |
| `gemini_deep_res_results.md` | Mixed, not ingestible as written | Contains useful themes, but the pack is a single concatenated file, frontmatter is malformed (`YAML---`), and several source dates/publishers/countries are wrong or unsupported. | Split only the salvageable sections, correct metadata, and keep human review required. |
| `grk_deepresearch_dakikobo_by_grok.md` | Keep as audit/gap report, not as direct RAG knowledge | It is cautious and explicitly reports missing official data. Some cited sources are useful, but its numeric table still needs source-level extraction. | Keep as `review_notes` / gap analysis. Do not ingest as farmer advice. |

## Source-Level Findings

| Source URL | Claimed in generated data | Verified finding | Verdict |
|---|---|---|---|
| `https://ag.purdue.edu/department/agecon/_docs/international-programs/ipim-sahel-french/fiche-technique-sorgo.pdf` | Gemini: Burkina Faso sorgho/mil, `INERA / ICRISAT / FAO`, year `2023` | PDF text says: `FICHE DE PRODUCTION ET DE COMMERCIALISATION DU SORGHO, MALI`, date `mars 2011`, linked to IER/INTSORMIL/IICEM and Mali context. | Do not use as Burkina official source. At most use as Mali comparative material. Correct year to 2011 if retained. |
| `https://ifdc.org/wp-content/uploads/2019/07/FICHE-TECHNIQUE-1-ITINERAIRE-TECHNIQUE-DU-MAI%CC%88S-MAIZE-TECHNICAL-ITINERARY.pdf` | Gemini: Burkina Faso maize, `INERA / FAO / Ministère de l'Agriculture`, year `2023` | Cover shows IFDC / ACMA2, funded by Royaume des Pays-Bas. Contact page says `IFDC-BENIN`, Cotonou, Benin. PDF metadata creation date: 2019-05-16. | Do not label as Burkina official. Use only as Benin/West Africa comparative source after review. Correct year to 2019 if retained. |
| `https://www.iita.org/wp-content/uploads/2020/05/Cowpea-manual-FRENCH_VERSION.pdf` | Gemini: `INERA / IITA`, year `2020` | PDF title: `Guide sur la production du niébé en Afrique de l'Ouest`. Copyright says IITA 2017. Citation says Omoigui et al. 2018. Includes INERA Burkina Faso author affiliation, but it is a West Africa guide, not a Burkina-only manual. | Potentially useful. Correct year to 2018 for citation, or note 2017 copyright. Keep as regional source with Burkina contributor, not Burkina official. |
| `https://www.inter-reseaux.org/wp-content/uploads/Catalogue-AFS-ProSol-04-12-2020.pdf` | Gemini: `CILSS / ProSol / CNABio`, year `2020` | PDF text says ProSol project: `Réhabilitation et protection des sols dégradés... au Burkina Faso`, `Version 1`, `ANNEE : 2020`, catalogue of soil fertility improvement measures. | Strong candidate. Correct publisher to ProSol / GIZ / Burkina project actors as supported by the document. Good for CES and soil fertility after extraction. |
| `https://agritrop.cirad.fr/612314/1/V2COR200225%20PROPULSE%20L%C3%89GUMINEUSES%20.pdf` | Grok: CIRAD ProPulse legumes, INERA Saria trials 2018-2019 | PDF text shows CIRAD/INERA/University affiliations in Burkina Faso and West Africa. PDF metadata creation date: 2025-02-20. It states it gathers research results from ProPulse and related projects. | Useful source, but metadata should say document date 2025 unless a specific section cites 2018-2019 trials. Extract carefully. |
| `https://openjicareport.jica.go.jp/pdf/1000040845.pdf` | Grok: JICA Burkina agricultural report with calendar table | URL was reachable in the quick probe, but full text extraction was not completed in this audit run. | Keep pending. Verify title, date, country, and the exact calendar table before using. |
| `https://www.researchgate.net/publication/369082846_Variabilite_Spatio-Temporelle_de_la_Pluviometrie_dans_les_Zones_Soudaniennes_Soudano-Sahelienne_et_Sahelenne_du_Burkina_Faso` | Gemini: climate source, year `2023`, publisher `INERA / Météorologie / Universités` | Automated access returned 403. ResearchGate is also not ideal as the canonical source. | Replace with the journal, institutional repository, DOI, or author PDF before ingestion. Do not ingest from this citation alone. |
| `https://www.webonary.org/fulfuldeburkina/` | Gemini: glossary for Dioula, Fulfulde, Mooré, year `2023`, publisher `SIL / CNRS / Universités locales` | Automated access returned 403. The URL is Fulfulde-specific and does not by itself support Dioula or Mooré claims. | Do not ingest multilingual glossary as written. Build separate language-specific sources and validate with native speakers/extension agents. |
| `https://fr.scribd.com/document/858694378/FT-de-l-Arachide` | Gemini: Burkina arachide, `INERA / STDF`, year `2022` | Scribd page is a user-uploaded document page, not an authoritative publisher. It contains AI-enhanced page metadata and cannot establish source provenance cleanly. | Reject for RAG. Find original INERA/STDF/IITA/Ministry source instead. |

## Most Important Corrections

1. The sorgho source is Mali, March 2011, not Burkina Faso 2023.
2. The maize source is IFDC/ACMA2 Benin, 2019, not INERA/FAO/Burkina 2023.
3. The cowpea source is a West Africa IITA guide with 2017 copyright and 2018 citation, not a 2020 publication.
4. The ProSol soil catalogue is the strongest verified Burkina-specific source among the checked Gemini sources.
5. The iAskPro synthesis should not be trusted as a source document because it cites a homepage, not exact documents.
6. The Grok file is useful because it admits gaps; keep that behavior as the standard for future research runs.

## Recommended Next Actions

1. Do not ingest any deep-research output directly into `Data/markdown/`.
2. Create a reviewed pack only from verified sources:
   - ProSol 2020 soil fertility / CES catalogue.
   - IITA 2018 cowpea West Africa guide, clearly labeled regional.
   - CIRAD ProPulse 2025 legume/cereal association material, with Burkina sections extracted only where supported.
3. Replace weak or blocked citations:
   - Find the original INERA or Ministry arachide source instead of Scribd.
   - Find the canonical climate article or institutional PDF instead of ResearchGate.
   - Find separate validated Dioula, Mooré, and Fulfulde lexicons instead of one Fulfulde-only URL.
4. Use Firecrawl for source collection and page-to-Markdown extraction, not for final truth. Every scraped page still needs metadata verification.
5. When using iAskPro manually, ask it for a short source list first, then verify each source before asking for a synthesis.

## Safe Prompt Pattern For Future Research

Use this before asking any model to generate RAG-ready Markdown:

```text
Return only a source register first. Do not write advice yet.

For each source, provide:
- exact title
- exact publisher
- exact publication year shown in the document
- country/region covered
- direct URL to the PDF/page
- 2 short quotes or page references proving the metadata
- whether it is Burkina-specific, West Africa regional, or non-local comparative
- whether it contains exact fertilizer/pesticide doses

Reject user-upload sites, blogs without authors/dates, and sources where the document country/date cannot be verified.
If you cannot verify the source, say "pending verification" instead of guessing.
```

## Final Decision

The deep-research outputs are useful as raw research notes, but they are not yet safe as farmer-facing RAG data. The safest next ingestion work is to build a small corrected Markdown pack from ProSol 2020, IITA cowpea 2018, and verified Burkina sections of CIRAD ProPulse 2025, while keeping all exact fertilizer and pesticide recommendations under human review.
