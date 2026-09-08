"""Write a review inventory without promoting or modifying any source."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.source_policy import eligible_source, source_review

def report():
    lines = ['# Source eligibility inventory', '', 'Generated from the local candidate files. Eligibility is not a new expert review or proof of deployed index contents.', '', '| File | Review status | Eligible |', '|---|---|---|']
    for path in sorted((ROOT / 'Data').rglob('*')):
        if path.suffix.lower() not in ('.pdf', '.md') or '_archive' in path.parts:
            continue
        if path.suffix == '.md' and 'markdown' not in path.parts:
            continue
        meta = source_review(path)
        lines.append(f'| `{path.relative_to(ROOT)}` | {meta.get("review_status", "missing")} | {"yes" if eligible_source(path) else "no"} |')
    return '\n'.join(lines) + '\n'

if __name__ == '__main__':
    destination = ROOT / 'Data/reviews/SOURCE_ELIGIBILITY_2026-09-06.md'
    destination.write_text(report())
    print(destination)
