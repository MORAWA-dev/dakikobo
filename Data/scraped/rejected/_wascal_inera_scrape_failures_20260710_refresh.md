# WASCAL / INERA scrape failures — 2026-07-10 refresh

Status: **failed** (Firecrawl internal proxy / tunnel error)

URLs tried in `scripts/refresh_trusted_sources.py`:
- https://www.inera.bf/
- https://wascal.org/
- https://www.wascal.org/

Error pattern:
`ERR_TUNNEL_CONNECTION_FAILED` / Firecrawl SCRAPE_SITE_ERROR

AGRHYMET:
- https://www.agrhymet.ne/ → HTTP 502 (file moved to rejected/)

Partial successes (pending, not promoted):
- MAERAH homepage re-scrape
- FAO MAFAP Burkina
- FAO AgriSurvey Burkina

Do **not** invent climate or INERA doses without a reviewed source.
