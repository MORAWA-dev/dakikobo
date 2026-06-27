"""Soil-aware fertilizer context using SoilGrids indicators."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import date

import requests


SOILGRIDS_QUERY_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
REQUEST_TIMEOUT_SECONDS = 12


class SoilError(RuntimeError):
    """Raised when soil indicators cannot be fetched or parsed."""


@dataclass(frozen=True)
class SoilLocation:
    id: str
    name: str
    latitude: float
    longitude: float


LOCATIONS = {
    "ouagadougou": SoilLocation("ouagadougou", "Ouagadougou", 12.3714, -1.5197),
    "bobo": SoilLocation("bobo", "Bobo-Dioulasso", 11.1771, -4.2979),
    "kaya": SoilLocation("kaya", "Kaya", 13.0917, -1.0844),
    "ouahigouya": SoilLocation("ouahigouya", "Ouahigouya", 13.5828, -2.4216),
    "fada": SoilLocation("fada", "Fada N'Gourma", 12.0616, 0.3584),
    "dori": SoilLocation("dori", "Dori", 14.0354, -0.0345),
}

SUPPORTED_CROPS = {
    "sorgho": "sorgho",
    "mil": "mil",
    "maïs": "maïs",
    "mais": "maïs",
    "niébé": "niébé",
    "niebe": "niébé",
    "arachide": "arachide",
}

SOURCE_SOILGRIDS = {
    "title": "SoilGrids REST API",
    "type": "Sol",
    "snippet": "Indicateurs pédologiques mondiaux: argile, sable, carbone organique, pH et CEC.",
}

_CACHE: dict[tuple[str, str], dict] = {}


def list_soil_locations() -> list[dict]:
    return [
        {
            "id": loc.id,
            "name": loc.name,
            "latitude": loc.latitude,
            "longitude": loc.longitude,
        }
        for loc in LOCATIONS.values()
    ]


def list_soil_crops() -> list[dict]:
    return [
        {"id": "sorgho", "name": "Sorgho"},
        {"id": "mil", "name": "Mil"},
        {"id": "maïs", "name": "Maïs"},
        {"id": "niébé", "name": "Niébé"},
        {"id": "arachide", "name": "Arachide"},
    ]


def clear_soil_cache() -> None:
    _CACHE.clear()


def normalize_crop(value: str) -> str | None:
    return SUPPORTED_CROPS.get((value or "").strip().lower())


def _round_or_none(value, digits: int = 1):
    if value is None:
        return None
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def _layer_value(payload: dict, property_name: str, value_key: str = "mean"):
    layers = payload.get("properties", {}).get("layers", [])
    for layer in layers:
        if layer.get("name") != property_name:
            continue
        depths = layer.get("depths", [])
        if not depths:
            return None
        values = depths[0].get("values", {})
        return values.get(value_key)
    return None


def _scaled_layer_value(payload: dict, property_name: str, divisor: float, digits: int = 1):
    value = _layer_value(payload, property_name)
    if value is None:
        return None
    try:
        return round(float(value) / divisor, digits)
    except (TypeError, ValueError):
        return None


def _status(label: str, state: str, value: str, text: str) -> dict:
    return {"label": label, "status": state, "value": value, "text": text}


def _texture_indicator(clay_percent, sand_percent) -> dict:
    if sand_percent is None or clay_percent is None:
        return _status("Texture", "watch", "Non disponible", "Donnée texture non disponible.")
    if sand_percent >= 65:
        return _status(
            "Texture",
            "risk",
            "Tendance sableuse",
            "Le sol risque de retenir peu d'eau et peu d'éléments nutritifs.",
        )
    if clay_percent >= 35:
        return _status(
            "Texture",
            "watch",
            "Tendance argileuse",
            "Le sol peut retenir l'eau, mais attention à la battance et au drainage.",
        )
    return _status(
        "Texture",
        "good",
        "Tendance équilibrée",
        "La texture paraît plus favorable, à confirmer au champ.",
    )


def _organic_carbon_indicator(soc_percent) -> dict:
    if soc_percent is None:
        return _status("Carbone organique", "watch", "Non disponible", "Donnée carbone non disponible.")
    if soc_percent < 0.6:
        return _status(
            "Carbone organique",
            "risk",
            "Faible",
            "Priorisez fumier, compost, résidus et rotations pour reconstruire la matière organique.",
        )
    if soc_percent < 1.2:
        return _status(
            "Carbone organique",
            "watch",
            "Moyen",
            "Maintenez les apports organiques; ils aident l'eau et les engrais à mieux servir la culture.",
        )
    return _status(
        "Carbone organique",
        "good",
        "Correct",
        "Bon signal pour la rétention d'eau et de nutriments, à confirmer par analyse locale.",
    )


def _ph_indicator(ph_h2o) -> dict:
    if ph_h2o is None:
        return _status("pH", "watch", "Non disponible", "Donnée pH non disponible.")
    if ph_h2o < 5.5:
        return _status(
            "pH",
            "risk",
            "Acide",
            "Un sol acide peut limiter la disponibilité des nutriments; demandez conseil avant chaulage.",
        )
    if ph_h2o <= 7.5:
        return _status(
            "pH",
            "good",
            "Proche neutre",
            "Le pH semble favorable pour les cultures principales.",
        )
    return _status(
        "pH",
        "watch",
        "Alcalin",
        "Un pH élevé peut bloquer certains nutriments; privilégiez le diagnostic local.",
    )


def _retention_indicator(sand_percent, soc_percent, cec_cmol_kg) -> dict:
    if sand_percent is None and soc_percent is None and cec_cmol_kg is None:
        return _status(
            "Rétention des nutriments",
            "watch",
            "Non disponible",
            "Impossible d'estimer la rétention sans sable, carbone organique ou CEC.",
        )

    risk_points = 0
    if sand_percent is not None and sand_percent >= 65:
        risk_points += 1
    if soc_percent is not None and soc_percent < 0.8:
        risk_points += 1
    if cec_cmol_kg is not None and cec_cmol_kg < 8:
        risk_points += 1

    if risk_points >= 2:
        return _status(
            "Rétention des nutriments",
            "risk",
            "Risque élevé",
            "Fractionnez l'urée, enfouissez légèrement et associez fumure organique.",
        )
    if risk_points == 1:
        return _status(
            "Rétention des nutriments",
            "watch",
            "Risque moyen",
            "Évitez les gros apports d'engrais en une seule fois, surtout avant une forte pluie.",
        )
    return _status(
        "Rétention des nutriments",
        "good",
        "Risque limité",
        "Les indicateurs ne montrent pas de risque fort, mais une analyse de sol reste nécessaire.",
    )


def _fetch_soilgrids(location: SoilLocation) -> dict:
    response = requests.get(
        SOILGRIDS_QUERY_URL,
        params=[
            ("lon", location.longitude),
            ("lat", location.latitude),
            ("property", "clay"),
            ("property", "sand"),
            ("property", "soc"),
            ("property", "phh2o"),
            ("property", "cec"),
            ("depth", "0-5cm"),
            ("value", "mean"),
        ],
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def _metrics_available(metrics: dict) -> bool:
    return any(value is not None for value in metrics.values())


def build_soil_context(location_id: str, crop: str, payload: dict | None = None) -> dict:
    location = LOCATIONS.get((location_id or "").strip().lower())
    if location is None:
        raise ValueError("Localité sol non prise en charge.")

    crop_key = normalize_crop(crop)
    if crop_key is None:
        raise ValueError("Culture non prise en charge.")

    cache_key = (location.id, date.today().isoformat())
    if payload is None and cache_key in _CACHE:
        cached = deepcopy(_CACHE[cache_key])
        cached["cached"] = True
        cached["crop"] = crop_key
        return cached

    try:
        raw = payload if payload is not None else _fetch_soilgrids(location)
    except requests.RequestException as exc:
        raise SoilError("Les indicateurs de sol ne sont pas disponibles.") from exc

    clay_percent = _scaled_layer_value(raw, "clay", 10)
    sand_percent = _scaled_layer_value(raw, "sand", 10)
    soc_percent = _scaled_layer_value(raw, "soc", 100, 2)
    ph_h2o = _scaled_layer_value(raw, "phh2o", 10)
    cec_cmol_kg = _scaled_layer_value(raw, "cec", 10)
    metrics = {
        "clay_percent": clay_percent,
        "sand_percent": sand_percent,
        "soc_percent": soc_percent,
        "ph_h2o": ph_h2o,
        "cec_cmol_kg": cec_cmol_kg,
    }
    data_available = _metrics_available(metrics)

    indicators = [
        _texture_indicator(clay_percent, sand_percent),
        _organic_carbon_indicator(soc_percent),
        _ph_indicator(ph_h2o),
        _retention_indicator(sand_percent, soc_percent, cec_cmol_kg),
    ]

    context = {
        "location": {
            "id": location.id,
            "name": location.name,
            "latitude": location.latitude,
            "longitude": location.longitude,
        },
        "crop": crop_key,
        "cached": False,
        "depth": "0-5 cm",
        "metrics": metrics,
        "data_available": data_available,
        "indicators": indicators,
        "actions": [
            "Utilisez ces signaux pour adapter la prudence, pas pour changer seul les doses exactes.",
            "Associez fumure organique et rotation lorsque le carbone ou la rétention sont faibles.",
            "Confirmez toujours par une analyse de sol locale ou avec un agent agricole.",
        ],
        "disclaimer": (
            "SoilGrids donne une estimation large, pas une analyse de votre champ. "
            "Les doses exactes doivent être confirmées par test de sol ou agent agricole."
        ),
        "sources": [dict(SOURCE_SOILGRIDS)],
    }

    if payload is None:
        _CACHE[cache_key] = deepcopy(context)
    return context
