import json
import logging
import sqlite3
import time
from typing import Dict, Optional

from config import CACHE_DB_PATH


logger = logging.getLogger(__name__)


class CacheManager:
    _db_path = CACHE_DB_PATH
    _initialized: bool = False
    # Sprint 88 (C1) — process-local counters so /api/health/cache-stats can
    # report cache effectiveness without external instrumentation. Per-worker;
    # not shared across gunicorn workers, but each worker's counts are
    # representative of the same workload.
    _stats: Dict[str, int] = {"hit": 0, "miss": 0, "expired": 0}

    @classmethod
    def _connect(cls):
        """Open a SQLite connection, lazily creating the schema on first use.

        FastAPI calls ``initialize()`` at startup, but cron-driven scripts
        (``daily_sync.sh`` → ``nba_client``) never go through that path.
        Lazy-init here so any caller is safe.
        """
        conn = sqlite3.connect(cls._db_path)
        if not cls._initialized:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires_at REAL NOT NULL
                )
                """
            )
            conn.commit()
            cls._initialized = True
        return conn

    @classmethod
    def initialize(cls):
        # Kept for the FastAPI startup hook + tests; same effect as ``_connect()``.
        cls._connect().close()

    @classmethod
    def get(cls, key: str) -> Optional[dict]:
        conn = cls._connect()
        row = conn.execute(
            "SELECT value, expires_at FROM cache WHERE key = ?", (key,)
        ).fetchone()
        conn.close()

        if row is None:
            cls._stats["miss"] += 1
            logger.debug("cache_miss: %s", key)
            return None

        value, expires_at = row
        if time.time() > expires_at:
            cls._stats["expired"] += 1
            logger.debug("cache_expired: %s", key)
            cls.delete(key)
            return None

        cls._stats["hit"] += 1
        logger.debug("cache_hit: %s", key)
        return json.loads(value)

    @classmethod
    def set(cls, key: str, value: dict, ttl_seconds: int):
        expires_at = time.time() + ttl_seconds
        conn = cls._connect()
        conn.execute(
            "INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?, ?, ?)",
            (key, json.dumps(value), expires_at),
        )
        conn.commit()
        conn.close()

    @classmethod
    def delete(cls, key: str):
        conn = cls._connect()
        conn.execute("DELETE FROM cache WHERE key = ?", (key,))
        conn.commit()
        conn.close()

    @classmethod
    def clear_expired(cls) -> int:
        """Remove expired rows. Returns the number deleted (Sprint 88 instrumentation)."""
        conn = cls._connect()
        cursor = conn.execute(
            "DELETE FROM cache WHERE expires_at < ?", (time.time(),)
        )
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted

    @classmethod
    def stats(cls) -> Dict[str, int]:
        """Sprint 88 (C1) — snapshot of process-local hit/miss/expired counts.

        Also returns total row count + DB size for capacity awareness.
        """
        conn = cls._connect()
        row_count = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
        conn.close()
        try:
            import os
            size_bytes = os.path.getsize(cls._db_path)
        except OSError:
            size_bytes = 0
        return {
            **cls._stats,
            "total": cls._stats["hit"] + cls._stats["miss"] + cls._stats["expired"],
            "row_count": row_count,
            "size_bytes": size_bytes,
        }
