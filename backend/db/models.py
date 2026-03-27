from sqlalchemy import (
    Column, Integer, String, Float, Boolean, ForeignKey, DateTime, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from db.database import Base


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True)  # NBA team ID
    abbreviation = Column(String(10), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    city = Column(String(100))
    conference = Column(String(10))
    division = Column(String(20))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    players = relationship("Player", back_populates="team")


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True)  # NBA player ID
    full_name = Column(String(100), nullable=False)
    first_name = Column(String(50))
    last_name = Column(String(50))
    is_active = Column(Boolean, default=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    jersey = Column(String(10))
    position = Column(String(20))
    height = Column(String(10))
    weight = Column(String(10))
    birth_date = Column(String(30))
    country = Column(String(50))
    school = Column(String(100))
    draft_year = Column(String(10))
    draft_round = Column(String(10))
    draft_number = Column(String(10))
    from_year = Column(Integer)
    to_year = Column(Integer)
    headshot_url = Column(String(255))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    team = relationship("Team", back_populates="players")
    season_stats = relationship("SeasonStat", back_populates="player", cascade="all, delete-orphan")


class SeasonStat(Base):
    __tablename__ = "season_stats"
    __table_args__ = (
        UniqueConstraint("player_id", "season", "team_abbreviation", "is_playoff",
                         name="uq_player_season_team_playoff"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    season = Column(String(10), nullable=False)  # e.g. "2024-25"
    team_abbreviation = Column(String(10), nullable=False)
    is_playoff = Column(Boolean, default=False)

    # Traditional stats
    gp = Column(Integer, default=0)
    gs = Column(Integer, default=0)
    min_total = Column(Float, default=0)
    min_pg = Column(Float, default=0)
    pts = Column(Integer, default=0)
    pts_pg = Column(Float, default=0)
    reb = Column(Integer, default=0)
    reb_pg = Column(Float, default=0)
    ast = Column(Integer, default=0)
    ast_pg = Column(Float, default=0)
    stl = Column(Integer, default=0)
    stl_pg = Column(Float, default=0)
    blk = Column(Integer, default=0)
    blk_pg = Column(Float, default=0)
    tov = Column(Integer, default=0)
    tov_pg = Column(Float, default=0)
    fgm = Column(Integer, default=0)
    fga = Column(Integer, default=0)
    fg_pct = Column(Float, default=0)
    fg3m = Column(Integer, default=0)
    fg3a = Column(Integer, default=0)
    fg3_pct = Column(Float, default=0)
    ftm = Column(Integer, default=0)
    fta = Column(Integer, default=0)
    ft_pct = Column(Float, default=0)
    oreb = Column(Integer, default=0)
    dreb = Column(Integer, default=0)
    pf = Column(Integer, default=0)

    # Advanced metrics
    ts_pct = Column(Float)
    efg_pct = Column(Float)
    usg_pct = Column(Float)
    per = Column(Float)
    bpm = Column(Float)
    off_rating = Column(Float)
    def_rating = Column(Float)
    net_rating = Column(Float)
    ws = Column(Float)
    vorp = Column(Float)
    pie = Column(Float)
    pace = Column(Float)
    darko = Column(Float)
    epm = Column(Float)
    rapm = Column(Float)

    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    player = relationship("Player", back_populates="season_stats")
