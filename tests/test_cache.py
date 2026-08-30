"""Tests for the shared SQLite TTL cache."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor

from core import cache as cache_module
from core.cache import SQLITE_TIMEOUT_SECONDS, TTLCache


def test_ttl_cache_round_trip_and_namespace_isolation(tmp_path):
    db_path = str(tmp_path / "state.sqlite3")
    weather = TTLCache("weather", 60, db_path=db_path)
    soil = TTLCache("soil", 60, db_path=db_path)

    weather.set("ouaga", {"label": "Pluie utile", "value": 12})

    assert weather.get("ouaga") == {"label": "Pluie utile", "value": 12}
    assert soil.get("ouaga") is None
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    assert SQLITE_TIMEOUT_SECONDS == 30


def test_ttl_cache_expiry_and_purge(monkeypatch, tmp_path):
    db_path = str(tmp_path / "expiry.sqlite3")
    clock = {"now": 1000.0}
    monkeypatch.setattr(cache_module.time, "time", lambda: clock["now"])
    cache = TTLCache("answers", 10, db_path=db_path)

    cache.set("expired", {"answer": "ancien"})
    cache.set("expired-two", {"answer": "ancien aussi"})
    clock["now"] = 1005.0
    cache.set("fresh", {"answer": "récent"})
    clock["now"] = 1011.0

    assert cache.get("expired") is None
    assert cache.get("fresh") == {"answer": "récent"}
    assert cache.purge_expired() == 1


def test_ttl_cache_wal_concurrency_smoke(tmp_path):
    db_path = str(tmp_path / "concurrent.sqlite3")
    worker_one = TTLCache("shared", 60, db_path=db_path)
    worker_two = TTLCache("shared", 60, db_path=db_path)

    def write(index: int) -> None:
        cache = worker_one if index % 2 else worker_two
        cache.set(str(index), {"index": index})

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(write, range(40)))

    assert [worker_one.get(str(i))["index"] for i in range(40)] == list(range(40))


def test_concurrent_first_open_negotiates_wal_without_boot_race(tmp_path):
    db_path = str(tmp_path / "first-open.sqlite3")

    def open_worker(index: int) -> dict:
        cache = TTLCache(f"worker-{index}", 60, db_path=db_path)
        cache.set("ready", {"worker": index})
        return cache.get("ready")

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(open_worker, range(8)))

    assert results == [{"worker": index} for index in range(8)]


def test_clear_removes_only_one_namespace(tmp_path):
    db_path = str(tmp_path / "clear.sqlite3")
    one = TTLCache("one", 60, db_path=db_path)
    two = TTLCache("two", 60, db_path=db_path)
    one.set("k", {"v": 1})
    two.set("k", {"v": 2})

    assert one.clear() == 1
    assert one.get("k") is None
    assert two.get("k") == {"v": 2}


def test_phase3_serving_and_dependency_contracts_are_pinned():
    dockerfile = open("Dockerfile", encoding="utf-8").read()
    requirements = {
        line.strip()
        for line in open("requirements.txt", encoding="utf-8")
        if line.strip() and not line.startswith("#")
    }

    assert "--workers 2 --threads 4 --timeout 90" in dockerfile
    assert "numpy==1.26.4" in requirements
    assert "torch==2.2.2" in requirements
    assert "transformers==4.57.6" in requirements
    assert not {"openai", "tiktoken", "rich", "Pygments"} & requirements
