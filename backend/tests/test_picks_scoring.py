"""Sprint 78 — CF2 — Bracket Pick'em scoring tests.

Three end-to-end checks against an in-memory SQLite seeded with closed
playoff series, completed games, and a thin SeasonStat layer for awards:

1. All-correct picks return 100% accuracy with full points.
2. Half-correct picks return ~50% with proportional points.
3. The model bracket endpoint returns a valid prediction set for every
   seeded series.
"""
from pathlib import Path
import sys
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import (  # noqa: E402
    GameLog,
    Player,
    PlayoffSeries,
    SeasonStat,
    Team,
)
from models.picks import AwardPick, SeriesPick, UserPicks  # noqa: E402
from services.picks_scoring_service import (  # noqa: E402
    get_model_picks,
    score_user_picks,
)


SEASON = "2024-25"


def _make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return Session()


def _seed_two_closed_series(session):
    """Seed two closed Round-1 series and a closed Round-2 series.

    Bracket layout:
        R1 #1: BOS (top, seed 1) beats MIA (bottom, seed 8) in 5
        R1 #2: NYK (top, seed 2) beats CHI (bottom, seed 7) in 6
        R2 #1: BOS beats NYK in 7
    """
    teams = [
        (1610612738, "BOS", "Boston Celtics"),
        (1610612748, "MIA", "Miami Heat"),
        (1610612752, "NYK", "New York Knicks"),
        (1610612741, "CHI", "Chicago Bulls"),
    ]
    for tid, abbr, name in teams:
        session.add(Team(id=tid, abbreviation=abbr, name=name, conference="East"))

    # Players for award-pick scoring (BPM-ranked).
    session.add_all([
        Player(id=1, full_name="Alpha Star", is_active=True),
        Player(id=2, full_name="Beta Star", is_active=True),
    ])
    session.add_all([
        SeasonStat(
            player_id=1,
            season=SEASON,
            team_abbreviation="BOS",
            is_playoff=False,
            gp=70,
            pts_pg=30.0,
            bpm=10.5,
            net_rating=8.0,
            def_rating=110.0,
        ),
        SeasonStat(
            player_id=2,
            season=SEASON,
            team_abbreviation="NYK",
            is_playoff=False,
            gp=68,
            pts_pg=27.0,
            bpm=8.2,
            net_rating=4.0,
            def_rating=108.0,
        ),
    ])

    session.add_all([
        PlayoffSeries(
            season=SEASON,
            round=1,
            series_id=f"{SEASON}-E-R1-BOS-MIA",
            top_seed_team_id=1610612738,
            bottom_seed_team_id=1610612748,
            top_seed=1,
            bottom_seed=8,
            top_wins=4,
            bottom_wins=1,
            status="closed",
            winner_team_id=1610612738,
        ),
        PlayoffSeries(
            season=SEASON,
            round=1,
            series_id=f"{SEASON}-E-R1-NYK-CHI",
            top_seed_team_id=1610612752,
            bottom_seed_team_id=1610612741,
            top_seed=2,
            bottom_seed=7,
            top_wins=4,
            bottom_wins=2,
            status="closed",
            winner_team_id=1610612752,
        ),
        PlayoffSeries(
            season=SEASON,
            round=2,
            series_id=f"{SEASON}-E-R2-BOS-NYK",
            top_seed_team_id=1610612738,
            bottom_seed_team_id=1610612752,
            top_seed=1,
            bottom_seed=2,
            top_wins=4,
            bottom_wins=3,
            status="closed",
            winner_team_id=1610612738,
        ),
    ])

    # Five completed games for BOS-MIA series.
    for i, (h, a, hp, ap) in enumerate([
        (1610612738, 1610612748, 110, 99),
        (1610612738, 1610612748, 105, 102),
        (1610612748, 1610612738, 100, 95),
        (1610612738, 1610612748, 115, 100),
        (1610612748, 1610612738, 88, 112),
    ], start=1):
        session.add(GameLog(
            game_id=f"00425001{i:02d}",
            season=SEASON,
            game_date=date(2025, 4, 18 + i),
            home_team_id=h,
            away_team_id=a,
            home_score=hp,
            away_score=ap,
            season_type="Playoffs",
            series_id=f"{SEASON}-E-R1-BOS-MIA",
            series_game_num=i,
        ))

    # Six games for NYK-CHI.
    for i, (h, a, hp, ap) in enumerate([
        (1610612752, 1610612741, 108, 97),
        (1610612752, 1610612741, 95, 100),
        (1610612741, 1610612752, 90, 105),
        (1610612741, 1610612752, 99, 110),
        (1610612752, 1610612741, 88, 95),
        (1610612741, 1610612752, 95, 112),
    ], start=1):
        session.add(GameLog(
            game_id=f"00425002{i:02d}",
            season=SEASON,
            game_date=date(2025, 4, 18 + i),
            home_team_id=h,
            away_team_id=a,
            home_score=hp,
            away_score=ap,
            season_type="Playoffs",
            series_id=f"{SEASON}-E-R1-NYK-CHI",
            series_game_num=i,
        ))

    # Seven games for the Round-2 BOS-NYK series.
    for i, (h, a, hp, ap) in enumerate([
        (1610612738, 1610612752, 115, 110),
        (1610612738, 1610612752, 99, 102),
        (1610612752, 1610612738, 90, 100),
        (1610612752, 1610612738, 95, 90),
        (1610612738, 1610612752, 110, 105),
        (1610612752, 1610612738, 95, 90),
        (1610612738, 1610612752, 112, 100),
    ], start=1):
        session.add(GameLog(
            game_id=f"00425003{i:02d}",
            season=SEASON,
            game_date=date(2025, 5, i + 1),
            home_team_id=h,
            away_team_id=a,
            home_score=hp,
            away_score=ap,
            season_type="Playoffs",
            series_id=f"{SEASON}-E-R2-BOS-NYK",
            series_game_num=i,
        ))

    session.commit()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_all_correct_picks_returns_full_points():
    session = _make_session()
    try:
        _seed_two_closed_series(session)

        picks = UserPicks(
            season=SEASON,
            series_picks=[
                SeriesPick(series_id=f"{SEASON}-E-R1-BOS-MIA", winner_team_abbr="BOS", games=5),
                SeriesPick(series_id=f"{SEASON}-E-R1-NYK-CHI", winner_team_abbr="NYK", games=6),
                SeriesPick(series_id=f"{SEASON}-E-R2-BOS-NYK", winner_team_abbr="BOS", games=7),
            ],
        )
        scorecard = score_user_picks(session, picks)

        # Round-1 base 1pt + length bonus 1pt each = 2pt × 2 = 4pt.
        # Round-2 base 2pt + length bonus 1pt = 3pt.
        # Total possible = 7pt. All correct → 7pt.
        assert scorecard.total_points == 7
        assert scorecard.total_points_possible == 7
        assert scorecard.accuracy_pct == 100.0
        assert all(r.winner_status == "correct" for r in scorecard.series_results)
        assert all(r.games_status == "correct" for r in scorecard.series_results)
        # User vs model — user is perfect; delta should be ≥ 0.
        assert scorecard.head_to_head.user_correct == 3
        assert scorecard.head_to_head.delta_points >= 0
    finally:
        session.close()


def test_half_correct_picks_proportional():
    session = _make_session()
    try:
        _seed_two_closed_series(session)

        picks = UserPicks(
            season=SEASON,
            series_picks=[
                # Right winner, wrong games → base only.
                SeriesPick(series_id=f"{SEASON}-E-R1-BOS-MIA", winner_team_abbr="BOS", games=4),
                # Wrong winner → 0pt.
                SeriesPick(series_id=f"{SEASON}-E-R1-NYK-CHI", winner_team_abbr="CHI", games=7),
                # Right winner + right games → base + bonus.
                SeriesPick(series_id=f"{SEASON}-E-R2-BOS-NYK", winner_team_abbr="BOS", games=7),
            ],
        )
        scorecard = score_user_picks(session, picks)

        # 1 (BOS-MIA winner only) + 0 (CHI wrong) + 3 (BOS-NYK winner+length) = 4pt.
        # Possible = 7pt. Accuracy = 4/7 ≈ 57.1%.
        assert scorecard.total_points == 4
        assert scorecard.total_points_possible == 7
        assert 50.0 < scorecard.accuracy_pct < 60.0

        by_id = {r.series_id: r for r in scorecard.series_results}
        assert by_id[f"{SEASON}-E-R1-BOS-MIA"].winner_status == "correct"
        assert by_id[f"{SEASON}-E-R1-BOS-MIA"].games_status == "incorrect"
        assert by_id[f"{SEASON}-E-R1-NYK-CHI"].winner_status == "incorrect"
        assert by_id[f"{SEASON}-E-R2-BOS-NYK"].winner_status == "correct"
        assert by_id[f"{SEASON}-E-R2-BOS-NYK"].games_status == "correct"
    finally:
        session.close()


def test_model_picks_returns_valid_predictions():
    session = _make_session()
    try:
        _seed_two_closed_series(session)

        model = get_model_picks(session, SEASON)

        # Three series seeded → three model series picks.
        assert len(model.series_picks) == 3
        # Already-closed series: simulator returns 1.0/0.0, so the model
        # should pick the actual winner abbreviations.
        actuals = {
            f"{SEASON}-E-R1-BOS-MIA": "BOS",
            f"{SEASON}-E-R1-NYK-CHI": "NYK",
            f"{SEASON}-E-R2-BOS-NYK": "BOS",
        }
        for pick in model.series_picks:
            expected = actuals.get(pick.series_id)
            assert pick.winner_team_abbr == expected
            assert pick.round in (1, 2)

        # Four award picks (mvp/coy/dpoy/roy). All should resolve to one of
        # the seeded players (Alpha or Beta Star).
        assert len(model.award_picks) == 4
        names = {a.player_name for a in model.award_picks if a.player_name}
        assert names.issubset({"Alpha Star", "Beta Star"})
        # Alpha (BPM 10.5) is the BPM leader → MVP/DPOY/COY/ROY proxies all
        # pick Alpha in this seeded universe.
        mvp_pick = next(a for a in model.award_picks if a.award == "mvp")
        assert mvp_pick.player_name == "Alpha Star"
    finally:
        session.close()
