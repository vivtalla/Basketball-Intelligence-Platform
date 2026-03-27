from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import CORS_ORIGINS
from data.cache import CacheManager
from routers import players, stats

app = FastAPI(title="Basketball Intelligence Platform", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(players.router, prefix="/api/players", tags=["players"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])


@app.on_event("startup")
def startup():
    CacheManager.initialize()


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
