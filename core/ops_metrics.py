"""In-process privacy-safe request metrics for demo observability.

Keeps a fixed-size ring of recent HTTP events so operators can inspect latency,
failures, and feature outcomes without a full log stack. Never stores question
text, answers, transcripts, or upload bytes.
"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Fields that may contain user content — never retain them.
_DROP_KEYS = {
    "question",
    "answer",
    "message",
    "messageText",
    "transcript",
    "text",
    "prompt",
    "image",
    "audio",
    "raw",
}


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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class OpsMetricsStore:
    """Thread-safe ring buffer of recent request metrics."""

    def __init__(self, max_events: int = 200):
        self._max_events = max(10, int(max_events))
        self._events: deque[MetricEvent] = deque(maxlen=self._max_events)
        self._lock = Lock()
        self._total = 0
        self._errors = 0

    def reset(self) -> None:
        with self._lock:
            self._events.clear()
            self._total = 0
            self._errors = 0

    def record(self, **fields: Any) -> MetricEvent | None:
        """Record a privacy-filtered metric event. Returns None if route is skipped."""
        route = str(fields.get("route") or "")
        # Avoid recording metrics scraping itself (noise loop).
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
            refusal=fields.get("refusal") if isinstance(fields.get("refusal"), bool) else None,
        )

        with self._lock:
            self._events.append(event)
            self._total += 1
            if status >= 400:
                self._errors += 1
        return event

    def snapshot(self, limit: int = 50) -> dict[str, Any]:
        limit = max(1, min(int(limit), self._max_events))
        with self._lock:
            events = list(self._events)
            total = self._total
            errors = self._errors

        recent = events[-limit:]
        latencies = sorted(
            e.latency_ms for e in events if isinstance(e.latency_ms, (int, float))
        )
        by_route = Counter(e.route for e in events)
        by_status = Counter(str(e.status_code) for e in events)
        by_outcome = Counter(e.outcome for e in events if e.outcome)
        by_failure = Counter(e.failure_type for e in events if e.failure_type)
        by_feature = Counter(e.feature or e.endpoint or e.route for e in events)

        def percentile(sorted_vals: list[float], p: float) -> float | None:
            if not sorted_vals:
                return None
            if len(sorted_vals) == 1:
                return round(sorted_vals[0], 2)
            idx = int(round((p / 100.0) * (len(sorted_vals) - 1)))
            idx = max(0, min(idx, len(sorted_vals) - 1))
            return round(sorted_vals[idx], 2)

        slow = sorted(
            (e for e in events if e.latency_ms is not None),
            key=lambda e: e.latency_ms or 0,
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
            "slowest": [e.to_dict() for e in slow],
            "recent": [e.to_dict() for e in reversed(recent)],
        }


# Process-wide store used by Flask.
metrics_store = OpsMetricsStore(max_events=200)


def configure_metrics_store(max_events: int) -> OpsMetricsStore:
    """Reconfigure capacity (mainly for tests / env overrides).

    Replaces the store in-place on the module attribute so importers that hold
    a direct reference should re-import; prefer using this module's
    ``metrics_store`` attribute after configure.
    """
    global metrics_store
    metrics_store = OpsMetricsStore(max_events=max_events)
    return metrics_store
