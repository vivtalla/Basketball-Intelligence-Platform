"""Tests for the Sprint 77 game-trajectory service.

Covers the WP curve and lead-tracker derivations end-to-end against tiny
in-memory PBP fixtures. The service is pure over the ``play_by_play`` table,
so we seed rows directly and avoid spinning up FastAPI.
"""

from datetime import date
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import GameLog, PlayByPlay, Team  # noqa: E402
from services.game_trajectory_service import (  # noqa: E402
    compute_lead_tracker,
    compute_win_probability,
)


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _seed_game_shell(session, game_id: str = "0022400777") -> None:
    home = session.query(Team).filter_by(id=1610612737).first()
    if home is None:
        home = Team(id=1610612737, abbreviation="ATL", name="Atlanta Hawks")
        session.add(home)
    away = session.query(Team).filter_by(id=1610612738).first()
    if away is None:
        away = Team(id=1610612738, abbreviation="BOS", name="Boston Celtics")
        session.add(away)
    session.flush()
    session.add(
        GameLog(
            game_id=game_id,
            season="2024-25",
            game_date=date(2025, 1, 1),
            home_team_id=home.id,
            away_team_id=away.id,
            home_score=0,
            away_score=0,
            season_type="Regular Season",
        )
    )
    session.commit()


def _clock(minutes: int, seconds: float = 0.0) -> str:
    return "PT{:02d}M{:05.2f}S".format(minutes, seconds)


def _add_event(
    session,
    *,
    game_id: str,
    action_number: int,
    period: int,
    clock: str,
    score_home: int,
    score_away: int,
    action_type: str = "2pt",
    sub_type: str = "made",
    team_id: int = 1610612737,
) -> None:
    session.add(
        PlayByPlay(
            game_id=game_id,
            action_number=action_number,
            period=period,
            clock=clock,
            team_id=team_id,
            player_id=None,
            action_type=action_type,
            sub_type=sub_type,
            description="seeded",
            score_home=score_home,
            score_away=score_away,
        )
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_wp_curve_drifts_toward_winner():
    """Home wins by 20: final WP for home should saturate above 0.95."""
    session = _make_session()
    try:
        game_id = "0022400777"
        _seed_game_shell(session, game_id)

        # Build a quick scoring sequence where the home team pulls away in Q4.
        # Final score 120-100 (home +20).
        events = [
            # Q1
            (1, _clock(11, 30), 2, 0, "2pt"),
            (2, _clock(10, 0), 2, 2, "2pt"),
            (3, _clock(8, 0), 5, 2, "3pt"),
            (4, _clock(0, 5), 28, 25, "2pt"),
            # Q2
            (5, _clock(11, 0), 30, 25, "2pt"),
            (6, _clock(0, 5), 58, 53, "2pt"),
            # Q3
            (7, _clock(11, 0), 60, 53, "2pt"),
            (8, _clock(0, 5), 90, 78, "2pt"),
            # Q4 — home buries the game
            (9, _clock(8, 0), 95, 80, "2pt"),
            (10, _clock(4, 0), 110, 90, "2pt"),
            (11, _clock(1, 30), 117, 95, "3pt"),
            (12, _clock(0, 1), 120, 100, "2pt"),
        ]
        for (action_number, clock, sh, sa, action_type) in events:
            period = 1
            if action_number > 4:
                period = 2
            if action_number > 6:
                period = 3
            if action_number > 8:
                period = 4
            _add_event(
                session,
                game_id=game_id,
                action_number=action_number,
                period=period,
                clock=clock,
                score_home=sh,
                score_away=sa,
                action_type=action_type,
            )
        session.commit()

        points = compute_win_probability(session, game_id)
        assert points, "expected at least one WP point"
        final = points[-1]
        assert final.wp_home > 0.95, (
            "home WP should saturate >0.95 after a 20-point lead in clutch; "
            "got wp_home={:.4f}".format(final.wp_home)
        )
    finally:
        session.close()


def test_wp_swing_event_flagged_on_big_play():
    """8-0 home run inside ~90 seconds should flag at least one swing event."""
    session = _make_session()
    try:
        game_id = "0022400778"
        _seed_game_shell(session, game_id)

        # Tight tied game in clutch then an 8-0 home run.
        events = [
            (1, 1, _clock(11, 30), 2, 0, "2pt"),
            (2, 1, _clock(10, 0), 2, 2, "2pt"),
            (3, 2, _clock(0, 5), 50, 50, "2pt"),
            (4, 3, _clock(0, 5), 75, 75, "2pt"),
            # Q4 score is tied at 95-95 with 90s left, then home 8-0 run.
            (5, 4, _clock(1, 30), 95, 95, "2pt"),
            (6, 4, _clock(1, 15), 98, 95, "3pt"),
            (7, 4, _clock(0, 50), 100, 95, "2pt"),
            (8, 4, _clock(0, 30), 103, 95, "3pt"),
        ]
        for (action_number, period, clock, sh, sa, action_type) in events:
            _add_event(
                session,
                game_id=game_id,
                action_number=action_number,
                period=period,
                clock=clock,
                score_home=sh,
                score_away=sa,
                action_type=action_type,
            )
        session.commit()

        points = compute_win_probability(session, game_id)
        labeled = [p for p in points if p.event]
        assert labeled, "expected at least one swing-labeled WP point during the 8-0 clutch run"

        # Verify the swing was actually >= 12pp by re-walking the points.
        max_swing = 0.0
        prev = None
        for p in points:
            if prev is not None:
                max_swing = max(max_swing, abs(p.wp_home - prev))
            prev = p.wp_home
        assert max_swing >= 0.12, (
            "expected at least one 12pp swing in the WP series; max was {:.3f}".format(max_swing)
        )
    finally:
        session.close()


def test_lead_tracker_length_48_for_regulation_game():
    """Regulation game ends after period 4 -> tracker has 48 entries."""
    session = _make_session()
    try:
        game_id = "0022400779"
        _seed_game_shell(session, game_id)

        # Sparse scoring across all four quarters; final play in Q4 0:01.
        events = [
            (1, 1, _clock(11, 0), 2, 0),
            (2, 1, _clock(0, 30), 25, 22),
            (3, 2, _clock(0, 30), 50, 47),
            (4, 3, _clock(0, 30), 75, 72),
            (5, 4, _clock(11, 30), 77, 72),
            (6, 4, _clock(0, 1), 102, 99),
        ]
        for (action_number, period, clock, sh, sa) in events:
            _add_event(
                session,
                game_id=game_id,
                action_number=action_number,
                period=period,
                clock=clock,
                score_home=sh,
                score_away=sa,
            )
        session.commit()

        tracker = compute_lead_tracker(session, game_id)
        assert len(tracker) == 48, (
            "regulation tracker should be exactly 48 entries; got {:d}".format(len(tracker))
        )
    finally:
        session.close()


def test_wp_series_provides_enough_signal_for_story_timeline():
    """Sprint 78 (CF4): a regulation game with several lead changes
    should produce both (a) a non-trivial WP curve and (b) at least one
    swing-labelled point for the front-end story-timeline ranker.

    The Game Story Mode timeline computes
        narrative_score = |wp_delta| * 100 + lead_impact * 0.5
    from the curve, so we assert the curve carries enough variation
    (>= 8 points; >= 1 labelled swing; observed swing magnitude >= 5pp)
    to seed a meaningful story.
    """
    session = _make_session()
    try:
        game_id = "0022400781"
        _seed_game_shell(session, game_id)

        # Tight game, two lead changes, away closing strong, with a
        # late clutch run that the trajectory service should label.
        events = [
            (1, 1, _clock(11, 0), 2, 0),
            (2, 1, _clock(8, 0), 5, 6),
            (3, 1, _clock(0, 5), 22, 24),
            (4, 2, _clock(8, 0), 35, 38),
            (5, 2, _clock(0, 5), 50, 52),
            (6, 3, _clock(6, 0), 65, 68),
            (7, 3, _clock(0, 5), 78, 79),
            # Q4 — tied at 95-95 with 90s left, then away 9-0 run.
            (8, 4, _clock(2, 0), 95, 95),
            (9, 4, _clock(1, 30), 95, 98, "3pt"),
            (10, 4, _clock(1, 0), 95, 101, "3pt"),
            (11, 4, _clock(0, 30), 95, 104, "3pt"),
            (12, 4, _clock(0, 1), 97, 104, "2pt"),
        ]
        for ev in events:
            action_number, period, clock = ev[0], ev[1], ev[2]
            sh, sa = ev[3], ev[4]
            action_type = ev[5] if len(ev) > 5 else "2pt"
            _add_event(
                session,
                game_id=game_id,
                action_number=action_number,
                period=period,
                clock=clock,
                score_home=sh,
                score_away=sa,
                action_type=action_type,
            )
        session.commit()

        points = compute_win_probability(session, game_id)
        # (a) curve has enough resolution for a 10-card timeline.
        assert len(points) >= 8, (
            "story timeline expects at least ~8 WP points; got {:d}".format(
                len(points)
            )
        )
        # (b) at least one swing is labelled — the front-end picks
        # these as the dominant narrative signal.
        labelled = [p for p in points if p.event]
        assert labelled, (
            "story timeline expects at least one swing-labelled WP point"
        )
        # (c) observed swing magnitude is meaningful.
        max_swing = 0.0
        prev = None
        for p in points:
            if prev is not None:
                max_swing = max(max_swing, abs(p.wp_home - prev))
            prev = p.wp_home
        assert max_swing >= 0.05, (
            "story timeline expects at least one >=5pp WP swing; max was {:.3f}".format(
                max_swing
            )
        )
    finally:
        session.close()


def test_lead_tracker_tied_at_tip():
    """First minute boundary always reports a 0 lead — neither team has scored at tip."""
    session = _make_session()
    try:
        game_id = "0022400780"
        _seed_game_shell(session, game_id)

        # First made bucket is 30 seconds into Q1 — at minute=0 the lead is 0.
        _add_event(
            session,
            game_id=game_id,
            action_number=1,
            period=1,
            clock=_clock(11, 30),
            score_home=2,
            score_away=0,
        )
        _add_event(
            session,
            game_id=game_id,
            action_number=2,
            period=4,
            clock=_clock(0, 1),
            score_home=110,
            score_away=100,
        )
        session.commit()

        tracker = compute_lead_tracker(session, game_id)
        assert tracker, "expected a non-empty tracker"
        first = tracker[0]
        assert first.minute == 0
        assert first.home_lead == 0
    finally:
        session.close()
