"""SQLite state, aggregate counters, and bounded in-memory rate limits.

No search terms, phone numbers, target IPs, visitor IPs, or account identities
are persisted. The two web processes share the same SQLite volume.
"""
from __future__ import annotations

import sqlite3
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path


class Store:
    def __init__(self, location: str):
        self.location = str(Path(location).resolve())

    def connect(self):
        conn = sqlite3.connect(self.location, timeout=5)
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def initialize(self):
        Path(self.location).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute("""CREATE TABLE IF NOT EXISTS counts (
                day TEXT NOT NULL, interface TEXT NOT NULL, tool TEXT NOT NULL,
                outcome TEXT NOT NULL, count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (day, interface, tool, outcome)
            )""")
            db.execute("INSERT OR IGNORE INTO settings(key, value) VALUES ('public_enabled','0')")

    def public_enabled(self) -> bool:
        try:
            with self.connect() as db:
                row = db.execute("SELECT value FROM settings WHERE key='public_enabled'").fetchone()
                return bool(row and row[0] == "1")
        except sqlite3.Error:
            # Fail closed if the database is missing, locked or corrupt.
            return False

    def set_public_enabled(self, enabled: bool):
        with self.connect() as db:
            db.execute("INSERT INTO settings(key,value) VALUES('public_enabled',?) "
                       "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                       ("1" if enabled else "0",))

    def count(self, interface: str, tool: str, outcome: str):
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        try:
            with self.connect() as db:
                db.execute("""INSERT INTO counts(day, interface, tool, outcome, count)
                    VALUES(?,?,?,?,1)
                    ON CONFLICT(day, interface, tool, outcome) DO UPDATE SET count=count+1""",
                    (day, interface, tool, outcome))
        except sqlite3.Error:
            # Metrics are best effort and may never interfere with lookups.
            pass

    def summary(self):
        with self.connect() as db:
            rows = db.execute("""SELECT day, interface, tool, outcome, count
                FROM counts ORDER BY day DESC, interface, tool, outcome LIMIT 200""").fetchall()
        return [{"day": r[0], "interface": r[1], "tool": r[2],
                 "outcome": r[3], "count": r[4]} for r in rows]


class RateLimiter:
    """Per-process and per-client sliding window. Designed for one worker/process."""

    def __init__(self, *, limit: int, window: float, max_clients: int = 10000):
        self.limit, self.window, self.max_clients = limit, window, max_clients
        self.clients = defaultdict(deque)
        self.lock = threading.Lock()

    def allow(self, client: str) -> bool:
        now = time.monotonic()
        with self.lock:
            if client not in self.clients and len(self.clients) >= self.max_clients:
                # Reject new peers if all tracked entries are still active.
                # Avoid growing without a bound under a large number of peers.
                expired = [ip for ip, times in self.clients.items()
                           if not times or times[-1] < now - self.window]
                for ip in expired:
                    self.clients.pop(ip, None)
                if len(self.clients) >= self.max_clients:
                    return False
            events = self.clients[client]
            while events and events[0] <= now - self.window:
                events.popleft()
            if len(events) >= self.limit:
                return False
            events.append(now)
            return True
