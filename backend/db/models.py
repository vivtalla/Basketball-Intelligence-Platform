from sqlalchemy import (
    Column, Date, Index, Integer, String, Float, Boolean, ForeignKey, DateTime, UniqueConstraint, JSON, Text
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
    name_aliases = relationship("PlayerNameAlias", back_populates="player", cascade="all, delete-orphan")


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


class SourceRun(Base):
    __tablename__ = "source_runs"
    __table_args__ = (
        Index("ix_source_runs_status_started", "status", "started_at"),
        Index("ix_source_runs_entity", "entity_type", "entity_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), nullable=False)
    job_type = Column(String(50), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(64), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    attempt_count = Column(Integer, nullable=False, default=1)
    records_written = Column(Integer, nullable=False, default=0)
    error_message = Column(String(1000))
    run_metadata = Column(JSON)
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime)


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"
    __table_args__ = (
        UniqueConstraint("job_type", "job_key", name="uq_ingestion_job_type_key"),
        Index("ix_ingestion_jobs_status_run_after", "status", "run_after"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_type = Column(String(50), nullable=False)
    job_key = Column(String(100), nullable=False)
    season = Column(String(10))
    game_id = Column(String(20))
    priority = Column(Integer, nullable=False, default=100)
    status = Column(String(20), nullable=False, default="queued")
    payload = Column(JSON)
    run_after = Column(DateTime, server_default=func.now())
    leased_until = Column(DateTime)
    attempt_count = Column(Integer, nullable=False, default=0)
    last_error = Column(String(1000))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime)


class ApiRequestState(Base):
    __tablename__ = "api_request_state"
    __table_args__ = (
        Index("ix_api_request_state_updated", "updated_at"),
    )

    source = Column(String(50), primary_key=True)
    available_at = Column(DateTime, nullable=False, server_default=func.now())
    last_request_at = Column(DateTime)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class RawSchedulePayload(Base):
    __tablename__ = "raw_schedule_payloads"
    __table_args__ = (
        UniqueConstraint("source", "season", "date_key", "content_hash", name="uq_raw_schedule_payload"),
        Index("ix_raw_schedule_payloads_season", "season"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), nullable=False)
    season = Column(String(10), nullable=False)
    date_key = Column(String(20), nullable=False, default="season")
    content_hash = Column(String(64), nullable=False)
    payload = Column(JSON, nullable=False)
    fetched_at = Column(DateTime, server_default=func.now())


class WarehouseGame(Base):
    __tablename__ = "games"
    __table_args__ = (
        Index("ix_games_season_date", "season", "game_date"),
        Index("ix_games_status_flags", "season", "has_final_box_score", "has_parsed_pbp"),
    )

    game_id = Column(String(20), primary_key=True)
    season = Column(String(10), nullable=False, index=True)
    game_date = Column(Date)
    status = Column(String(20), nullable=False, default="scheduled")
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    home_team_abbreviation = Column(String(10))
    away_team_abbreviation = Column(String(10))
    home_team_name = Column(String(100))
    away_team_name = Column(String(100))
    home_score = Column(Integer)
    away_score = Column(Integer)
    source = Column(String(50))
    schedule_source = Column(String(50))
    box_score_source = Column(String(50))
    pbp_source = Column(String(50))
    has_schedule = Column(Boolean, nullable=False, default=False)
    has_final_box_score = Column(Boolean, nullable=False, default=False)
    has_pbp_payload = Column(Boolean, nullable=False, default=False)
    has_parsed_pbp = Column(Boolean, nullable=False, default=False)
    has_materialized_game_stats = Column(Boolean, nullable=False, default=False)
    has_materialized_season = Column(Boolean, nullable=False, default=False)
    pbp_parse_status = Column(String(20), nullable=False, default="missing")
    last_schedule_sync_at = Column(DateTime)
    last_box_score_sync_at = Column(DateTime)
    last_pbp_sync_at = Column(DateTime)
    last_materialized_at = Column(DateTime)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class RawGamePayload(Base):
    __tablename__ = "raw_game_payloads"
    __table_args__ = (
        UniqueConstraint("game_id", "source", "payload_type", "content_hash", name="uq_raw_game_payload"),
        Index("ix_raw_game_payloads_game_type", "game_id", "payload_type"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(String(20), nullable=False, index=True)
    season = Column(String(10))
    source = Column(String(50), nullable=False)
    payload_type = Column(String(30), nullable=False)
    content_hash = Column(String(64), nullable=False)
    payload = Column(JSON, nullable=False)
    fetched_at = Column(DateTime, server_default=func.now())


class GameTeamStat(Base):
    __tablename__ = "game_team_stats"
    __table_args__ = (
        UniqueConstraint("game_id", "team_id", name="uq_game_team_stats"),
        Index("ix_game_team_stats_team_season", "team_id", "season"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(String(20), ForeignKey("games.game_id"), nullable=False)
    season = Column(String(10), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    team_abbreviation = Column(String(10))
    is_home = Column(Boolean, nullable=False, default=False)
    won = Column(Boolean)
    pts = Column(Integer, default=0)
    reb = Column(Integer, default=0)
    ast = Column(Integer, default=0)
    stl = Column(Integer, default=0)
    blk = Column(Integer, default=0)
    tov = Column(Integer, default=0)
    fgm = Column(Integer, default=0)
    fga = Column(Integer, default=0)
    fg3m = Column(Integer, default=0)
    fg3a = Column(Integer, default=0)
    ftm = Column(Integer, default=0)
    fta = Column(Integer, default=0)
    oreb = Column(Integer, default=0)
    dreb = Column(Integer, default=0)
    pf = Column(Integer, default=0)
    minutes = Column(Float)
    plus_minus = Column(Float)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class GamePlayerStat(Base):
    __tablename__ = "game_player_stats"
    __table_args__ = (
        UniqueConstraint("game_id", "player_id", name="uq_game_player_stats"),
        Index("ix_game_player_stats_player_season", "player_id", "season"),
        Index("ix_game_player_stats_team_season", "team_id", "season"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(String(20), ForeignKey("games.game_id"), nullable=False)
    season = Column(String(10), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    team_abbreviation = Column(String(10))
    game_date = Column(Date)
    matchup = Column(String(30))
    wl = Column(String(1))
    min = Column(Float)
    pts = Column(Integer, default=0)
    reb = Column(Integer, default=0)
    ast = Column(Integer, default=0)
    stl = Column(Integer, default=0)
    blk = Column(Integer, default=0)
    tov = Column(Integer, default=0)
    fgm = Column(Integer, default=0)
    fga = Column(Integer, default=0)
    fg_pct = Column(Float)
    fg3m = Column(Integer, default=0)
    fg3a = Column(Integer, default=0)
    fg3_pct = Column(Float)
    ftm = Column(Integer, default=0)
    fta = Column(Integer, default=0)
    ft_pct = Column(Float)
    oreb = Column(Integer, default=0)
    dreb = Column(Integer, default=0)
    pf = Column(Integer, default=0)
    plus_minus = Column(Float)
    is_starter = Column(Boolean, nullable=False, default=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class PlayByPlayEvent(Base):
    __tablename__ = "play_by_play_events"
    __table_args__ = (
        UniqueConstraint("game_id", "order_index", name="uq_pbp_event_order"),
        Index("ix_pbp_events_game_player", "game_id", "player_id"),
        Index("ix_pbp_events_team_type", "team_id", "action_type"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(String(20), ForeignKey("games.game_id"), nullable=False)
    season = Column(String(10), nullable=False)
    source_event_id = Column(String(50))
    action_number = Column(Integer)
    order_index = Column(Integer, nullable=False)
    period = Column(Integer)
    clock = Column(String(20))
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=True)
    action_type = Column(String(50))
    action_family = Column(String(50))
    sub_type = Column(String(50))
    description = Column(String(500))
    score_home = Column(Integer)
    score_away = Column(Integer)
    raw_event = Column(JSON)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ---------------------------------------------------------------------------
# Sprint 26 — Data Foundation Models
# ---------------------------------------------------------------------------

class PlayerInjury(Base):
    """Current and historical injury status per player, sourced from NBA CDN."""
    __tablename__ = "player_injuries"
    __table_args__ = (
        UniqueConstraint("player_id", "report_date", name="uq_player_injury_date"),
        Index("ix_player_injuries_player", "player_id"),
        Index("ix_player_injuries_date", "report_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    report_date = Column(Date, nullable=False)      # date the CDN report was fetched
    return_date = Column(Date, nullable=True)        # estimated return, if provided
    injury_type = Column(String(100))                # "Lower Leg", "Hamstring", etc.
    injury_status = Column(String(50))               # "Out", "Questionable", "Doubtful", "GTD", "Day-To-Day"
    detail = Column(String(200))                     # "Left Hamstring Soreness"
    comment = Column(Text)
    season = Column(String(10))
    source = Column(String(100), default="cdn.nba.com/injuries")
    fetched_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    player = relationship("Player")


class PlayerNameAlias(Base):
    __tablename__ = "player_name_aliases"
    __table_args__ = (
        UniqueConstraint("player_id", "alias_normalized", name="uq_player_alias_normalized"),
        Index("ix_player_alias_normalized", "alias_normalized"),
        Index("ix_player_alias_player", "player_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    alias_normalized = Column(String(150), nullable=False)
    alias_display = Column(String(150), nullable=False)
    source = Column(String(100), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    player = relationship("Player", back_populates="name_aliases")


class InjurySyncUnresolved(Base):
    __tablename__ = "injury_sync_unresolved"
    __table_args__ = (
        UniqueConstraint(
            "season",
            "report_date",
            "team_abbreviation",
            "player_name",
            "injury_status",
            "detail",
            name="uq_injury_sync_unresolved_entry",
        ),
        Index("ix_injury_sync_unresolved_report", "season", "report_date"),
        Index("ix_injury_sync_unresolved_lookup", "normalized_lookup_key"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    season = Column(String(10), nullable=False, default="")
    report_date = Column(Date, nullable=False)
    team_abbreviation = Column(String(10), nullable=False, default="")
    team_name = Column(String(100), nullable=False, default="")
    player_name = Column(String(100), nullable=False, default="")
    injury_status = Column(String(50), nullable=False, default="")
    injury_type = Column(String(100), nullable=False, default="")
    detail = Column(String(200), nullable=False, default="")
    source = Column(String(100), nullable=False, default="")
    source_url = Column(String(255))
    normalized_lookup_key = Column(String(200), nullable=False, default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class PlayerShotChart(Base):
    """Persisted shot chart data per player/season. Eliminates live API calls on every page load."""
    __tablename__ = "player_shot_charts"
    __table_args__ = (
        UniqueConstraint("player_id", "season", "season_type", name="uq_shot_chart_player_season"),
        Index("ix_shot_charts_player", "player_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    season = Column(String(10), nullable=False)
    season_type = Column(String(30), nullable=False, default="Regular Season")
    shots = Column(JSON, nullable=False)             # array of shot objects from nba_api
    shot_count = Column(Integer, default=0)
    fetched_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=False)    # TTL: 6h current season, 30d historical

    player = relationship("Player")


class TeamStanding(Base):
    """Materialized standings per team per season. Replaces per-request computation from player_game_logs."""
    __tablename__ = "team_standings"
    __table_args__ = (
        UniqueConstraint("team_id", "season", name="uq_team_standing_season"),
        Index("ix_team_standings_season", "season"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    season = Column(String(10), nullable=False)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    home_wins = Column(Integer, default=0)
    home_losses = Column(Integer, default=0)
    road_wins = Column(Integer, default=0)
    road_losses = Column(Integer, default=0)
    last_10_wins = Column(Integer, default=0)
    last_10_losses = Column(Integer, default=0)
    current_streak = Column(Integer, default=0)      # positive = win streak, negative = loss streak
    streak_type = Column(String(1))                  # "W" or "L"
    conference = Column(String(10))
    division = Column(String(20))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    team = relationship("Team")
