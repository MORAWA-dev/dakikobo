# DakiKobo Deployment Guide

This app can be hosted as a Flask web service on Hugging Face Spaces, Render, Railway, Fly.io, Azure App Service, or any Docker-capable platform.

## Recommended Demo Path

If the budget is zero, start with Hugging Face Spaces using the Docker SDK:

- Free CPU Spaces are realistic for this app's Python/RAG dependency stack.
- Space secrets can hold `GROQ_API_KEY`, `GEMINI_API_KEY`, and `FLASK_SECRET_KEY`.
- The root `README.md` includes the Space metadata (`sdk: docker`, `app_port: 7860`).
- The included `Dockerfile` listens on port `7860`, which is the expected Space port.

Render or Railway are also good demo options if you later have a small monthly budget:

- They can deploy directly from GitHub.
- They provide HTTPS URLs for sharing.
- Environment variables can be configured in the dashboard.
- The included `Procfile` and `Dockerfile` give the platform a production start command.

For a longer-lived production system, use Azure App Service, Fly.io, or another provider where you can attach persistent storage or move the vector database to a managed service.

## Required Server Environment Variables

Set these in the hosting provider dashboard or service manager. The Flask web
process intentionally does not read `.env` files. Never place a `.env` inside
`public_html`, the repository served by Apache, or a container build context.

```text
GROQ_API_KEY=...
GEMINI_API_KEY=...
FLASK_SECRET_KEY=generate-a-long-random-secret
APP_ENV=production
FLASK_DEBUG=false
REBUILD_VECTORSTORE=false
```

Optional:

```text
APP_VERSION=0.1.0
LOG_LEVEL=INFO
LLM_MODEL=openai/gpt-oss-120b
LLM_REASONING_FORMAT=hidden
LLM_REASONING_EFFORT=low
STT_MODEL=whisper-large-v3-turbo
VECTORSTORE_DIR=chroma_db
CITATION_SCORE_MARGIN=0.12
MAX_RAG_SOURCES=2
STATE_DB_PATH=data/runtime_state.sqlite3
ANSWER_CACHE_ENABLED=true
ANSWER_CACHE_TTL_SECONDS=86400
SEARCH_ENGINE_INDEXING_ENABLED=false
```

## Hugging Face Spaces

1. Create a new Space at Hugging Face.
2. Use the owner/account `kimcomehome`.
3. Name the Space `dakikobo`, so the public URL will be:

```text
https://huggingface.co/spaces/kimcomehome/dakikobo
```

4. Select **Docker** as the Space SDK.
5. Upload or push this repository to the Space repo.
6. In **Settings -> Secrets**, add:

```text
GROQ_API_KEY
GEMINI_API_KEY
FLASK_SECRET_KEY
```

7. In **Settings -> Variables**, add:

```text
FLASK_DEBUG=false
REBUILD_VECTORSTORE=false
PORT=7860
```

8. Push from this repo:

```bash
git remote add hf https://huggingface.co/spaces/kimcomehome/dakikobo
git push hf main
```

9. Wait for the Space to build, then open `/healthz` to confirm the Flask process is alive.
10. Watch `/healthz` until `rag_status` is `ready`; the Docker image starts RAG warm-up in the background.
11. Open `/version` to confirm the deployed model/config flags.
12. Open the app once online, reload it, then briefly disable the network and ask
    `Dose d'engrais pour le sorgho`. The offline banner and fixed fertilizer card should appear.

Free Space caveats:

- Free Spaces may sleep when inactive.
- The runtime disk is not a production database; feedback CSV and generated audio should be treated as temporary.
- Keep `.env`, API keys, and generated files out of Git.
- Keep secrets in the Space **Secrets** panel, not in repository files or Docker
  build arguments. `.dockerignore` excludes local secret files from image builds.
- If the Space is public, source code is public, but secrets configured in the Space settings stay hidden.

## Generic Build And Start

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 90
```

Health check path:

```text
/healthz
```

## Important Production Notes

- The Docker image sets `RAG_WARMUP_ON_START=true`, so Hugging Face starts preparing RAG in the
  background after the app boots. `/healthz` reports `rag_status` as `cold`, `warming`, `ready`,
  or `error`.
- Answer, weather, soil, and ops state share one WAL-enabled SQLite file, so both Gunicorn workers
  see the same cache entries and metrics. The free Space disk is still ephemeral across rebuilds.
- The separate WAL-enabled case-log database stores the field journal and privacy-safe evidence
  ledger. `/journal/due` exposes only ids and due metadata, never question or answer text.
- A kernel file lock serializes first-time Chroma initialization; both workers load the same completed
  vector store instead of racing its schema migration.
- A real RAG question can still be slow if it arrives before warm-up finishes; open `/healthz`
  or ask one warm-up question before a live demo.
- The service worker caches the public app shell and previously successful `/ask` responses in the
  visitor's browser. Bump `VERSION` in `static/sw.js` whenever cached frontend assets change.
- Regenerate the offline fertilizer asset after changing doses, crop aliases, sources, or fertilizer
  keywords: `.venv/bin/python scripts/export_offline_fertilizer.py`. Verify it with `--check`.
- Keep `Data/` available on the deployed service if the vector store must be rebuilt.
- Do not commit `.env`, `chroma_db/`, generated audio, case-log SQLite files, or private exports.
- A durable production version should move the case-log SQLite database and generated audio to
  persistent managed storage; Hugging Face free-Space disk can be replaced on rebuild.
- If traffic grows, separate ingestion/vector-store building from the Flask web process.

### Journal persistence: what is and is not verified

The state database, journal database, and photo directory paths are set with
`STATE_DB_PATH`, `CASE_LOG_DB_PATH`, and `FEEDBACK_IMAGE_DIR`. Point them at a
durable mount (for example `/data/dakikobo`) so the private journal outlives a
container restart.

`tests/docker_journal_rehearsal.py` is a bounded, synthetic rehearsal that
proves **local bind-mount persistence**: with the production image and
`APP_ENV=production` (production `Secure` cookie kept intact), one explicitly
consented synthetic case saved into a bind-mounted directory survives stopping
and removing the container and starting a fresh replacement from the same image,
secret, and mount. It also checks owner-only visibility, that a non-owner delete
returns `deleted: 0`, and that the owner can delete. The negative control keeps
the populated mount live and points the **same owner cookie** at a separate
container backed by a fresh empty mount: the owner sees the case on the
populated mount and none on the empty mount, and the populated case stays intact
before the owner deletion runs. Container names are unique per run (a UUID
token), so the rehearsal only ever removes the containers it started and never a
fixed name that could belong to another run; cleanup removes each container
independently (one slow removal cannot skip the others) and inspects the
`docker rm -f` exit code, so a nonzero result is treated as a cleanup failure
rather than silent success. A container is untracked only after its removal is
confirmed, and the bind-mount data is deleted only once every owned container is
confirmed removed; otherwise the deletion is withheld and reported so data is
never removed under a still-running mount. Run it locally with Docker:

```bash
python tests/docker_journal_rehearsal.py
```

This is **local bind-mount persistence evidence only**. It does NOT demonstrate
hosting-provider disk durability, survival of a host rebuild or volume
migration, or real-browser/physical-phone behaviour. Provider-disk durability,
host-rebuild recovery, and a field pilot remain explicitly pending human/device
acceptance work.

## Apache / `public_html` hardening

Prefer placing this repository outside `public_html` and proxying only public
requests to Gunicorn. If shared hosting forces the repository below the webroot,
keep the included `.htaccess`: it disables directory listings and denies access
to dotfiles, `.env` variants, Python/configuration files, SQLite data, logs, and
private source/test directories. Confirm Apache allows `FileInfo`, `AuthConfig`,
and `Options` overrides; otherwise move the same rules into the virtual-host
configuration. Test that `/.env`, `/.git/config`, `/config.py`, and
`/data/case_log.sqlite3` return 403 or 404 before making the site public.

The app sends a restrictive Content Security Policy, anti-framing and MIME
sniffing protections, a no-referrer policy, HTTPS transport security, and camera/
microphone permissions limited to the app itself. Search indexing is disabled by
default through `robots.txt` and `X-Robots-Tag`; enable it only with the server
variable `SEARCH_ENGINE_INDEXING_ENABLED=true` after a deliberate public-launch
review. These controls reduce exposure and common browser attacks but do not
replace provider firewalls, dependency updates, monitoring, or backups.


## Persistence and recovery rehearsal (plan ticket 07)

Mount a durable private directory outside Flask static files, for example
`/data/dakikobo`, and configure these server variables:

```text
STATE_DB_PATH=/data/dakikobo/runtime_state.sqlite3
CASE_LOG_DB_PATH=/data/dakikobo/case_log.sqlite3
FEEDBACK_IMAGE_DIR=/data/dakikobo/feedback_images
APP_ENV=production
FLASK_DEBUG=false
```

Keep `FLASK_SECRET_KEY` stable in the hosting secret manager across restarts and
restores. Changing it invalidates browser session cookies and can prevent users
from accessing their existing owned journal. A container filesystem alone does
not establish durability; verify the provider's actual volume survives rebuilds.
Audio is a disposable cache. The reviewed corpus can rebuild Chroma separately.

### Consistent backup

1. Choose a restricted backup location outside every served directory. Record the
   application commit, corpus/policy revision, backup time and retention deadline.
2. For a consistent journal **and photos** snapshot, pause journal writes on all
   workers while snapshotting. An ordinary copy of an active SQLite main file can
   omit committed WAL data. Use SQLite's backup API for each database, or stop all
   workers before making a complete filesystem snapshot.
3. With writers paused, use the following Python pattern with explicitly selected
   source/destination paths. The destination must be a new private file; never
   point it at the active database. Repeat for the runtime-state database if its
   contents are needed. Copy the photo directory during the same write pause.

```python
from pathlib import Path
import sqlite3

source_path = Path('/data/dakikobo/case_log.sqlite3')
backup_path = Path('/private-backups/SELECT_NEW_BACKUP_NAME.sqlite3')
assert source_path.is_file()
assert not backup_path.exists()
with sqlite3.connect(source_path.as_uri() + '?mode=ro', uri=True) as source:
    with sqlite3.connect(backup_path) as destination:
        source.backup(destination)
        assert destination.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
```

4. Resume writers and check health. Protect database backups, photo copies and
   the session secret independently; do not put them in Git or public artifacts.
   Apply a documented retention/deletion policy to backups as well as live data.

### Restore and rollback

1. Restore to an isolated instance first, with outbound model calls disabled and
   synthetic or explicitly authorized data. Use the same session secret to test
   continuity. Keep the original snapshot unchanged for comparison.
2. Journal photo references currently store filesystem paths. Preserve the same
   absolute mount path in the isolated container, or perform a separately tested
   reference migration. Moving photos to a different path alone is insufficient.
3. Run integrity checks, then verify owner access, denial for a second browser,
   deletion and expiry through the application. Restoring an older snapshot can
   resurrect deleted rows: reconcile deletions and retention before reopening.
4. Before replacing a live instance, pause writers and take a fresh rollback
   snapshot of databases and photos. If restore verification fails, keep the
   service closed to writes and return to that exact snapshot and application
   version. Revalidate cache-policy identity and session access before reopening.

The local synthetic rehearsal is executable with:

```bash
.venv/bin/python -m pytest -q tests/test_recovery.py
```

It creates consented synthetic cases, starts fresh Python/Flask processes,
reuses the owner's test cookie, denies another client, backs up through SQLite,
restores into a separate temporary directory, then verifies deletion and expiry.
A separate snapshot test restores synthetic photos at their original isolated
path. The HTTP rehearsal uses a real loopback Werkzeug server, preserves the
HTTP client's cookie through a restart and restore, and verifies that another
client cannot delete the owner's case. Secure cookies are disabled only inside
that loopback test server because it uses HTTP rather than TLS.
The original journal and snapshots remain unchanged. No real user data, provider
calls, device browser, host reboot or durable provider volume are involved.
Provider-volume persistence remains a release check; this local rehearsal cannot
establish it. See `reports/operational_readiness_2026-09-15.md` for remaining gates.
