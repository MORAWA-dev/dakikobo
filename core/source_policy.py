"""Explicit ingestion eligibility; missing or pending review fails closed."""
import json
from pathlib import Path

APPROVED_STATUSES = frozenset({'reviewed_by_owner', 'reviewed_by_agronomist'})


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
    if not text.startswith('---\n'):
        return {}
    metadata = {}
    for line in text.splitlines()[1:]:
        if line.strip() == '---':
            break
        key, separator, value = line.partition(':')
        if separator:
            metadata[key.strip()] = value.strip().strip('\"\'')
    return metadata


def eligible_source(path):
    metadata = source_review(path)
    return (metadata.get('review_status') in APPROVED_STATUSES
            and bool(metadata.get('title'))
            and bool(metadata.get('source_file') or metadata.get('source_url')))
