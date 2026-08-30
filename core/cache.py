"""Concurrency-safe SQLite state for DakiKobo runtime caches.

The cache is intentionally small and boring: each operation uses a short-lived
SQLite connection, WAL mode, and a 30-second busy timeout. That makes entries
visible to every Gunicorn worker without keeping process-local dictionaries in
sync.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from contextlib import contextmanager
from typing import Iterator

from config import STATE_DB_PATH


SQLITE_TIMEOUT_SECONDS = 30


def _ensure_parent_dir(db_path: str) -> None:
    directory = os.path.dirname(os.path.abspath(db_path))
    if directory:
        os.makedirs(directory, exist_ok=True)


@contextmanager
def sqlite_connection(db_path: str = STATE_DB_PATH) -> Iterator[sqlite3.Connection]:
    """Yield a WAL-enabled SQLite connection shared by cache/metrics stores."""
    _ensure_parent_dir(db_path)
    conn = sqlite3.connect(db_path, timeout=SQLITE_TIMEOUT_SECONDS)
    conn.row_factory = sqlite3.Row
    conn.execute(f"PRAGMA busy_timeout = {SQLITE_TIMEOUT_SECONDS * 1000}")
    # Two Gunicorn workers can first-open a brand-new database at the same
    # instant. SQLite may raise `database is locked` while one connection is
    # negotiating WAL even with busy_timeout set, so retry within the same
    # locked 30-second budget instead of failing worker boot.
    deadline = time.monotonic() + SQLITE_TIMEOUT_SECONDS
    delay = 0.02
    while True:
        try:
            conn.execute("PRAGMA journal_mode = WAL")
            break
        except sqlite3.OperationalError as exc:
            retryable = "locked" in str(exc).lower() or "busy" in str(exc).lower()
            if not retryable or time.monotonic() >= deadline:
                conn.close()
                raise
            time.sleep(delay)
            delay = min(delay * 2, 0.25)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


class TTLCache:
    """JSON-object cache with namespace isolation and per-entry expiry."""

    def __init__(
        self,
        namespace: str,
        ttl_seconds: int | float,
        backend: str = "sqlite",
        *,
        db_path: str = STATE_DB_PATH,
    ):
        namespace = (namespace or "").strip()
        if not namespace:
            raise ValueError("cache namespace must not be empty")
        if backend != "sqlite":
            raise ValueError("only the sqlite cache backend is supported")
        if float(ttl_seconds) < 0:
            raise ValueError("ttl_seconds must be non-negative")

        self.namespace = namespace
        self.ttl_seconds = float(ttl_seconds)
        self.backend = backend
        self.db_path = str(db_path)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with sqlite_connection(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_entries (
                    namespace TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value_json TEXT NOT NULL,
                    expires_at REAL NOT NULL,
                    PRIMARY KEY (namespace, key)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_cache_entries_expires_at
                ON cache_entries(expires_at)
                """
            )

    def get(self, key: str) -> dict | None:
        cache_key = str(key)
        now = time.time()
        with sqlite_connection(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT value_json, expires_at
                FROM cache_entries
                WHERE namespace = ? AND key = ?
                """,
                (self.namespace, cache_key),
            ).fetchone()
            if row is None:
                return None
            if float(row["expires_at"]) <= now:
                conn.execute(
                    "DELETE FROM cache_entries WHERE namespace = ? AND key = ?",
                    (self.namespace, cache_key),
                )
                return None
            try:
                value = json.loads(row["value_json"])
            except (TypeError, ValueError, json.JSONDecodeError):
                conn.execute(
                    "DELETE FROM cache_entries WHERE namespace = ? AND key = ?",
                    (self.namespace, cache_key),
                )
                return None
        return value if isinstance(value, dict) else None

    def set(self, key: str, value: dict) -> None:
        if not isinstance(value, dict):
            raise TypeError("cache values must be dictionaries")
        value_json = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        expires_at = time.time() + self.ttl_seconds
        with sqlite_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO cache_entries (namespace, key, value_json, expires_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(namespace, key) DO UPDATE SET
                    value_json = excluded.value_json,
                    expires_at = excluded.expires_at
                """,
                (self.namespace, str(key), value_json, expires_at),
            )

    def purge_expired(self) -> int:
        with sqlite_connection(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM cache_entries WHERE expires_at <= ?",
                (time.time(),),
            )
            return max(0, int(cursor.rowcount))

    def clear(self) -> int:
        """Remove this namespace only; useful for tests and manual refreshes."""
        with sqlite_connection(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM cache_entries WHERE namespace = ?",
                (self.namespace,),
            )
            return max(0, int(cursor.rowcount))
