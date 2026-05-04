"""Sprint 89 — Team-side player fit (roster + league candidates)."""
from pathlib import Path
import sys

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import Player, SeasonStat, Team  # noqa: E402
from services.team_roster_fit_service import (  # noqa: E402
    METHODOLOGY_VERSION,
    build_team_roster_fit_report,
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


def _seed_league(db, n_per_team: int = 8):
    """Seed a 4-team league with 8 players each — enough spread for stable z-scores."""
    teams = [
        (1, "BOS", "Boston Celtics"),
        (2, "ORL", "Orlando Magic"),
        (3, "LAL", "Los Angeles Lakers"),
        (4, "CHI", "Chicago Bulls"),
    ]
    for tid, abbr, name in teams:
        _team(db, tid, abbr, name)
    pid = 1000
    for _tid, abbr, _name in teams:
        for i in range(n_per_team):
            position = ["Guard", "Forward", "Center"][i % 3]
            _row(
                db,
                pid,
                "{0} Filler {1}".format(abbr, i),
                abbr,
                position=position,
                usg_pct=13.0 + (i * 2.0),
                pts_pg=9.0 + (i * 1.8),
                ast_pg=1.5 + (i * 0.6),
                reb_pg=3.0 + (i * 0.9),
                stl_pg=0.4 + (i * 0.18),
                blk_pg=0.1 + (i * 0.22),
                ts_pct=0.50 + (i * 0.012),
                per=10.0 + (i * 1.2),
                par3=0.18 + (i * 0.06),
                ftr=0.14 + (i * 0.04),
            )
            pid += 1
    db.commit()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_report_basic_shape_and_methodology_version():
    db = make_session()
    try:
        _seed_league(db)
        report = build_team_roster_fit_report(db, "BOS", season=SEASON)
        assert report.team_abbreviation == "BOS"
        assert report.team_name == "Boston Celtics"
        assert report.season == SEASON
        assert report.methodology.version == METHODOLOGY_VERSION
        assert report.methodology.position_cohort_enabled is True
        assert report.qualified_roster_count >= 3
        assert len(report.current_roster_fits) == report.qualified_roster_count
        assert len(report.league_candidates) > 0
        assert report.team_need_vector.features  # vector populated
        assert report.generated_at  # ISO timestamp present
    finally:
        db.close()


def test_self_exclusion_no_self_overlap():
    """A current-roster player must never appear as their own overlap teammate."""
    db = make_session()
    try:
        _seed_league(db)
        report = build_team_roster_fit_report(db, "BOS", season=SEASON)
        for entry in report.current_roster_fits:
            for flag in entry.overlap_flags:
                assert flag.teammate_id != entry.player_id, (
                    "Self-overlap detected for player {0}".format(entry.player_id)
                )
    finally:
        db.close()


def test_position_cohort_percentile_distinct_buckets():
    """Each player's cohort percentiles should be tagged with their own bucket
    (G / F / C / other), not the team's average bucket."""
    db = make_session()
    try:
        _seed_league(db)
        report = build_team_roster_fit_report(db, "BOS", season=SEASON)
        seen_buckets = set()
        for entry in report.current_roster_fits:
            for cp in entry.cohort_percentiles:
                seen_buckets.add(cp.bucket)
        # Seed mixes Guard/Forward/Center per team; expect at least 2 distinct buckets
        assert len(seen_buckets) >= 2, "Expected multiple cohort buckets, saw {0}".format(seen_buckets)
        assert seen_buckets.issubset({"G", "F", "C"})
    finally:
        db.close()


def test_low_confidence_when_roster_thin():
    """Roster with < 3 qualified rows ⇒ warnings flagged, no league candidates scored."""
    db = make_session()
    try:
        _seed_league(db)
        # Add a separate near-empty team
        _team(db, 99, "MIA", "Miami Heat")
        _row(db, 9999, "Lonely Heat", "MIA", position="Forward")
        db.commit()

        report = build_team_roster_fit_report(db, "MIA", season=SEASON)
        assert report.qualified_roster_count < 3
        assert any("qualified roster rows" in w for w in report.warnings)
        assert report.league_candidates == []  # gate skips when roster too thin
        assert report.current_roster_fits == []
    finally:
        db.close()


def test_team_need_vector_surfaces_3pt_poor_team():
    """A roster constructed to be far below league avg on par3 (3PA rate) should
    surface 'Spacing' in primary_needs."""
    db = make_session()
    try:
        _seed_league(db)
        # Construct a team deliberately starved of par3
        _team(db, 88, "DET", "Detroit Pistons")
        for i in range(5):
            _row(
                db,
                8800 + i,
                "DET Brick {0}".format(i),
                "DET",
                position=["Guard", "Forward", "Center"][i % 3],
                par3=0.05,  # league avg seeded at ~0.18-0.60 → far below
                pts_pg=12.0,
                usg_pct=18.0,
                ast_pg=2.5,
                reb_pg=5.0,
                ts_pct=0.50,
                per=12.0,
            )
        db.commit()

        report = build_team_roster_fit_report(db, "DET", season=SEASON)
        # par3 → "Spacing" in TEAM_FIT_FEATURE_LABELS
        assert "Spacing" in report.team_need_vector.primary_needs, (
            "Expected 'Spacing' in primary_needs, got: {0} (full vector: {1})".format(
                report.team_need_vector.primary_needs,
                [(f.label, f.team_z) for f in report.team_need_vector.features],
            )
        )
    finally:
        db.close()


def test_cache_round_trip_payload_identical():
    """Pydantic round-trip through SQLite cache must hydrate to an identical model."""
    from data.cache import CacheManager
    from models.team_roster_fit import TeamRosterFitResponse

    db = make_session()
    try:
        _seed_league(db)
        report = build_team_roster_fit_report(db, "BOS", season=SEASON, league_candidate_limit=10)

        CacheManager.initialize()
        key = "test_sprint89:BOS:{0}".format(SEASON)
        CacheManager.delete(key)  # clean slate
        CacheManager.set(key, report.model_dump(mode="json"), ttl_seconds=3600)
        cached = CacheManager.get(key)
        assert cached is not None
        hydrated = TeamRosterFitResponse(**cached)
        assert hydrated.model_dump() == report.model_dump()
        CacheManager.delete(key)
    finally:
        db.close()


def test_unknown_team_raises_404():
    db = make_session()
    try:
        _seed_league(db)
        with pytest.raises(HTTPException) as exc:
            build_team_roster_fit_report(db, "ZZZ", season=SEASON)
        assert exc.value.status_code == 404
    finally:
        db.close()


def test_determinism_two_calls_match():
    db = make_session()
    try:
        _seed_league(db)
        r1 = build_team_roster_fit_report(db, "BOS", season=SEASON, league_candidate_limit=10)
        r2 = build_team_roster_fit_report(db, "BOS", season=SEASON, league_candidate_limit=10)
        # generated_at differs by definition — strip it before comparing
        d1 = r1.model_dump(); d1["generated_at"] = ""
        d2 = r2.model_dump(); d2["generated_at"] = ""
        assert d1 == d2
    finally:
        db.close()


def test_league_candidates_exclude_own_roster():
    """No candidate's player_id should match a current-roster player."""
    db = make_session()
    try:
        _seed_league(db)
        report = build_team_roster_fit_report(db, "BOS", season=SEASON)
        roster_ids = {e.player_id for e in report.current_roster_fits}
        candidate_ids = {e.player_id for e in report.league_candidates}
        assert roster_ids.isdisjoint(candidate_ids), (
            "Candidate appeared in own roster: {0}".format(roster_ids & candidate_ids)
        )
        # And every candidate's current_team_abbr should be a different team
        for entry in report.league_candidates:
            assert entry.current_team_abbr != "BOS"
    finally:
        db.close()
