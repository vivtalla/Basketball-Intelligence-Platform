import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import CORS_ORIGINS
from data.cache import CacheManager
from db.database import engine
from db.models import Base
from routers import players, stats, shotchart, leaderboards, teams, advanced, gamelogs, games, similarity, standings, insights, warehouse, metrics

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="CourtVue Labs", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(standings.router, prefix="/api/standings", tags=["standings"])
app.include_router(insights.router, prefix="/api/insights", tags=["insights"])
app.include_router(warehouse.router, prefix="/api/warehouse", tags=["warehouse"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["metrics"])


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    CacheManager.initialize()


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
