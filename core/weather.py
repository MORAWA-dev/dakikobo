"""Weather-aware agricultural context for Burkina Faso locations."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, timedelta

import requests


OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT_SECONDS = 10


class WeatherError(RuntimeError):
    """Raised when the weather context cannot be fetched or parsed."""


@dataclass(frozen=True)
class WeatherLocation:
    id: str
    name: str
    latitude: float
    longitude: float


LOCATIONS = {
    "ouagadougou": WeatherLocation("ouagadougou", "Ouagadougou", 12.3714, -1.5197),
    "bobo": WeatherLocation("bobo", "Bobo-Dioulasso", 11.1771, -4.2979),
    "kaya": WeatherLocation("kaya", "Kaya", 13.0917, -1.0844),
    "ouahigouya": WeatherLocation("ouahigouya", "Ouahigouya", 13.5828, -2.4216),
    "fada": WeatherLocation("fada", "Fada N'Gourma", 12.0616, 0.3584),
    "dori": WeatherLocation("dori", "Dori", 14.0354, -0.0345),
}

SOURCE_OPEN_METEO = {
    "title": "Open-Meteo Forecast API",
    "type": "Météo",
    "snippet": "Prévision gratuite: pluie, température, évapotranspiration ET0 et humidité du sol.",
}

_CACHE: dict[tuple[str, str], dict] = {}


def list_weather_locations() -> list[dict]:
    return [
        {
            "id": loc.id,
            "name": loc.name,
            "latitude": loc.latitude,
            "longitude": loc.longitude,
        }
        for loc in LOCATIONS.values()
    ]


def clear_weather_cache() -> None:
    _CACHE.clear()


def _round_or_none(value, digits: int = 1):
    if value is None:
        return None
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def _sum_numbers(values) -> float:
    total = 0.0
    for value in values:
        if value is None:
            continue
        try:
            total += float(value)
        except (TypeError, ValueError):
            continue
    return total


def _mean_recent(values, count: int = 24):
    numeric = []
    for value in values[-count:]:
        rounded = _round_or_none(value, 3)
        if rounded is not None:
            numeric.append(rounded)
    if not numeric:
        return None
    return round(sum(numeric) / len(numeric), 3)


def _numeric_values(values) -> list[float]:
    output = []
    for value in values:
        rounded = _round_or_none(value)
        if rounded is not None:
            output.append(rounded)
    return output


def _parse_date(value: str):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _daily_window(daily: dict, start: date, end: date) -> dict[str, list]:
    output = {
        "time": [],
        "precipitation_sum": [],
        "et0_fao_evapotranspiration": [],
        "temperature_2m_max": [],
    }
    times = daily.get("time", [])
    for idx, raw_date in enumerate(times):
        parsed = _parse_date(raw_date)
        if parsed is None or parsed < start or parsed >= end:
            continue
        output["time"].append(raw_date)
        for key in ("precipitation_sum", "et0_fao_evapotranspiration", "temperature_2m_max"):
            values = daily.get(key, [])
            output[key].append(values[idx] if idx < len(values) else None)
    return output


def _status(label: str, state: str, text: str) -> dict:
    return {"label": label, "status": state, "text": text}


def _rain_insight(rain_7d: float) -> dict:
    if rain_7d >= 20:
        return _status(
            "Pluie utile (7 jours)",
            "good",
            f"{rain_7d:.1f} mm récents : humidité favorable si le champ infiltre bien.",
        )
    if rain_7d >= 8:
        return _status(
            "Pluie utile (7 jours)",
            "watch",
            f"{rain_7d:.1f} mm récents : surveillez l'humidité avant de semer.",
        )
    return _status(
        "Pluie utile (7 jours)",
        "risk",
        f"{rain_7d:.1f} mm récents : le sol peut rester trop sec pour une levée régulière.",
    )


def _stress_insight(rain_7d: float, et0_7d: float, temp_now) -> dict:
    balance = rain_7d - et0_7d
    hot = temp_now is not None and temp_now >= 38
    if balance <= -25 or (rain_7d < 5 and hot):
        return _status(
            "Risque de stress hydrique",
            "risk",
            "Risque élevé : peu de pluie récente face à une forte demande en eau.",
        )
    if balance <= -10 or rain_7d < 15:
        return _status(
            "Risque de stress hydrique",
            "watch",
            "Risque moyen : gardez l'humidité avec paillage, sarclage précoce ou zai.",
        )
    return _status(
        "Risque de stress hydrique",
        "good",
        "Risque limité à court terme, mais vérifiez toujours l'humidité réelle du sol.",
    )


def _sowing_insight(rain_7d: float, rain_next_3d: float) -> dict:
    if rain_7d >= 20 and rain_next_3d >= 5:
        return _status(
            "Fenêtre de semis probable",
            "good",
            "Fenêtre favorable si le sol est humide en profondeur et la parcelle prête.",
        )
    if rain_7d >= 10 or rain_next_3d >= 10:
        return _status(
            "Fenêtre de semis probable",
            "watch",
            "Possible, mais attendez une pluie confirmée si le sol sèche vite.",
        )
    return _status(
        "Fenêtre de semis probable",
        "risk",
        "Attendez une pluie plus régulière avant de semer les céréales pluviales.",
    )


def _urea_insight(rain_next_3d: float, max_next_rain: float) -> dict:
    if rain_next_3d >= 25 or max_next_rain >= 15:
        return _status(
            "Urée avant forte pluie",
            "risk",
            "Évitez l'urée juste avant une forte pluie : risque de pertes par ruissellement.",
        )
    if rain_next_3d >= 8:
        return _status(
            "Urée avant forte pluie",
            "watch",
            "Apport possible avec prudence : enfouissez légèrement et évitez les sols inondables.",
        )
    return _status(
        "Urée avant forte pluie",
        "good",
        "Pas de forte pluie signalée à court terme, mais appliquez sur sol humide.",
    )


def _soil_moisture_signal(value) -> str:
    if value is None:
        return "Non disponible"
    if value < 0.12:
        return "Faible"
    if value < 0.22:
        return "Moyenne"
    return "Bonne"


def _fetch_open_meteo(location: WeatherLocation) -> dict:
    response = requests.get(
        OPEN_METEO_FORECAST_URL,
        params={
            "latitude": location.latitude,
            "longitude": location.longitude,
            "current": "temperature_2m,relative_humidity_2m,precipitation",
            "hourly": "soil_moisture_3_to_9cm",
            "daily": "precipitation_sum,et0_fao_evapotranspiration,temperature_2m_max",
            "past_days": 7,
            "forecast_days": 3,
            "timezone": "Africa/Abidjan",
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise WeatherError(payload.get("reason", "Erreur météo inconnue."))
    return payload


def build_weather_context(location_id: str, payload: dict | None = None) -> dict:
    location = LOCATIONS.get((location_id or "").strip().lower())
    if location is None:
        raise ValueError("Localité météo non prise en charge.")

    today = date.today()
    cache_key = (location.id, today.isoformat())
    if payload is None and cache_key in _CACHE:
        cached = deepcopy(_CACHE[cache_key])
        cached["cached"] = True
        return cached

    try:
        raw = payload if payload is not None else _fetch_open_meteo(location)
    except requests.RequestException as exc:
        raise WeatherError("La météo n'est pas disponible pour le moment.") from exc

    daily = raw.get("daily", {})
    hourly = raw.get("hourly", {})
    current = raw.get("current", {})

    recent = _daily_window(daily, today - timedelta(days=7), today)
    forecast = _daily_window(daily, today, today + timedelta(days=3))

    rain_7d = round(_sum_numbers(recent["precipitation_sum"]), 1)
    et0_7d = round(_sum_numbers(recent["et0_fao_evapotranspiration"]), 1)
    rain_next_3d = round(_sum_numbers(forecast["precipitation_sum"]), 1)
    max_next_rain = max([0.0] + _numeric_values(forecast["precipitation_sum"]))
    temp_now = _round_or_none(current.get("temperature_2m"))
    humidity_now = _round_or_none(current.get("relative_humidity_2m"), 0)
    soil_moisture = _mean_recent(hourly.get("soil_moisture_3_to_9cm", []))

    insights = [
        _rain_insight(rain_7d),
        _stress_insight(rain_7d, et0_7d, temp_now),
        _sowing_insight(rain_7d, rain_next_3d),
        _urea_insight(rain_next_3d, max_next_rain),
    ]

    result = {
        "location": {
            "id": location.id,
            "name": location.name,
            "latitude": location.latitude,
            "longitude": location.longitude,
        },
        "updated_at": current.get("time") or today.isoformat(),
        "cached": False,
        "metrics": {
            "rain_7d_mm": rain_7d,
            "rain_next_3d_mm": rain_next_3d,
            "et0_7d_mm": et0_7d,
            "temperature_c": temp_now,
            "humidity_percent": humidity_now,
            "soil_moisture_m3_m3": soil_moisture,
            "soil_moisture_signal": _soil_moisture_signal(soil_moisture),
        },
        "insights": insights,
        "disclaimer": (
            "Ces signaux météo sont indicatifs. Vérifiez toujours l'humidité réelle "
            "du sol dans la parcelle avant de semer ou d'apporter l'engrais."
        ),
        "sources": [dict(SOURCE_OPEN_METEO)],
    }

    if payload is None:
        _CACHE[cache_key] = deepcopy(result)
    return result
