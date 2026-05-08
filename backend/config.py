import os
from dotenv import load_dotenv

load_dotenv()

# CORS
# Default local dev origins should cover both localhost and 127.0.0.1 on the
# common frontend ports used during manual QA.
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    ",".join(
        [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
        ]
    ),
).split(",")

# Cache TTLs (seconds)
CACHE_TTL_PLAYER_BIO = 7 * 24 * 3600      # 7 days
CACHE_TTL_CAREER_STATS = 24 * 3600         # 24 hours
CACHE_TTL_LEAGUE_DASH = 12 * 3600          # 12 hours
CACHE_TTL_STATIC_PLAYERS = 30 * 24 * 3600  # 30 days

# NBA API
NBA_API_DELAY = 0.6  # seconds between requests
NBA_API_TIMEOUT = 30

# Database
CACHE_DB_PATH = os.path.join(os.path.dirname(__file__), "db", "cache.db")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/bip")

# Playoff cache override (drops below CURRENT_SEASON_CACHE_TTL during the
# postseason window so live brackets stay fresh during games).
PLAYOFF_CACHE_TTL = 7200  # 2 hours during playoff window

# Sprint 93 — Admin endpoint protection.
# Set in /etc/bip/env on production. When unset, admin endpoints are open
# (dev mode). Never commit a real value.
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", None)

# Sprint 93 — Application-layer rate limiting (slowapi).
# Set ENABLE_RATE_LIMIT=false in /etc/bip/env to disable without a redeploy.
ENABLE_RATE_LIMIT = os.getenv("ENABLE_RATE_LIMIT", "true").lower() == "true"

# Sprint 82d — Public hosting safety flag.
# When True, nba_client raises LiveFetchBlockedError on cache miss instead of
# calling stats.nba.com. Cron scripts (daily_sync.sh) explicitly opt into live
# fetches via NBA_API_USER_FETCH_DISABLED=false in their environment.
NBA_API_USER_FETCH_DISABLED = os.getenv("NBA_API_USER_FETCH_DISABLED", "false").lower() == "true"
