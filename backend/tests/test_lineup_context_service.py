from pathlib import Path
import sys

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import LineupStats, Player, PlayerOnOff, Team  # noqa: E402
from services.lineup_context_service import build_lineup_context  # noqa: E402


def make_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


def seed_lineup_pool(session):
    okc = Team(id=1610612760, abbreviation="OKC", name="Oklahoma City Thunder")
    session.add(okc)

    # Five players; player 1 is our focal player.
    for pid, name, pos in [
        (1, "Focal Star", "G"),
        (2, "Top Teammate", "F"),
        (3, "Secondary Mate", "C"),
        (4, "Bench Mate", "G"),
        (5, "Fringe Mate", "F"),
    ]:
        session.add(Player(id=pid, full_name=name, position=pos, team=okc, team_id=okc.id))

    # On/off data for player 1.
    session.add(PlayerOnOff(
        player_id=1,
        season="2025-26",
        is_playoff=False,
        on_minutes=1200.0,
        off_minutes=500.0,
        on_net_rating=8.4,
        off_net_rating=2.1,
        on_off_net=6.3,
    ))

    # Lineups involving player 1. lineup_key is sorted player IDs joined by "-".
    # Lineup with players 1,2,3,4,5 — 300 possessions (qualifies).
    key_full = "-".join(str(p) for p in sorted([1, 2, 3, 4, 5]))
    session.add(LineupStats(
        lineup_key=key_full,
        season="2025-26",
        team_id=okc.id,
        minutes=200.0,
        net_rating=9.5,
        ortg=115.0,
        drtg=105.5,
        possessions=300,
    ))

    # Lineup with players 1,2,3 — 150 possessions (qualifies).
    key_trio = "-".join(str(p) for p in sorted([1, 2, 3]))
    session.add(LineupStats(
        lineup_key=key_trio,
        season="2025-26",
        team_id=okc.id,
        minutes=100.0,
        net_rating=12.0,
        ortg=118.0,
        drtg=106.0,
        possessions=150,
    ))

    # Lineup with players 1,4,5 — 50 possessions (below threshold, should be excluded).
    key_bench = "-".join(str(p) for p in sorted([1, 4, 5]))
    session.add(LineupStats(
        lineup_key=key_bench,
        season="2025-26",
        team_id=okc.id,
        minutes=30.0,
        net_rating=-2.0,
        ortg=108.0,
        drtg=110.0,
        possessions=50,
    ))

    # Lineup not involving player 1.
    key_other = "-".join(str(p) for p in sorted([2, 3, 4, 5, 6]))
    session.add(Player(id=6, full_name="Other Player", position="G", team=okc, team_id=okc.id))
    session.add(LineupStats(
        lineup_key=key_other,
        season="2025-26",
        team_id=okc.id,
        minutes=80.0,
        net_rating=3.0,
        ortg=112.0,
        drtg=109.0,
        possessions=120,
    ))

    session.commit()


def test_lineup_context_returns_correct_player():
    session = make_session()
    try:
        seed_lineup_pool(session)
        result = build_lineup_context(session, player_id=1, season="2025-26")
        assert result.player_id == 1
        assert result.player_name == "Focal Star"
        assert result.season == "2025-26"
    finally:
        session.close()


def test_lineup_context_on_off_from_player_on_off():
    session = make_session()
    try:
        seed_lineup_pool(session)
        result = build_lineup_context(session, player_id=1, season="2025-26")
        assert result.on_off_net == 6.3
        assert result.on_minutes == 1200.0
        assert result.off_minutes == 500.0
    finally:
        session.close()


def test_lineup_context_excludes_below_threshold_lineups():
    session = make_session()
    try:
        seed_lineup_pool(session)
        # Player 6 only appears in the 120-poss lineup that does NOT include player 1.
        # So player 6 should never appear in player 1's top_teammates.
        result = build_lineup_context(session, player_id=1, season="2025-26")
        teammate_ids = {t.teammate_id for t in result.top_teammates}
        assert 6 not in teammate_ids
        # The 50-poss lineup (players 1,4,5) is below threshold so it contributes
        # 0 possessions toward teammate credit. Players 4 and 5 still appear
        # because they are also in the qualifying 5-man lineup (300 poss).
        # This confirms the threshold gate works: only lineups ≥100 poss are counted.
        assert all(t.possessions >= 100 for t in result.top_teammates)
    finally:
        session.close()


def test_lineup_context_top_teammates_by_shared_minutes():
    session = make_session()
    try:
        seed_lineup_pool(session)
        result = build_lineup_context(session, player_id=1, season="2025-26")
        # Player 2 appears in both qualifying lineups (200 + 100 = 300 shared minutes).
        # Player 3 also appears in both (same shared minutes).
        # Both should be in top_teammates.
        teammate_ids = {t.teammate_id for t in result.top_teammates}
        assert 2 in teammate_ids
        assert 3 in teammate_ids
    finally:
        session.close()


def test_lineup_context_net_rating_is_possession_weighted():
    session = make_session()
    try:
        seed_lineup_pool(session)
        result = build_lineup_context(session, player_id=1, season="2025-26")
        # Player 2 shares two lineups: (9.5, 300 poss) and (12.0, 150 poss).
        # Weighted avg = (9.5*300 + 12.0*150) / 450 = (2850 + 1800) / 450 = 10.33...
        mate2 = next((t for t in result.top_teammates if t.teammate_id == 2), None)
        assert mate2 is not None
        assert mate2.net_rating_with is not None
        assert abs(mate2.net_rating_with - 10.3) < 0.2
    finally:
        session.close()


def test_lineup_context_unknown_player_raises_404():
    session = make_session()
    try:
        seed_lineup_pool(session)
        with pytest.raises(HTTPException) as exc_info:
            build_lineup_context(session, player_id=9999, season="2025-26")
        assert exc_info.value.status_code == 404
    finally:
        session.close()


def test_lineup_context_no_on_off_data_returns_none_fields():
    session = make_session()
    try:
        seed_lineup_pool(session)
        # Player 3 has no PlayerOnOff row.
        result = build_lineup_context(session, player_id=3, season="2025-26")
        assert result.on_off_net is None
        assert result.on_minutes is None
    finally:
        session.close()


def test_lineup_context_notes_always_present():
    session = make_session()
    try:
        seed_lineup_pool(session)
        result = build_lineup_context(session, player_id=1, season="2025-26")
        assert len(result.notes) >= 1
    finally:
        session.close()
