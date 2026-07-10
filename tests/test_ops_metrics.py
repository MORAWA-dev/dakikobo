"""Tests for privacy-safe ops metrics."""

import app as app_module
from core.ops_metrics import OpsMetricsStore, configure_metrics_store


def test_ops_metrics_store_aggregates_and_hides_content():
    store = OpsMetricsStore(max_events=5)
    store.record(
        method="POST",
        route="/ask",
        endpoint="ask",
        status_code=200,
        latency_ms=120.5,
        feature="ask",
        outcome="ok",
        confidence="Fort",
        source_count=2,
        question="should never appear",
        answer="secret answer",
    )
    store.record(
        method="POST",
        route="/ask",
        endpoint="ask",
        status_code=500,
        latency_ms=900.0,
        feature="ask",
        outcome="service_error",
        failure_type="Timeout",
    )
    store.record(
        method="GET",
        route="/ops/metrics",
        endpoint="ops_metrics",
        status_code=200,
        latency_ms=5.0,
    )

    snap = store.snapshot(limit=10)
    assert snap["totals"]["buffer_size"] == 2  # /ops skipped
    assert snap["totals"]["http_errors"] == 1
    assert snap["latency_ms"]["p50"] is not None
    assert snap["by_route"]["/ask"] == 2
    assert snap["by_failure_type"]["Timeout"] == 1
    blob = str(snap)
    assert "should never appear" not in blob
    assert "secret answer" not in blob
    assert "question" not in snap["recent"][0]


def test_ops_metrics_route_returns_snapshot(monkeypatch):
    store = configure_metrics_store(50)
    store.reset()
    monkeypatch.setattr(app_module, "OPS_METRICS_ENABLED", True)
    monkeypatch.setattr(app_module.ops_metrics_mod, "metrics_store", store)

    client = app_module.app.test_client()
    # Generate a couple of tracked requests.
    client.get("/healthz")
    client.post("/ask", data={"messageText": ""})  # validation error

    response = client.get("/ops/metrics?limit=20")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["enabled"] is True
    assert payload["bot"] == "DakiKobo"
    assert "privacy_note" in payload
    assert payload["totals"]["buffer_size"] >= 2
    assert "/healthz" in payload["by_route"] or "/ask" in payload["by_route"]


def test_ops_metrics_route_can_be_disabled(monkeypatch):
    monkeypatch.setattr(app_module, "OPS_METRICS_ENABLED", False)
    client = app_module.app.test_client()
    response = client.get("/ops/metrics")
    assert response.status_code == 503
    assert response.get_json()["enabled"] is False
