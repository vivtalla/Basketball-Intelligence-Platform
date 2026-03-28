from sqlalchemy import (
    Column, Date, Index, Integer, String, Float, Boolean, ForeignKey, DateTime, UniqueConstraint
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
    # External import: public metrics (LEBRON, RAPTOR, PIPM)
    lebron = Column(Float)
    raptor = Column(Float)
    pipm = Column(Float)
    # Split BPM components
    obpm = Column(Float)
    dbpm = Column(Float)
    # Secondary box-score metrics
    ftr = Column(Float)      # Free Throw Rate = FTA / FGA
    par3 = Column(Float)     # 3-Point Attempt Rate = FG3A / FGA
    ast_tov = Column(Float)  # Assist-to-Turnover Ratio = AST / TOV
    oreb_pct = Column(Float) # Offensive Rebound % (simplified)

    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    player = relationship("Player", back_populates="season_stats")

    # Play-by-play derived stats (populated by pbp_import.py)
    clutch_pts = Column(Float)
    clutch_fga = Column(Integer)          # clutch field goal attempts (sample size)
    clutch_fg_pct = Column(Float)
    clutch_plus_minus = Column(Float)
    second_chance_pts = Column(Float)
    fast_break_pts = Column(Float)


class GameLog(Base):
    __tablename__ = "game_logs"

    game_id = Column(String(10), primary_key=True)
    season = Column(String(7), nullable=False)
    game_date = Column(Date)
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    home_score = Column(Integer)
    away_score = Column(Integer)

    play_by_play = relationship("PlayByPlay", back_populates="game", cascade="all, delete-orphan")


class PlayByPlay(Base):
    __tablename__ = "play_by_play"
    __table_args__ = (
        UniqueConstraint("game_id", "action_number", name="uq_pbp_game_action"),
        Index("ix_pbp_player_game", "player_id", "game_id"),
        Index("ix_pbp_game_action_type", "game_id", "action_type"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(String(10), ForeignKey("game_logs.game_id"), nullable=False)
    action_number = Column(Integer, nullable=False)
    period = Column(Integer)
    clock = Column(String(20))      # e.g. "PT05M30.00S"
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=True)
    action_type = Column(String(50))   # "2pt", "3pt", "rebound", "substitution", etc.
    sub_type = Column(String(50))      # "missed", "made", "offensive", "defensive", etc.
    description = Column(String(500))
    score_home = Column(Integer)
    score_away = Column(Integer)

    game = relationship("GameLog", back_populates="play_by_play")


class PlayerOnOff(Base):
    __tablename__ = "player_on_off"
    __table_args__ = (
        UniqueConstraint("player_id", "season", "is_playoff", name="uq_on_off_player_season"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    season = Column(String(7), nullable=False)
    is_playoff = Column(Boolean, default=False)
    on_minutes = Column(Float)
    off_minutes = Column(Float)
    on_net_rating = Column(Float)
    off_net_rating = Column(Float)
    on_off_net = Column(Float)   # on_net_rating - off_net_rating
    on_ortg = Column(Float)
    on_drtg = Column(Float)
    off_ortg = Column(Float)
    off_drtg = Column(Float)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    player = relationship("Player")


class PlayerGameLog(Base):
    __tablename__ = "player_game_logs"
    __table_args__ = (
        UniqueConstraint("player_id", "game_id", "season_type", name="uq_player_game_log"),
    )

    id          = Column(Integer, primary_key=True, autoincrement=True)
    player_id   = Column(Integer, ForeignKey("players.id"), nullable=False, index=True)
    game_id     = Column(String(20), nullable=False)
    season      = Column(String(7), nullable=False)
    season_type = Column(String(30), nullable=False, default="Regular Season")
    game_date   = Column(Date, nullable=True)
    matchup     = Column(String(30), nullable=True)
    wl          = Column(String(1), nullable=True)
    min         = Column(Float, nullable=True)
    pts         = Column(Integer, nullable=True)
    reb         = Column(Integer, nullable=True)
    ast         = Column(Integer, nullable=True)
    stl         = Column(Integer, nullable=True)
    blk         = Column(Integer, nullable=True)
    tov         = Column(Integer, nullable=True)
    fgm         = Column(Integer, nullable=True)
    fga         = Column(Integer, nullable=True)
    fg_pct      = Column(Float, nullable=True)
    fg3m        = Column(Integer, nullable=True)
    fg3a        = Column(Integer, nullable=True)
    fg3_pct     = Column(Float, nullable=True)
    ftm         = Column(Integer, nullable=True)
    fta         = Column(Integer, nullable=True)
    ft_pct      = Column(Float, nullable=True)
    oreb        = Column(Integer, nullable=True)
    dreb        = Column(Integer, nullable=True)
    pf          = Column(Integer, nullable=True)
    plus_minus  = Column(Integer, nullable=True)
    synced_at   = Column(DateTime, server_default=func.now())

    player = relationship("Player")


class LineupStats(Base):
    __tablename__ = "lineup_stats"
    __table_args__ = (
        UniqueConstraint("lineup_key", "season", name="uq_lineup_season"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    lineup_key = Column(String(200), nullable=False)  # sorted player IDs joined by "-"
    season = Column(String(7), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    minutes = Column(Float)
    net_rating = Column(Float)
    ortg = Column(Float)
    drtg = Column(Float)
    plus_minus = Column(Float)
    possessions = Column(Integer)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class SyncStatus(Base):
    __tablename__ = "sync_status"
    __table_args__ = (
        UniqueConstraint("sync_type", "season", name="uq_sync_type_season"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    sync_type = Column(String(50), nullable=False)   # "players", "game_logs", "pbp"
    season = Column(String(10), nullable=False)
    status = Column(String(20), nullable=False, default="pending")  # pending, running, complete, failed
    records_synced = Column(Integer, default=0)
    total_records = Column(Integer)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(String(500))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
