"""Fetch candidate web sources with Firecrawl and keep them out of active RAG.

Usage:
    python scripts/firecrawl_ingest.py --url https://example.org/page
    python scripts/firecrawl_ingest.py --urls-file source_urls.txt
    python scripts/firecrawl_ingest.py --promote Data/scraped/pending/page.md --reviewer codex

Scraped pages are written to Data/scraped/pending/ with review metadata and a
checklist. They only enter the active RAG corpus after promotion into
Data/markdown/scraped_reviewed/.
"""

from __future__ import annotations

import argparse
import csv
import fnmatch
import hashlib
import os
import re
import sys
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    FIRECRAWL_API_KEY,
    FIRECRAWL_API_URL,
    FIRECRAWL_HTTP_TIMEOUT_SECONDS,
    FIRECRAWL_MAX_RETRIES,
    FIRECRAWL_PENDING_DIR,
    FIRECRAWL_REVIEWED_DIR,
    FIRECRAWL_SCRAPE_TIMEOUT_MS,
)


RETRYABLE_STATUSES = {408, 409, 425, 429, 500, 502, 503, 504}
CONTENT_MARKER = "<!-- DAKIKOBO_SCRAPED_CONTENT_START -->"
DEFAULT_ALLOWLIST_PATH = PROJECT_ROOT / "Data" / "scraped" / "source_allowlist.csv"
DEFAULT_SEED_URLS_PATH = PROJECT_ROOT / "Data" / "scraped" / "seed_urls_fao_burkina.txt"
DEFAULT_TRUSTED_SEED_URLS_PATH = (
    PROJECT_ROOT / "Data" / "scraped" / "seed_urls_trusted_bf.txt"
)


class FirecrawlIngestError(RuntimeError):
    """Raised when a candidate source cannot be scraped or written."""


@dataclass(frozen=True)
class ScrapedPage:
    url: str
    title: str
    markdown: str
    metadata: dict[str, Any]
    scraped_at: str


@dataclass(frozen=True)
class AllowlistEntry:
    source_id: str
    enabled: bool
    url_pattern: str
    publisher: str
    scope: str
    topics: str
    crops: str
    license_note: str
    notes: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _slugify(value: str, fallback: str = "source") -> str:
    value = (value or "").strip().lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"https?://", "", value)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return (value or fallback)[:80]


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split())


def _url_fingerprint(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]


def _quote_frontmatter(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\\", "\\\\").replace('"', '\\"')
    text = text.replace("\n", " ").replace("\r", " ")
    return f'"{text}"'


def _frontmatter_block(metadata: dict[str, Any]) -> str:
    lines = ["---"]
    for key, value in metadata.items():
        if value in (None, ""):
            continue
        lines.append(f"{key}: {_quote_frontmatter(value)}")
    lines.append("---")
    return "\n".join(lines)


def _split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    end_index = None
    for idx, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_index = idx
            break
    if end_index is None:
        return {}, text

    metadata: dict[str, str] = {}
    for line in lines[1:end_index]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"')
        if key:
            metadata[key] = value.replace('\\"', '"').replace("\\\\", "\\")
    body = "\n".join(lines[end_index + 1 :]).strip()
    return metadata, body


def _content_after_marker(body: str) -> str:
    if CONTENT_MARKER not in body:
        return body.strip()
    return body.split(CONTENT_MARKER, 1)[1].strip()


def _title_from_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.rstrip("/").split("/")[-1]
    return path.replace("-", " ").replace("_", " ").strip().title() or parsed.netloc


def _normalize_url_for_match(url: str) -> str:
    parsed = urlparse((url or "").strip())
    if not parsed.scheme or not parsed.netloc:
        raise FirecrawlIngestError(f"Invalid URL: {url}")
    normalized = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
        fragment="",
    )
    return normalized.geturl().rstrip("/").lower()


def _is_enabled(value: str) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "y", "enabled"}


def load_allowlist(path: str | Path = DEFAULT_ALLOWLIST_PATH) -> list[AllowlistEntry]:
    allowlist_path = Path(path)
    if not allowlist_path.exists():
        raise FirecrawlIngestError(f"Allowlist file not found: {allowlist_path}")

    entries = []
    with allowlist_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(
            line for line in f if line.strip() and not line.lstrip().startswith("#")
        )
        for row in reader:
            pattern = (row.get("url_pattern") or "").strip()
            source_id = (row.get("source_id") or "").strip()
            if not pattern or not source_id:
                continue
            entries.append(
                AllowlistEntry(
                    source_id=source_id,
                    enabled=_is_enabled(row.get("enabled", "")),
                    url_pattern=pattern,
                    publisher=(row.get("publisher") or "unknown").strip(),
                    scope=(row.get("scope") or "").strip(),
                    topics=(row.get("topics") or "").strip(),
                    crops=(row.get("crops") or "").strip(),
                    license_note=(row.get("license_note") or "unknown").strip(),
                    notes=(row.get("notes") or "").strip(),
                )
            )
    return entries


def match_allowlist_entry(
    url: str,
    entries: list[AllowlistEntry],
) -> AllowlistEntry | None:
    normalized_url = _normalize_url_for_match(url)
    for entry in entries:
        if not entry.enabled:
            continue
        pattern = _normalize_url_for_match(entry.url_pattern.replace("*", "wildcard"))
        pattern = pattern.replace("wildcard", "*")
        if fnmatch.fnmatch(normalized_url, pattern):
            return entry
        # Patterns like https://example.org/* should also allow the site root.
        if pattern.endswith("/*"):
            base = pattern[:-2].rstrip("/")
            if normalized_url.rstrip("/") == base:
                return entry
    return None


def require_url_allowed(url: str, entries: list[AllowlistEntry]) -> AllowlistEntry:
    entry = match_allowlist_entry(url, entries)
    if entry is None:
        raise FirecrawlIngestError(
            f"URL is not in the Firecrawl allowlist: {url}. "
            "Add it to Data/scraped/source_allowlist.csv or pass --allow-unlisted."
        )
    return entry


class FirecrawlClient:
    def __init__(
        self,
        *,
        api_key: str,
        api_url: str = FIRECRAWL_API_URL,
        http_timeout_seconds: float = FIRECRAWL_HTTP_TIMEOUT_SECONDS,
        scrape_timeout_ms: int = FIRECRAWL_SCRAPE_TIMEOUT_MS,
        max_retries: int = FIRECRAWL_MAX_RETRIES,
        session=requests,
        sleep=time.sleep,
    ):
        if not api_key:
            raise FirecrawlIngestError("FIRECRAWL_API_KEY is not configured.")
        self.api_key = api_key
        self.api_url = api_url
        self.http_timeout_seconds = http_timeout_seconds
        self.scrape_timeout_ms = scrape_timeout_ms
        self.max_retries = max_retries
        self.session = session
        self.sleep = sleep

    def scrape(self, url: str) -> ScrapedPage:
        payload = {
            "url": url,
            "formats": ["markdown"],
            "onlyMainContent": True,
            "removeBase64Images": True,
            "blockAds": True,
            "timeout": self.scrape_timeout_ms,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        last_error = ""
        attempts = self.max_retries + 1
        for attempt in range(attempts):
            try:
                response = self.session.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=self.http_timeout_seconds,
                )
            except requests.RequestException as exc:
                last_error = str(exc)
                if attempt < self.max_retries:
                    self.sleep(min(2 ** attempt, 8))
                    continue
                raise FirecrawlIngestError(f"{url}: {last_error}") from exc

            if response.status_code in RETRYABLE_STATUSES and attempt < self.max_retries:
                last_error = f"HTTP {response.status_code}"
                self.sleep(min(2 ** attempt, 8))
                continue

            if response.status_code >= 400:
                raise FirecrawlIngestError(
                    f"{url}: Firecrawl returned HTTP {response.status_code}: "
                    f"{response.text[:300]}"
                )

            try:
                body = response.json()
            except ValueError as exc:
                raise FirecrawlIngestError(f"{url}: Firecrawl returned invalid JSON.") from exc

            if body.get("success") is False:
                raise FirecrawlIngestError(f"{url}: Firecrawl reported failure: {body}")

            data = body.get("data") or {}
            markdown = (data.get("markdown") or "").strip()
            if not markdown:
                raise FirecrawlIngestError(f"{url}: Firecrawl returned no Markdown.")

            metadata = data.get("metadata") or {}
            source_url = metadata.get("sourceURL") or metadata.get("url") or url
            title = _clean_text(metadata.get("title") or _title_from_url(source_url))
            return ScrapedPage(
                url=source_url,
                title=title,
                markdown=markdown,
                metadata=metadata,
                scraped_at=_utc_now(),
            )

        raise FirecrawlIngestError(f"{url}: {last_error or 'scrape failed'}")


def pending_markdown(
    page: ScrapedPage,
    *,
    country: str,
    language: str,
    publisher: str,
    topics: str,
    crops: str,
    license_note: str = "unknown",
    source_id: str = "",
) -> str:
    metadata = {
        "title": page.title,
        "source_file": page.url,
        "source_url": page.url,
        "source_id": source_id,
        "doc_type": "scraped_web",
        "language": language,
        "country": country,
        "publisher": publisher,
        "year": page.metadata.get("publishedTime") or page.metadata.get("year") or "unknown",
        "license": license_note,
        "review_status": "pending_human_review",
        "scraped_at": page.scraped_at,
        "topics": topics,
        "crops": crops,
    }
    source_status = page.metadata.get("statusCode", "unknown")
    lines = [
        _frontmatter_block(metadata),
        "",
        f"# {page.title}",
        "",
        "## Review checklist",
        "",
        "- [ ] Verify title, publisher, date, country or regional scope.",
        "- [ ] Verify license or reuse terms before committing active RAG content.",
        "- [ ] Remove navigation, ads, unrelated comments, and duplicate boilerplate.",
        "- [ ] Confirm crop names, fertilizer doses, pesticide names, and dates against the source.",
        "- [ ] Set useful `topics` and `crops` metadata before promotion.",
        "",
        "## Source metadata",
        "",
        f"- URL: {page.url}",
        f"- Firecrawl status code: {source_status}",
        f"- Scraped at: {page.scraped_at}",
        "",
        CONTENT_MARKER,
        "",
        page.markdown.strip(),
        "",
    ]
    return "\n".join(lines)


def write_pending_markdown(
    page: ScrapedPage,
    *,
    output_dir: str | Path = FIRECRAWL_PENDING_DIR,
    country: str = "Burkina Faso",
    language: str = "fr",
    publisher: str = "unknown",
    topics: str = "",
    crops: str = "",
    license_note: str = "unknown",
    source_id: str = "",
    overwrite: bool = False,
) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    date_part = page.scraped_at[:10].replace("-", "")
    slug = _slugify(page.title or page.url)
    filename = f"{date_part}_{slug}_{_url_fingerprint(page.url)}.md"
    target = output_path / filename
    if target.exists() and not overwrite:
        raise FirecrawlIngestError(f"Refusing to overwrite existing file: {target}")
    target.write_text(
        pending_markdown(
            page,
            country=country,
            language=language,
            publisher=publisher,
            topics=topics,
            crops=crops,
            license_note=license_note,
            source_id=source_id,
        ),
        encoding="utf-8",
    )
    return target


def promote_reviewed_markdown(
    pending_path: str | Path,
    *,
    reviewer: str,
    reviewed_dir: str | Path = FIRECRAWL_REVIEWED_DIR,
    reviewed_at: str | None = None,
    overwrite: bool = False,
) -> Path:
    if not reviewer:
        raise FirecrawlIngestError("A reviewer name/id is required for promotion.")

    pending = Path(pending_path)
    metadata, body = _split_frontmatter(pending.read_text(encoding="utf-8"))
    if not metadata:
        raise FirecrawlIngestError(f"{pending}: missing frontmatter.")

    content = _content_after_marker(body)
    if not content:
        raise FirecrawlIngestError(f"{pending}: no scraped content found.")

    reviewed_at = reviewed_at or _utc_now()
    metadata.update(
        {
            "review_status": f"reviewed_by_{reviewer}",
            "reviewed_at": reviewed_at,
            "data_format": "markdown",
        }
    )

    reviewed_root = Path(reviewed_dir)
    reviewed_root.mkdir(parents=True, exist_ok=True)
    target = reviewed_root / pending.name
    if target.exists() and not overwrite:
        raise FirecrawlIngestError(f"Refusing to overwrite existing file: {target}")

    title = metadata.get("title", pending.stem)
    reviewed_text = "\n".join(
        [
            _frontmatter_block(metadata),
            "",
            f"# {title}",
            "",
            f"Source web revue: {metadata.get('source_url', metadata.get('source_file', 'unknown'))}",
            "",
            content,
            "",
        ]
    )
    target.write_text(reviewed_text, encoding="utf-8")
    return target


def _read_urls_file(path: str | Path) -> list[str]:
    urls = []
    for raw_line in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line)
    return urls


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape candidate sources with Firecrawl.")
    parser.add_argument("--url", action="append", default=[], help="URL to scrape; can be repeated.")
    parser.add_argument("--urls-file", help="Text file with one URL per line.")
    parser.add_argument("--seed-batch", action="store_true", help="Use the curated FAO Burkina Faso seed URL batch.")
    parser.add_argument(
        "--trusted-batch",
        action="store_true",
        help="Use the expanded trusted seed batch (ministry/INERA/WASCAL/AGRHYMET/CILSS/FAO).",
    )
    parser.add_argument("--list-seeds", action="store_true", help="Print the curated seed URLs and exit.")
    parser.add_argument("--allowlist", default=str(DEFAULT_ALLOWLIST_PATH), help="CSV allowlist of trusted URL patterns.")
    parser.add_argument("--allow-unlisted", action="store_true", help="Scrape URLs outside the allowlist; use only for manual experiments.")
    parser.add_argument("--output-dir", default=FIRECRAWL_PENDING_DIR, help="Pending output directory.")
    parser.add_argument("--reviewed-dir", default=FIRECRAWL_REVIEWED_DIR, help="Reviewed output directory.")
    parser.add_argument("--promote", action="append", default=[], help="Pending Markdown file to promote.")
    parser.add_argument("--reviewer", help="Reviewer name/id required with --promote.")
    parser.add_argument("--country", default="Burkina Faso")
    parser.add_argument("--language", default="fr")
    parser.add_argument("--publisher", default="unknown")
    parser.add_argument("--topics", default="", help="Comma-separated topics metadata.")
    parser.add_argument("--crops", default="", help="Comma-separated crops metadata.")
    parser.add_argument("--timeout", type=float, default=FIRECRAWL_HTTP_TIMEOUT_SECONDS)
    parser.add_argument("--scrape-timeout-ms", type=int, default=FIRECRAWL_SCRAPE_TIMEOUT_MS)
    parser.add_argument("--max-retries", type=int, default=FIRECRAWL_MAX_RETRIES)
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output files.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    if args.list_seeds:
        seed_path = (
            DEFAULT_TRUSTED_SEED_URLS_PATH if args.trusted_batch else DEFAULT_SEED_URLS_PATH
        )
        for url in _read_urls_file(seed_path):
            print(url)
        return 0

    if args.promote:
        failures = 0
        for path in args.promote:
            try:
                promoted = promote_reviewed_markdown(
                    path,
                    reviewer=args.reviewer or "",
                    reviewed_dir=args.reviewed_dir,
                    overwrite=args.overwrite,
                )
                print(f"Promoted: {promoted}")
            except FirecrawlIngestError as exc:
                failures += 1
                print(f"ERROR: {exc}", file=sys.stderr)
        return 1 if failures else 0

    urls = list(args.url)
    if args.urls_file:
        urls.extend(_read_urls_file(args.urls_file))
    if args.seed_batch:
        urls.extend(_read_urls_file(DEFAULT_SEED_URLS_PATH))
    if args.trusted_batch:
        urls.extend(_read_urls_file(DEFAULT_TRUSTED_SEED_URLS_PATH))
    if not urls:
        print(
            "ERROR: provide --url, --urls-file, --seed-batch, --trusted-batch, or --promote.",
            file=sys.stderr,
        )
        return 2

    allowlist_entries: list[AllowlistEntry] = []
    allowlist_matches: dict[str, AllowlistEntry | None] = {}
    if not args.allow_unlisted:
        try:
            allowlist_entries = load_allowlist(args.allowlist)
            for url in urls:
                allowlist_matches[url] = require_url_allowed(url, allowlist_entries)
        except FirecrawlIngestError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2

    try:
        client = FirecrawlClient(
            api_key=FIRECRAWL_API_KEY,
            http_timeout_seconds=args.timeout,
            scrape_timeout_ms=args.scrape_timeout_ms,
            max_retries=args.max_retries,
        )
    except FirecrawlIngestError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    failures = 0
    for url in urls:
        try:
            entry = allowlist_matches.get(url)
            page = client.scrape(url)
            path = write_pending_markdown(
                page,
                output_dir=args.output_dir,
                country=args.country,
                language=args.language,
                publisher=args.publisher if args.publisher != "unknown" else (
                    entry.publisher if entry else args.publisher
                ),
                topics=args.topics or (entry.topics if entry else ""),
                crops=args.crops or (entry.crops if entry else ""),
                license_note=entry.license_note if entry else "unknown",
                source_id=entry.source_id if entry else "",
                overwrite=args.overwrite,
            )
            print(f"Pending review: {path}")
        except FirecrawlIngestError as exc:
            failures += 1
            print(f"ERROR: {exc}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
