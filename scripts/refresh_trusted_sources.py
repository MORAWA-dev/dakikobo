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
import tempfile
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.check_trusted_sources import probe_url

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
        "--probe-timeout",
        type=float,
        default=12.0,
        help="Per-URL reachability probe timeout before scrape (default 12s).",
    )
    parser.add_argument(
        "--skip-health-check",
        action="store_true",
        help="Scrape all seed URLs without a preflight HTTP probe.",
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


def _filter_reachable(urls: list[str], *, timeout: float) -> tuple[list[str], list[str]]:
    """Return (up_urls, down_urls) using lightweight HTTP probes."""
    up: list[str] = []
    down: list[str] = []
    for url in urls:
        result = probe_url(url, timeout=timeout)
        if result.get("ok"):
            up.append(url)
            print(f"  UP    {url}")
        else:
            down.append(url)
            detail = result.get("status_code") or result.get("error") or "unreachable"
            print(f"  DOWN  {url} ({detail})")
    return up, down


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

    print(f"Trusted refresh — {len(urls)} seed URL(s) from {seed_path}")
    down_urls: list[str] = []
    scrape_urls = list(urls)
    if not args.skip_health_check:
        print("Preflight HTTP probe (skip DOWN hosts)...")
        scrape_urls, down_urls = _filter_reachable(
            urls, timeout=args.probe_timeout
        )
        print(f"Reachable for scrape: {len(scrape_urls)}/{len(urls)}")
    else:
        for url in urls:
            print(f"  - {url}")

    if args.dry_run:
        print("Dry run only — no scrape.")
        if down_urls:
            print(f"Would skip {len(down_urls)} DOWN URL(s).")
        return 0

    if not scrape_urls:
        print(
            "ERROR: no reachable URLs to scrape. "
            "Retry later or pass --skip-health-check.",
            file=sys.stderr,
        )
        return 2

    if not os.environ.get("FIRECRAWL_API_KEY"):
        # firecrawl_ingest also checks config; fail early with a clear message.
        print(
            "ERROR: FIRECRAWL_API_KEY is not set. Load .env before refreshing.",
            file=sys.stderr,
        )
        return 2

    # Write a temporary seed of only UP URLs so Firecrawl is not wasted on DOWN hosts.
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix="_trusted_up.txt",
        delete=False,
    ) as tmp:
        tmp.write("\n".join(scrape_urls) + "\n")
        up_seed = tmp.name

    cmd = [
        sys.executable,
        str(INGEST_SCRIPT),
        "--urls-file",
        up_seed,
        "--timeout",
        str(args.timeout),
        "--max-retries",
        str(args.max_retries),
    ]
    if args.overwrite:
        cmd.append("--overwrite")

    print("Running offline scrape (pending only, no promote)...", flush=True)
    try:
        proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    finally:
        try:
            os.unlink(up_seed)
        except OSError:
            pass
    finished = datetime.now(timezone.utc).isoformat(timespec="seconds")

    log_path.parent.mkdir(parents=True, exist_ok=True)
    body = [
        f"# Source refresh log — {started}",
        "",
        f"- Finished: `{finished}`",
        f"- Seed file: `{seed_path}`",
        f"- Seed URL count: `{len(urls)}`",
        f"- Scraped (reachable): `{len(scrape_urls)}`",
        f"- Skipped DOWN: `{len(down_urls)}`",
        f"- Exit code: `{proc.returncode}`",
        f"- Auto-promote: **never** (review `Data/scraped/pending/` first)",
        "",
        "## Skipped (DOWN preflight)",
        "",
    ]
    if down_urls:
        body.extend(f"- `{u}`" for u in down_urls)
    else:
        body.append("- (none)")
    body.extend(
        [
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
    )
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
