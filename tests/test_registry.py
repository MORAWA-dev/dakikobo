"""Tests for the canonical registry modules (Phase 1).

Covers ``core/places.py``, ``core/crops.py``, and the ``GET /registry`` route
that bridges them to the frontend. No live services are touched.
"""

from core.places import PLACES, list_places, resolve_place
from core.crops import CROPS, list_crops, resolve_crop
from core.fertilizer import _RECOMMENDATIONS
from core.query_context import is_short_followup
from core.soil import LOCATIONS as SOIL_LOCATIONS, list_soil_crops
from core.weather import LOCATIONS as WEATHER_LOCATIONS

import app as app_module


# ---------------------------------------------------------------------------
# core.places
# ---------------------------------------------------------------------------


def test_places_registry_counts_and_slug_format():
    """Registry exposes a stable set of places with ascii-slug ids."""
    places = list_places()
    assert len(places) == 20
    for p in places:
        assert isinstance(p["id"], str) and p["id"]
        assert isinstance(p["label_fr"], str) and p["label_fr"]
        assert isinstance(p["aliases"], list)
        assert isinstance(p["has_weather"], bool)


def test_places_weather_backed_have_coordinates():
    """Only has_weather places carry coordinates; the rest are None."""
    for p in list_places():
        if p["has_weather"]:
            assert isinstance(p["latitude"], float)
            assert isinstance(p["longitude"], float)
        else:
            assert p["latitude"] is None
            assert p["longitude"] is None


def test_places_weather_backed_count_is_six():
    weather_places = [p for p in list_places() if p["has_weather"]]
    ids = {p["id"] for p in weather_places}
    assert ids == {"ouagadougou", "bobo", "kaya", "ouahigouya", "fada", "dori"}


def test_places_resolve_by_alias_and_label():
    """resolve_place recognises ids, aliases, and display labels."""
    assert resolve_place("Bobo-Dioulasso").id == "bobo"
    assert resolve_place("bobo").id == "bobo"
    assert resolve_place("Mogtedo").id == "mogtedo"
    assert resolve_place("Mogtédo").id == "mogtedo"
    assert resolve_place("Ouaga").id == "ouagadougou"


def test_places_resolve_unknown_returns_none():
    assert resolve_place("Timbuktu") is None
    assert resolve_place("") is None


def test_places_aliases_resolve_to_same_entry():
    """Every alias maps back to a place that lists it."""
    for place in PLACES.values():
        for alias in place.aliases:
            assert resolve_place(alias).id == place.id


def test_place_aliases_are_disjoint_after_normalization():
    owners = {}
    for place in PLACES.values():
        for alias in place.aliases:
            normalized = alias.casefold()
            assert normalized not in owners or owners[normalized] == place.id
            owners[normalized] = place.id


# ---------------------------------------------------------------------------
# core.crops
# ---------------------------------------------------------------------------


def test_crops_registry_counts_and_slug_format():
    """Registry exposes a stable set of crops with ascii-slug ids."""
    crops = list_crops()
    assert len(crops) == 10
    for c in crops:
        assert isinstance(c["id"], str) and c["id"]
        assert isinstance(c["label_fr"], str) and c["label_fr"]
        assert isinstance(c["label_simple"], str) and c["label_simple"]
        assert isinstance(c["aliases"], list)
        assert isinstance(c["family"], str)
        assert isinstance(c["fertilizer_supported"], bool)


def test_crops_ids_are_ascii_slugs():
    """Accented labels must not leak into ids (mais, niebe, sesame, ...)."""
    ids = {c["id"] for c in list_crops()}
    for cid in ids:
        assert cid.isascii(), cid
    missing = {"sorgho", "mil", "mais", "niebe", "arachide", "soja", "coton", "riz", "sesame", "fonio"}
    assert ids == missing


def test_crops_fertilizer_supported_matches_primary_set():
    """Only the 5 primary crops are fertiliser-supported."""
    supported = {c["id"] for c in list_crops() if c["fertilizer_supported"]}
    assert supported == {"sorgho", "mil", "mais", "niebe", "arachide"}


def test_crops_resolve_by_alias_and_accented_label():
    """resolve_crop recognises ids, aliases, and accented labels."""
    assert resolve_crop("maïs").id == "mais"
    assert resolve_crop("maize").id == "mais"
    assert resolve_crop("cowpea").id == "niebe"
    assert resolve_crop("niébé").id == "niebe"
    assert resolve_crop("sésame").id == "sesame"


def test_crops_resolve_unknown_returns_none():
    assert resolve_crop("mangue") is None
    assert resolve_crop("") is None


def test_crops_aliases_resolve_to_same_entry():
    """Every alias maps back to a crop that lists it."""
    for crop in CROPS.values():
        for alias in crop.aliases:
            assert resolve_crop(alias).id == crop.id


def test_crop_aliases_are_disjoint_after_normalization():
    owners = {}
    for crop in CROPS.values():
        for alias in crop.aliases:
            normalized = alias.casefold()
            assert normalized not in owners or owners[normalized] == crop.id
            owners[normalized] = crop.id


def test_registry_support_flags_match_all_consumers():
    fertilizer_ids = set(_RECOMMENDATIONS)
    registry_fertilizer_ids = {
        crop.id for crop in CROPS.values() if crop.fertilizer_supported
    }
    soil_crop_ids = {crop["id"] for crop in list_soil_crops()}
    weather_place_ids = set(WEATHER_LOCATIONS)
    soil_place_ids = set(SOIL_LOCATIONS)

    assert registry_fertilizer_ids == fertilizer_ids == soil_crop_ids
    assert weather_place_ids == soil_place_ids
    assert weather_place_ids == {
        place.id for place in PLACES.values() if place.has_weather
    }


def test_koudougou_remains_a_short_followup():
    assert is_short_followup("koudougou?") is True


# ---------------------------------------------------------------------------
# GET /registry route
# ---------------------------------------------------------------------------


def test_registry_route_returns_crops_and_places():
    client = app_module.app.test_client()
    resp = client.get("/registry")
    assert resp.status_code == 200
    data = resp.get_json()
    assert set(data.keys()) == {"crops", "places"}
    assert len(data["crops"]) == 10
    assert len(data["places"]) == 20
    assert resp.headers["Cache-Control"] == "public, max-age=3600"


def test_registry_route_matches_public_lists():
    """The route payloads are exactly what list_crops/list_places produce."""
    client = app_module.app.test_client()
    data = client.get("/registry").get_json()
    assert data["crops"] == list_crops()
    assert data["places"] == list_places()


def test_registry_route_has_weather_flag_per_place():
    client = app_module.app.test_client()
    places = {p["id"]: p for p in client.get("/registry").get_json()["places"]}
    assert places["ouagadougou"]["has_weather"] is True
    assert places["koudougou"]["has_weather"] is False
    assert places["fada"]["label_fr"] == "Fada N'Gourma"
