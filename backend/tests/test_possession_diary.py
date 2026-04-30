"""Sprint 77 (EA2) — Possession Diary + per-quarter +/- service tests.

Three focused tests:
  1. The diary truncates to <= 24 rows even when the source game has many
     more lead-changing possessions.
  2. And-1 sequences (made FG + foul + 1-of-1 FT) attribute the bonus point
     to the made shot's possession entry — i.e. ``points_scored == 3`` for
     a 2-point and-1 — and do not emit a separate FT possession.
  3. Per-player per-quarter +/- sums match the player's total game +/-.
"""
from __future__ import annotations

from datetime import date as date_cls
from pathlib import Path
import sys
from typing import Iterable, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import GameLog, PlayByPlayEvent, Player, Team, WarehouseGame  # noqa: E402
from services.possession_diary_service import (  # noqa: E402
    compute_player_quarter_plus_minus,
    compute_possession_diary,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


HOME_TEAM_ID = 1610612737
AWAY_TEAM_ID = 1610612738


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def _seed_game_skeleton(
    session,
    game_id: str,
    home_player_ids: Iterable[int],
    away_player_ids: Iterable[int],
) -> None:
    session.add(Team(id=HOME_TEAM_ID, abbreviation="HOM", name="Home Team"))
    session.add(Team(id=AWAY_TEAM_ID, abbreviation="AWY", name="Away Team"))
    session.flush()
    for pid in home_player_ids:
        session.add(
            Player(
                id=pid,
                full_name="Home Player {}".format(pid),
                team_id=HOME_TEAM_ID,
                is_active=True,
            )
        )
    for pid in away_player_ids:
        session.add(
            Player(
                id=pid,
                full_name="Away Player {}".format(pid),
                team_id=AWAY_TEAM_ID,
                is_active=True,
            )
        )
    session.add(
        GameLog(
            game_id=game_id,
            season="2024-25",
            game_date=date_cls(2025, 1, 14),
            home_team_id=HOME_TEAM_ID,
            away_team_id=AWAY_TEAM_ID,
            home_score=0,
            away_score=0,
        )
    )
    session.commit()


def _add_pbp_row(
    session,
    *,
    game_id: str,
    action_number: int,
    period: int,
    clock: str,
    team_id: Optional[int],
    player_id: Optional[int],
    action_type: str,
    sub_type: Optional[str],
    description: str,
    score_home: int,
    score_away: int,
) -> None:
    if not session.query(WarehouseGame).filter_by(game_id=game_id).first():
        session.add(WarehouseGame(game_id=game_id, season="2024-25"))
        session.flush()
    session.add(
        PlayByPlayEvent(
            game_id=game_id,
            season="2024-25",
            action_number=action_number,
            order_index=action_number,
            period=period,
            clock=clock,
            team_id=team_id,
            player_id=player_id,
            action_type=action_type,
            sub_type=sub_type,
            description=description,
            score_home=score_home,
            score_away=score_away,
        )
    )


# ---------------------------------------------------------------------------
# Test 1 — diary 24-row cap
# ---------------------------------------------------------------------------


def test_diary_respects_24_row_cap():
    session = _make_session()
    try:
        home_ids = list(range(101, 106))
        away_ids = list(range(201, 206))
        _seed_game_skeleton(session, "0099900001", home_ids, away_ids)

        # 80 alternating made-3pt possessions, half by home half by away.
        # Each made 3 swings the lead by ±3, so every possession is impactful.
        action = 1
        score_home = 0
        score_away = 0
        for i in range(80):
            scoring_team_id = HOME_TEAM_ID if i % 2 == 0 else AWAY_TEAM_ID
            scorer_id = home_ids[0] if i % 2 == 0 else away_ids[0]
            if scoring_team_id == HOME_TEAM_ID:
                score_home += 3
            else:
                score_away += 3
            # Tick the clock down across periods to keep events ordered.
            period = (i // 20) + 1
            seconds_left = 700 - ((i % 20) * 30)
            mins = seconds_left // 60
            secs = seconds_left - mins * 60
            clock = "PT{:02d}M{:05.2f}S".format(mins, float(secs))
            _add_pbp_row(
                session,
                game_id="0099900001",
                action_number=action,
                period=period,
                clock=clock,
                team_id=scoring_team_id,
                player_id=scorer_id,
                action_type="3pt",
                sub_type="made",
                description="Made 3PT jumper",
                score_home=score_home,
                score_away=score_away,
            )
            action += 1
        session.commit()

        diary = compute_possession_diary(session, "0099900001")
        assert len(diary) <= 24
        # Sanity: the diary should be sorted by absolute lead-swing desc.
        swings = [abs(entry.lead_swing) for entry in diary]
        assert swings == sorted(swings, reverse=True)
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Test 2 — and-1 handling
# ---------------------------------------------------------------------------


def test_possession_boundaries_handle_and_1():
    session = _make_session()
    try:
        home_ids = list(range(301, 306))
        away_ids = list(range(401, 406))
        _seed_game_skeleton(session, "0099900002", home_ids, away_ids)

        scorer_id = home_ids[0]
        defender_id = away_ids[0]

        # Made 2 by home (2-0) -> shooting foul on away -> made 1 of 1 (3-0).
        _add_pbp_row(
            session,
            game_id="0099900002",
            action_number=1,
            period=1,
            clock="PT11M00.00S",
            team_id=HOME_TEAM_ID,
            player_id=scorer_id,
            action_type="2pt",
            sub_type="made",
            description="Made layup",
            score_home=2,
            score_away=0,
        )
        _add_pbp_row(
            session,
            game_id="0099900002",
            action_number=2,
            period=1,
            clock="PT11M00.00S",
            team_id=AWAY_TEAM_ID,
            player_id=defender_id,
            action_type="foul",
            sub_type="shooting",
            description="Shooting foul",
            score_home=2,
            score_away=0,
        )
        _add_pbp_row(
            session,
            game_id="0099900002",
            action_number=3,
            period=1,
            clock="PT11M00.00S",
            team_id=HOME_TEAM_ID,
            player_id=scorer_id,
            action_type="freethrow",
            sub_type="made",
            description="Free Throw 1 of 1",
            score_home=3,
            score_away=0,
        )
        # Follow-up away possession that ends in a turnover so we can confirm
        # the prior and-1 produced exactly ONE diary entry, not two.
        _add_pbp_row(
            session,
            game_id="0099900002",
            action_number=4,
            period=1,
            clock="PT10M40.00S",
            team_id=AWAY_TEAM_ID,
            player_id=away_ids[1],
            action_type="turnover",
            sub_type="bad_pass",
            description="Bad pass turnover",
            score_home=3,
            score_away=0,
        )
        session.commit()

        diary = compute_possession_diary(session, "0099900002")
        assert diary, "expected at least one possession in the diary"

        # The made-2 + and-1 FT must roll up into ONE possession, with 3 points.
        and_one_entries = [
            entry
            for entry in diary
            if entry.offense_team_abbr == "HOM"
            and entry.points_scored == 3
            and entry.primary_action_type.startswith("And-1")
        ]
        assert len(and_one_entries) == 1, "expected exactly one and-1 possession entry"

        # No standalone freethrow entry should exist for this same possession.
        freethrow_entries = [
            entry
            for entry in diary
            if entry.primary_action_type.startswith("Made FT")
            and entry.offense_team_abbr == "HOM"
        ]
        assert freethrow_entries == [], "and-1 FT must not produce a separate possession"
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Test 3 — per-quarter +/- sums match game +/-
# ---------------------------------------------------------------------------


def test_per_quarter_plus_minus_sums_match_box():
    session = _make_session()
    try:
        home_ids = list(range(501, 506))
        away_ids = list(range(601, 606))
        _seed_game_skeleton(session, "0099900003", home_ids, away_ids)

        # Build a deterministic 2-quarter game with no substitutions so all
        # 5 home starters share the same on-court time and per-quarter +/-.
        # Q1: home scores 8, away scores 5  -> home +3 / away -3
        # Q2: home scores 4, away scores 7  -> home -3 / away +3
        # Total: home 0 / away 0
        action = 1
        score_home = 0
        score_away = 0

        def _score(team_id: int, points: int, period: int, clock: str, player_id: int):
            nonlocal action, score_home, score_away
            if team_id == HOME_TEAM_ID:
                score_home += points
            else:
                score_away += points
            atype = "3pt" if points == 3 else "2pt"
            _add_pbp_row(
                session,
                game_id="0099900003",
                action_number=action,
                period=period,
                clock=clock,
                team_id=team_id,
                player_id=player_id,
                action_type=atype,
                sub_type="made",
                description="Made bucket",
                score_home=score_home,
                score_away=score_away,
            )
            action += 1

        # Q1
        _score(HOME_TEAM_ID, 3, 1, "PT11M00.00S", home_ids[0])
        _score(AWAY_TEAM_ID, 2, 1, "PT10M00.00S", away_ids[0])
        _score(HOME_TEAM_ID, 3, 1, "PT08M00.00S", home_ids[1])
        _score(AWAY_TEAM_ID, 3, 1, "PT06M00.00S", away_ids[1])
        _score(HOME_TEAM_ID, 2, 1, "PT01M00.00S", home_ids[2])

        # Q2
        _score(AWAY_TEAM_ID, 3, 2, "PT11M00.00S", away_ids[0])
        _score(HOME_TEAM_ID, 2, 2, "PT09M00.00S", home_ids[0])
        _score(AWAY_TEAM_ID, 2, 2, "PT07M00.00S", away_ids[2])
        _score(HOME_TEAM_ID, 2, 2, "PT04M00.00S", home_ids[1])
        _score(AWAY_TEAM_ID, 2, 2, "PT01M00.00S", away_ids[1])

        session.commit()

        impacts = compute_player_quarter_plus_minus(session, "0099900003")
        assert impacts, "expected at least one per-quarter impact row"

        # Sum per-quarter +/- per player and assert against expected game +/-.
        # All home starters were on for the whole game, so each ends at 0.
        per_player_total = {}
        for row in impacts:
            per_player_total.setdefault(row.player_id, 0)
            per_player_total[row.player_id] += row.plus_minus

        # Every home starter: total +/- == 0 (8+4)-(5+7) = 0
        for pid in home_ids:
            assert per_player_total.get(pid) == 0, "home starter {} +/- mismatch".format(pid)
        # Every away starter: total +/- == 0
        for pid in away_ids:
            assert per_player_total.get(pid) == 0, "away starter {} +/- mismatch".format(pid)

        # Also assert the per-quarter splits look right for at least one player.
        home_q1 = [r for r in impacts if r.player_id == home_ids[0] and r.quarter == 1]
        home_q2 = [r for r in impacts if r.player_id == home_ids[0] and r.quarter == 2]
        assert home_q1 and home_q1[0].plus_minus == 3
        assert home_q2 and home_q2[0].plus_minus == -3
    finally:
        session.close()
