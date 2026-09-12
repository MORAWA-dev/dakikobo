# Trusted source health — 2026-09-11T23:36:41+00:00

- Up: **6/9**

| Status | Code | ms | URL | Error |
| --- | ---: | ---: | --- | --- |
| UP | 200 | 601 | `https://www.agriculture.bf/` |  |
| DOWN | - | 6531 | `https://www.inera.bf/` | HTTPSConnectionPool(host='www.inera.bf', port=443): Max retries exceeded with ur |
| UP | 200 | 2329 | `https://wascal.org/` |  |
| UP | 200 | 2628 | `https://www.wascal.org/` |  |
| DOWN | - | 15157 | `https://www.agrhymet.ne/` | HTTPSConnectionPool(host='www.agrhymet.ne', port=443): Max retries exceeded with |
| UP | 200 | 1263 | `https://www.cilss.int/` |  |
| UP | 200 | 302 | `https://www.fao.org/in-action/mafap/where-we-work/burkina-faso/en` |  |
| UP | 200 | 464 | `https://www.fao.org/in-action/agrisurvey/access-to-data/burkina-faso/en` |  |
| DOWN | 404 | 393 | `https://www.fao.org/countryprofiles/index/en/?iso3=BFA` |  |

Next: if UP and allowlisted, run `scripts/refresh_trusted_sources.py` then human-review pending files. Never auto-promote.

# Trusted source health — 2026-07-10T13:47:23+00:00

- Up: **4/10**

| Status | Code | ms | URL | Error |
| --- | ---: | ---: | --- | --- |
| UP | 200 | 562 | `https://www.agriculture.bf/` |  |
| DOWN | - | 374 | `https://agriculture.bf/` | HTTPSConnectionPool(host='agriculture.bf', port=443): Max retries exceeded with  |
| DOWN | - | 6207 | `https://www.inera.bf/` | HTTPSConnectionPool(host='www.inera.bf', port=443): Max retries exceeded with ur |
| DOWN | - | 127 | `https://wascal.org/` | HTTPSConnectionPool(host='wascal.org', port=443): Max retries exceeded with url: |
| DOWN | - | 82 | `https://www.wascal.org/` | HTTPSConnectionPool(host='www.wascal.org', port=443): Max retries exceeded with  |
| DOWN | - | 12010 | `https://www.agrhymet.ne/` | HTTPSConnectionPool(host='www.agrhymet.ne', port=443): Max retries exceeded with |
| UP | 200 | 948 | `https://www.cilss.int/` |  |
| UP | 200 | 504 | `https://www.fao.org/in-action/mafap/where-we-work/burkina-faso/en` |  |
| DOWN | - | 12117 | `https://www.fao.org/in-action/agrisurvey/access-to-data/burkina-faso/en` | HTTPSConnectionPool(host='www.fao.org', port=443): Read timed out. (read timeout |
| UP | 200 | 265 | `https://www.fao.org/countryprofiles/index/en/?iso3=BFA` |  |

Next: if UP and allowlisted, run `scripts/refresh_trusted_sources.py` then human-review pending files. Never auto-promote.

