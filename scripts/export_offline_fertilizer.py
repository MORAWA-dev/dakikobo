"""Generate the PWA fertilizer table from the authoritative Python data."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.fertilizer import build_offline_fertilizer_payload


OUTPUT = ROOT / "static" / "data" / "fertilizer.json"


def serialized_payload() -> str:
    return json.dumps(
        build_offline_fertilizer_payload(),
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Échoue si le fichier hors ligne n'est plus synchronisé.",
    )
    args = parser.parse_args()
    expected = serialized_payload()
    if args.check:
        return 0 if OUTPUT.read_text(encoding="utf-8") == expected else 1
    OUTPUT.write_text(expected, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
