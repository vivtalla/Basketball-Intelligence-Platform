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

    # Sprint 52 — per-metric attribution for external impact metrics.
    # Keys: epm, lebron, raptor, pipm, darko, rapm. Values: {"source": str, "as_of": "YYYY-MM-DD", "note": str}.
    external_metrics_meta = Column(JSON)


class GameLog(Base):
    __tablename__ = "game_logs"
    __table_args__ = (
        Index("ix_game_logs_series_id", "series_id"),
    )

    game_id = Column(String(10), primary_key=True)
    season = Column(String(7), nullable=False)
    game_date = Column(Date)
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    home_score = Column(Integer)
    away_score = Column(Integer)

    # Sprint 73 — playoffs data layer
    season_type = Column(String, nullable=False, default="Regular Season", server_default="Regular Season")
    series_id = Column(String, nullable=True)
    series_game_num = Column(Integer, nullable=True)
    playoff_seed = Column(Integer, nullable=True)

    # Sprint 81: legacy `play_by_play` relationship retired. PlayByPlayEvent
    # is the canonical PBP table. The `games` table (WarehouseGame) is the
    # canonical parent for play_by_play_events; `game_logs` carries no PBP rows.


# Sprint 81: legacy `PlayByPlay` model removed. Use `PlayByPlayEvent` instead.


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
        UniqueConstraint(
            "lineup_key", "season", "is_playoff", name="uq_lineup_season_playoff"
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    lineup_key = Column(String(200), nullable=False)  # sorted player IDs joined by "-"
    season = Column(String(7), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    is_playoff = Column(Boolean, nullable=False, default=False)
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
        Index("ix_games_series_id", "series_id"),
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

    # Sprint 73 — playoffs data layer
    season_type = Column(String, nullable=False, default="Regular Season", server_default="Regular Season")
    series_id = Column(String, nullable=True)
    series_game_num = Column(Integer, nullable=True)
    playoff_seed = Column(Integer, nullable=True)


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


class PlayerAnalysisContext(Base):
    """Manual analyst context that changes interpretation, not raw stat storage."""
    __tablename__ = "player_analysis_contexts"
    __table_args__ = (
        Index("ix_player_analysis_contexts_player_season", "player_id", "season"),
        Index("ix_player_analysis_contexts_dates", "start_date", "end_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    season = Column(String(10), nullable=False)
    context_type = Column(String(40), nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    severity = Column(String(20), nullable=True)
    source = Column(String(40), nullable=False, default="manual")
    note = Column(Text)
    applies_to = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
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
        UniqueConstraint("team_id", "season", "snapshot_date", name="uq_team_standing_season_date"),
        Index("ix_team_standings_season", "season"),
        Index("ix_team_standings_team_season", "team_id", "season"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    season = Column(String(10), nullable=False)
    snapshot_date = Column(Date, nullable=False)
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


class MvpRaceSnapshot(Base):
    """Persisted daily MVP race output for timeline/movement reads."""
    __tablename__ = "mvp_race_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "season",
            "snapshot_date",
            "profile",
            "min_gp",
            name="uq_mvp_race_snapshot_run",
        ),
        Index("ix_mvp_race_snapshots_season_profile_date", "season", "profile", "snapshot_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    season = Column(String(10), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    as_of_date = Column(Date)
    profile = Column(String(40), nullable=False)
    min_gp = Column(Integer, nullable=False, default=20)
    top = Column(Integer, nullable=False, default=15)
    scoring_profile = Column(String(80), nullable=False, default="")
    payload_summary = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    candidates = relationship(
        "MvpRaceSnapshotCandidate",
        back_populates="snapshot",
        cascade="all, delete-orphan",
    )


class MvpRaceSnapshotCandidate(Base):
    __tablename__ = "mvp_race_snapshot_candidates"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "player_id", name="uq_mvp_race_snapshot_candidate"),
        Index("ix_mvp_snapshot_candidates_snapshot_rank", "snapshot_id", "rank"),
        Index("ix_mvp_snapshot_candidates_player", "player_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(Integer, ForeignKey("mvp_race_snapshots.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    player_name = Column(String(100), nullable=False, default="")
    team_abbreviation = Column(String(10), nullable=False, default="")
    rank = Column(Integer, nullable=False)
    composite_score = Column(Float, nullable=False, default=0.0)
    context_adjusted_score = Column(Float)
    momentum = Column(String(20), nullable=False, default="steady")
    eligibility_status = Column(String(20), nullable=False, default="unknown")
    impact_consensus_score = Column(Float)
    clutch_confidence = Column(String(20))
    gravity_score = Column(Float)
    coverage_warning_count = Column(Integer, nullable=False, default=0)
    pillar_scores = Column(JSON)
    case_summary = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    snapshot = relationship("MvpRaceSnapshot", back_populates="candidates")
    player = relationship("Player")


class TeamSeasonStat(Base):
    """Official persisted team season stats from the NBA team dashboard."""
    __tablename__ = "team_season_stats"
    __table_args__ = (
        UniqueConstraint("team_id", "season", "is_playoff", name="uq_team_season_playoff"),
        Index("ix_team_season_stats_season", "season"),
        Index("ix_team_season_stats_team_season", "team_id", "season"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    season = Column(String(10), nullable=False)
    is_playoff = Column(Boolean, nullable=False, default=False)
    source = Column(String(50), nullable=False, default="stats.nba.com/team-dashboard")
    gp = Column(Integer, default=0)
    w = Column(Integer, default=0)
    l = Column(Integer, default=0)
    w_pct = Column(Float, default=0)
    pts_pg = Column(Float)
    ast_pg = Column(Float)
    reb_pg = Column(Float)
    tov_pg = Column(Float)
    blk_pg = Column(Float)
    stl_pg = Column(Float)
    fg_pct = Column(Float)
    fg3_pct = Column(Float)
    ft_pct = Column(Float)
    plus_minus_pg = Column(Float)
    off_rating = Column(Float)
    def_rating = Column(Float)
    net_rating = Column(Float)
    pace = Column(Float)
    efg_pct = Column(Float)
    ts_pct = Column(Float)
    pie = Column(Float)
    oreb_pct = Column(Float)
    dreb_pct = Column(Float)
    tov_pct = Column(Float)
    ast_pct = Column(Float)
    off_rating_rank = Column(Integer)
    def_rating_rank = Column(Integer)
    net_rating_rank = Column(Integer)
    pace_rank = Column(Integer)
    efg_pct_rank = Column(Integer)
    ts_pct_rank = Column(Integer)
    oreb_pct_rank = Column(Integer)
    tov_pct_rank = Column(Integer)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    team = relationship("Team")


class TeamSplitStat(Base):
    """Official persisted team general split stats from the NBA team dashboard."""
    __tablename__ = "team_split_stats"
    __table_args__ = (
        UniqueConstraint(
            "team_id",
            "season",
            "is_playoff",
            "split_family",
            "split_value",
            name="uq_team_split_stat",
        ),
        Index("ix_team_split_stats_season", "season"),
        Index("ix_team_split_stats_team_season", "team_id", "season"),
        Index("ix_team_split_stats_family", "split_family"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    season = Column(String(10), nullable=False)
    is_playoff = Column(Boolean, nullable=False, default=False)
    split_family = Column(String(50), nullable=False)
    split_value = Column(String(80), nullable=False)
    label = Column(String(120), nullable=False)
    source = Column(String(60), nullable=False, default="stats.nba.com/team-general-splits")
    gp = Column(Integer, default=0)
    w = Column(Integer, default=0)
    l = Column(Integer, default=0)
    w_pct = Column(Float, default=0)
    min = Column(Float)
    pts = Column(Float)
    reb = Column(Float)
    ast = Column(Float)
    tov = Column(Float)
    stl = Column(Float)
    blk = Column(Float)
    fg_pct = Column(Float)
    fg3_pct = Column(Float)
    ft_pct = Column(Float)
    plus_minus = Column(Float)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    team = relationship("Team")


# ----------------------------------------------------------------------------
# Sprint 81 — Player split dashboards (LeagueDashPlayerStats split families).
# Mirrors team_split_stats but per-player. Daily sync writes Location, W/L,
# Days Rest, Month, Pre/Post All-Star, Clutch slices.
# ----------------------------------------------------------------------------
class PlayerSplitStat(Base):
    __tablename__ = "player_split_stats"
    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "season",
            "is_playoff",
            "split_family",
            "split_value",
            name="uq_player_split_stat",
        ),
        Index("ix_player_split_stats_player_season", "player_id", "season"),
        Index("ix_player_split_stats_family", "split_family"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    season = Column(String(10), nullable=False)
    is_playoff = Column(Boolean, nullable=False, default=False)
    split_family = Column(String(50), nullable=False)
    split_value = Column(String(80), nullable=False)
    label = Column(String(120), nullable=False)
    source = Column(String(70), nullable=False, default="stats.nba.com/player-general-splits")
    gp = Column(Integer, default=0)
    w = Column(Integer, default=0)
    l = Column(Integer, default=0)
    w_pct = Column(Float, default=0)
    min = Column(Float)
    pts = Column(Float)
    reb = Column(Float)
    ast = Column(Float)
    tov = Column(Float)
    stl = Column(Float)
    blk = Column(Float)
    fg_pct = Column(Float)
    fg3_pct = Column(Float)
    ft_pct = Column(Float)
    ts_pct = Column(Float)
    usg_pct = Column(Float)
    plus_minus = Column(Float)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    player = relationship("Player")
    team = relationship("Team")


# ----------------------------------------------------------------------------
# Sprint 81 — Play type stats. Per-player by archetype: isolation, transition,
# pick-and-roll ball handler/roll man, post-up, spot-up, hand-off, cut,
# off-screen, putback, miscellaneous. Powers scouting and style classification.
# ----------------------------------------------------------------------------
class PlayTypeStat(Base):
    __tablename__ = "play_type_stats"
    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "season",
            "is_playoff",
            "play_type",
            "play_role",
            name="uq_play_type_stat",
        ),
        Index("ix_play_type_stats_player_season", "player_id", "season"),
        Index("ix_play_type_stats_play_type", "play_type"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    season = Column(String(10), nullable=False)
    is_playoff = Column(Boolean, nullable=False, default=False)
    play_type = Column(String(40), nullable=False)
    # play_role distinguishes Pick-and-Roll Ball Handler vs Roll Man, etc.
    # Single-role play types (Isolation, Transition) just store "primary".
    play_role = Column(String(40), nullable=False, default="primary")
    source = Column(String(70), nullable=False, default="stats.nba.com/playtype")
    gp = Column(Integer, default=0)
    poss = Column(Integer, default=0)
    poss_pct = Column(Float)        # share of player's total possessions
    pts = Column(Float)
    fgm = Column(Float)
    fga = Column(Float)
    fg_pct = Column(Float)
    efg_pct = Column(Float)
    ts_pct = Column(Float)
    ftm = Column(Float)
    fta = Column(Float)
    ft_pct = Column(Float)
    ppp = Column(Float)             # points per possession
    percentile = Column(Float)      # league percentile rank
    score_freq_pct = Column(Float)  # % of possessions ending in score
    sf_freq_pct = Column(Float)     # % drawing shooting fouls
    tov_freq_pct = Column(Float)    # turnover rate
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    player = relationship("Player")
    team = relationship("Team")


class TeamShootingSplitStat(Base):
    """Official persisted team shooting split stats from the NBA team dashboard."""
    __tablename__ = "team_shooting_split_stats"
    __table_args__ = (
        UniqueConstraint(
            "team_id",
            "season",
            "is_playoff",
            "split_family",
            "split_value",
            name="uq_team_shooting_split_stat",
        ),
        Index("ix_team_shooting_split_stats_season", "season"),
        Index("ix_team_shooting_split_stats_team_season", "team_id", "season"),
        Index("ix_team_shooting_split_stats_family", "split_family"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    season = Column(String(10), nullable=False)
    is_playoff = Column(Boolean, nullable=False, default=False)
    split_family = Column(String(60), nullable=False)
    split_value = Column(String(120), nullable=False)
    label = Column(String(120), nullable=False)
    source = Column(String(70), nullable=False, default="stats.nba.com/team-shooting-splits")
    fgm = Column(Float)
    fga = Column(Float)
    fg_pct = Column(Float)
    fg3m = Column(Float)
    fg3a = Column(Float)
    fg3_pct = Column(Float)
    efg_pct = Column(Float)
    blka = Column(Float)
    pct_ast_2pm = Column(Float)
    pct_uast_2pm = Column(Float)
    pct_ast_3pm = Column(Float)
    pct_uast_3pm = Column(Float)
    pct_ast_fgm = Column(Float)
    pct_uast_fgm = Column(Float)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    team = relationship("Team")


class PlayerPlayTypeStat(Base):
    """Persisted official/player play-type rows for DB-first style and gravity reads."""
    __tablename__ = "player_play_type_stats"
    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "season",
            "season_type",
            "play_type",
            "type_grouping",
            "source",
            name="uq_player_play_type_stat",
        ),
        Index("ix_player_play_type_stats_season", "season"),
        Index("ix_player_play_type_stats_player_season", "player_id", "season"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    season = Column(String(10), nullable=False)
    season_type = Column(String(30), nullable=False, default="Regular Season")
    source = Column(String(80), nullable=False, default="stats.nba.com/synergy-play-types")
    play_type = Column(String(80), nullable=False)
    type_grouping = Column(String(80), nullable=False, default="offensive")
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    team_abbreviation = Column(String(10))
    gp = Column(Integer, default=0)
    possessions = Column(Float)
    poss_pct = Column(Float)
    points = Column(Float)
    ppp = Column(Float)
    percentile = Column(Float)
    fg_pct = Column(Float)
    efg_pct = Column(Float)
    tov_poss_pct = Column(Float)
    score_poss_pct = Column(Float)
    raw_payload = Column(JSON)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    player = relationship("Player")


class PlayerTrackingStat(Base):
    """Persisted player tracking dashboard rows normalized by family/split."""
    __tablename__ = "player_tracking_stats"
    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "season",
            "season_type",
            "tracking_family",
            "split_key",
            "source",
            name="uq_player_tracking_stat",
        ),
        Index("ix_player_tracking_stats_season", "season"),
        Index("ix_player_tracking_stats_player_season", "player_id", "season"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    season = Column(String(10), nullable=False)
    season_type = Column(String(30), nullable=False, default="Regular Season")
    source = Column(String(80), nullable=False, default="stats.nba.com/player-tracking")
    tracking_family = Column(String(50), nullable=False)
    split_key = Column(String(80), nullable=False, default="overall")
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    team_abbreviation = Column(String(10))
    gp = Column(Integer, default=0)
    minutes = Column(Float)
    touches = Column(Float)
    front_court_touches = Column(Float)
    time_of_possession = Column(Float)
    drives = Column(Float)
    passes_made = Column(Float)
    passes_received = Column(Float)
    catch_shoot_fga = Column(Float)
    catch_shoot_pts = Column(Float)
    pull_up_fga = Column(Float)
    pull_up_pts = Column(Float)
    paint_touch_pts = Column(Float)
    close_touch_pts = Column(Float)
    raw_payload = Column(JSON)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    player = relationship("Player")


class PlayerHustleStat(Base):
    """Persisted official hustle rows for screen/attention and non-box-score context."""
    __tablename__ = "player_hustle_stats"
    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "season",
            "season_type",
            "source",
            name="uq_player_hustle_stat",
        ),
        Index("ix_player_hustle_stats_season", "season"),
        Index("ix_player_hustle_stats_player_season", "player_id", "season"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    season = Column(String(10), nullable=False)
    season_type = Column(String(30), nullable=False, default="Regular Season")
    source = Column(String(80), nullable=False, default="stats.nba.com/league-hustle")
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    team_abbreviation = Column(String(10))
    gp = Column(Integer, default=0)
    minutes = Column(Float)
    contested_shots = Column(Float)
    deflections = Column(Float)
    charges_drawn = Column(Float)
    screen_assists = Column(Float)
    screen_assist_points = Column(Float)
    loose_balls_recovered = Column(Float)
    box_outs = Column(Float)
    raw_payload = Column(JSON)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    player = relationship("Player")


class PlayerGravityStat(Base):
    """Official or CourtVue-derived player gravity profile."""
    __tablename__ = "player_gravity_stats"
    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "season",
            "season_type",
            "source",
            name="uq_player_gravity_stat",
        ),
        Index("ix_player_gravity_stats_season", "season"),
        Index("ix_player_gravity_stats_player_season", "player_id", "season"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    season = Column(String(10), nullable=False)
    season_type = Column(String(30), nullable=False, default="Regular Season")
    source = Column(String(80), nullable=False, default="courtvue_proxy")
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    team_abbreviation = Column(String(10))
    gravity_minutes = Column(Float)
    overall_gravity = Column(Float)
    shooting_gravity = Column(Float)
    rim_gravity = Column(Float)
    creation_gravity = Column(Float)
    roll_or_screen_gravity = Column(Float)
    off_ball_gravity = Column(Float)
    spacing_lift = Column(Float)
    on_ball_perimeter_gravity = Column(Float)
    off_ball_perimeter_gravity = Column(Float)
    on_ball_interior_gravity = Column(Float)
    off_ball_interior_gravity = Column(Float)
    gravity_confidence = Column(String(20), nullable=False, default="low")
    source_note = Column(String(500))
    warnings = Column(JSON)
    raw_payload = Column(JSON)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    player = relationship("Player")


class PlayerClutchStat(Base):
    """League-dashboard clutch signals (last 5 min, margin ≤ 5). Sprint 52."""
    __tablename__ = "player_clutch_stats"
    __table_args__ = (
        UniqueConstraint(
            "player_id", "season", "season_type", "source",
            name="uq_player_clutch_stat",
        ),
        Index("ix_player_clutch_stats_season", "season"),
        Index("ix_player_clutch_stats_player_season", "player_id", "season"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    season = Column(String(10), nullable=False)
    season_type = Column(String(30), nullable=False, default="Regular Season")
    source = Column(String(80), nullable=False, default="stats.nba.com/leaguedashplayerclutch")
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    team_abbreviation = Column(String(10))
    clutch_games = Column(Integer)
    clutch_minutes = Column(Float)
    clutch_possessions = Column(Float)
    clutch_pts = Column(Float)
    clutch_fgm = Column(Float)
    clutch_fga = Column(Float)
    clutch_fg_pct = Column(Float)
    clutch_fg3m = Column(Float)
    clutch_fg3a = Column(Float)
    clutch_ts_pct = Column(Float)
    clutch_efg_pct = Column(Float)
    clutch_ast = Column(Float)
    clutch_tov = Column(Float)
    clutch_ast_to = Column(Float)
    clutch_usg_pct = Column(Float)
    clutch_plus_minus = Column(Float)
    clutch_net_rating = Column(Float)
    clutch_on_off = Column(Float)
    close_game_wins = Column(Integer)
    close_game_losses = Column(Integer)
    confidence = Column(String(20), nullable=False, default="low")
    raw_payload = Column(JSON)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    player = relationship("Player")


class PlayerOpponentSplit(Base):
    """Opponent-bucketed production for opponent-adjusted scoring. Sprint 52.

    `opponent_bucket` is one of: top10_def, mid_def, bottom_def (by opponent DRtg tier).
    """
    __tablename__ = "player_opponent_splits"
    __table_args__ = (
        UniqueConstraint(
            "player_id", "season", "season_type", "opponent_bucket",
            name="uq_player_opponent_split",
        ),
        Index("ix_player_opponent_splits_season", "season"),
        Index("ix_player_opponent_splits_player_season", "player_id", "season"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    season = Column(String(10), nullable=False)
    season_type = Column(String(30), nullable=False, default="Regular Season")
    opponent_bucket = Column(String(30), nullable=False)
    bucket_label = Column(String(80))
    games = Column(Integer)
    minutes = Column(Float)
    pts_per_game = Column(Float)
    reb_per_game = Column(Float)
    ast_per_game = Column(Float)
    ts_pct = Column(Float)
    efg_pct = Column(Float)
    plus_minus = Column(Float)
    confidence = Column(String(20), nullable=False, default="low")
    raw_payload = Column(JSON)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    player = relationship("Player")


class PreReadSnapshot(Base):
    __tablename__ = "pre_read_snapshots"
    __table_args__ = (
        UniqueConstraint("snapshot_id", name="uq_pre_read_snapshot_id"),
        Index("ix_pre_read_snapshots_matchup", "team_abbreviation", "opponent_abbreviation", "season"),
        Index("ix_pre_read_snapshots_created", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(String(36), nullable=False)
    team_abbreviation = Column(String(10), nullable=False)
    opponent_abbreviation = Column(String(10), nullable=False)
    season = Column(String(10), nullable=False)
    game_id = Column(String(20))
    saved_from = Column(String(50))
    title = Column(String(160))
    note = Column(Text)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ShotLabSnapshot(Base):
    __tablename__ = "shot_lab_snapshots"
    __table_args__ = (
        UniqueConstraint("snapshot_id", name="uq_shot_lab_snapshot_id"),
        Index("ix_shot_lab_snapshots_subject", "subject_kind", "subject_id", "season"),
        Index("ix_shot_lab_snapshots_created", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(String(36), nullable=False)
    snapshot_type = Column(String(30), nullable=False)
    subject_kind = Column(String(30), nullable=False)
    subject_id = Column(String(50), nullable=False)
    season = Column(String(10), nullable=False)
    season_type = Column(String(30), nullable=False, default="Regular Season")
    route_path = Column(String(255), nullable=False, default="/compare")
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ShotQualityBaseline(Base):
    __tablename__ = "shot_quality_baselines"
    __table_args__ = (
        UniqueConstraint(
            "season",
            "season_type",
            "methodology_version",
            name="uq_shot_quality_baseline_key",
        ),
        Index(
            "ix_shot_quality_baselines_lookup",
            "season",
            "season_type",
            "methodology_version",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    season = Column(String(10), nullable=False)
    season_type = Column(String(30), nullable=False, default="Regular Season")
    methodology_version = Column(String(40), nullable=False, default="shot_quality_v1")
    sample_n = Column(Integer, nullable=False, default=0)
    payload = Column(JSON, nullable=False)
    computed_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime, server_default=func.now())


# ---------------------------------------------------------------------------
# Sprint 73 — Playoffs Data Layer
# ---------------------------------------------------------------------------

class PlayoffSeries(Base):
    """A single playoff series between two teams (best-of-7 within a bracket round)."""
    __tablename__ = "playoff_series"
    __table_args__ = (
        UniqueConstraint("season", "series_id", name="uq_playoff_series_season_series"),
        Index("ix_playoff_series_season", "season"),
        Index("ix_playoff_series_round", "round"),
        Index("ix_playoff_series_status", "status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    season = Column(String, nullable=False)
    # Bracket round: 1=first round, 2=conference semis, 3=conference finals, 4=NBA Finals
    round = Column(Integer, nullable=False)
    series_id = Column(String, nullable=False)  # e.g. "2025-26-W-R1-OKC-MIN"
    # Sprint 85 — both team pointers are nullable so a Round-(N+1) row can be
    # stood up the moment one parent closes (one seed populated, the other
    # waiting). Existing Round-1 rows always have both populated; auto-advance
    # is the only path that intentionally leaves one side null.
    top_seed_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    bottom_seed_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    top_seed = Column(Integer, nullable=True)      # 1..16; null until matched
    bottom_seed = Column(Integer, nullable=True)
    top_wins = Column(Integer, nullable=False, default=0)
    bottom_wins = Column(Integer, nullable=False, default=0)
    status = Column(String, nullable=False)        # "scheduled", "active", "closed"
    winner_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    # Sprint 85 — Bracket auto-advancement.
    # When this row is a Round-(N+1) slot waiting on its parents, these point
    # to the upstream series whose winner fills the top/bottom seat. Null for
    # Round 1 series (no parents) and for any pre-Sprint-85 rows.
    parent_top_series_id = Column(String(80), nullable=True, index=True)
    parent_bottom_series_id = Column(String(80), nullable=True, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ---------------------------------------------------------------------------
# Sprint 78 — Phase 0 schema kickoff
# ---------------------------------------------------------------------------
# These tables back the 10 Sprint 78 feature teams. Schemas land here ahead of
# the team architects so all 10 can spec their services against stable types.
# Additive only: nothing in this block should reorder or modify pre-existing
# columns above.
# ---------------------------------------------------------------------------


class PlayerContract(Base):
    """Active player contract (per season). Backs FO1 Trade Machine + FO2 Free
    Agency Workspace + FO4 Multi-Year Team Trajectory.

    Sourced from Spotrac (primary) with HoopsHype fallback. Refresh cadence is
    daily via `daily_sync.sh`. One row per (player, season). For multi-year
    deals, additional rows exist for future seasons with `years_remaining`
    decremented.
    """
    __tablename__ = "player_contracts"
    __table_args__ = (
        UniqueConstraint("player_id", "season", name="uq_player_contract_player_season"),
        Index("ix_player_contracts_player", "player_id"),
        Index("ix_player_contracts_season", "season"),
        Index("ix_player_contracts_team", "team_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)  # nullable for FAs
    season = Column(String(10), nullable=False)        # e.g. "2025-26"
    salary = Column(Integer, nullable=False)           # USD, integer dollars
    years_remaining = Column(Integer, default=1)       # at start of `season`
    is_player_option = Column(Boolean, default=False)
    is_team_option = Column(Boolean, default=False)
    is_non_guaranteed = Column(Boolean, default=False)
    no_trade_clause = Column(Boolean, default=False)
    contract_type = Column(String(20))                 # "standard", "two-way", "rookie", "max", "supermax", "veteran-min"
    signed_on = Column(Date, nullable=True)
    expires_on = Column(Date, nullable=True)
    source = Column(String(40), default="spotrac")     # "spotrac" | "hoopshype" | "manual"
    source_url = Column(Text)
    last_synced_at = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    player = relationship("Player")


class DraftProspect(Base):
    """A single draft-eligible prospect for an upcoming or recent draft.

    Backs FO3 Draft Prospect Workspace. Top ~60 of each draft class — sourced
    from public mock-draft consensus + Sports Reference (NCAA stats) +
    NBA Draft Combine measurements.
    """
    __tablename__ = "draft_prospects"
    __table_args__ = (
        UniqueConstraint("draft_year", "external_id", name="uq_draft_prospect_year_extid"),
        Index("ix_draft_prospects_year", "draft_year"),
        Index("ix_draft_prospects_consensus", "consensus_rank"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String(80), nullable=False)   # stable ID from Sports Reference / source
    full_name = Column(String(120), nullable=False)
    draft_year = Column(Integer, nullable=False)       # e.g. 2026
    age_on_draft_day = Column(Float, nullable=True)
    height_inches = Column(Float, nullable=True)       # listed height
    weight_lbs = Column(Float, nullable=True)          # listed weight
    primary_position = Column(String(10), nullable=True)  # PG, SG, SF, PF, C, F, G
    school = Column(String(120), nullable=True)        # last team (college / G League / international)
    school_type = Column(String(20), nullable=True)    # "ncaa" | "g_league" | "international" | "high_school"
    consensus_rank = Column(Integer, nullable=True)    # avg of major mocks (1..60)
    consensus_sources = Column(JSON)                   # {"espn": 5, "ringer": 7, ...}
    nba_player_id = Column(Integer, ForeignKey("players.id"), nullable=True)  # populated post-draft once linked
    headshot_url = Column(String(300))
    bio = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    stats = relationship("DraftProspectStat", back_populates="prospect", cascade="all, delete-orphan")
    measurements = relationship("DraftProspectMeasurement", back_populates="prospect", cascade="all, delete-orphan")


class DraftProspectStat(Base):
    """Per-season pre-NBA stat line for a prospect (NCAA / G League / international)."""
    __tablename__ = "draft_prospect_stats"
    __table_args__ = (
        UniqueConstraint("prospect_id", "season", "league", name="uq_dp_stat_prospect_season_league"),
        Index("ix_dp_stats_prospect", "prospect_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    prospect_id = Column(Integer, ForeignKey("draft_prospects.id"), nullable=False)
    season = Column(String(10), nullable=False)        # e.g. "2025-26"
    league = Column(String(40), nullable=False)        # "NCAA D-I", "G League Ignite", "Euroleague", etc.
    team_name = Column(String(120))
    gp = Column(Integer)
    min_pg = Column(Float)
    pts_pg = Column(Float)
    reb_pg = Column(Float)
    ast_pg = Column(Float)
    stl_pg = Column(Float)
    blk_pg = Column(Float)
    tov_pg = Column(Float)
    fg_pct = Column(Float)
    fg3_pct = Column(Float)
    ft_pct = Column(Float)
    ts_pct = Column(Float)
    usg_pct = Column(Float)
    pace = Column(Float)            # league pace, used for translation
    # Per-100 normalization is computed in service layer; raw per-game stored here.
    source = Column(String(40), default="sports_reference")
    last_synced_at = Column(DateTime, server_default=func.now())

    prospect = relationship("DraftProspect", back_populates="stats")


class DraftProspectMeasurement(Base):
    """Combine + workout measurements for a draft prospect."""
    __tablename__ = "draft_prospect_measurements"
    __table_args__ = (
        Index("ix_dp_measurements_prospect", "prospect_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    prospect_id = Column(Integer, ForeignKey("draft_prospects.id"), nullable=False)
    height_no_shoes = Column(Float)        # inches
    height_with_shoes = Column(Float)
    weight = Column(Float)                 # lbs
    wingspan = Column(Float)               # inches
    standing_reach = Column(Float)         # inches
    body_fat_pct = Column(Float)
    hand_length = Column(Float)            # inches
    hand_width = Column(Float)             # inches
    standing_vert = Column(Float)          # inches
    max_vert = Column(Float)
    lane_agility_seconds = Column(Float)
    three_quarter_sprint_seconds = Column(Float)
    bench_press_135 = Column(Integer)
    measured_on = Column(Date)
    source = Column(String(40), default="nba_combine")
    created_at = Column(DateTime, server_default=func.now())

    prospect = relationship("DraftProspect", back_populates="measurements")


class DraftPickAsset(Base):
    """A single draft pick owned (or owed) by an NBA team.

    Backs FO4 Multi-Year Team Trajectory. Captures pick swaps, protections,
    conveyance windows. Curated initially; can be replaced by an automated
    feed in a future sprint.
    """
    __tablename__ = "draft_pick_assets"
    __table_args__ = (
        Index("ix_dp_assets_owner", "owner_team_id"),
        Index("ix_dp_assets_year", "draft_year"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    draft_year = Column(Integer, nullable=False)
    round = Column(Integer, nullable=False)            # 1 or 2
    owner_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)  # team that currently owns the pick
    origin_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)  # team whose pick this is (record-of)
    is_swap = Column(Boolean, default=False)
    is_conveyed = Column(Boolean, default=False)       # has it landed yet?
    protection_summary = Column(String(200))           # e.g. "top-4 protected through 2027"
    expected_slot_low = Column(Integer)                # est. range, low end (e.g. 12)
    expected_slot_high = Column(Integer)               # est. range, high end (e.g. 18)
    note = Column(Text)
    source = Column(String(40), default="manual")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class PlayerInjuryHistory(Base):
    """Historical per-injury record for a player. Backs FO5 Injury Duration Model.

    Distinct from `player_injuries` (which is a current-state CDN snapshot).
    Sourced from Pro Sports Transactions historical data, backfilled for the
    last 10+ NBA seasons. One row per discrete injury event with start /
    resolved / games-missed.
    """
    __tablename__ = "player_injury_history"
    __table_args__ = (
        Index("ix_pih_player", "player_id"),
        Index("ix_pih_started", "started_on"),
        Index("ix_pih_body_part", "body_part"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    season = Column(String(10))                        # NBA season the injury happened in
    body_part = Column(String(60))                     # normalized: "knee", "ankle", "hamstring", etc.
    severity = Column(String(20))                      # "minor", "moderate", "severe", "season-ending"
    diagnosis = Column(String(200))                    # raw text from source
    started_on = Column(Date, nullable=False)
    resolved_on = Column(Date)                         # may be null for season-ending
    games_missed = Column(Integer)                     # canonical absence length
    age_at_start = Column(Float)                       # for cohort filtering
    is_recurring = Column(Boolean, default=False)      # same body part as a prior injury
    source = Column(String(40), default="prosportstransactions")
    source_url = Column(Text)
    last_synced_at = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())

    player = relationship("Player")


class PlayerStreak(Base):
    """Cached active streak for a player. Backs CF5 Streaks & Milestones Tracker.

    Computed nightly. One row per (player, streak_type). Snapshot pattern —
    overwritten on each refresh; not a historical streaks log.
    """
    __tablename__ = "player_streaks"
    __table_args__ = (
        UniqueConstraint("player_id", "streak_type", name="uq_player_streak_type"),
        Index("ix_player_streaks_type", "streak_type"),
        Index("ix_player_streaks_length", "length"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    streak_type = Column(String(40), nullable=False)   # "30plus_pts", "double_double", "triple_double", etc.
    length = Column(Integer, nullable=False)           # consecutive games meeting criterion
    started_on = Column(Date)
    last_game_on = Column(Date)
    last_game_id = Column(String(20))
    threshold = Column(JSON)                           # criteria dict, e.g. {"pts_ge": 30}
    is_active = Column(Boolean, default=True)
    season = Column(String(10))
    computed_at = Column(DateTime, server_default=func.now())

    player = relationship("Player")


class MilestoneSnapshot(Base):
    """Cached milestone progress per (player, milestone). Backs CF5.

    Captures both achieved milestones (with date) and approaching milestones
    (with games-to-go). Recomputed nightly; snapshot-style.
    """
    __tablename__ = "milestone_snapshots"
    __table_args__ = (
        UniqueConstraint("player_id", "milestone_key", name="uq_milestone_player_key"),
        Index("ix_milestones_player", "player_id"),
        Index("ix_milestones_key", "milestone_key"),
        Index("ix_milestones_proximity", "games_to_milestone"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    milestone_key = Column(String(40), nullable=False)  # "10k_pts", "1k_3pm", "20k_pts", etc.
    threshold = Column(Integer, nullable=False)         # numerical threshold
    current_value = Column(Float, nullable=False)       # current career total
    games_to_milestone = Column(Integer)                # est. games until reached, null if achieved
    achieved_on = Column(Date, nullable=True)
    achieved_in_game_id = Column(String(20), nullable=True)
    season = Column(String(10))
    is_career_milestone = Column(Boolean, default=True)
    computed_at = Column(DateTime, server_default=func.now())

    player = relationship("Player")


# ----------------------------------------------------------------------------
# Sprint 79 Stream A1 — historical award voting outcomes for mvp_case_v5
# voter calibration. One row per (player, season, award, ballot_position).
# Methodology: specs/methodology-future-modeling.md#1.
# ----------------------------------------------------------------------------
class AwardVote(Base):
    __tablename__ = "award_voting"
    __table_args__ = (
        UniqueConstraint(
            "player_id", "season", "award_type", "ballot_position",
            name="uq_award_voting",
        ),
        Index("ix_award_voting_season_award", "season", "award_type"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    season = Column(String(10), nullable=False)
    award_type = Column(String(10), nullable=False)        # MVP, DPOY, MIP, 6MOY
    ballot_position = Column(Integer, nullable=True)        # NULL = not on ballot
    voter_count = Column(Integer, nullable=False)
    total_award_points = Column(Float, nullable=False)      # published point share
    source = Column(String(40), default="basketball_reference")
    created_at = Column(DateTime, server_default=func.now())

    player = relationship("Player")


# ----------------------------------------------------------------------------
# Sprint 81 — historical Basketball Value + 5-pillar modifier vectors for
# every (player, season) in award_voting. Powers award_calibration_service:
# without these vectors the LOO-CV harness cannot fit calibrated weights, so
# `mvp_case_v5` ships with `calibration_pending=True` until this table is
# populated. Re-runnable via data/materialize_award_modifiers.py.
# ----------------------------------------------------------------------------
class AwardCaseCandidate(Base):
    __tablename__ = "award_case_candidates"
    __table_args__ = (
        UniqueConstraint(
            "player_id", "season", "award_type",
            name="uq_award_case_candidate",
        ),
        Index("ix_award_case_candidates_season", "season"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    season = Column(String(10), nullable=False)
    award_type = Column(String(10), nullable=False, default="MVP")
    basketball_value = Column(Float, nullable=False)
    # Five modifier dimensions in this fixed order:
    # team_framing, eligibility_pressure, clutch, momentum, signature_games.
    modifier_team_framing = Column(Float, nullable=False, default=0.0)
    modifier_eligibility_pressure = Column(Float, nullable=False, default=0.0)
    modifier_clutch = Column(Float, nullable=False, default=0.0)
    modifier_momentum = Column(Float, nullable=False, default=0.0)
    modifier_signature_games = Column(Float, nullable=False, default=0.0)
    last_synced_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    player = relationship("Player")


# ----------------------------------------------------------------------------
# Sprint 79 Stream A2 — role expansion observations for opportunity_v2 uplift.
# Materialized from season_stats nightly via sync_role_expansion.py.
# Methodology: specs/methodology-future-modeling.md#2.
# ----------------------------------------------------------------------------
class RoleExpansionObservation(Base):
    __tablename__ = "role_expansion_observations"
    __table_args__ = (
        UniqueConstraint(
            "player_id", "from_season", "to_season",
            name="uq_role_expansion_pair",
        ),
        Index("ix_role_expansion_archetype", "pre_role_archetype", "pre_ts_pct"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    from_season = Column(String(10), nullable=False)
    to_season = Column(String(10), nullable=False)
    usg_delta = Column(Float, nullable=False)
    pre_ts_pct = Column(Float, nullable=False)
    post_ts_pct = Column(Float, nullable=False)
    ts_delta = Column(Float, nullable=False)
    pre_ast_rate = Column(Float, nullable=True)  # ast per 36 min, derived from ast_pg/min_pg*36
    pre_obpm = Column(Float, nullable=True)
    pre_age = Column(Integer, nullable=True)
    pre_role_archetype = Column(String(40), nullable=True)
    computed_at = Column(DateTime, server_default=func.now())

    player = relationship("Player")
