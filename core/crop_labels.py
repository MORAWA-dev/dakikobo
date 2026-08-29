"""Load experimental crop label glossary (French primary).

Local-language fields are optional and ignored until non-empty + reviewed.

The glossary only covers the crops a reviewer has curated. Crop *identity* lives
in the ``core.crops`` registry (A1), so any registry crop without a glossary entry
still gets a proper French label instead of a bare id (P7).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from core.crops import CROPS

DEFAULT_GLOSSARY_PATH = (
    Path(__file__).resolve().parents[1] / "Data" / "glossaries" / "crop_labels.json"
)


@lru_cache(maxsize=4)
def load_crop_labels(path: str | None = None) -> dict:
    glossary_path = Path(path) if path else DEFAULT_GLOSSARY_PATH
    with glossary_path.open(encoding="utf-8") as f:
        return json.load(f)


def french_label(crop_id: str, *, simple: bool = False) -> str:
    """Return French display label for a crop id.

    Curated glossary text wins. Otherwise fall back to the registry label, and
    finally to the id itself for values that are not crops at all.
    """
    key = (crop_id or "").lower()
    data = load_crop_labels()
    for crop in data.get("crops") or []:
        if (crop.get("id") or "").lower() == key:
            if simple and crop.get("fr_simple"):
                return str(crop["fr_simple"])
            return str(crop.get("fr") or crop_id)

    registry_crop = CROPS.get(key)
    if registry_crop:
        return registry_crop.label_simple if simple else registry_crop.label_fr
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
