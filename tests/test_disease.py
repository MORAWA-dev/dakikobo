"""Tests for leaf disease screening logic (HTTP mocked — no network/key needed)."""

import core.disease as disease
from core.disease import screen_leaf_image, UNCLEAR_MESSAGE, DISCLAIMER


class _FakeResp:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = "error body"

    def json(self):
        return self._payload


def _candidate(text):
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def _patch(monkeypatch, resp):
    monkeypatch.setattr(disease, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(disease.requests, "post", lambda *a, **k: resp)


def test_unclear_photo_returns_polite_message(monkeypatch):
    _patch(monkeypatch, _FakeResp(200, _candidate("UNCLEAR")))
    out = screen_leaf_image(b"x", "image/jpeg")
    assert out["answer"] == UNCLEAR_MESSAGE
    assert out["case"]["confidence"] == "Faible"
    assert out["case"]["actions"]


def test_normal_screening_gets_disclaimer_appended(monkeypatch):
    _patch(monkeypatch, _FakeResp(200, _candidate(
        "Il pourrait s'agir d'une carence en azote. Apportez de la fumure."
    )))
    out = screen_leaf_image(b"x", "image/jpeg")
    assert "carence en azote" in out["answer"]
    assert DISCLAIMER in out["answer"]
    assert out["case"]["observations"]
    assert out["case"]["needs_human_confirmation"] is True


def test_existing_disclaimer_not_duplicated(monkeypatch):
    text = "Possible mildiou. Ceci n'est pas un diagnostic, voyez votre agent."
    _patch(monkeypatch, _FakeResp(200, _candidate(text)))
    out = screen_leaf_image(b"x", "image/jpeg")
    assert out["answer"].lower().count("pas un diagnostic") == 1


def test_rate_limit_returns_friendly_message(monkeypatch):
    _patch(monkeypatch, _FakeResp(429))
    out = screen_leaf_image(b"x", "image/jpeg")
    assert "quota" in out["answer"].lower()


def test_missing_key_is_handled(monkeypatch):
    monkeypatch.setattr(disease, "GEMINI_API_KEY", "")
    out = screen_leaf_image(b"x", "image/jpeg")
    assert "configur" in out["answer"].lower()


def test_falls_back_to_next_model_on_429(monkeypatch):
    # First model is out of quota (429), second succeeds.
    responses = [
        _FakeResp(429),
        _FakeResp(200, _candidate("Il pourrait s'agir de la rouille du mil.")),
    ]
    calls = {"i": 0}

    def fake_post(*a, **k):
        r = responses[min(calls["i"], len(responses) - 1)]
        calls["i"] += 1
        return r

    monkeypatch.setattr(disease, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(disease.requests, "post", fake_post)
    out = screen_leaf_image(b"x", "image/jpeg")
    assert "rouille" in out["answer"]
    assert calls["i"] >= 2, "should have tried a fallback model"


def test_structured_json_response_builds_case(monkeypatch):
    payload = {
        "observations": ["Taches brunes visibles sur la feuille."],
        "problemes_possibles": ["Il pourrait s'agir d'une maladie foliaire."],
        "actions_immediates": ["Retirez les feuilles très atteintes."],
        "niveau_de_confiance": "Moyen",
        "a_confirmer_par": "Agent agricole local.",
        "reponse_courte": "Les taches brunes indiquent un probleme possible.",
    }
    _patch(monkeypatch, _FakeResp(200, _candidate(__import__("json").dumps(payload))))

    out = screen_leaf_image(
        b"x",
        "image/jpeg",
        crop="maïs",
        growth_stage="fructification / épi",
        location="Bobo-Dioulasso",
    )

    assert "probleme possible" in out["answer"]
    assert out["case"]["crop"] == "maïs"
    assert out["case"]["growth_stage"] == "fructification / épi"
    assert out["case"]["location"] == "Bobo-Dioulasso"
    assert out["case"]["observations"] == payload["observations"]
    assert out["case"]["possible_causes"] == payload["problemes_possibles"]
    assert out["case"]["actions"] == payload["actions_immediates"]


def test_context_is_added_to_gemini_prompt(monkeypatch):
    seen = {}

    def fake_post(*args, **kwargs):
        seen["prompt"] = kwargs["json"]["contents"][0]["parts"][0]["text"]
        return _FakeResp(200, _candidate("UNCLEAR"))

    monkeypatch.setattr(disease, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(disease.requests, "post", fake_post)

    screen_leaf_image(
        b"x",
        "image/jpeg",
        crop="niébé",
        growth_stage="floraison",
        location="Koudougou",
    )

    assert "culture: niébé" in seen["prompt"]
    assert "stade: floraison" in seen["prompt"]
    assert "localisation: Koudougou" in seen["prompt"]


def test_gemini_timeout_is_configurable(monkeypatch):
    seen = {}

    def fake_post(*args, **kwargs):
        seen["timeout"] = kwargs["timeout"]
        return _FakeResp(200, _candidate("UNCLEAR"))

    monkeypatch.setattr(disease, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(disease, "GEMINI_TIMEOUT_SECONDS", 6.5)
    monkeypatch.setattr(disease.requests, "post", fake_post)

    screen_leaf_image(b"x", "image/jpeg")

    assert seen["timeout"] == 6.5



# =====================================================================
# Audit regressions — payload validation, confidence ceiling, redaction
# =====================================================================

import json as _json

import pytest

from core.answer_safety import REDACTION_NOTICE


@pytest.mark.parametrize(
    "body",
    [
        '["taches brunes", "feuilles jaunes"]',   # list, not object
        '"une simple chaine"',                    # string, not object
        "42",                                     # number, not object
        "true",                                   # boolean, not object
        "null",                                   # null, not object
    ],
)
def test_non_object_json_does_not_crash_screening(monkeypatch, body):
    """`json.loads` succeeds for these, but they are not screening payloads.

    The previous code called `.get` on the parsed value, so a model returning a
    bare list raised AttributeError out of a function documented as never
    raising.
    """
    _patch(monkeypatch, _FakeResp(200, _candidate(body)))

    out = screen_leaf_image(b"x", "image/jpeg")

    assert isinstance(out["answer"], str) and out["answer"]
    assert DISCLAIMER in out["answer"]
    assert out["case"]["confidence"] in {"Faible", "Moyen"}
    assert out["service_status"] == "ok"


def test_wrongly_typed_structured_fields_are_normalized(monkeypatch):
    payload = {
        "observations": "Taches brunes sur les feuilles.",
        "problemes_possibles": {"a": "Carence possible."},
        "actions_immediates": [{"texte": "Retirez les feuilles."}, "Surveillez."],
        "niveau_de_confiance": 3,
        "a_confirmer_par": ["Agent", "agricole"],
        "reponse_courte": ["Observation", "prudente."],
    }
    _patch(monkeypatch, _FakeResp(200, _candidate(_json.dumps(payload))))

    out = screen_leaf_image(b"x", "image/jpeg", crop="maïs")

    case = out["case"]
    assert case["observations"] == ["Taches brunes sur les feuilles."]
    assert case["possible_causes"] == ["Carence possible."]
    assert case["actions"] == ["Retirez les feuilles.", "Surveillez."]
    assert case["confirmation"] == "Agent agricole"
    assert "Observation prudente." in out["answer"]
    # An unparsable confidence degrades rather than being trusted.
    assert case["confidence"] == "Faible"


def test_model_reported_fort_confidence_is_capped_at_moyen(monkeypatch):
    payload = {
        "observations": ["Taches nettes."],
        "reponse_courte": "Observation prudente.",
        "niveau_de_confiance": "Fort",
    }
    _patch(monkeypatch, _FakeResp(200, _candidate(_json.dumps(payload))))

    out = screen_leaf_image(b"x", "image/jpeg", crop="mil")

    assert out["case"]["confidence"] == "Moyen"
    assert out["case"]["confidence"] != "Fort"


def test_pesticide_name_and_dose_are_removed_from_screening(monkeypatch):
    payload = {
        "observations": ["Taches brunes sur les feuilles."],
        "problemes_possibles": ["Il pourrait s'agir d'une maladie foliaire."],
        "actions_immediates": [
            "Retirez les feuilles très atteintes.",
            "Pulvérisez du mancozèbe à 25 g par litre d'eau.",
        ],
        "niveau_de_confiance": "Moyen",
        "reponse_courte": (
            "Taches brunes visibles. Traitez avec du Décis à 10 ml par litre."
        ),
    }
    _patch(monkeypatch, _FakeResp(200, _candidate(_json.dumps(payload))))

    out = screen_leaf_image(b"x", "image/jpeg", crop="maïs")

    serialized = _json.dumps(out, ensure_ascii=False).lower()
    assert "mancozèbe".lower() not in serialized
    assert "décis".lower() not in serialized
    assert "25 g" not in serialized
    assert "10 ml" not in serialized
    # The safe action survives and the farmer is told something was removed.
    assert "Retirez les feuilles très atteintes." in out["case"]["actions"]
    assert REDACTION_NOTICE in out["answer"]
    # Mandatory messages are still present.
    assert DISCLAIMER in out["answer"]
    assert out["case"]["needs_human_confirmation"] is True
    assert out["case"]["confirmation"]


def test_definitive_diagnosis_is_replaced_by_a_hedged_refusal(monkeypatch):
    payload = {
        "observations": ["Il s'agit de la rouille du mil."],
        "problemes_possibles": ["C'est la rouille, sans aucun doute."],
        "actions_immediates": ["Traitez avec du chlorpyrifos."],
        "niveau_de_confiance": "Fort",
        "reponse_courte": "Il s'agit de la rouille du mil.",
    }
    _patch(monkeypatch, _FakeResp(200, _candidate(_json.dumps(payload))))

    out = screen_leaf_image(b"x", "image/jpeg", crop="mil")

    assert "il s'agit de la rouille" not in out["answer"].lower()
    assert "chlorpyrifos" not in _json.dumps(out, ensure_ascii=False).lower()
    assert out["case"]["confidence"] == "Moyen"
    # Non-diagnosis and agent-confirmation guarantees hold on the refusal too.
    assert DISCLAIMER in out["answer"]
    assert "agent agricole" in out["answer"].lower()
    assert out["case"]["needs_human_confirmation"] is True


def test_empty_object_yields_deterministic_refusal_not_raw_json(monkeypatch):
    _patch(monkeypatch, _FakeResp(200, _candidate('{"autre": "valeur"}')))

    out = screen_leaf_image(b"x", "image/jpeg")

    assert "autre" not in out["answer"]
    assert "{" not in out["answer"]
    assert "agent agricole" in out["answer"].lower()
    assert DISCLAIMER in out["answer"]


# --------------------------------------------------------------
# Audit regression — truthful service status for real failures
# --------------------------------------------------------------

def test_service_status_distinguishes_screening_from_failure(monkeypatch):
    _patch(monkeypatch, _FakeResp(200, _candidate("UNCLEAR")))
    assert screen_leaf_image(b"x", "image/jpeg")["service_status"] == "ok"


def test_missing_key_reports_not_configured_status(monkeypatch):
    monkeypatch.setattr(disease, "GEMINI_API_KEY", "")
    assert screen_leaf_image(b"x", "image/jpeg")["service_status"] == "not_configured"


def test_quota_exhaustion_reports_rate_limited_status(monkeypatch):
    _patch(monkeypatch, _FakeResp(429))
    assert screen_leaf_image(b"x", "image/jpeg")["service_status"] == "rate_limited"


def test_upstream_error_reports_upstream_error_status(monkeypatch):
    _patch(monkeypatch, _FakeResp(500))
    assert screen_leaf_image(b"x", "image/jpeg")["service_status"] == "upstream_error"


def test_network_failure_reports_unreachable_status(monkeypatch):
    monkeypatch.setattr(disease, "GEMINI_API_KEY", "test-key")

    def boom(*args, **kwargs):
        raise disease.requests.RequestException("no route to host")

    monkeypatch.setattr(disease.requests, "post", boom)

    out = screen_leaf_image(b"x", "image/jpeg")
    assert out["service_status"] == "unreachable"
    assert "connexion" in out["answer"].lower()


def test_unreadable_response_reports_its_own_status(monkeypatch):
    _patch(monkeypatch, _FakeResp(200, {"unexpected": "shape"}))

    out = screen_leaf_image(b"x", "image/jpeg")
    assert out["service_status"] == "unreadable_response"
    assert "interpréter" in out["answer"]



# =====================================================================
# PR revision — a_confirmer_par is safety-filtered (revision item 2)
# =====================================================================

_CONFIRMATION_FALLBACK = "Montrez la plante à un agent agricole pour confirmer."


def _payload_with_confirmation(confirmation):
    return {
        "observations": ["Taches brunes visibles."],
        "problemes_possibles": ["Il pourrait s'agir d'une maladie foliaire."],
        "actions_immediates": ["Retirez les feuilles très atteintes."],
        "niveau_de_confiance": "Moyen",
        "a_confirmer_par": confirmation,
        "reponse_courte": "Observation prudente des taches brunes.",
    }


@pytest.mark.parametrize(
    "confirmation",
    [
        "Traitez vous-même avec du Décis à 10 ml par litre.",  # pesticide + dose
        "Appliquez 100 kg/ha de NPK 14-23-14.",                # dose
        "Il s'agit certainement de la rouille.",               # definitive diagnosis
        "",                                                     # empty
        "ok",                                                  # malformed
        "Attendez la prochaine pluie pour décider.",           # not agent-directed
    ],
)
def test_unsafe_or_missing_confirmation_uses_agent_fallback(monkeypatch, confirmation):
    _patch(
        monkeypatch,
        _FakeResp(200, _candidate(_json.dumps(_payload_with_confirmation(confirmation)))),
    )

    out = screen_leaf_image(b"x", "image/jpeg", crop="mil")

    assert out["case"]["confirmation"] == _CONFIRMATION_FALLBACK
    # No unsafe content leaks through the confirmation field.
    serialized = _json.dumps(out, ensure_ascii=False).lower()
    assert "décis".lower() not in serialized
    assert "100 kg/ha" not in serialized
    assert out["case"]["needs_human_confirmation"] is True


def test_valid_agent_confirmation_is_kept(monkeypatch):
    _patch(
        monkeypatch,
        _FakeResp(
            200,
            _candidate(
                _json.dumps(
                    _payload_with_confirmation("Confirmez avec un agent agricole local.")
                )
            ),
        ),
    )

    out = screen_leaf_image(b"x", "image/jpeg", crop="mil")

    assert out["case"]["confirmation"] == "Confirmez avec un agent agricole local."
