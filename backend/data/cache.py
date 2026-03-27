import json
import sqlite3
import time
from typing import Optional

from config import CACHE_DB_PATH


class CacheManager:
    _db_path = CACHE_DB_PATH

    @classmethod
    def initialize(cls):
        conn = sqlite3.connect(cls._db_path)
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
        conn.close()

    @classmethod
    def get(cls, key: str) -> Optional[dict]:
        conn = sqlite3.connect(cls._db_path)
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
        conn = sqlite3.connect(cls._db_path)
        conn.execute(
            "INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?, ?, ?)",
            (key, json.dumps(value), expires_at),
        )
        conn.commit()
        conn.close()

    @classmethod
    def delete(cls, key: str):
        conn = sqlite3.connect(cls._db_path)
        conn.execute("DELETE FROM cache WHERE key = ?", (key,))
        conn.commit()
        conn.close()

    @classmethod
    def clear_expired(cls):
        conn = sqlite3.connect(cls._db_path)
        conn.execute("DELETE FROM cache WHERE expires_at < ?", (time.time(),))
        conn.commit()
        conn.close()
