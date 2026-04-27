"""Sprint 69 — analysis context and injury-aware trend tests."""
from datetime import date, timedelta
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import (  # noqa: E402
    GamePlayerStat,
    Player,
    PlayerAnalysisContext,
    PlayerGameLog,
    PlayerInjury,
    SeasonStat,
    Team,
)
from models.analysis_context import AnalysisContextCreate, AnalysisContextUpdate  # noqa: E402
from services.analysis_context_service import (  # noqa: E402
    create_analysis_context,
    delete_analysis_context,
    list_analysis_contexts,
    update_analysis_context,
)
from services.player_trend_service import build_player_trend_report  # noqa: E402


SEASON = "2025-26"


def make_session():
    engine = create_engine("sqlite:///:memory:")
    TS = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return TS()


def _seed_player(db) -> Player:
    team = Team(id=1610612738, abbreviation="BOS", name="Boston Celtics")
    player = Player(id=1, full_name="Context Player", team=team, team_id=team.id)
    db.add(team)
    db.add(player)
    db.add(
        SeasonStat(
            player_id=1,
            season=SEASON,
            team_abbreviation="BOS",
            is_playoff=False,
            gp=20,
            min_pg=24.0,
            pts_pg=14.0,
            ts_pct=0.56,
            per=14.0,
            bpm=0.0,
        )
    )
    db.commit()
    return player


def _seed_role_drop_games(db, player: Player) -> None:
    base_date = date(2026, 1, 20)
    for index in range(20):
        recent = index < 10
        game_date = base_date - timedelta(days=index)
        minutes = 12.0 if recent else 34.0
        pts = 6 if recent else 21
        game_id = "002260{0:04d}".format(index)
        db.add(
            PlayerGameLog(
                player_id=player.id,
                season=SEASON,
                season_type="Regular Season",
                game_id=game_id,
                game_date=game_date,
                matchup="BOS vs. NYK",
                wl="W",
                min=minutes,
                pts=pts,
                reb=4,
                ast=3,
                fg_pct=0.44,
                fg3_pct=0.34,
                plus_minus=0,
            )
        )
        db.add(
            GamePlayerStat(
                game_id=game_id,
                season=SEASON,
                player_id=player.id,
                team_id=player.team_id,
                team_abbreviation="BOS",
                game_date=game_date,
                matchup="BOS vs. NYK",
                wl="W",
                min=minutes,
                pts=pts,
                reb=4,
                ast=3,
                fg_pct=0.44,
                fg3_pct=0.34,
                plus_minus=0,
                is_starter=not recent,
            )
        )
    db.commit()


def test_auto_injury_contexts_include_recovery_buffer():
    db = make_session()
    try:
        player = _seed_player(db)
        db.add_all(
            [
                PlayerInjury(
                    player_id=player.id,
                    season=SEASON,
                    report_date=date(2026, 1, 5),
                    injury_status="Out",
                    injury_type="Hamstring",
                    detail="Left hamstring strain",
                ),
                PlayerInjury(
                    player_id=player.id,
                    season=SEASON,
                    report_date=date(2026, 1, 9),
                    injury_status="Available",
                    injury_type="Hamstring",
                    detail="Available",
                ),
            ]
        )
        db.commit()

        contexts = list_analysis_contexts(db, player.id, SEASON)
        injury = next(ctx for ctx in contexts if ctx.context_type == "injury")
        recovery = next(ctx for ctx in contexts if ctx.context_type == "recovery")

        assert injury.source == "injury_report_auto"
        assert injury.start_date == date(2026, 1, 5)
        assert injury.end_date == date(2026, 1, 9)
        assert injury.severity == "high"
        assert recovery.start_date == date(2026, 1, 10)
        assert recovery.end_date == date(2026, 1, 16)
    finally:
        db.close()


def test_manual_context_crud_round_trip():
    db = make_session()
    try:
        player = _seed_player(db)
        created = create_analysis_context(
            db,
            player.id,
            AnalysisContextCreate(
                season=SEASON,
                context_type="injury",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 15),
                severity="medium",
                note="Manual injury window",
                applies_to=["trend"],
            ),
        )
        assert created.id is not None
        assert created.source == "manual"

        updated = update_analysis_context(
            db,
            player.id,
            created.id,
            AnalysisContextUpdate(note="Updated note", applies_to=["trend", "team_fit"]),
        )
        assert updated.note == "Updated note"
        assert updated.applies_to == ["trend", "team_fit"]

        delete_analysis_context(db, player.id, created.id)
        assert db.query(PlayerAnalysisContext).count() == 0
    finally:
        db.close()


def test_role_drop_without_context_remains_losing_trust():
    db = make_session()
    try:
        player = _seed_player(db)
        _seed_role_drop_games(db, player)

        report = build_player_trend_report(db, player, SEASON)

        assert report.role_status == "losing_trust"
        assert report.adjusted_role_status is None
        assert report.injury_context is None
    finally:
        db.close()


def test_role_drop_inside_injury_window_gets_injury_context():
    db = make_session()
    try:
        player = _seed_player(db)
        _seed_role_drop_games(db, player)
        db.add(
            PlayerInjury(
                player_id=player.id,
                season=SEASON,
                report_date=date(2026, 1, 12),
                return_date=date(2026, 1, 22),
                injury_status="Out",
                injury_type="Ankle",
                detail="Right ankle sprain",
            )
        )
        db.commit()

        report = build_player_trend_report(db, player, SEASON)

        assert report.role_status == "losing_trust"
        assert report.adjusted_role_status == "injury_context"
        assert report.injury_context is not None
        assert "availability-affected" in report.role_status_reason
        assert "Injury report context" in report.context_flags
    finally:
        db.close()
