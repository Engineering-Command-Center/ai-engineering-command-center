"""
UsageTracker — SQLite-backed per-user query logging.

Tracks every RAG query with:
  - who asked (email, name)
  - what they asked (question, repo_filter)
  - how good the answer was (confidence, chunks_retrieved)
  - performance (response_ms, cached)
  - when (timestamp)

Used by admin endpoints to show growth metrics and per-user analytics.
"""

from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)


class UsageTracker:
    def __init__(self, db_path: str) -> None:
        self._path = Path(db_path)
        self._init_db()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self._path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS queries (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp   TEXT    NOT NULL,
                    email       TEXT    NOT NULL,
                    name        TEXT    NOT NULL,
                    question    TEXT    NOT NULL,
                    repo_filter TEXT,
                    confidence  REAL    DEFAULT 0,
                    chunks      INTEGER DEFAULT 0,
                    cached      INTEGER DEFAULT 0,
                    response_ms INTEGER DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_queries_email     ON queries(email);
                CREATE INDEX IF NOT EXISTS idx_queries_timestamp ON queries(timestamp);
            """)

    def log(
        self,
        email: str,
        name: str,
        question: str,
        repo_filter: str | None,
        confidence: float,
        chunks: int,
        cached: bool,
        response_ms: int,
    ) -> None:
        ts = datetime.now(UTC).isoformat()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO queries
                   (timestamp, email, name, question, repo_filter, confidence, chunks, cached, response_ms)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (ts, email, name, question, repo_filter, confidence, chunks, int(cached), response_ms),
            )

    # ── Admin queries ─────────────────────────────────────────────────────────

    def overall_stats(self) -> dict:
        with self._conn() as conn:
            row = conn.execute("""
                SELECT
                    COUNT(*)                                    AS total_queries,
                    COUNT(DISTINCT email)                       AS total_users,
                    ROUND(AVG(confidence), 3)                   AS avg_confidence,
                    ROUND(AVG(response_ms))                     AS avg_response_ms,
                    SUM(cached)                                 AS cache_hits,
                    COUNT(DISTINCT DATE(timestamp))             AS active_days
                FROM queries
            """).fetchone()

            # Daily queries for last 14 days
            daily = conn.execute("""
                SELECT DATE(timestamp) AS day, COUNT(*) AS count
                FROM queries
                WHERE timestamp >= DATE('now', '-14 days')
                GROUP BY day ORDER BY day
            """).fetchall()

            # DAU last 7 days
            dau = conn.execute("""
                SELECT DATE(timestamp) AS day, COUNT(DISTINCT email) AS users
                FROM queries
                WHERE timestamp >= DATE('now', '-7 days')
                GROUP BY day ORDER BY day
            """).fetchall()

        cache_rate = round((row["cache_hits"] or 0) / max(row["total_queries"] or 1, 1) * 100, 1)
        return {
            "total_queries": row["total_queries"] or 0,
            "total_users": row["total_users"] or 0,
            "avg_confidence": row["avg_confidence"] or 0,
            "avg_response_ms": int(row["avg_response_ms"] or 0),
            "cache_hit_rate_pct": cache_rate,
            "active_days": row["active_days"] or 0,
            "daily_queries": [{"day": r["day"], "count": r["count"]} for r in daily],
            "daily_active_users": [{"day": r["day"], "users": r["users"]} for r in dau],
        }

    def users_summary(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT
                    email,
                    name,
                    COUNT(*)                        AS total_queries,
                    MAX(timestamp)                  AS last_active,
                    MIN(timestamp)                  AS first_active,
                    ROUND(AVG(confidence), 3)       AS avg_confidence,
                    SUM(cached)                     AS cache_hits,
                    COUNT(DISTINCT DATE(timestamp)) AS active_days
                FROM queries
                GROUP BY email
                ORDER BY last_active DESC
            """).fetchall()
        return [dict(r) for r in rows]

    def user_queries(self, email: str, limit: int = 50) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT timestamp, question, repo_filter, confidence,
                       chunks, cached, response_ms
                FROM queries
                WHERE email = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (email, limit)).fetchall()
        return [dict(r) for r in rows]

    def user_daily_activity(self, email: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT DATE(timestamp) AS day, COUNT(*) AS count
                FROM queries WHERE email = ?
                GROUP BY day ORDER BY day DESC LIMIT 30
            """, (email,)).fetchall()
        return [dict(r) for r in rows]


# ── Singleton ─────────────────────────────────────────────────────────────────
_tracker: UsageTracker | None = None


def get_usage_tracker(db_path: str = "usage.db") -> UsageTracker:
    global _tracker
    if _tracker is None:
        _tracker = UsageTracker(db_path)
    return _tracker
