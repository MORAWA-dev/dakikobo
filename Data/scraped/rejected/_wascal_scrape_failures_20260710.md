# WASCAL scrape attempts — 2026-07-10

Status: **failed** (Firecrawl internal proxy / tunnel error)

URLs tried:
- https://www.wascal.org/
- https://wascal.org/
- https://wascal.org/about-wascal/

Error pattern:
`ERR_TUNNEL_CONNECTION_FAILED` / Firecrawl SCRAPE_SITE_ERROR

Next steps:
1. Retry later when Firecrawl proxy is healthy.
2. Or manually download a public WASCAL PDF and curate Markdown offline.
3. Do **not** invent climate guidance without a reviewed source.

Allowlist entries remain valid: `wascal_org`, `wascal_www`.
