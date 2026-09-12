"""Explicit ingestion eligibility; missing or pending review fails closed."""
import json
from pathlib import Path

APPROVED_STATUSES = frozenset({'reviewed_by_owner', 'reviewed_by_agronomist'})

# Explicit set-aside: unclear usage rights or a reviewer decision to exclude.
# Quarantine always wins over any approval flag, including via the
# `_quarantine` directory convention.
QUARANTINE_STATUSES = frozenset({'quarantined', 'rights_unclear'})


def quarantined_source(path):
    """True when a source is explicitly set aside and must never be indexed."""
    if '_quarantine' in Path(path).parts:
        return True
    return source_review(path).get('review_status') in QUARANTINE_STATUSES


def split_markdown_frontmatter(raw_text):
    """Return flat YAML-style metadata and body for the reviewed corpus."""
    text = raw_text.lstrip('\ufeff')
    lines = text.splitlines()
    if not lines or lines[0].strip() != '---':
        return {}, raw_text
    end_index = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.strip() == '---'),
        None,
    )
    if end_index is None:
        return {}, raw_text
    metadata = {}
    for line in lines[1:end_index]:
        key, separator, value = line.partition(':')
        if separator and key.strip():
            metadata[key.strip()] = value.strip().strip('\"\'')
    return metadata, '\n'.join(lines[end_index + 1:]).strip()


def source_review(path):
    path = Path(path)
    if path.suffix.lower() == '.pdf':
        sidecar = path.with_suffix('.pdf.review.json')
        try:
            data = json.loads(sidecar.read_text())
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}
    try:
        text = path.read_text(encoding='utf-8').lstrip('\ufeff')
    except (OSError, UnicodeError):
        return {}
    metadata, _ = split_markdown_frontmatter(text)
    return metadata


def eligible_source(path):
    if quarantined_source(path):
        return False
    metadata = source_review(path)
    return (metadata.get('review_status') in APPROVED_STATUSES
            and bool(metadata.get('title'))
            and bool(metadata.get('source_file') or metadata.get('source_url')))
