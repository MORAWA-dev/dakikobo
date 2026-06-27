"""Tests for soil-aware fertilizer context."""

from core import soil


class _FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def _layer(name, mean):
    return {
        "name": name,
        "depths": [
            {
                "label": "0-5cm",
                "values": {"mean": mean},
            }
        ],
    }


def _sample_payload():
    return {
        "properties": {
            "layers": [
                _layer("clay", 120),
                _layer("sand", 720),
                _layer("soc", 45),
                _layer("phh2o", 62),
                _layer("cec", 50),
            ]
        }
    }


def _empty_payload():
    return {"properties": {"layers": []}}


def test_build_soil_context_fetches_and_caches(monkeypatch):
    soil.clear_soil_cache()
    calls = []

    def fake_get(url, params, timeout):
        calls.append((url, params, timeout))
        return _FakeResponse(_sample_payload())

    monkeypatch.setattr(soil.requests, "get", fake_get)

    first = soil.build_soil_context("ouagadougou", "sorgho")
    second = soil.build_soil_context("ouagadougou", "mil")

    assert len(calls) == 1
    assert calls[0][0] == soil.SOILGRIDS_QUERY_URL
    assert ("property", "clay") in calls[0][1]
    assert ("property", "soc") in calls[0][1]
    assert first["location"]["name"] == "Ouagadougou"
    assert first["crop"] == "sorgho"
    assert first["metrics"]["sand_percent"] == 72.0
    assert first["metrics"]["soc_percent"] == 0.45
    assert first["metrics"]["ph_h2o"] == 6.2
    assert first["data_available"] is True
    assert first["indicators"][0]["value"] == "Tendance sableuse"
    assert first["indicators"][1]["value"] == "Faible"
    assert first["indicators"][3]["value"] == "Risque élevé"
    assert first["sources"][0]["type"] == "Sol"
    assert second["cached"] is True
    assert second["crop"] == "mil"


def test_missing_soil_metrics_are_not_low_risk():
    context = soil.build_soil_context("ouagadougou", "maïs", payload=_empty_payload())

    assert context["data_available"] is False
    assert context["metrics"] == {
        "clay_percent": None,
        "sand_percent": None,
        "soc_percent": None,
        "ph_h2o": None,
        "cec_cmol_kg": None,
    }
    assert context["indicators"][0]["value"] == "Non disponible"
    assert context["indicators"][3]["value"] == "Non disponible"
    assert "Impossible d'estimer" in context["indicators"][3]["text"]


def test_build_soil_context_rejects_unknown_inputs():
    payload = _sample_payload()

    try:
        soil.build_soil_context("inconnu", "sorgho", payload=payload)
    except ValueError as exc:
        assert "Localité" in str(exc)
    else:
        raise AssertionError("unknown location should fail")

    try:
        soil.build_soil_context("bobo", "coton", payload=payload)
    except ValueError as exc:
        assert "Culture" in str(exc)
    else:
        raise AssertionError("unknown crop should fail")


def test_soil_api_error_is_wrapped(monkeypatch):
    soil.clear_soil_cache()

    def fake_get(url, params, timeout):
        raise soil.requests.RequestException("offline")

    monkeypatch.setattr(soil.requests, "get", fake_get)

    try:
        soil.build_soil_context("bobo", "sorgho")
    except soil.SoilError:
        pass
    else:
        raise AssertionError("request errors should be wrapped")
