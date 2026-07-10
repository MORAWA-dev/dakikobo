"""HTTP health probe for trusted seed URLs (no scrape, no promote).

Use before Firecrawl refresh to skip known-down hosts, or on a cron to log
reachability of WASCAL / AGRHYMET / INERA / ministry / FAO seeds.

Usage:
    python scripts/check_trusted_sources.py
    python scripts/check_trusted_sources.py --urls-file Data/scraped/seed_urls_trusted_bf.txt
    python scripts/check_trusted_sources.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_SEED = PROJECT_ROOT / "Data" / "scraped" / "seed_urls_trusted_bf.txt"
DEFAULT_LOG = PROJECT_ROOT / "reports" / "trusted_source_health.md"


def read_urls(path: Path) -> list[str]:
    if not path.is_file():
        raise FileNotFoundError(f"Seed file not found: {path}")
    urls = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line)
    return urls


def probe_url(url: str, timeout: float) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    result: dict[str, Any] = {
        "url": url,
        "ok": False,
        "status_code": None,
        "error": "",
        "elapsed_ms": 0,
    }
    try:
        # HEAD first; some sites block HEAD — fall back to GET range-ish GET.
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        if response.status_code in {403, 405, 501}:
            response = requests.get(url, timeout=timeout, allow_redirects=True, stream=True)
            response.close()
        result["status_code"] = response.status_code
        result["ok"] = 200 <= response.status_code < 400
    except requests.RequestException as exc:
        result["error"] = str(exc)[:240]
    elapsed = datetime.now(timezone.utc) - started
    result["elapsed_ms"] = int(elapsed.total_seconds() * 1000)
    return result


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe trusted seed URL health.")
    parser.add_argument("--urls-file", default=str(DEFAULT_SEED))
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--json", action="store_true", help="Print JSON array to stdout.")
    parser.add_argument(
        "--log",
        default=str(DEFAULT_LOG),
        help="Optional markdown log path (append). Empty string disables.",
    )
    parser.add_argument(
        "--fail-on-down",
        action="store_true",
        help="Exit 1 if any URL is down (useful in CI optional jobs).",
    )
    return parser.parse_args(argv)


def format_markdown(results: list[dict[str, Any]], *, started: str) -> str:
    up = sum(1 for r in results if r["ok"])
    lines = [
        f"# Trusted source health — {started}",
        "",
        f"- Up: **{up}/{len(results)}**",
        "",
        "| Status | Code | ms | URL | Error |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    for r in results:
        mark = "UP" if r["ok"] else "DOWN"
        err = (r.get("error") or "").replace("|", "\\|")[:80]
        lines.append(
            f"| {mark} | {r.get('status_code') or '-'} | {r.get('elapsed_ms', 0)} | "
            f"`{r['url']}` | {err} |"
        )
    lines.append("")
    lines.append(
        "Next: if UP and allowlisted, run `scripts/refresh_trusted_sources.py` "
        "then human-review pending files. Never auto-promote."
    )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    seed = Path(args.urls_file)
    try:
        urls = read_urls(seed)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if not urls:
        print("ERROR: no URLs in seed file.", file=sys.stderr)
        return 2

    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(probe_url, url, args.timeout): url for url in urls}
        for fut in as_completed(futures):
            results.append(fut.result())

    # Stable order = seed order
    by_url = {r["url"]: r for r in results}
    ordered = [by_url[u] for u in urls if u in by_url]

    if args.json:
        print(json.dumps(ordered, ensure_ascii=False, indent=2))
    else:
        for r in ordered:
            mark = "UP  " if r["ok"] else "DOWN"
            code = r.get("status_code") if r.get("status_code") is not None else "-"
            print(f"{mark}  {code:>4}  {r['elapsed_ms']:>5}ms  {r['url']}")
            if r.get("error") and not r["ok"]:
                print(f"       {r['error'][:120]}")

    if args.log:
        log_path = Path(args.log)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        body = format_markdown(ordered, started=started)
        previous = log_path.read_text(encoding="utf-8") if log_path.is_file() else ""
        log_path.write_text(body + "\n" + previous, encoding="utf-8")
        if not args.json:
            print(f"Wrote log: {log_path}")

    down = [r for r in ordered if not r["ok"]]
    if args.fail_on_down and down:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
