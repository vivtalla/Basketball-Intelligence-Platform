"""Sprint 94 — On/Off Impact Command Center service tests."""
from pathlib import Path
import sys

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import LineupStats, Player, PlayerOnOff, SeasonStat, Team, TeamSeasonStat  # noqa: E402
from models.stats import ConfidenceTier, ImpactClassification  # noqa: E402
from services.on_off_impact_service import (  # noqa: E402
    _classify_impact,
    _confidence_tier,
    build_enhanced_on_off,
    build_enhanced_on_off_leaderboard,
)


SEASON = "2024-25"


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return Session()


def _team(db, tid: int, abbr: str):
    t = Team(id=tid, abbreviation=abbr, name="{0} Team".format(abbr))
    db.add(t)


def _player(db, pid: int, name: str, team_id: int = None):
    db.add(Player(id=pid, full_name=name, position="Forward", team_id=team_id))


def _on_off(db, pid: int, on_minutes: float = 900.0, **kwargs):
    defaults = dict(
        player_id=pid,
        season=SEASON,
        is_playoff=False,
        on_minutes=on_minutes,
        off_minutes=500.0,
        on_net_rating=8.0,
        off_net_rating=2.0,
        on_off_net=6.0,
        on_ortg=112.0,
        on_drtg=104.0,
        off_ortg=108.0,
        off_drtg=106.0,
    )
    defaults.update(kwargs)
    db.add(PlayerOnOff(**defaults))


def _team_season(db, team_id: int, net_rating: float = 4.0):
    db.add(TeamSeasonStat(
        team_id=team_id,
        season=SEASON,
        is_playoff=False,
        net_rating=net_rating,
        off_rating=112.0,
        def_rating=108.0,
        gp=60,
        w=35,
        l=25,
        w_pct=0.583,
    ))


def _season_stat(db, pid: int, team_abbr: str, rapm: float = None,
                 epm: float = None, pipm: float = None, gp: int = 70):
    db.add(SeasonStat(
        player_id=pid,
        season=SEASON,
        team_abbreviation=team_abbr,
        is_playoff=False,
        gp=gp,
        min_pg=28.0,
        pts_pg=14.0,
        reb_pg=5.0,
        ast_pg=3.0,
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
        rapm=rapm,
        epm=epm,
        pipm=pipm,
    ))


def _lineup(db, lineup_key: str, team_id: int, possessions: int, net_rating: float):
    db.add(LineupStats(
        lineup_key=lineup_key,
        season=SEASON,
        team_id=team_id,
        is_playoff=False,
        possessions=possessions,
        net_rating=net_rating,
        ortg=112.0,
        drtg=108.0,
        minutes=float(possessions) / 4,
        plus_minus=net_rating * possessions / 100,
    ))


# ---------------------------------------------------------------------------
# Unit tests: _classify_impact
# ---------------------------------------------------------------------------

def test_classify_two_way_elite():
    result = _classify_impact(4.0, 4.0)
    assert result == ImpactClassification.TWO_WAY_ELITE


def test_classify_offensive_engine():
    result = _classify_impact(4.0, 0.5)
    assert result == ImpactClassification.OFFENSIVE_ENGINE


def test_classify_defensive_anchor():
    result = _classify_impact(0.5, 4.0)
    assert result == ImpactClassification.DEFENSIVE_ANCHOR


def test_classify_liability():
    result = _classify_impact(-3.0, -3.0)
    assert result == ImpactClassification.LIABILITY


def test_classify_none_when_none_inputs():
    assert _classify_impact(None, None) is None
    assert _classify_impact(4.0, None) is None
    assert _classify_impact(None, 4.0) is None


# ---------------------------------------------------------------------------
# Unit tests: _confidence_tier
# ---------------------------------------------------------------------------

def test_confidence_tier_thresholds():
    assert _confidence_tier(900.0) == ConfidenceTier.HIGH
    assert _confidence_tier(800.0) == ConfidenceTier.HIGH
    assert _confidence_tier(600.0) == ConfidenceTier.MEDIUM
    assert _confidence_tier(400.0) == ConfidenceTier.MEDIUM
    assert _confidence_tier(300.0) == ConfidenceTier.LOW
    assert _confidence_tier(200.0) == ConfidenceTier.LOW
    assert _confidence_tier(100.0) == ConfidenceTier.INSUFFICIENT
    assert _confidence_tier(None) == ConfidenceTier.INSUFFICIENT


# ---------------------------------------------------------------------------
# Integration tests: build_enhanced_on_off
# ---------------------------------------------------------------------------

def test_build_enhanced_on_off_decomposition():
    """Decomposition fields are computed correctly from existing on/off values."""
    db = make_session()
    _team(db, 1, "LAL")
    _player(db, 1, "Test Player")
    _on_off(db, 1, on_minutes=900.0,
            on_ortg=112.0, on_drtg=104.0, off_ortg=108.0, off_drtg=108.0,
            on_net_rating=8.0, off_net_rating=0.0, on_off_net=8.0)
    _team_season(db, 1, net_rating=4.0)
    _season_stat(db, 1, "LAL")
    db.commit()

    result = build_enhanced_on_off(db, player_id=1, season=SEASON)

    assert result.decomposition is not None
    assert result.decomposition.ortg_impact == 4.0   # 112 - 108
    assert result.decomposition.drtg_impact == 4.0   # 108 - 104
    assert result.decomposition.marginal_net == 4.0  # 8.0 - 4.0 (team_net)
    assert result.impact_classification == ImpactClassification.TWO_WAY_ELITE
    assert result.confidence_tier == ConfidenceTier.HIGH
    assert result.team_net_rating == 4.0


def test_build_enhanced_on_off_lineup_slots():
    """Top/worst lineups are filtered to >=100 poss and false-positive LIKE matches."""
    db = make_session()
    _team(db, 1, "BOS")
    _player(db, 12, "Player Twelve")
    _player(db, 50, "Teammate A")
    _player(db, 80, "Teammate B")
    _player(db, 120, "Teammate C")  # lineup_key "112-120-130-140-150": false positive for 12
    _on_off(db, 12, on_minutes=900.0)
    _team_season(db, 1, net_rating=2.0)
    _season_stat(db, 12, "BOS")

    # True positive — player 12 is in key
    _lineup(db, "12-50-80-100-200", 1, possessions=150, net_rating=10.0)
    _lineup(db, "12-50-80-100-300", 1, possessions=120, net_rating=5.0)
    # Below threshold — should be excluded
    _lineup(db, "12-50-80-100-400", 1, possessions=50, net_rating=20.0)
    # False positive — "12" appears inside "120" and "212"
    _lineup(db, "120-212-300-400-500", 1, possessions=200, net_rating=15.0)
    db.commit()

    result = build_enhanced_on_off(db, player_id=12, season=SEASON)

    assert len(result.top_lineups) == 2
    assert all(p >= 100 for slot in result.top_lineups for p in [slot.possessions])
    assert all(12 in slot.player_ids for slot in result.top_lineups)


def test_build_enhanced_on_off_missing_team_stat():
    """Marginal net is None when no TeamSeasonStat exists for the player's team."""
    db = make_session()
    _team(db, 1, "GSW")
    _player(db, 1, "Player One")
    _on_off(db, 1, on_minutes=900.0)
    _season_stat(db, 1, "GSW")
    # No TeamSeasonStat inserted
    db.commit()

    result = build_enhanced_on_off(db, player_id=1, season=SEASON)

    assert result.decomposition is not None
    assert result.decomposition.marginal_net is None
    assert result.team_net_rating is None


def test_build_enhanced_on_off_external_validation_consistent():
    """Agreement note says 'Consistent' when RAPM and raw on/off are close."""
    db = make_session()
    _team(db, 1, "PHX")
    _player(db, 1, "Player One")
    _on_off(db, 1, on_minutes=900.0, on_off_net=6.0)
    _team_season(db, 1, net_rating=3.0)
    _season_stat(db, 1, "PHX", rapm=5.5)
    db.commit()

    result = build_enhanced_on_off(db, player_id=1, season=SEASON)

    assert result.external_validation is not None
    assert result.external_validation.rapm == 5.5
    assert result.external_validation.agreement_note is not None
    assert "Consistent" in result.external_validation.agreement_note


def test_build_enhanced_on_off_external_validation_diverges():
    """Agreement note says 'Diverges' when gap between RAPM and on/off is >=8."""
    db = make_session()
    _team(db, 1, "MIA")
    _player(db, 1, "Player One")
    _on_off(db, 1, on_minutes=900.0, on_off_net=15.0)
    _team_season(db, 1, net_rating=2.0)
    _season_stat(db, 1, "MIA", rapm=3.0)
    db.commit()

    result = build_enhanced_on_off(db, player_id=1, season=SEASON)

    assert result.external_validation is not None
    assert result.external_validation.agreement_note is not None
    assert "Diverges" in result.external_validation.agreement_note


def test_build_enhanced_on_off_not_found():
    """Raises 404 when no PlayerOnOff row exists."""
    db = make_session()
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        build_enhanced_on_off(db, player_id=9999, season=SEASON)
    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Integration tests: build_enhanced_on_off_leaderboard
# ---------------------------------------------------------------------------

def test_build_leaderboard_min_minutes_filter():
    """Players below min_minutes threshold are excluded."""
    db = make_session()
    _team(db, 1, "DEN")
    _player(db, 1, "Player High Min")
    _player(db, 2, "Player Low Min")
    _on_off(db, 1, on_minutes=300.0, on_off_net=5.0)
    _on_off(db, 2, on_minutes=150.0, on_off_net=8.0)
    db.commit()

    result = build_enhanced_on_off_leaderboard(db, season=SEASON, min_minutes=200.0)

    assert len(result.players) == 1
    assert result.players[0].player_id == 1


def test_build_leaderboard_ordered_by_on_off_net():
    """Leaderboard entries are ordered by on_off_net descending."""
    db = make_session()
    _team(db, 1, "MIL")
    for i, (pid, on_off_val) in enumerate([(1, 3.0), (2, 9.0), (3, 6.0)]):
        _player(db, pid, "Player {0}".format(pid))
        _on_off(db, pid, on_minutes=500.0, on_off_net=on_off_val)
    db.commit()

    result = build_enhanced_on_off_leaderboard(db, season=SEASON, min_minutes=200.0)

    assert len(result.players) == 3
    assert result.players[0].on_off_net == 9.0
    assert result.players[1].on_off_net == 6.0
    assert result.players[2].on_off_net == 3.0


def test_build_leaderboard_ortg_drtg_impact_computed():
    """ortg_impact and drtg_impact are correctly computed per entry."""
    db = make_session()
    _team(db, 1, "CLE")
    _player(db, 1, "Player One")
    _on_off(db, 1, on_minutes=600.0,
            on_ortg=114.0, off_ortg=110.0,
            on_drtg=105.0, off_drtg=110.0,
            on_off_net=4.0)
    db.commit()

    result = build_enhanced_on_off_leaderboard(db, season=SEASON, min_minutes=200.0)

    entry = result.players[0]
    assert entry.ortg_impact == 4.0   # 114 - 110
    assert entry.drtg_impact == 5.0   # 110 - 105


def test_build_leaderboard_external_metrics_surfaced():
    """rapm and epm from SeasonStat appear in leaderboard entries when available."""
    db = make_session()
    _team(db, 1, "OKC")
    _player(db, 1, "Player One")
    _player(db, 2, "Player Two")
    _on_off(db, 1, on_minutes=600.0, on_off_net=5.0)
    _on_off(db, 2, on_minutes=600.0, on_off_net=3.0)
    _season_stat(db, 1, "OKC", rapm=4.2, epm=3.8)
    # Player 2 has no SeasonStat
    db.commit()

    result = build_enhanced_on_off_leaderboard(db, season=SEASON, min_minutes=200.0)

    p1 = next(e for e in result.players if e.player_id == 1)
    p2 = next(e for e in result.players if e.player_id == 2)
    assert p1.rapm == 4.2
    assert p1.epm == 3.8
    assert p2.rapm is None
    assert p2.epm is None


def test_lineup_slot_false_positive_filter():
    """LIKE match on player_id=12 must not return lineup_key='112-120-130-140-150'."""
    db = make_session()
    _team(db, 1, "SAS")
    _player(db, 12, "Player Twelve")
    _on_off(db, 12, on_minutes=900.0)
    _season_stat(db, 12, "SAS")
    _team_season(db, 1, net_rating=1.0)

    # False positive: "12" appears in "120" and "112" — must be excluded
    _lineup(db, "112-120-130-140-150", 1, possessions=200, net_rating=8.0)
    # True positive
    _lineup(db, "12-50-80-100-200", 1, possessions=200, net_rating=6.0)
    db.commit()

    result = build_enhanced_on_off(db, player_id=12, season=SEASON)

    assert len(result.top_lineups) == 1
    assert result.top_lineups[0].lineup_key == "12-50-80-100-200"
