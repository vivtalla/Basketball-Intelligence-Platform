"""Sprint 95 — Lineup Lab leaderboard service tests."""
from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import LineupStats, Player, Team, TeamSeasonStat  # noqa: E402
from services.lineup_leaderboard_service import (  # noqa: E402
    _classify_lineup,
    _lineup_confidence,
    _shrink,
    build_lineup_leaderboard,
)

SEASON = "2024-25"


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return Session()


def _team(db, tid: int, abbr: str):
    db.add(Team(id=tid, abbreviation=abbr, name="{0} Team".format(abbr)))


def _player(db, pid: int, name: str):
    db.add(Player(id=pid, full_name=name, position="Guard", team_id=None))


def _tss(db, tid: int, net_rating: float = 2.0, off_rating: float = 110.0, def_rating: float = 108.0):
    db.add(TeamSeasonStat(
        team_id=tid,
        season=SEASON,
        is_playoff=False,
        net_rating=net_rating,
        off_rating=off_rating,
        def_rating=def_rating,
    ))


def _lineup(db, key: str, tid: int, poss: int, net_rating: float,
            ortg: float = 112.0, drtg: float = 108.0, minutes: float = 100.0, is_playoff: bool = False):
    db.add(LineupStats(
        lineup_key=key,
        season=SEASON,
        team_id=tid,
        is_playoff=is_playoff,
        possessions=poss,
        net_rating=net_rating,
        ortg=ortg,
        drtg=drtg,
        minutes=minutes,
        plus_minus=10.0,
    ))


# --- Unit tests for pure functions ---

def test_confidence_high():
    assert _lineup_confidence(200) == "high"
    assert _lineup_confidence(500) == "high"


def test_confidence_medium():
    assert _lineup_confidence(80) == "medium"
    assert _lineup_confidence(199) == "medium"


def test_confidence_low():
    assert _lineup_confidence(1) == "low"
    assert _lineup_confidence(79) == "low"
    assert _lineup_confidence(None) == "low"


def test_shrunk_net_rating_formula():
    # shrunk = nr * w + baseline * (1 - w), where w = poss / (poss + 150)
    poss = 150
    nr = 10.0
    baseline = 2.0
    w = poss / (poss + 150.0)
    expected = round(nr * w + baseline * (1.0 - w), 2)
    result = _shrink(nr, baseline, poss)
    assert result == expected


def test_shrunk_net_none_when_nr_none():
    assert _shrink(None, 2.0, 200) is None


def test_shrunk_net_returns_nr_when_no_baseline():
    result = _shrink(8.0, None, 200)
    assert result == 8.0


def test_archetype_elite():
    result = _classify_lineup(6.0, 3.0, 3.0)
    assert result == "Elite"


def test_archetype_offensive_wall():
    # ortg_delta >= 4, drtg_delta < -2
    result = _classify_lineup(3.0, 5.0, -3.0)
    assert result == "Offensive Wall"


def test_archetype_defensive_wall():
    # drtg_delta >= 4, ortg_delta < 1
    result = _classify_lineup(2.0, 0.5, 5.0)
    assert result == "Defensive Wall"


def test_archetype_negative():
    result = _classify_lineup(-5.0, -3.0, -3.0)
    assert result == "Negative"


def test_archetype_balanced():
    result = _classify_lineup(1.0, 1.0, 1.0)
    assert result == "Balanced"


def test_archetype_unclassified_when_no_baseline():
    result = _classify_lineup(None, None, None)
    assert result == "Unclassified"


# --- Integration tests ---

def test_leaderboard_season_filter():
    db = make_session()
    _team(db, 1, "LAL")
    _tss(db, 1)
    _lineup(db, "10-20-30-40-50", 1, 150, 8.0)
    db.add(LineupStats(
        lineup_key="10-20-30-40-50",
        season="2023-24",
        team_id=1,
        is_playoff=False,
        possessions=200,
        net_rating=5.0,
        ortg=112.0,
        drtg=107.0,
        minutes=100.0,
        plus_minus=5.0,
    ))
    db.commit()

    result = build_lineup_leaderboard(db, season=SEASON, min_possessions=100)
    assert result.season == SEASON
    assert result.total == 1
    assert result.lineups[0].net_rating == 8.0


def test_leaderboard_min_possessions_gate():
    db = make_session()
    _team(db, 1, "LAL")
    _tss(db, 1)
    _lineup(db, "10-20-30-40-50", 1, 80, 8.0)
    _lineup(db, "10-20-30-40-60", 1, 150, 5.0)
    db.commit()

    result = build_lineup_leaderboard(db, season=SEASON, min_possessions=100)
    assert result.total == 1
    assert result.lineups[0].possessions == 150


def test_leaderboard_sort_by_ortg():
    db = make_session()
    _team(db, 1, "LAL")
    _tss(db, 1)
    _lineup(db, "10-20-30-40-50", 1, 150, 5.0, ortg=108.0)
    _lineup(db, "10-20-30-40-60", 1, 150, 8.0, ortg=115.0)
    db.commit()

    result = build_lineup_leaderboard(db, season=SEASON, min_possessions=100, sort_by="ortg")
    assert result.lineups[0].ortg == 115.0


def test_leaderboard_sort_asc():
    db = make_session()
    _team(db, 1, "LAL")
    _tss(db, 1)
    _lineup(db, "10-20-30-40-50", 1, 150, 8.0)
    _lineup(db, "10-20-30-40-60", 1, 150, 3.0)
    db.commit()

    result = build_lineup_leaderboard(db, season=SEASON, min_possessions=100, sort_dir="asc")
    assert result.lineups[0].net_rating == 3.0


def test_leaderboard_team_filter():
    db = make_session()
    _team(db, 1, "LAL")
    _team(db, 2, "BOS")
    _tss(db, 1)
    _tss(db, 2)
    _lineup(db, "10-20-30-40-50", 1, 150, 8.0)
    _lineup(db, "60-70-80-90-100", 2, 200, 12.0)
    db.commit()

    result = build_lineup_leaderboard(db, season=SEASON, team_id=1, min_possessions=100)
    assert result.total == 1
    assert result.lineups[0].team_id == 1


def test_missing_team_stat_graceful():
    db = make_session()
    _team(db, 1, "LAL")
    # No TeamSeasonStat row
    _lineup(db, "10-20-30-40-50", 1, 150, 8.0)
    db.commit()

    result = build_lineup_leaderboard(db, season=SEASON, min_possessions=100)
    assert result.total == 1
    entry = result.lineups[0]
    assert entry.net_vs_baseline is None
    assert entry.archetype == "Unclassified"
