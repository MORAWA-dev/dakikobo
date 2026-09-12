"""Write a review inventory without promoting or modifying any source."""
import argparse
from datetime import date
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.source_policy import eligible_source, quarantined_source, source_review


def report(root=ROOT):
    lines = [
        '# Source eligibility inventory',
        '',
        f'Generated {date.today().isoformat()} from the local candidate files. '
        'Eligibility is not a new expert review or proof of deployed index contents.',
        '',
        '| File | Review status | Rights / license | Quarantined | Eligible |',
        '|---|---|---|---|---|',
    ]
    counts = {'eligible': 0, 'quarantined': 0, 'pending_or_missing': 0}
    for path in sorted((root / 'Data').rglob('*')):
        if path.suffix.lower() not in ('.pdf', '.md') or '_archive' in path.parts:
            continue
        if path.suffix == '.md' and 'markdown' not in path.parts:
            continue
        meta = source_review(path)
        quarantined = quarantined_source(path)
        eligible = eligible_source(path)
        if eligible:
            counts['eligible'] += 1
        elif quarantined:
            counts['quarantined'] += 1
        else:
            counts['pending_or_missing'] += 1
        lines.append(
            f'| `{path.relative_to(root)}` '
            f'| {meta.get("review_status", "missing")} '
            f'| {meta.get("license", "unknown")} '
            f'| {"yes" if quarantined else "no"} '
            f'| {"yes" if eligible else "no"} |'
        )
    lines += [
        '',
        f"Totals: {counts['eligible']} eligible, {counts['quarantined']} quarantined, "
        f"{counts['pending_or_missing']} pending or missing review.",
        '',
        'Quarantine always wins: a file under a `_quarantine` directory or with '
        '`review_status: quarantined`/`rights_unclear` is never indexed, even if '
        'an approval flag is also present.',
    ]
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--output',
        default=str(ROOT / 'Data/reviews/SOURCE_ELIGIBILITY_2026-09-06.md'),
        help='Markdown inventory destination.',
    )
    args = parser.parse_args()
    destination = Path(args.output)
    destination.write_text(report())
    print(destination)
