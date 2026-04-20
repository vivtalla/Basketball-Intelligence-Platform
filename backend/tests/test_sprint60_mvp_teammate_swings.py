from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import LineupStats, Player, Team  # noqa: E402
from services.mvp_service import _teammate_on_off_swings  # noqa: E402


def make_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


def seed_team(session):
    team = Team(id=1610612760, abbreviation="OKC", name="Oklahoma City Thunder")
    session.add(team)
    for pid, name in [
        (1, "Candidate"),
        (2, "Top Partner"),
        (3, "Secondary"),
        (4, "Rotation"),
        (5, "Bench"),
    ]:
        session.add(Player(id=pid, full_name=name, team=team, team_id=team.id))
    return team


def add_lineup(session, team, ids, minutes, net, possessions):
    key = "-".join(str(p) for p in sorted(ids))
    session.add(LineupStats(
        lineup_key=key,
        season="2025-26",
        team_id=team.id,
        minutes=minutes,
        net_rating=net,
        ortg=110.0,
        drtg=110.0 - net,
        possessions=possessions,
    ))


def test_empty_lineups_returns_empty():
    session = make_session()
    try:
        team = seed_team(session)
        session.commit()
        result = _teammate_on_off_swings(session, player_id=1, team_id=team.id, season="2025-26")
        assert result == []
    finally:
        session.close()


def test_no_team_id_returns_empty():
    session = make_session()
    try:
        seed_team(session)
        session.commit()
        result = _teammate_on_off_swings(session, player_id=1, team_id=None, season="2025-26")
        assert result == []
    finally:
        session.close()


def test_gating_by_possessions():
    session = make_session()
    try:
        team = seed_team(session)
        # Below the 100-possession floor.
        add_lineup(session, team, [1, 2, 3, 4, 5], minutes=50.0, net=10.0, possessions=40)
        session.commit()
        result = _teammate_on_off_swings(session, player_id=1, team_id=team.id, season="2025-26")
        assert result == []
    finally:
        session.close()


def test_single_teammate_swing():
    session = make_session()
    try:
        team = seed_team(session)
        for pid in (10, 11, 12, 13):
            session.add(Player(id=pid, full_name=f"P{pid}", team=team, team_id=team.id))
        # Two pair lineups with teammate 2 give teammate 2 the most shared minutes.
        add_lineup(session, team, [1, 2, 3, 4, 5], minutes=200.0, net=8.0, possessions=300)
        add_lineup(session, team, [1, 2, 10, 11, 12], minutes=100.0, net=8.0, possessions=160)
        # One lineup without teammate 2.
        add_lineup(session, team, [1, 3, 4, 5, 13], minutes=100.0, net=2.0, possessions=150)
        session.commit()
        result = _teammate_on_off_swings(session, player_id=1, team_id=team.id, season="2025-26")
        assert result
        top = next(s for s in result if s.teammate_id == 2)
        assert top.both_on_net == 8.0
        assert top.candidate_without_teammate_net == 2.0
        assert top.swing == 6.0
    finally:
        session.close()


def test_top_n_ordering_by_minutes():
    session = make_session()
    try:
        team = seed_team(session)
        for pid in (10, 11, 12, 13, 14):
            session.add(Player(id=pid, full_name=f"P{pid}", team=team, team_id=team.id))
        # Teammate 3 accumulates 500 min; no other teammate exceeds 300 min.
        add_lineup(session, team, [1, 3, 10, 11, 12], minutes=300.0, net=4.0, possessions=400)
        add_lineup(session, team, [1, 3, 4, 13, 14], minutes=200.0, net=6.0, possessions=260)
        session.commit()
        result = _teammate_on_off_swings(session, player_id=1, team_id=team.id, season="2025-26")
        assert result
        assert result[0].teammate_id == 3
        assert result[0].shared_minutes == 500.0
    finally:
        session.close()


def test_confidence_bands():
    session = make_session()
    try:
        team = seed_team(session)
        # High confidence: 400 possessions shared.
        add_lineup(session, team, [1, 2, 3, 4, 5], minutes=300.0, net=6.0, possessions=400)
        session.commit()
        result = _teammate_on_off_swings(session, player_id=1, team_id=team.id, season="2025-26")
        for swing in result:
            assert swing.confidence == "high"
    finally:
        session.close()


def test_top_n_limit():
    session = make_session()
    try:
        team = seed_team(session)
        for pid, name in [(10, "X"), (11, "Y"), (12, "Z"), (13, "W")]:
            session.add(Player(id=pid, full_name=name, team=team, team_id=team.id))
        # Four different teammate pairs, each qualifying.
        add_lineup(session, team, [1, 10, 11, 12, 13], minutes=200.0, net=5.0, possessions=250)
        add_lineup(session, team, [1, 2, 11, 12, 13], minutes=150.0, net=4.0, possessions=200)
        session.commit()
        result = _teammate_on_off_swings(session, player_id=1, team_id=team.id, season="2025-26")
        assert len(result) <= 3
    finally:
        session.close()
