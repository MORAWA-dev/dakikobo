"""Export feedback/case-log rows for private evaluation datasets.

Usage:
    python scripts/export_feedback_eval.py
    python scripts/export_feedback_eval.py --db data/case_log.sqlite3 --output reports/feedback_eval.csv
    python scripts/export_feedback_eval.py --format jsonl --output reports/feedback_eval.jsonl

Does not upload anything. Image refs are paths only (no binary embedding).
Do not share the export without consent review.

Re-smoke exported questions (private):
    python scripts/evaluate_rag.py --feedback-csv reports/feedback_eval.csv --feedback-limit 10
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import CASE_LOG_DB_PATH
from core.case_log import list_feedback_events


DEFAULT_OUTPUT = os.path.join("reports", "feedback_eval.csv")
PRIVACY_NOTE = """# Feedback evaluation exports — privacy

These files are for **private evaluation only**.

- Do **not** publish, commit, or train public models on this export without
  explicit consent review.
- Rows may contain free-text questions and answers from real sessions.
- Image columns are **path references only** (no binary content).
- Prefer deleting exports after the evaluation run.

Related tools:

- `scripts/export_feedback_eval.py` — create CSV/JSONL
- `scripts/evaluate_rag.py --feedback-csv ...` — re-ask questions as smoke tests
"""


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export feedback rows for evaluation.")
    parser.add_argument("--db", default=CASE_LOG_DB_PATH, help="Path to case_log SQLite DB.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="CSV/JSONL output path.")
    parser.add_argument(
        "--format",
        choices=("csv", "jsonl"),
        default="csv",
        help="Export format (default: csv).",
    )
    parser.add_argument(
        "--no-privacy-note",
        action="store_true",
        help="Skip writing FEEDBACK_EVAL_PRIVACY.md next to the export.",
    )
    return parser.parse_args(argv)


def _row_dict(row: dict) -> dict:
    before = row.get("before_image_ref") or ""
    after = row.get("after_image_ref") or ""
    return {
        "id": row.get("id"),
        "created_at": row.get("created_at"),
        "rating": row.get("rating"),
        "question": row.get("question"),
        "answer": row.get("answer"),
        "outcome": row.get("outcome"),
        "outcome_at": row.get("outcome_at"),
        "before_image_ref": before,
        "after_image_ref": after,
        "before_image_exists": bool(before and Path(before).is_file()),
        "after_image_exists": bool(after and Path(after).is_file()),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    rows = list_feedback_events(args.db)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "id",
        "created_at",
        "rating",
        "question",
        "answer",
        "outcome",
        "outcome_at",
        "before_image_ref",
        "after_image_ref",
        "before_image_exists",
        "after_image_exists",
    ]
    records = [_row_dict(row) for row in rows]

    if args.format == "jsonl":
        with out.open("w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
    else:
        with out.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for record in records:
                writer.writerow(record)

    if not args.no_privacy_note:
        note_path = out.parent / "FEEDBACK_EVAL_PRIVACY.md"
        note_path.write_text(PRIVACY_NOTE, encoding="utf-8")
        print(f"Wrote privacy note: {note_path}")

    print(f"Wrote {len(records)} rows to {out} ({args.format})")
    print("Privacy: treat this file as evaluation-only; do not publish without consent.")
    print(
        "Re-smoke: python scripts/evaluate_rag.py "
        f"--feedback-csv {out} --feedback-limit 10"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
