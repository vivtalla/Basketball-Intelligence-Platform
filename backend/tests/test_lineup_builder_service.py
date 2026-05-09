"""Sprint 95 — Lineup Lab builder service tests."""
from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import LineupStats, Player, Team, TeamSeasonStat  # noqa: E402
from services.lineup_builder_service import build_lineup_builder_result  # noqa: E402

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


def _tss(db, tid: int, net_rating: float = 3.0):
    db.add(TeamSeasonStat(
        team_id=tid,
        season=SEASON,
        is_playoff=False,
        net_rating=net_rating,
        off_rating=112.0,
        def_rating=109.0,
    ))


def _lineup(db, key: str, tid: int, poss: int, net_rating: float, minutes: float = 100.0):
    db.add(LineupStats(
        lineup_key=key,
        season=SEASON,
        team_id=tid,
        is_playoff=False,
        possessions=poss,
        net_rating=net_rating,
        ortg=115.0,
        drtg=110.0,
        minutes=minutes,
        plus_minus=5.0,
    ))


def _seed_base(db):
    _team(db, 1, "OKC")
    _tss(db, 1)
    for pid, name in [(10, "A"), (20, "B"), (30, "C"), (40, "D"), (50, "E"), (60, "F")]:
        _player(db, pid, name)


def test_builder_exact_match():
    db = make_session()
    _seed_base(db)
    _lineup(db, "10-20-30-40-50", 1, 200, 10.0)
    db.commit()

    result = build_lineup_builder_result(db, [50, 10, 30, 20, 40], SEASON)
    assert result.match_quality == "exact"
    assert result.exact_match is not None
    assert result.exact_match.net_rating == 10.0


def test_builder_sorted_player_key():
    """Lookup is order-independent — IDs are sorted before key construction."""
    db = make_session()
    _seed_base(db)
    _lineup(db, "10-20-30-40-50", 1, 200, 10.0)
    db.commit()

    result = build_lineup_builder_result(db, [50, 40, 30, 20, 10], SEASON)
    assert result.match_quality == "exact"


def test_builder_partial_match():
    db = make_session()
    _seed_base(db)
    # No exact 5-man match; only a 4-of-5 overlap lineup
    _lineup(db, "10-20-30-40-60", 1, 150, 6.0)
    db.commit()

    result = build_lineup_builder_result(db, [10, 20, 30, 40, 50], SEASON)
    assert result.match_quality == "partial"
    assert result.exact_match is None
    assert len(result.closest_matches) >= 1


def test_builder_no_match():
    db = make_session()
    _seed_base(db)
    # Lineup uses completely different players
    _lineup(db, "60-70-80-90-100", 1, 150, 5.0)
    for pid, name in [(70, "G"), (80, "H"), (90, "I"), (100, "J")]:
        _player(db, pid, name)
    db.commit()

    result = build_lineup_builder_result(db, [10, 20, 30, 40, 50], SEASON)
    assert result.match_quality == "none"
    assert result.exact_match is None
    assert result.closest_matches == []


def test_removal_impact_computed():
    db = make_session()
    _seed_base(db)
    _lineup(db, "10-20-30-40-50", 1, 200, 10.0)
    # Lineup without player 50 (the four remaining)
    _lineup(db, "10-20-30-40-60", 1, 150, 6.0)
    db.commit()

    result = build_lineup_builder_result(db, [10, 20, 30, 40, 50], SEASON)
    impacts = {imp.player_id: imp for imp in result.player_removal_impacts}
    # Without player 50: lineup "10-20-30-40-60" contains 10,20,30,40 but not 50
    assert 50 in impacts
    assert impacts[50].lineups_without_count >= 1
    assert impacts[50].avg_net_rating_without == 6.0


def test_removal_delta_sign():
    db = make_session()
    _seed_base(db)
    _lineup(db, "10-20-30-40-50", 1, 200, 10.0)
    _lineup(db, "10-20-30-40-60", 1, 150, 6.0)
    db.commit()

    result = build_lineup_builder_result(db, [10, 20, 30, 40, 50], SEASON)
    impacts = {imp.player_id: imp for imp in result.player_removal_impacts}
    # delta_vs_full = avg_without - exact_match.net_rating = 6.0 - 10.0 = -4.0
    assert impacts[50].delta_vs_full == pytest.approx(-4.0, abs=0.1)


def test_small_sample_warning():
    db = make_session()
    _seed_base(db)
    _lineup(db, "10-20-30-40-50", 1, 50, 10.0)  # 50 poss < 80 threshold
    db.commit()

    result = build_lineup_builder_result(db, [10, 20, 30, 40, 50], SEASON)
    assert len(result.warnings) > 0
    assert any("possessions" in w.lower() for w in result.warnings)


def test_false_positive_filter():
    """lineup_key '112-120-130-140-150' must NOT match player_id=12."""
    db = make_session()
    _seed_base(db)
    _lineup(db, "112-120-130-140-150", 1, 200, 8.0)
    for pid, name in [(112, "AA"), (120, "BB"), (130, "CC"), (140, "DD"), (150, "EE")]:
        _player(db, pid, name)
    db.commit()

    result = build_lineup_builder_result(db, [10, 20, 30, 40, 50], SEASON)
    # Player 12 is not in submitted list, but more importantly the overlap should be 0
    # The lineup "112-120-130-140-150" shares no real IDs with [10,20,30,40,50]
    assert result.match_quality == "none"
