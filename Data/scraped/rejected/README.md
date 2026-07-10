# Rejected scrapes

Files here were scraped or attempted but **must not** enter RAG.

Common reasons:

- HTTP 404 / 502 / error pages
- Firecrawl proxy or tunnel failures (empty body)
- Navigation-only or non-agricultural noise

## 2026-07-10 batch

| File | Source | Reason |
|------|--------|--------|
| `20260710_502-bad-gateway_c1fb33ad.md` | https://www.agrhymet.ne/ | HTTP 502 Bad Gateway |
| `20260710_bienvenue-sur-le-portail-web-du-cilss-page-not-found_26253fab.md` | https://www.cilss.int/a-propos/ | HTTP 404 page not found |
| `_wascal_scrape_failures_20260710.md` | wascal.org / www.wascal.org | Firecrawl `ERR_TUNNEL_CONNECTION_FAILED` |
| `_wascal_inera_scrape_failures_20260710_refresh.md` | INERA + WASCAL (refresh batch) | Tunnel errors again on full trusted refresh |
| `20260710_502-bad-gateway_c1fb33ad.md` | agrhymet.ne | HTTP 502 (re-scraped during refresh) |

**Active curated alternatives already in RAG:**

- `Data/markdown/scraped_reviewed/maerah_oaph_orientation_burkina_2026.md`
- `Data/markdown/scraped_reviewed/cilss_orientation_sahel_2026.md`

Retry WASCAL and AGRHYMET later when the sites / Firecrawl proxy are healthy.
Do not invent climate guidance without a reviewed source.
