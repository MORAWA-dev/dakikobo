"""Single source of truth for Burkina Faso places (A1).

Replaces the duplicated place vocabularies that lived in ``core/query_context``,
``core/weather``, ``core/soil`` and the frontend bridge. Only the six
weather/soil-backed cities carry coordinates; every other recognised place uses
``has_weather=False`` so a query mentioning it still resolves for retrieval and
for the ``ResolvedQueryContext`` without pretending to have live weather data.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class Place:
    id: str                 # slug, e.g. "koudougou"
    label_fr: str           # display, e.g. "Koudougou"
    aliases: tuple[str, ...]
    latitude: float | None  # None when not weather-backed
    longitude: float | None
    has_weather: bool       # True only for the 6 weather/soil rows


PLACES: dict[str, Place] = {
    p.id: p
    for p in [
        # ---- The 6 weather/soil-backed cities (coordinates from core/weather). ----
        Place("ouagadougou", "Ouagadougou", ("ouagadougou", "ouaga"), 12.3714, -1.5197, True),
        Place("bobo", "Bobo-Dioulasso", ("bobo", "bobo-dioulasso", "bobodioulasso"), 11.1771, -4.2979, True),
        Place("kaya", "Kaya", ("kaya",), 13.0917, -1.0844, True),
        Place("ouahigouya", "Ouahigouya", ("ouahigouya",), 13.5828, -2.4216, True),
        Place("fada", "Fada N'Gourma", ("fada", "fada n'gourma", "fada ngourma"), 12.0616, 0.3584, True),
        Place("dori", "Dori", ("dori",), 14.0354, -0.0345, True),
        # ---- Non-weather-backed regional towns (no coordinates; has_weather=False). ----
        Place("koudougou", "Koudougou", ("koudougou",), None, None, False),
        Place("banfora", "Banfora", ("banfora",), None, None, False),
        Place("tenkodogo", "Tenkodogo", ("tenkodogo",), None, None, False),
        Place("dedougou", "Dédougou", ("dedougou", "dédougou"), None, None, False),
        Place("mogtedo", "Mogtédo", ("mogtedo", "mogtédo"), None, None, False),
        Place("pouytenga", "Pouytenga", ("pouytenga",), None, None, False),
        Place("kouepela", "Koupéla", ("koupela", "koupéla"), None, None, False),
        Place("ziniare", "Ziniaré", ("ziniare", "ziniaré"), None, None, False),
        Place("manga", "Manga", ("manga",), None, None, False),
        Place("gaoua", "Gaoua", ("gaoua",), None, None, False),
        Place("kongoussi", "Kongoussi", ("kongoussi",), None, None, False),
        # ---- Additional recognised towns kept non-weather (has_weather=False). ----
        Place("reo", "Réo", ("reo", "réo"), None, None, False),
        Place("boromo", "Boromo", ("boromo",), None, None, False),
        Place("yako", "Yako", ("yako",), None, None, False),
    ]
}

_ALIAS_TO_ID: dict[str, str] = {}
for _place in PLACES.values():
    for _alias in _place.aliases:
        _ALIAS_TO_ID[_alias] = _place.id


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower().strip()


def resolve_place(text: str) -> Place | None:
    """Return the Place named in free text, or None.

    Recognises all 20 places (same coverage as the old ``_LOCATION_ALIASES``).
    """
    t = _normalize(text)
    if not t:
        return None
    for alias in sorted(_ALIAS_TO_ID, key=len, reverse=True):
        if re.search(rf"(?<!\w){re.escape(_normalize(alias))}(?!\w)", t):
            return PLACES[_ALIAS_TO_ID[alias]]
    return None


def list_places() -> list[dict]:
    """Registry payload for ``/registry`` and the frontend bridge."""
    return [
        {
            "id": place.id,
            "label_fr": place.label_fr,
            "aliases": list(place.aliases),
            "latitude": place.latitude,
            "longitude": place.longitude,
            "has_weather": place.has_weather,
        }
        for place in PLACES.values()
    ]
