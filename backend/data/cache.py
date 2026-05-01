import json
import sqlite3
import time
from typing import Optional

from config import CACHE_DB_PATH


class CacheManager:
    _db_path = CACHE_DB_PATH
    _initialized: bool = False

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
            return None

        value, expires_at = row
        if time.time() > expires_at:
            cls.delete(key)
            return None

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
    def clear_expired(cls):
        conn = cls._connect()
        conn.execute("DELETE FROM cache WHERE expires_at < ?", (time.time(),))
        conn.commit()
        conn.close()
