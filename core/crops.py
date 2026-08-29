"""Single source of truth for Burkina Faso crops (A1).

Replaces the duplicated crop vocabularies that lived in ``core/query_context``,
``core/fertilizer``, ``core/soil``, the glossary and the frontend selects. The
id is an ascii slug (``mais``, ``niebe``) so it is stable for cache keys and
programmatic lookups; ``label_fr`` carries the accented canonical French name
used in prompts and farmer-facing cards; ``label_simple`` is the glossary/simple
spelling used for simpler UI text.

``fertilizer_supported`` is independent of ``family`` and is True only for the
five crops that have a grounded (non-LLM) dose table in ``core/fertilizer``.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class Crop:
    id: str                 # ascii slug, e.g. "mais"
    label_fr: str           # canonical FR with diacritics, e.g. "maïs"
    label_simple: str       # glossary/simple spelling, e.g. "mais"
    aliases: tuple[str, ...]
    family: str             # cereale | legumineuse | oleagineux | fibre | racine | autre
    fertilizer_supported: bool  # True only for sorgho/mil/mais/niebe/arachide


CROPS: dict[str, Crop] = {
    crop.id: crop
    for crop in [
        Crop("sorgho", "sorgho", "sorgho", ("sorgho", "sorghum"), "cereale", True),
        Crop("mil", "mil", "mil (céréale)", ("mil", "millet", "petit mil"), "cereale", True),
        Crop("mais", "maïs", "maïs", ("maïs", "mais", "maize"), "cereale", True),
        Crop("niebe", "niébé", "niébé (haricot)", ("niébé", "niebe", "cowpea", "haricot"), "legumineuse", True),
        Crop("arachide", "arachide", "arachide (cacahuète)", ("arachide", "arachides", "groundnut", "cacahuète", "cacahuete"), "oleagineux", True),
        Crop("soja", "soja", "soja", ("soja", "soya", "soybean"), "oleagineux", False),
        Crop("coton", "coton", "coton", ("coton",), "fibre", False),
        Crop("riz", "riz", "riz", ("riz",), "cereale", False),
        Crop("sesame", "sésame", "sésame", ("sésame", "sesame"), "oleagineux", False),
        Crop("fonio", "fonio", "fonio", ("fonio",), "cereale", False),
    ]
}

_ALIAS_TO_ID: dict[str, str] = {}
for _crop in CROPS.values():
    for _alias in _crop.aliases:
        _ALIAS_TO_ID[_alias] = _crop.id


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower().strip()


def resolve_crop(text: str) -> Crop | None:
    """Return the Crop named in free text, or None."""
    t = _normalize(text)
    if not t:
        return None
    for alias in sorted(_ALIAS_TO_ID, key=len, reverse=True):
        if re.search(rf"(?<!\w){re.escape(_normalize(alias))}(?!\w)", t):
            return CROPS[_ALIAS_TO_ID[alias]]
    return None


def list_crops() -> list[dict]:
    """Registry payload for ``/registry`` and the frontend bridge."""
    return [
        {
            "id": crop.id,
            "label_fr": crop.label_fr,
            "label_simple": crop.label_simple,
            "aliases": list(crop.aliases),
            "family": crop.family,
            "fertilizer_supported": crop.fertilizer_supported,
        }
        for crop in CROPS.values()
    ]
