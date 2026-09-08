"""Atomic fixed-window budgets shared by workers; no raw client addresses."""
import time
from core.cache import sqlite_connection


def consume(db_path, identity, *, minute_limit=60, daily_limit=2000, global_minute_limit=120, now=None):
    now = time.time() if now is None else now
    windows = [('client:' + identity, 60, minute_limit), ('global', 60, global_minute_limit), ('daily', 86400, daily_limit)]
    with sqlite_connection(db_path) as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS request_budgets (bucket TEXT, window INTEGER, count INTEGER NOT NULL, expires REAL NOT NULL, PRIMARY KEY(bucket, window))')
        conn.execute('BEGIN IMMEDIATE')
        conn.execute('DELETE FROM request_budgets WHERE expires<=?', (now,))
        for bucket, duration, limit in windows:
            window = int(now // duration)
            row = conn.execute('SELECT count FROM request_budgets WHERE bucket=? AND window=?', (bucket, window)).fetchone()
            if row and row['count'] >= limit:
                return max(1, int((window+1)*duration-now))
        for bucket, duration, limit in windows:
            window = int(now // duration)
            conn.execute('INSERT INTO request_budgets VALUES (?, ?, 1, ?) ON CONFLICT(bucket, window) DO UPDATE SET count=count+1', (bucket, window, (window+1)*duration))
    return 0
