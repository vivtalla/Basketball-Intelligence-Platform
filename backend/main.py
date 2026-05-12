import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import CORS_ORIGINS
from data.cache import CacheManager
from rate_limiting import limiter, _slowapi_available
from utils.logging_setup import configure_logging
from utils.request_id_middleware import RequestIDMiddleware

if _slowapi_available:
    from slowapi import _rate_limit_exceeded_handler  # type: ignore[import]
    from slowapi.errors import RateLimitExceeded  # type: ignore[import]
from routers import (
    advanced,
    archetype,
    career,
    compare,
    decision,
    free_agency,
    gamelogs,
    games,
    injuries,
    insights,
    leaderboards,
    lineups,
    metrics,
    methodology,
    milestones,
    mvp,
    draft,
    picks,
    players,
    playoffs,
    pre_read,
    query,
    schedule,
    scouting,
    season_phase,
    share,
    shotchart,
    similarity,
    standings,
    stats,
    styles,
    team_fit,
    teams,
    trade,
    trends,
    warehouse,
)

# Sprint 98 Stream A3 — structured logging with run_id / request_id context
# binding. JSON renderer in production (ENV=production), console renderer in
# dev. Replaces the prior `logging.basicConfig(level=INFO)` which produced
# unstructured stdout text and made cron-tick correlation impossible.
configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="CourtVue Labs", version="0.2.0")

# Sprint 93 — application-layer rate limiting as secondary defence behind
# Cloudflare's 100 req/10 min WAF rule.  Targets expensive endpoints only.
# Set ENABLE_RATE_LIMIT=false in /etc/bip/env to disable without a redeploy.
app.state.limiter = limiter
if _slowapi_available:
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Sprint 98 Stream A3 — request-ID propagation. Middleware order matters
# for Starlette: middlewares are added outside-in, so the request-id binds
# to the contextvars BEFORE CORS handles preflight. Honor an inbound
# X-Request-ID header if a client sends one, else generate a fresh UUID.
app.add_middleware(RequestIDMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    # Sprint 87 — narrow from "*" to actually-used methods. Platform has
    # 40 POST + 2 PATCH + 2 DELETE endpoints; PATCH/DELETE are admin-only and
    # not called from the browser, so we drop them. PUT is unused.
    allow_methods=["GET", "HEAD", "POST", "OPTIONS"],
    # Sprint 87 — narrow from "*" to specific headers. Authorization +
    # X-Request-ID are kept so clients can correlate.
    allow_headers=["Content-Type", "Accept", "Authorization", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)

app.include_router(players.router, prefix="/api/players", tags=["players"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])
app.include_router(shotchart.router, prefix="/api/shotchart", tags=["shotchart"])
app.include_router(leaderboards.router, prefix="/api/leaderboards", tags=["leaderboards"])
app.include_router(teams.router, prefix="/api/teams", tags=["teams"])
app.include_router(advanced.router, prefix="/api/advanced", tags=["advanced"])
app.include_router(gamelogs.router, prefix="/api/gamelogs", tags=["gamelogs"])
app.include_router(games.router, prefix="/api/games", tags=["games"])
app.include_router(similarity.router, prefix="/api/similarity", tags=["similarity"])
app.include_router(archetype.router, prefix="/api/archetype", tags=["archetype"])
app.include_router(compare.router, prefix="/api/compare", tags=["compare"])
app.include_router(standings.router, prefix="/api/standings", tags=["standings"])
app.include_router(insights.router, prefix="/api/insights", tags=["insights"])
app.include_router(pre_read.router, prefix="/api/pre-read", tags=["pre-read"])
app.include_router(schedule.router, prefix="/api/schedule", tags=["schedule"])
app.include_router(scouting.router, prefix="/api/scouting", tags=["scouting"])
app.include_router(decision.router, prefix="/api/decision", tags=["decision"])
app.include_router(decision.follow_router, prefix="/api/follow-through", tags=["follow-through"])
app.include_router(styles.router, prefix="/api/styles", tags=["styles"])
app.include_router(team_fit.router, prefix="/api/team-fit", tags=["team-fit"])
app.include_router(trends.router, prefix="/api/trends", tags=["trends"])
app.include_router(trends.scenarios_router, prefix="/api/scenarios", tags=["scenarios"])
app.include_router(warehouse.router, prefix="/api/warehouse", tags=["warehouse"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["metrics"])
app.include_router(methodology.router, prefix="/api/methodology", tags=["methodology"])
app.include_router(injuries.router, prefix="/api/injuries", tags=["injuries"])
app.include_router(query.router, prefix="/api/query", tags=["query"])
app.include_router(mvp.router, prefix="/api/mvp", tags=["mvp"])
app.include_router(season_phase.router, prefix="/api/season-phase", tags=["season-phase"])
app.include_router(playoffs.router, prefix="/api/playoffs", tags=["playoffs"])
app.include_router(share.router, prefix="/api/share", tags=["share"])
app.include_router(career.router, prefix="/api/players", tags=["career"])
app.include_router(milestones.router, prefix="/api/milestones", tags=["milestones"])
app.include_router(trade.router, prefix="/api/trade", tags=["trade"])
app.include_router(free_agency.router, prefix="/api/free-agency", tags=["free-agency"])
app.include_router(draft.router, prefix="/api/draft", tags=["draft"])
app.include_router(picks.router, prefix="/api/picks", tags=["picks"])
app.include_router(lineups.router, prefix="/api/lineups", tags=["lineups"])


@app.on_event("startup")
def startup():
    CacheManager.initialize()


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/health/cache-stats")
def cache_stats():
    """Sprint 88 (C1) — process-local SQLite cache effectiveness snapshot.

    Per gunicorn worker (not aggregated across workers). Public-safe: just
    counts + row count + db file size, no key contents. Useful for spot-checking
    cache hit rate during capacity planning + post-deploy validation.
    """
    return CacheManager.stats()


@app.get("/api/health/sync-status")
def sync_status():
    """Sprint 97/98 — surface recent sync state for monitoring.

    Three sections in the response:

    - ``playoff_backfill_last_24h`` (Sprint 97, kept for back-compat): summary
      of the last playoff backfill event, populated when gaps were recovered.
    - ``syncs`` (Sprint 98): map of every registered sync entity → its last
      run marker + freshness (``stale=True`` when older than 2x cadence).
      Entities with no marker still appear with ``ran_at=null, stale=true``.
    - ``cache_db`` (Sprint 98): size + row-count snapshot of the SQLite cache
      that stores both API responses and freshness markers.

    The healthy steady state: ``playoff_backfill_last_24h.count == 0`` and
    every entry in ``syncs`` has ``stale: false``.
    """
    from services.sync_freshness import read_all_syncs

    last_backfill = CacheManager.peek("sync_gaps:playoff_backfill:last")
    cache_snapshot = CacheManager.stats()
    return {
        "playoff_backfill_last_24h": last_backfill
        or {"count": 0, "ran_at": None, "backfilled_ids": [], "season": None},
        "syncs": read_all_syncs(),
        "cache_db": {
            "size_bytes": cache_snapshot.get("size_bytes", 0),
            "size_kb": cache_snapshot.get("size_bytes", 0) // 1024,
            "row_count": cache_snapshot.get("row_count", 0),
        },
    }
