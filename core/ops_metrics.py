"""SQLite-backed privacy-safe request metrics for demo observability.

Only an explicit field whitelist is persisted. Question text, answers,
transcripts, and upload bytes never enter the metric table. SQLite WAL keeps
the recent-event view coherent across Gunicorn workers.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from config import OPS_METRICS_MAX_EVENTS, STATE_DB_PATH
from core.cache import sqlite_connection


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class MetricEvent:
    timestamp: str
    method: str
    route: str
    endpoint: str
    status_code: int
    latency_ms: float | None
    feature: str = ""
    intent: str = ""
    outcome: str = ""
    failure_type: str = ""
    confidence: str = ""
    source_count: int | None = None
    answer_kind: str = ""
    refusal: bool | None = None
    cache_hit: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_EVENT_COLUMNS = (
    "timestamp",
    "method",
    "route",
    "endpoint",
    "status_code",
    "latency_ms",
    "feature",
    "intent",
    "outcome",
    "failure_type",
    "confidence",
    "source_count",
    "answer_kind",
    "refusal",
    "cache_hit",
)


class OpsMetricsStore:
    """Privacy-filtered SQLite event store with a bounded snapshot window."""

    def __init__(
        self,
        max_events: int = OPS_METRICS_MAX_EVENTS,
        *,
        db_path: str = STATE_DB_PATH,
    ):
        self._max_events = max(10, int(max_events))
        self.db_path = str(db_path)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with sqlite_connection(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS metric_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    method TEXT NOT NULL,
                    route TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    status_code INTEGER NOT NULL,
                    latency_ms REAL,
                    feature TEXT NOT NULL DEFAULT '',
                    intent TEXT NOT NULL DEFAULT '',
                    outcome TEXT NOT NULL DEFAULT '',
                    failure_type TEXT NOT NULL DEFAULT '',
                    confidence TEXT NOT NULL DEFAULT '',
                    source_count INTEGER,
                    answer_kind TEXT NOT NULL DEFAULT '',
                    refusal INTEGER,
                    cache_hit INTEGER
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS metric_totals (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    recorded_events INTEGER NOT NULL,
                    http_errors INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO metric_totals (id, recorded_events, http_errors)
                SELECT 1,
                       COUNT(*),
                       COALESCE(SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END), 0)
                FROM metric_events
                WHERE NOT EXISTS (SELECT 1 FROM metric_totals WHERE id = 1)
                """
            )

    def reset(self) -> None:
        with sqlite_connection(self.db_path) as conn:
            conn.execute("DELETE FROM metric_events")
            conn.execute(
                """
                UPDATE metric_totals
                SET recorded_events = 0, http_errors = 0
                WHERE id = 1
                """
            )

    def record(self, **fields: Any) -> MetricEvent | None:
        """Record a privacy-filtered event; skip the metrics endpoint itself."""
        route = str(fields.get("route") or "")
        if route.startswith("/ops"):
            return None

        status = int(fields.get("status_code") or 0)
        latency = fields.get("latency_ms")
        try:
            latency_ms = float(latency) if latency is not None else None
        except (TypeError, ValueError):
            latency_ms = None

        source_count = fields.get("source_count")
        try:
            source_count_i = int(source_count) if source_count is not None else None
        except (TypeError, ValueError):
            source_count_i = None

        refusal = fields.get("refusal")
        refusal = refusal if isinstance(refusal, bool) else None
        cache_hit = fields.get("cache_hit")
        cache_hit = cache_hit if isinstance(cache_hit, bool) else None

        event = MetricEvent(
            timestamp=str(fields.get("timestamp") or _utc_now_iso()),
            method=str(fields.get("method") or "")[:12],
            route=route[:120],
            endpoint=str(fields.get("endpoint") or "")[:80],
            status_code=status,
            latency_ms=latency_ms,
            feature=str(fields.get("feature") or "")[:40],
            intent=str(fields.get("intent") or "")[:40],
            outcome=str(fields.get("outcome") or "")[:40],
            failure_type=str(fields.get("failure_type") or "")[:60],
            confidence=str(fields.get("confidence") or "")[:20],
            source_count=source_count_i,
            answer_kind=str(fields.get("answer_kind") or "")[:30],
            refusal=refusal,
            cache_hit=cache_hit,
        )

        values = event.to_dict()
        values["refusal"] = None if refusal is None else int(refusal)
        values["cache_hit"] = None if cache_hit is None else int(cache_hit)
        placeholders = ", ".join("?" for _ in _EVENT_COLUMNS)
        with sqlite_connection(self.db_path) as conn:
            conn.execute(
                f"INSERT INTO metric_events ({', '.join(_EVENT_COLUMNS)}) "
                f"VALUES ({placeholders})",
                tuple(values[column] for column in _EVENT_COLUMNS),
            )
            conn.execute(
                """
                UPDATE metric_totals
                SET recorded_events = recorded_events + 1,
                    http_errors = http_errors + ?
                WHERE id = 1
                """,
                (1 if status >= 400 else 0,),
            )
            conn.execute(
                """
                DELETE FROM metric_events
                WHERE id NOT IN (
                    SELECT id FROM metric_events ORDER BY id DESC LIMIT ?
                )
                """,
                (self._max_events,),
            )
        return event

    @staticmethod
    def _event_from_row(row) -> MetricEvent:
        values = {column: row[column] for column in _EVENT_COLUMNS}
        values["refusal"] = (
            None if values["refusal"] is None else bool(values["refusal"])
        )
        values["cache_hit"] = (
            None if values["cache_hit"] is None else bool(values["cache_hit"])
        )
        return MetricEvent(**values)

    def snapshot(self, limit: int = 50) -> dict[str, Any]:
        limit = max(1, min(int(limit), self._max_events))
        with sqlite_connection(self.db_path) as conn:
            totals = conn.execute(
                "SELECT recorded_events, http_errors FROM metric_totals WHERE id = 1"
            ).fetchone()
            rows = conn.execute(
                f"""
                SELECT {', '.join(_EVENT_COLUMNS)}
                FROM metric_events
                ORDER BY id DESC
                LIMIT ?
                """,
                (self._max_events,),
            ).fetchall()

        events = [self._event_from_row(row) for row in reversed(rows)]
        total = int(totals["recorded_events"] or 0)
        errors = int(totals["http_errors"] or 0)
        recent = events[-limit:]
        latencies = sorted(
            event.latency_ms
            for event in events
            if isinstance(event.latency_ms, (int, float))
        )
        by_route = Counter(event.route for event in events)
        by_status = Counter(str(event.status_code) for event in events)
        by_outcome = Counter(event.outcome for event in events if event.outcome)
        by_failure = Counter(
            event.failure_type for event in events if event.failure_type
        )
        by_feature = Counter(
            event.feature or event.endpoint or event.route for event in events
        )

        def percentile(sorted_vals: list[float], p: float) -> float | None:
            if not sorted_vals:
                return None
            if len(sorted_vals) == 1:
                return round(sorted_vals[0], 2)
            idx = int(round((p / 100.0) * (len(sorted_vals) - 1)))
            idx = max(0, min(idx, len(sorted_vals) - 1))
            return round(sorted_vals[idx], 2)

        slow = sorted(
            (event for event in events if event.latency_ms is not None),
            key=lambda event: event.latency_ms or 0,
            reverse=True,
        )[:10]

        return {
            "generated_at": _utc_now_iso(),
            "privacy_note": (
                "Métriques agrégées sans texte de question, réponse, photo ni audio."
            ),
            "totals": {
                "recorded_events": total,
                "buffer_size": len(events),
                "buffer_capacity": self._max_events,
                "http_errors": errors,
                "error_rate": round(errors / total, 4) if total else 0.0,
            },
            "latency_ms": {
                "count": len(latencies),
                "p50": percentile(latencies, 50),
                "p95": percentile(latencies, 95),
                "max": round(latencies[-1], 2) if latencies else None,
            },
            "by_route": dict(by_route.most_common(20)),
            "by_status": dict(sorted(by_status.items())),
            "by_outcome": dict(by_outcome.most_common(20)),
            "by_failure_type": dict(by_failure.most_common(20)),
            "by_feature": dict(by_feature.most_common(20)),
            "slowest": [event.to_dict() for event in slow],
            "recent": [event.to_dict() for event in reversed(recent)],
        }


_metrics_store: OpsMetricsStore | None = None
_metrics_store_lock = Lock()


def get_metrics_store() -> OpsMetricsStore:
    """Return the configured process facade over the shared SQLite database."""
    global _metrics_store
    if _metrics_store is None:
        with _metrics_store_lock:
            if _metrics_store is None:
                _metrics_store = OpsMetricsStore()
    return _metrics_store


def configure_metrics_store(
    max_events: int,
    *,
    db_path: str = STATE_DB_PATH,
) -> OpsMetricsStore:
    """Replace the local facade while retaining SQLite cross-worker sharing."""
    global _metrics_store
    with _metrics_store_lock:
        _metrics_store = OpsMetricsStore(max_events=max_events, db_path=db_path)
    return _metrics_store
