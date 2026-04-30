"""Sprint 81 — award modifier materialization + calibration activation tests."""
from __future__ import annotations

import os
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from data.materialize_award_modifiers import (  # noqa: E402
    _basketball_value,
    _eligibility_pressure,
    _team_framing,
    materialize,
)
from db.models import (  # noqa: E402
    AwardCaseCandidate,
    AwardVote,
    Base,
    Player,
    SeasonStat,
    Team,
    TeamSeasonStat,
)
from services.award_calibration_service import (  # noqa: E402
    DEFAULT_AWARD_CASE_WEIGHTS,
    calibrate_award_case_weights,
)


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()
    engine.dispose()


def _seed_player(session, player_id: int, name: str) -> Player:
    p = Player(id=player_id, full_name=name, first_name=name.split()[0], last_name=name.split()[-1])
    session.add(p)
    return p


def _seed_stat(
    session,
    *,
    player_id: int,
    season: str,
    team_abbr: str = "BOS",
    pts: float = 25.0,
    ast: float = 5.0,
    reb: float = 7.0,
    ts_pct: float = 0.60,
    gp: int = 75,
) -> SeasonStat:
    stat = SeasonStat(
        player_id=player_id,
        season=season,
        team_abbreviation=team_abbr,
        is_playoff=False,
        pts=pts,
        ast=ast,
        reb=reb,
        ts_pct=ts_pct,
        gp=gp,
    )
    session.add(stat)
    return stat


def _seed_team_record(
    session, *, season: str, team_abbr: str, wins: int, losses: int
) -> None:
    team_id = abs(hash(team_abbr)) % 1_000_000
    if not session.query(Team).filter_by(id=team_id).first():
        session.add(Team(id=team_id, abbreviation=team_abbr, name=team_abbr))
        session.flush()
    session.add(
        TeamSeasonStat(
            team_id=team_id,
            season=season,
            is_playoff=False,
            w=wins,
            l=losses,
        )
    )


# ---------------------------------------------------------------------------
# Pure-math primitives
# ---------------------------------------------------------------------------


def test_basketball_value_scales_with_production_and_efficiency(session) -> None:
    """Higher production + efficiency = higher Basketball Value."""
    elite = SeasonStat(player_id=1, season="2023-24", team_abbreviation="DEN",
                      is_playoff=False, pts=30, ast=8, reb=10, ts_pct=0.65, gp=80)
    average = SeasonStat(player_id=2, season="2023-24", team_abbreviation="DEN",
                        is_playoff=False, pts=15, ast=3, reb=4, ts_pct=0.55, gp=80)
    assert _basketball_value(elite) > _basketball_value(average)


def test_basketball_value_discounts_low_gp(session) -> None:
    """Player who played 30 games gets a reliability discount vs 80 games."""
    full_season = SeasonStat(player_id=1, season="2023-24", team_abbreviation="LAL",
                             is_playoff=False, pts=25, ast=5, reb=7, ts_pct=0.60, gp=80)
    half_season = SeasonStat(player_id=2, season="2023-24", team_abbreviation="LAL",
                             is_playoff=False, pts=25, ast=5, reb=7, ts_pct=0.60, gp=30)
    assert _basketball_value(full_season) > _basketball_value(half_season)


def test_team_framing_centered_on_500() -> None:
    index = {("BOS", "2023-24"): (60, 22), ("LAL", "2023-24"): (41, 41), ("DET", "2023-24"): (15, 67)}
    bos_stat = SeasonStat(player_id=1, season="2023-24", team_abbreviation="BOS", is_playoff=False)
    lal_stat = SeasonStat(player_id=1, season="2023-24", team_abbreviation="LAL", is_playoff=False)
    det_stat = SeasonStat(player_id=1, season="2023-24", team_abbreviation="DET", is_playoff=False)
    assert _team_framing(bos_stat, index) > 0
    assert abs(_team_framing(lal_stat, index)) < 0.01  # ~0
    assert _team_framing(det_stat, index) < 0


def test_eligibility_pressure_penalizes_low_gp() -> None:
    healthy = SeasonStat(player_id=1, season="2023-24", team_abbreviation="BOS",
                        is_playoff=False, gp=75, min_total=2400)  # 32 mpg
    sparse = SeasonStat(player_id=2, season="2023-24", team_abbreviation="BOS",
                       is_playoff=False, gp=30, min_total=900)
    assert _eligibility_pressure(healthy) == 0.0
    assert _eligibility_pressure(sparse) <= -1.0


# ---------------------------------------------------------------------------
# Full materialization driver
# ---------------------------------------------------------------------------


def test_materialize_creates_one_row_per_award_voting_entry(session) -> None:
    _seed_player(session, 100, "Player A")
    _seed_stat(session, player_id=100, season="2022-23", team_abbr="DEN",
               pts=29.0, ast=10.0, reb=11.0, ts_pct=0.66, gp=79)
    _seed_team_record(session, season="2022-23", team_abbr="DEN", wins=53, losses=29)
    session.add(AwardVote(
        player_id=100, season="2022-23", award_type="MVP",
        ballot_position=1, voter_count=100, total_award_points=900.0,
    ))
    session.commit()

    summary = materialize(session, verbose=False)

    assert summary["inserted"] == 1
    cand = session.query(AwardCaseCandidate).first()
    assert cand.player_id == 100
    assert cand.season == "2022-23"
    assert cand.basketball_value > 20.0
    assert cand.modifier_team_framing > 0  # winning team


def test_materialize_idempotent(session) -> None:
    _seed_player(session, 200, "Player B")
    _seed_stat(session, player_id=200, season="2023-24")
    session.add(AwardVote(
        player_id=200, season="2023-24", award_type="MVP",
        ballot_position=2, voter_count=100, total_award_points=400.0,
    ))
    session.commit()

    materialize(session, verbose=False)
    first_count = session.query(AwardCaseCandidate).count()
    materialize(session, verbose=False)
    second_count = session.query(AwardCaseCandidate).count()

    assert first_count == 1
    assert second_count == 1


def test_materialize_skips_player_seasons_without_stats(session) -> None:
    """No SeasonStat → row is skipped (not inserted with junk values)."""
    _seed_player(session, 300, "Player C")
    session.add(AwardVote(
        player_id=300, season="2010-11", award_type="MVP",
        ballot_position=1, voter_count=100, total_award_points=500.0,
    ))
    session.commit()

    summary = materialize(session, verbose=False)
    assert summary["inserted"] == 0
    assert summary["skipped_no_season_stat"] == 1


# ---------------------------------------------------------------------------
# Calibration activation
# ---------------------------------------------------------------------------


def test_calibration_returns_pending_when_candidates_table_empty(session) -> None:
    """award_voting populated + award_case_candidates empty → calibration_pending=True."""
    _seed_player(session, 400, "Player D")
    session.add(AwardVote(
        player_id=400, season="2023-24", award_type="MVP",
        ballot_position=1, voter_count=100, total_award_points=900.0,
    ))
    session.commit()

    result = calibrate_award_case_weights(session)
    assert result["calibration_pending"] is True
    assert result["weights"] == DEFAULT_AWARD_CASE_WEIGHTS
    assert any("award_case_candidates is empty" in note for note in result["notes"])


def test_calibration_returns_pending_when_too_few_seasons(session) -> None:
    """< MIN_FOLDS_REQUIRED seasons → calibration_pending=True."""
    for i, (player_id, name) in enumerate(((10, "P1"), (11, "P2"), (12, "P3"))):
        _seed_player(session, player_id, name)
        season = "202{0}-2{1}".format(i, i + 1)
        _seed_stat(session, player_id=player_id, season=season)
        session.add(AwardVote(
            player_id=player_id, season=season, award_type="MVP",
            ballot_position=1, voter_count=100, total_award_points=900.0 - i * 100,
        ))
    session.commit()

    materialize(session, verbose=False)
    result = calibrate_award_case_weights(session)

    assert result["calibration_pending"] is True
    assert result["fold_count"] == 3
    assert any("Only 3 season(s)" in note for note in result["notes"])
