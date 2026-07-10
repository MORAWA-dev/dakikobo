"""Export feedback/case-log rows for private evaluation datasets.

Usage:
    python scripts/export_feedback_eval.py
    python scripts/export_feedback_eval.py --db data/case_log.sqlite3 --output reports/feedback_eval.csv

Does not upload anything. Image refs are paths only (no binary embedding).
Do not share the export without consent review.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import CASE_LOG_DB_PATH
from core.case_log import list_feedback_events


DEFAULT_OUTPUT = os.path.join("reports", "feedback_eval.csv")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export feedback rows for evaluation.")
    parser.add_argument("--db", default=CASE_LOG_DB_PATH, help="Path to case_log SQLite DB.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="CSV output path.")
    return parser.parse_args(argv)


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
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            before = row.get("before_image_ref") or ""
            after = row.get("after_image_ref") or ""
            writer.writerow(
                {
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
            )

    print(f"Wrote {len(rows)} rows to {out}")
    print("Privacy: treat this file as evaluation-only; do not publish without consent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
