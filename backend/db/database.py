from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from config import DATABASE_URL

# Sprint 88 (B3) — explicit pool config. Default SQLAlchemy pool is 5 + 10
# overflow; with gunicorn 2 workers that gave 30 max conns. The CPX11 Postgres
# default max_connections is 100, so we have headroom for a larger pool.
# pool_size=10 / max_overflow=20 → 60 max conns (2 workers × 30) leaves 40
# free for backups + manual psql sessions + cron scripts.
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,  # recycle conns every hour to avoid Postgres idle-kill
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
