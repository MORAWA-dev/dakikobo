"""Tests for privacy-safe ops metrics."""

import app as app_module
from core.ops_metrics import OpsMetricsStore


def test_ops_metrics_store_aggregates_and_hides_content(tmp_path):
    store = OpsMetricsStore(
        max_events=10,
        db_path=str(tmp_path / "metrics.sqlite3"),
    )
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
        cache_hit=True,
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
    assert snap["recent"][-1]["cache_hit"] is True


def test_ops_metrics_route_returns_snapshot(monkeypatch, tmp_path):
    store = OpsMetricsStore(
        50,
        db_path=str(tmp_path / "route-metrics.sqlite3"),
    )
    store.reset()
    monkeypatch.setattr(app_module, "OPS_METRICS_ENABLED", True)
    monkeypatch.setattr(app_module.ops_metrics_mod, "_metrics_store", store)

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


def test_ops_metrics_are_coherent_across_store_instances(tmp_path):
    db_path = str(tmp_path / "shared-metrics.sqlite3")
    worker_one = OpsMetricsStore(20, db_path=db_path)
    worker_two = OpsMetricsStore(20, db_path=db_path)
    worker_one.reset()

    for latency in (10, 20, 30):
        worker_one.record(
            method="POST",
            route="/ask",
            endpoint="ask",
            status_code=200,
            latency_ms=latency,
        )
    for latency in (40, 50):
        worker_two.record(
            method="GET",
            route="/healthz",
            endpoint="healthz",
            status_code=200,
            latency_ms=latency,
        )

    snap = worker_one.snapshot(limit=20)
    assert snap["totals"]["recorded_events"] == 5
    assert snap["totals"]["buffer_size"] == 5
    assert snap["latency_ms"]["p50"] == 30.0
    assert snap["latency_ms"]["p95"] == 50.0
    assert snap["by_route"] == {"/ask": 3, "/healthz": 2}


def test_ops_metrics_keeps_bounded_rows_and_cumulative_totals(tmp_path):
    store = OpsMetricsStore(10, db_path=str(tmp_path / "bounded.sqlite3"))
    for index in range(15):
        store.record(
            method="GET",
            route="/healthz",
            endpoint="healthz",
            status_code=500 if index == 0 else 200,
            latency_ms=index,
        )

    snap = store.snapshot(limit=10)
    assert snap["totals"]["recorded_events"] == 15
    assert snap["totals"]["http_errors"] == 1
    assert snap["totals"]["buffer_size"] == 10
    assert len(snap["recent"]) == 10


def test_ops_metrics_route_can_be_disabled(monkeypatch):
    monkeypatch.setattr(app_module, "OPS_METRICS_ENABLED", False)
    client = app_module.app.test_client()
    response = client.get("/ops/metrics")
    assert response.status_code == 503
    assert response.get_json()["enabled"] is False
