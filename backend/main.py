import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import CORS_ORIGINS
from data.cache import CacheManager
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

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="CourtVue Labs", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    # Sprint 87 — narrow from "*" to actually-used methods. Platform has
    # 40 POST + 2 PATCH + 2 DELETE endpoints; PATCH/DELETE are admin-only and
    # not called from the browser, so we drop them. PUT is unused.
    allow_methods=["GET", "HEAD", "POST", "OPTIONS"],
    # Sprint 87 — narrow from "*" to specific headers. Authorization is kept
    # as a future-proof no-op for any auth-bearing endpoint.
    allow_headers=["Content-Type", "Accept", "Authorization"],
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
