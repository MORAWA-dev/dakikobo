"""Tests for weather-aware agricultural context."""

from datetime import date, timedelta

import pytest

from core import weather


class _FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def _sample_payload():
    today = date.today()
    days = [today - timedelta(days=7) + timedelta(days=i) for i in range(10)]
    return {
        "current": {
            "time": f"{today.isoformat()}T12:00",
            "temperature_2m": 34.4,
            "relative_humidity_2m": 52,
            "precipitation": 0,
        },
        "daily": {
            "time": [day.isoformat() for day in days],
            "precipitation_sum": [0, 2, 4, 6, 3, 4, 2, 8, 10, 1],
            "et0_fao_evapotranspiration": [4, 4, 4, 4, 4, 4, 4, 4, 4, 4],
            "temperature_2m_max": [35, 35, 36, 36, 37, 37, 36, 35, 35, 34],
        },
        "hourly": {
            "soil_moisture_3_to_9cm": [0.18] * 30,
        },
    }


def test_build_weather_context_fetches_and_caches(monkeypatch):
    weather.clear_weather_cache()
    calls = []

    def fake_get(url, params, timeout):
        calls.append((url, params, timeout))
        return _FakeResponse(_sample_payload())

    monkeypatch.setattr(weather.requests, "get", fake_get)

    first = weather.build_weather_context("ouagadougou")
    second = weather.build_weather_context("ouagadougou")

    assert len(calls) == 1
    assert calls[0][0] == weather.OPEN_METEO_FORECAST_URL
    assert calls[0][1]["past_days"] == 7
    assert first["location"]["name"] == "Ouagadougou"
    assert first["metrics"]["rain_7d_mm"] == 21.0
    assert first["metrics"]["rain_next_3d_mm"] == 19.0
    assert first["metrics"]["soil_moisture_signal"] == "Moyenne"
    assert len(first["insights"]) == 4
    assert first["sources"][0]["type"] == "Météo"
    assert second["cached"] is True


def test_build_weather_context_rejects_unknown_location():
    with pytest.raises(ValueError):
        weather.build_weather_context("inconnu", payload=_sample_payload())


def test_weather_api_error_is_wrapped(monkeypatch):
    weather.clear_weather_cache()

    def fake_get(url, params, timeout):
        raise weather.requests.RequestException("offline")

    monkeypatch.setattr(weather.requests, "get", fake_get)

    with pytest.raises(weather.WeatherError):
        weather.build_weather_context("bobo")
