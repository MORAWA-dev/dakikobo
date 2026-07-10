"""Offline trusted-source refresh (manual or cron).

Scrapes allowlisted seed URLs into Data/scraped/pending/ via Firecrawl.
Never promotes into active RAG. Always review before promotion.

Usage:
    python scripts/refresh_trusted_sources.py
    python scripts/refresh_trusted_sources.py --urls-file Data/scraped/seed_urls_trusted_bf.txt
    python scripts/refresh_trusted_sources.py --dry-run

Cron example (weekly, local machine with FIRECRAWL_API_KEY in env):
    0 6 * * 1 cd /path/to/dakikobo && .venv/bin/python scripts/refresh_trusted_sources.py
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_SEED = PROJECT_ROOT / "Data" / "scraped" / "seed_urls_trusted_bf.txt"
DEFAULT_LOG = PROJECT_ROOT / "reports" / "source_refresh_log.md"
INGEST_SCRIPT = PROJECT_ROOT / "scripts" / "firecrawl_ingest.py"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh trusted source scrapes offline (no auto-promote)."
    )
    parser.add_argument(
        "--urls-file",
        default=str(DEFAULT_SEED),
        help="Seed URL list (one URL per line).",
    )
    parser.add_argument(
        "--log",
        default=str(DEFAULT_LOG),
        help="Markdown log path for this run.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List URLs that would be scraped and exit.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=90.0,
        help="HTTP timeout seconds passed to firecrawl_ingest.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=2,
        help="Max Firecrawl retries per URL.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting existing pending scrapes.",
    )
    return parser.parse_args(argv)


def _read_urls(path: Path) -> list[str]:
    if not path.is_file():
        raise FileNotFoundError(f"Seed file not found: {path}")
    urls = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line)
    return urls


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    seed_path = Path(args.urls_file)
    log_path = Path(args.log)
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")

    try:
        urls = _read_urls(seed_path)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"Trusted refresh — {len(urls)} URL(s) from {seed_path}")
    for url in urls:
        print(f"  - {url}")

    if args.dry_run:
        print("Dry run only — no scrape.")
        return 0

    if not os.environ.get("FIRECRAWL_API_KEY"):
        # firecrawl_ingest also checks config; fail early with a clear message.
        print(
            "ERROR: FIRECRAWL_API_KEY is not set. Load .env before refreshing.",
            file=sys.stderr,
        )
        return 2

    cmd = [
        sys.executable,
        str(INGEST_SCRIPT),
        "--urls-file",
        str(seed_path),
        "--timeout",
        str(args.timeout),
        "--max-retries",
        str(args.max_retries),
    ]
    if args.overwrite:
        cmd.append("--overwrite")

    print("Running offline scrape (pending only, no promote)...", flush=True)
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    finished = datetime.now(timezone.utc).isoformat(timespec="seconds")

    log_path.parent.mkdir(parents=True, exist_ok=True)
    body = [
        f"# Source refresh log — {started}",
        "",
        f"- Finished: `{finished}`",
        f"- Seed file: `{seed_path}`",
        f"- URL count: `{len(urls)}`",
        f"- Exit code: `{proc.returncode}`",
        f"- Auto-promote: **never** (review `Data/scraped/pending/` first)",
        "",
        "## Command",
        "",
        "```",
        " ".join(cmd),
        "```",
        "",
        "## Stdout",
        "",
        "```",
        (proc.stdout or "").strip() or "(empty)",
        "```",
        "",
        "## Stderr",
        "",
        "```",
        (proc.stderr or "").strip() or "(empty)",
        "```",
        "",
        "## Next steps",
        "",
        "1. Open new files under `Data/scraped/pending/`.",
        "2. Reject 404/502/nav-only pages into `Data/scraped/rejected/`.",
        "3. Curate useful content into `Data/markdown/scraped_reviewed/`.",
        "4. Rebuild / redeploy only after review.",
        "",
    ]
    # Append so weekly runs keep history.
    previous = log_path.read_text(encoding="utf-8") if log_path.is_file() else ""
    log_path.write_text("\n".join(body) + "\n" + previous, encoding="utf-8")
    print(f"Wrote log: {log_path}")

    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
    if proc.stderr:
        print(proc.stderr, end="" if proc.stderr.endswith("\n") else "\n", file=sys.stderr)

    print(
        "Reminder: scrapes stay pending until human review. "
        "Do not treat this as scheduled RAG update."
    )
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
