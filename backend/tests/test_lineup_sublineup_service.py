"""Sprint 95 — Lineup Lab sub-lineup (2-man/3-man combos) service tests."""
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import LineupStats, Player, Team, TeamSeasonStat  # noqa: E402
from services.lineup_sublineup_service import build_sublineups  # noqa: E402

SEASON = "2024-25"
TEAM_ID = 1


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return Session()


def _team(db):
    db.add(Team(id=TEAM_ID, abbreviation="LAL", name="Lakers"))


def _tss(db, net_rating: float = 3.0):
    db.add(TeamSeasonStat(
        team_id=TEAM_ID,
        season=SEASON,
        is_playoff=False,
        net_rating=net_rating,
        off_rating=112.0,
        def_rating=109.0,
    ))


def _player(db, pid: int, name: str):
    db.add(Player(id=pid, full_name=name, position="Guard", team_id=None))


def _lineup(db, key: str, poss: int, net_rating: float, minutes: float = 80.0):
    db.add(LineupStats(
        lineup_key=key,
        season=SEASON,
        team_id=TEAM_ID,
        is_playoff=False,
        possessions=poss,
        net_rating=net_rating,
        ortg=115.0,
        drtg=112.0,
        minutes=minutes,
        plus_minus=5.0,
    ))


def test_2man_combos_from_five_man():
    """One 5-man lineup generates C(5,2)=10 pairs."""
    db = make_session()
    _team(db)
    _tss(db)
    for pid, name in [(1, "A"), (2, "B"), (3, "C"), (4, "D"), (5, "E")]:
        _player(db, pid, name)
    _lineup(db, "1-2-3-4-5", poss=100, net_rating=8.0)
    db.commit()

    result = build_sublineups(db, TEAM_ID, SEASON, size=2, min_possessions=50)
    assert len(result.lineups) == 10


def test_3man_combos_from_five_man():
    """One 5-man lineup generates C(5,3)=10 trios."""
    db = make_session()
    _team(db)
    _tss(db)
    for pid, name in [(1, "A"), (2, "B"), (3, "C"), (4, "D"), (5, "E")]:
        _player(db, pid, name)
    _lineup(db, "1-2-3-4-5", poss=100, net_rating=8.0)
    db.commit()

    result = build_sublineups(db, TEAM_ID, SEASON, size=3, min_possessions=50)
    assert len(result.lineups) == 10


def test_min_possessions_gate():
    """Combos below threshold excluded."""
    db = make_session()
    _team(db)
    _tss(db)
    for pid, name in [(1, "A"), (2, "B"), (3, "C"), (4, "D"), (5, "E")]:
        _player(db, pid, name)
    # Lineup with only 25 possessions — below pre-filter floor of 25 is fine,
    # but combined combo possessions will be 25 < 50 min_possessions
    _lineup(db, "1-2-3-4-5", poss=25, net_rating=8.0)
    db.commit()

    result = build_sublineups(db, TEAM_ID, SEASON, size=2, min_possessions=50)
    assert len(result.lineups) == 0


def test_possessions_aggregated_across_lineups():
    """Same 2-man pair appearing in two different lineups has possessions summed."""
    db = make_session()
    _team(db)
    _tss(db)
    for pid, name in [(1, "A"), (2, "B"), (3, "C"), (4, "D"), (5, "E"), (6, "F")]:
        _player(db, pid, name)
    # Both lineups contain players 1 and 2
    _lineup(db, "1-2-3-4-5", poss=60, net_rating=10.0)
    _lineup(db, "1-2-3-4-6", poss=40, net_rating=4.0)
    db.commit()

    result = build_sublineups(db, TEAM_ID, SEASON, size=2, min_possessions=50)
    # Find the "1-2" combo
    pair_12 = next((e for e in result.lineups if set(e.player_ids) == {1, 2}), None)
    assert pair_12 is not None
    assert pair_12.possessions == 100  # 60 + 40


def test_weighted_net_rating():
    """Possession-weighted average net rating formula."""
    db = make_session()
    _team(db)
    _tss(db)
    for pid, name in [(1, "A"), (2, "B"), (3, "C"), (4, "D"), (5, "E"), (6, "F")]:
        _player(db, pid, name)
    # Pair 1-2 in two lineups: 60 poss @ 10.0 NR, 40 poss @ 4.0 NR
    # Weighted avg = (60*10 + 40*4) / 100 = (600+160)/100 = 7.6
    _lineup(db, "1-2-3-4-5", poss=60, net_rating=10.0)
    _lineup(db, "1-2-3-4-6", poss=40, net_rating=4.0)
    db.commit()

    result = build_sublineups(db, TEAM_ID, SEASON, size=2, min_possessions=50)
    pair_12 = next((e for e in result.lineups if set(e.player_ids) == {1, 2}), None)
    assert pair_12 is not None
    assert abs(pair_12.net_rating - 7.6) < 0.1


def test_sorted_by_net_rating():
    """Sub-lineups sorted by net_rating descending."""
    db = make_session()
    _team(db)
    _tss(db)
    for pid, name in [(1, "A"), (2, "B"), (3, "C"), (4, "D"), (5, "E"), (6, "F")]:
        _player(db, pid, name)
    _lineup(db, "1-2-3-4-5", poss=60, net_rating=5.0)
    _lineup(db, "1-2-3-4-6", poss=60, net_rating=12.0)
    db.commit()

    result = build_sublineups(db, TEAM_ID, SEASON, size=2, min_possessions=50)
    nrs = [e.net_rating for e in result.lineups if e.net_rating is not None]
    assert nrs == sorted(nrs, reverse=True)
