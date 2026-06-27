# DakiKobo Data Sources Register

This register tracks source quality before any document enters the RAG corpus.

Only reviewed Markdown under `Data/markdown/` should power the app. Raw research
outputs, scraped pages, or model-generated packs must stay outside the active RAG
path until reviewed.

## Status Labels

| Status | Meaning |
|---|---|
| `active_rag` | Already part of the reviewed Markdown/PDF corpus. |
| `candidate` | Good source candidate, but still needs clean extraction/review. |
| `pending` | Needs title/date/publisher/content verification before use. |
| `comparative` | Useful context, but not Burkina-specific. Label clearly if used. |
| `reject` | Do not ingest. |

## Candidate Sources To Extract Carefully

| Status | Date added | Source | Publisher / year | Scope | Topics | License / usage note | Review status | Notes |
|---|---|---|---|---|---|---|---|---|
| `active_rag` | 2026-06-27 | [Catalogue de fiches techniques des mesures d'amélioration de la fertilité des sols](https://www.inter-reseaux.org/wp-content/uploads/Catalogue-AFS-ProSol-04-12-2020.pdf) | ProSol, 2020 | Burkina Faso | fumure organique, compost, parcs améliorés, légumineuses, CES | unknown | reviewed_by_codex_pending_human_review | Extracted to `Data/markdown/prosol_fertilite_sols_burkina_2020.md`; pesticide section excluded and exact microdose table kept out of general RAG advice. |
| `active_rag` | 2026-06-27 | [Guide sur la production du niébé en Afrique de l'Ouest](https://www.iita.org/wp-content/uploads/2020/05/Cowpea-manual-FRENCH_VERSION.pdf) | IITA, copyright 2017, citation 2018 | West Africa | niébé production, varieties, pests, storage | copyright IITA 2017; reuse terms not fully verified | reviewed_by_codex_pending_human_review | Extracted to `Data/markdown/iita_niebe_afrique_ouest_2018.md`; chemical product tables excluded and source kept labeled as regional. |
| `candidate` | 2026-06-27 | [ProPulse Légumineuses](https://agritrop.cirad.fr/612314/1/V2COR200225%20PROPULSE%20L%C3%89GUMINEUSES%20.pdf) | CIRAD / partners, PDF created 2025 | Burkina Faso and West Africa | cereal-legume associations, rotations, legumes | unknown | pending_human_review | Useful where the document explicitly supports Burkina sections. Extract cautiously by section. |

## Pending Sources

| Status | Date added | Source | Claimed use | License / usage note | Review status | What to verify |
|---|---|---|---|---|---|---|
| `pending` | 2026-06-27 | [JICA report 1000040845](https://openjicareport.jica.go.jp/pdf/1000040845.pdf) | Burkina Faso agricultural calendar/table | unknown | pending_verification | Verify exact title, publication date, country scope, and the claimed calendar table before using. |
| `pending` | 2026-06-27 | ResearchGate climate/pluviometry page | climate zones and rainfall variability | unknown | pending_verification | Replace with canonical journal, DOI, institutional PDF, or author repository before ingestion. |
| `pending` | 2026-06-27 | Webonary Fulfulde Burkina | local-language glossary | unknown | pending_verification | Fulfulde-only URL does not prove Dioula/Mooré terms. Build language-specific sources and human review. |

## Comparative Or Rejected Sources From Deep Research Audit

| Status | Date added | Source | License / usage note | Review status | Reason |
|---|---|---|---|---|---|
| `comparative` | 2026-06-27 | [Fiche de production et de commercialisation du sorgho, Mali](https://ag.purdue.edu/department/agecon/_docs/international-programs/ipim-sahel-french/fiche-technique-sorgo.pdf) | unknown | reviewed_for_rejection | Verified as Mali, March 2011. Do not label as Burkina Faso or 2023. |
| `comparative` | 2026-06-27 | [IFDC / ACMA2 itinéraire technique du maïs](https://ifdc.org/wp-content/uploads/2019/07/FICHE-TECHNIQUE-1-ITINERAIRE-TECHNIQUE-DU-MAI%CC%88S-MAIZE-TECHNICAL-ITINERARY.pdf) | unknown | reviewed_for_rejection | Verified as IFDC/ACMA2 Benin context, PDF metadata 2019. Do not label as INERA/FAO/Burkina 2023. |
| `reject` | 2026-06-27 | `Data/_archive/rejected_deep_research_2026-06-27/iaskpro.md` | internal generated output | reviewed_for_rejection | Synthetic guide with only a homepage source URL and unsupported exact claims. |
| `reject` | 2026-06-27 | `Data/_archive/rejected_deep_research_2026-06-27/gemini_deep_res_results.md` | internal generated output | reviewed_for_rejection | Useful themes but wrong dates/publishers/countries and malformed pack. Use audit only, not content. |
| `reject` | 2026-06-27 | `Data/_archive/rejected_deep_research_2026-06-27/deep_research_result_by_chatgpt_dakikobo.md` | internal generated output | reviewed_for_rejection | Off-topic failed run. |
| `reject` | 2026-06-27 | [Scribd FT de l'Arachide](https://fr.scribd.com/document/858694378/FT-de-l-Arachide) | third-party user upload | reviewed_for_rejection | User-upload source with unclear provenance. Find original publisher instead. |

## Ingestion Rules

1. A source must have verified title, publisher, year or explicit `null`, direct URL, and country/region.
2. `West Africa regional` sources can support general advice but must not be presented as Burkina official recommendations.
3. Exact fertilizer doses, pesticide names, crop calendars, and disease treatment advice need source-backed extraction plus human review.
4. Firecrawl output is raw material, not truth. Scraped Markdown must keep URL, crawl date, publisher, and review status.
5. Accepted documents move into `Data/markdown/` only after review.

## Next Source Work

1. Extract verified Burkina sections from CIRAD ProPulse 2025.
2. Search for original official arachide and climate sources to replace weak citations.
