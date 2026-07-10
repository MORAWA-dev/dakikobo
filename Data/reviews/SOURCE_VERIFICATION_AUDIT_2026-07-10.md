# Source verification audit — MAERAH / CILSS (2026-07-10)

This audit supports SESSION.md item **“Human validation of MAERAH/CILSS”**.
It is **agent-assisted source verification**, not a substitute for final
owner/field sign-off.

## Scope

| Document | Path | Active RAG |
|----------|------|------------|
| MAERAH / OAPH orientation | `maerah_oaph_orientation_burkina_2026.md` | yes |
| CILSS regional orientation | `cilss_orientation_sahel_2026.md` | yes |

## Automated checks performed

| Check | MAERAH | CILSS |
|-------|--------|-------|
| Primary URL reachable (HTTP 200) | yes — agriculture.bf OAPH + projets | yes — cilss.int |
| Publisher / institution name matches site | MAERAH on site title | CILSS portal title |
| OAPH expansion vs official page | **Offensive agropastorale et halieutique 2023-2025** confirmed in pending scrape body and URL path | n/a |
| No invented fertilizer doses / pesticide products in synthesis | pass | pass |
| News/nav boilerplate excluded from curated body | pass | pass |
| License note present (short orientation + cite URL) | updated | updated |
| AGRHYMET / WASCAL / INERA live fetch | n/a | AGRHYMET/WASCAL/INERA: timeout/error 2026-07-10 (not promoted) |

## OAPH facts locked for RAG

- Acronym: **Offensive Agropastorale et Halieutique 2023-2025** only.
- Not: “Office des Aménagements…” or other invented expansions.
- Official page presents OAPH as operational plan for food sovereignty and
  decent jobs; adopted in Council of Ministers **30 August 2023** (per page).
- Eight strategic value chains on the official page: riz, maïs, pomme de terre,
  blé, poisson, bétail-viande, volaille, mangue.

## License / reuse stance (demo app)

- Full ministry / CILSS pages remain the property of those institutions.
- DakiKobo keeps a **short orientation synthesis** for retrieval, always with
  source URL when available.
- This is **not** a bulk mirror of the websites.
- Owner should still confirm before commercial redistribution of long excerpts.

## Owner sign-off (recorded)

- [x] Product owner accepts synthesis wording for public demo.
- [x] Budget/employment targets: only as *official published targets*, not field promises.
- [ ] Local agent review of French field phrasing (optional, still recommended).

**Signed:** morawa-dev (GitHub) on 2026-07-10  
See `OWNER_SIGNOFF.md`. `review_status` on both docs is now `reviewed_by_owner`.

## Follow-ups

1. Retry AGRHYMET, WASCAL, INERA when network/Firecrawl healthy.
2. Do not promote raw pending scrapes (news-heavy) into RAG.
3. Optional: local agent review of French field phrasing.
