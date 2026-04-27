"""Sprint 69 — Team-Fit Intelligence & Explanation tests."""
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import Player, SeasonStat, Team  # noqa: E402
from routers.similarity import similar_players  # noqa: E402
from services.similarity_service import (  # noqa: E402
    _TEAM_FIT_PENALTY,
    build_team_fit_similarity_context,
)
from services.team_fit_service import (  # noqa: E402
    BETTER_FIT_DELTA_THRESHOLD,
    build_team_fit_report,
)


SEASON = "2025-26"
_PENDING_PLAYERS = set()


def make_session():
    engine = create_engine("sqlite:///:memory:")
    TS = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    _PENDING_PLAYERS.clear()
    return TS()


def _team(db, tid: int, abbr: str, name: str):
    db.add(Team(id=tid, abbreviation=abbr, name=name))


def _player(db, pid: int, name: str, position: str = "Forward", team_id=None):
    if pid not in _PENDING_PLAYERS and db.query(Player).filter(Player.id == pid).first() is None:
        db.add(Player(id=pid, full_name=name, position=position, team_id=team_id))
        _PENDING_PLAYERS.add(pid)


def _row(db, pid: int, name: str, team: str, position: str = "Forward", season: str = SEASON, **stats):
    _player(db, pid, name, position=position)
    defaults = dict(
        player_id=pid,
        season=season,
        team_abbreviation=team,
        is_playoff=False,
        gp=70,
        min_pg=30.0,
        pts_pg=15.0,
        reb_pg=5.0,
        ast_pg=4.0,
        stl_pg=1.0,
        blk_pg=0.5,
        tov_pg=2.0,
        fgm=5,
        fga=12,
        fg_pct=0.45,
        fg3m=2,
        fg3a=5,
        fg3_pct=0.36,
        ftm=3,
        fta=4,
        ft_pct=0.75,
        oreb=1,
        dreb=4,
        pf=2,
        usg_pct=20.0,
        ts_pct=0.56,
        efg_pct=0.53,
        per=15.0,
        bpm=0.0,
        off_rating=112.0,
        def_rating=112.0,
        net_rating=0.0,
        pace=100.0,
        pie=0.10,
        darko=0.0,
        epm=0.0,
        rapm=0.0,
        obpm=0.0,
        dbpm=0.0,
        ftr=0.30,
        par3=0.40,
        ast_tov=2.0,
        oreb_pct=4.0,
    )
    defaults.update(stats)
    db.add(SeasonStat(**defaults))


def _seed_teams(db):
    _team(db, 1, "BOS", "Boston Celtics")
    _team(db, 2, "ORL", "Orlando Magic")
    _team(db, 3, "LAL", "Los Angeles Lakers")
    _team(db, 4, "CHI", "Chicago Bulls")


def _seed_league(db):
    # Enough spread for stable season z-scores.
    for i in range(24):
        team = ["CHI", "LAL", "ORL", "BOS"][i % 4]
        _row(
            db,
            1000 + i,
            "Filler {0}".format(i),
            team,
            position=["Guard", "Forward", "Center"][i % 3],
            usg_pct=13.0 + (i % 8) * 2.0,
            pts_pg=9.0 + (i % 9) * 2.0,
            ast_pg=1.5 + (i % 6) * 0.8,
            reb_pg=3.0 + (i % 7) * 1.0,
            stl_pg=0.4 + (i % 5) * 0.25,
            blk_pg=0.1 + (i % 5) * 0.25,
            ts_pct=0.50 + (i % 8) * 0.015,
            per=10.0 + (i % 9) * 1.5,
            par3=0.18 + (i % 7) * 0.07,
            ftr=0.14 + (i % 6) * 0.05,
        )


def _seed_fit_case(db):
    _seed_teams(db)
    _seed_league(db)
    _row(
        db,
        1,
        "Subject Wing",
        "BOS",
        usg_pct=30.0,
        pts_pg=27.0,
        ast_pg=7.0,
        reb_pg=7.0,
        stl_pg=1.5,
        blk_pg=0.8,
        ts_pct=0.61,
        per=24.0,
        par3=0.48,
        ftr=0.38,
    )
    _row(
        db,
        2,
        "Covered Star",
        "BOS",
        usg_pct=29.7,
        pts_pg=26.8,
        ast_pg=6.8,
        reb_pg=6.8,
        stl_pg=1.4,
        blk_pg=0.7,
        ts_pct=0.60,
        per=23.0,
        par3=0.47,
        ftr=0.36,
    )
    _row(db, 3, "Boston Spacer", "BOS", usg_pct=15.0, pts_pg=10.0, ast_pg=2.0, par3=0.52)
    _row(db, 4, "Boston Big", "BOS", usg_pct=13.0, pts_pg=8.0, ast_pg=1.2, reb_pg=9.0, blk_pg=1.2)

    # ORL is deliberately thin on the subject's role features.
    _row(db, 20, "Orlando Guard", "ORL", position="Guard", usg_pct=15.0, pts_pg=11.0, ast_pg=2.5, par3=0.22, ftr=0.16)
    _row(db, 21, "Orlando Wing", "ORL", usg_pct=14.0, pts_pg=10.0, ast_pg=2.0, par3=0.24, ftr=0.18)
    _row(db, 22, "Orlando Big", "ORL", position="Center", usg_pct=12.0, pts_pg=9.0, ast_pg=1.0, reb_pg=8.0, blk_pg=0.8)
    db.commit()


def test_similarity_team_fit_context_names_covering_teammate_and_multiplier():
    db = make_session()
    try:
        _seed_fit_case(db)
        context = build_team_fit_similarity_context(db, 1, SEASON)
        assert context is not None
        flags = context["overlap_flags"]
        usage = next(flag for flag in flags if flag["feature_key"] == "usg_pct")
        assert usage["label"] == "Usage"
        assert usage["teammate_name"] == "Covered Star"
        assert usage["multiplier"] == _TEAM_FIT_PENALTY
        assert usage["gap"] < 0.5
        assert "player_z" in usage
        assert "teammate_z" in usage
    finally:
        db.close()


def test_team_fit_report_scores_current_and_alternate_teams():
    db = make_session()
    try:
        _seed_fit_case(db)
        report = build_team_fit_report(db, 1, SEASON, limit=5)
        assert report.methodology.version == "team_fit_v2"
        assert report.current_team is not None
        assert report.current_team.team_abbreviation == "BOS"
        assert report.current_team.skill_supply_score is not None
        assert report.current_team.roster_need_score is not None
        assert report.current_team.role_competition_score is not None
        assert report.current_team.confidence in {"high", "medium", "low"}
        assert report.current_team.confidence_notes
        assert report.current_team.overlap_flags
        assert report.current_team.value_drivers or report.current_team.role_runway_drivers

        team_abbrs = [row.team_abbreviation for row in report.alternative_teams]
        assert "BOS" not in team_abbrs
        assert "ORL" in team_abbrs
        orlando = next(row for row in report.alternative_teams if row.team_abbreviation == "ORL")
        assert orlando.score_delta_vs_current >= BETTER_FIT_DELTA_THRESHOLD
        assert orlando.label == "better_fit"
        assert orlando.confidence in {"high", "medium", "low"}
        assert orlando.summary
    finally:
        db.close()


def test_team_fit_report_prefers_non_tot_row_for_current_team():
    db = make_session()
    try:
        _seed_teams(db)
        _seed_league(db)
        _row(db, 50, "Split Player", "TOT", usg_pct=24.0, pts_pg=20.0, min_pg=31.0)
        _row(db, 50, "Split Player", "LAL", usg_pct=24.0, pts_pg=20.0, min_pg=28.0)
        _row(db, 51, "Laker One", "LAL", usg_pct=16.0, pts_pg=12.0)
        _row(db, 52, "Laker Two", "LAL", usg_pct=17.0, pts_pg=13.0)
        _row(db, 53, "Laker Three", "LAL", usg_pct=14.0, pts_pg=10.0)
        db.commit()

        report = build_team_fit_report(db, 50, SEASON, limit=3)
        assert report.current_team is not None
        assert report.current_team.team_abbreviation == "LAL"
    finally:
        db.close()


def test_team_fit_report_warns_when_current_team_is_thin():
    db = make_session()
    try:
        _seed_teams(db)
        _seed_league(db)
        _team(db, 5, "MIA", "Miami Heat")
        _row(db, 60, "Thin Team Player", "MIA", usg_pct=24.0, pts_pg=20.0)
        db.commit()

        report = build_team_fit_report(db, 60, SEASON, limit=3)
        assert report.current_team is not None or report.warnings
        assert any("qualified roster rows" in warning for warning in report.warnings)
    finally:
        db.close()


def test_team_fit_report_falls_back_to_latest_qualified_season():
    db = make_session()
    try:
        _seed_fit_case(db)
        # Add an unqualified newer row; missing V2 fields means it should not
        # drive Team-Fit, but the player page may still default to this season.
        _player(db, 1, "Subject Wing")
        db.add(SeasonStat(
            player_id=1,
            season="2026-27",
            team_abbreviation="BOS",
            is_playoff=False,
            gp=3,
            min_pg=8.0,
        ))
        db.commit()

        report = build_team_fit_report(db, 1, "2026-27", limit=3)
        assert report.season == SEASON
        assert report.current_team is not None
        assert any("latest qualified season" in warning for warning in report.warnings)
    finally:
        db.close()


def test_similarity_route_only_threads_context_for_team_fit_mode():
    db = make_session()
    try:
        _seed_fit_case(db)
        season_response = similar_players(
            player_id=1,
            season=SEASON,
            n=5,
            cross_era=True,
            mode="season",
            db=db,
        )
        team_fit_response = similar_players(
            player_id=1,
            season=SEASON,
            n=5,
            cross_era=True,
            mode="team_fit",
            db=db,
        )
        legacy_response = similar_players(
            player_id=1,
            season=SEASON,
            n=5,
            cross_era=False,
            mode=None,
            db=db,
        )

        assert "team_fit_context" not in season_response
        assert "team_fit_context" not in legacy_response
        assert team_fit_response["team_fit_context"] is not None
        assert team_fit_response["team_fit_context"]["overlap_flags"]
    finally:
        db.close()
