"""Load experimental crop label glossary (French primary).

Local-language fields are optional and ignored until non-empty + reviewed.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DEFAULT_GLOSSARY_PATH = (
    Path(__file__).resolve().parents[1] / "Data" / "glossaries" / "crop_labels.json"
)


@lru_cache(maxsize=4)
def load_crop_labels(path: str | None = None) -> dict:
    glossary_path = Path(path) if path else DEFAULT_GLOSSARY_PATH
    with glossary_path.open(encoding="utf-8") as f:
        return json.load(f)


def french_label(crop_id: str, *, simple: bool = False) -> str:
    """Return French display label for a crop id, or the id itself."""
    data = load_crop_labels()
    for crop in data.get("crops") or []:
        if (crop.get("id") or "").lower() == (crop_id or "").lower():
            if simple and crop.get("fr_simple"):
                return str(crop["fr_simple"])
            return str(crop.get("fr") or crop_id)
    return crop_id or ""


def local_labels_ready(crop_id: str) -> bool:
    """True when at least one local-language name is filled (not production-ready alone)."""
    data = load_crop_labels()
    for crop in data.get("crops") or []:
        if (crop.get("id") or "").lower() != (crop_id or "").lower():
            continue
        for key in ("moore", "dioula", "fulfulde"):
            if (crop.get(key) or "").strip():
                return True
    return False
