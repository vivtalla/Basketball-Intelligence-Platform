"""Sprint 78 — FO2 Free Agency Workspace tests."""
from datetime import date, timedelta
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import Player, PlayerContract, SeasonStat, Team  # noqa: E402
from services.free_agency_service import (  # noqa: E402
    compute_expiring_contracts,
    tier_for_contract,
    top_team_fits_for_player,
)


SEASON = "2025-26"


def make_session():
    engine = create_engine("sqlite:///:memory:")
    TS = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return TS()


def _team(db, tid: int, abbr: str, name: str) -> Team:
    team = Team(id=tid, abbreviation=abbr, name=name)
    db.add(team)
    return team


def _player(db, pid: int, name: str, position: str = "Forward", team_id=None) -> Player:
    player = Player(
        id=pid,
        full_name=name,
        position=position,
        team_id=team_id,
        is_active=True,
    )
    db.add(player)
    return player


def _contract(
    db,
    *,
    player_id: int,
    salary: int,
    season: str = SEASON,
    years_remaining: int = 1,
    expires_on=None,
    team_id=None,
    is_player_option: bool = False,
):
    db.add(
        PlayerContract(
            player_id=player_id,
            season=season,
            salary=salary,
            years_remaining=years_remaining,
            is_player_option=is_player_option,
            is_team_option=False,
            is_non_guaranteed=False,
            no_trade_clause=False,
            contract_type="standard",
            expires_on=expires_on,
            team_id=team_id,
            source="manual",
        )
    )


def _row(db, pid: int, team: str, season: str = SEASON, **stats):
    defaults = dict(
        player_id=pid,
        season=season,
        team_abbreviation=team,
        is_playoff=False,
        gp=70,
        min_pg=30.0,
        pts_pg=15.0,
        reb_pg=5.0,
        ast_pg=4.0,
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
        usg_pct=20.0,
        ts_pct=0.56,
        efg_pct=0.53,
        per=15.0,
        bpm=0.0,
        off_rating=112.0,
        def_rating=112.0,
        net_rating=0.0,
        pace=100.0,
        pie=0.10,
        darko=0.0,
        epm=0.0,
        rapm=0.0,
        obpm=0.0,
        dbpm=0.0,
        ftr=0.30,
        par3=0.40,
        ast_tov=2.0,
        oreb_pct=4.0,
    )
    defaults.update(stats)
    db.add(SeasonStat(**defaults))


def test_tier_for_contract_buckets_correctly():
    # Max tier — Tatum/Booker territory
    assert tier_for_contract(45_000_000) == "max"
    # Above-MLE veteran
    assert tier_for_contract(20_000_000) == "above_mid"
    # Mid-level exception band
    assert tier_for_contract(8_000_000) == "mid_level"
    # Veteran minimum
    assert tier_for_contract(2_000_000) == "minimum"
    # Two-way / unknown
    assert tier_for_contract(500_000) == "two_way"
    assert tier_for_contract(None) == "two_way"
    assert tier_for_contract(0) == "two_way"


def test_compute_expiring_contracts_returns_empty_when_table_empty():
    db = make_session()
    try:
        # Nothing in player_contracts.
        response = compute_expiring_contracts(db, season=SEASON)
        assert response.is_empty_dataset is True
        assert response.contracts == []
        assert response.total_count == 0
        assert response.filtered_count == 0
        assert response.methodology.version == "free_agency_v1"
        assert response.warnings, "expected an empty-state warning"
    finally:
        db.close()


def test_compute_expiring_contracts_buckets_by_tier():
    db = make_session()
    try:
        _team(db, 1, "BOS", "Boston Celtics")
        _team(db, 2, "LAL", "Los Angeles Lakers")
        _player(db, 100, "Max Star", position="Forward", team_id=1)
        _player(db, 101, "Mid Veteran", position="Guard", team_id=2)
        _player(db, 102, "Vet Min", position="Center", team_id=1)
        # Multi-year deal — should NOT appear.
        _player(db, 103, "Long Deal", position="Forward", team_id=2)
        db.commit()

        _contract(db, player_id=100, salary=45_000_000, years_remaining=1, team_id=1)
        _contract(db, player_id=101, salary=8_000_000, years_remaining=1, team_id=2)
        _contract(db, player_id=102, salary=1_500_000, years_remaining=0, team_id=1)
        _contract(db, player_id=103, salary=30_000_000, years_remaining=4, team_id=2)
        db.commit()

        # SeasonStats so production fields render.
        _row(db, 100, "BOS", pts_pg=27.0, usg_pct=30.0, ts_pct=0.62)
        _row(db, 101, "LAL", pts_pg=14.0, usg_pct=20.0, ts_pct=0.55)
        _row(db, 102, "BOS", pts_pg=6.0, usg_pct=12.0)
        _row(db, 103, "LAL", pts_pg=24.0, usg_pct=28.0)
        db.commit()

        response = compute_expiring_contracts(db, season=SEASON)
        assert response.is_empty_dataset is False
        assert response.total_count == 4
        assert response.filtered_count == 3  # Long Deal excluded
        ids = sorted(c.player_id for c in response.contracts)
        assert ids == [100, 101, 102]

        tiers = {c.player_id: c.tier for c in response.contracts}
        assert tiers[100] == "max"
        assert tiers[101] == "mid_level"
        assert tiers[102] == "minimum"

        # Sort: salary desc -> Max Star first.
        assert response.contracts[0].player_id == 100
        # Production hydrated.
        assert response.contracts[0].pts_pg == 27.0
        # Available tiers reflects the bucketed set.
        assert "max" in response.available_tiers
        assert "mid_level" in response.available_tiers

        # Tier filter narrows correctly.
        max_only = compute_expiring_contracts(db, season=SEASON, tier="max")
        assert max_only.filtered_count == 1
        assert max_only.contracts[0].player_id == 100

        # Position filter narrows correctly (case-insensitive substring).
        guards = compute_expiring_contracts(db, season=SEASON, position="guard")
        guard_ids = [c.player_id for c in guards.contracts]
        assert guard_ids == [101]
    finally:
        db.close()


def test_compute_expiring_contracts_uses_expires_on_window():
    db = make_session()
    try:
        _team(db, 1, "BOS", "Boston Celtics")
        _player(db, 200, "Future Expiry", position="Forward", team_id=1)
        _player(db, 201, "Far Expiry", position="Forward", team_id=1)
        db.commit()

        soon = date.today() + timedelta(days=180)
        far = date.today() + timedelta(days=720)
        # years_remaining=2 to fail the years gate; only the date gate should
        # admit the "soon" expiry.
        _contract(db, player_id=200, salary=10_000_000, years_remaining=2, expires_on=soon, team_id=1)
        _contract(db, player_id=201, salary=10_000_000, years_remaining=2, expires_on=far, team_id=1)
        db.commit()

        response = compute_expiring_contracts(db, season=SEASON)
        ids = [c.player_id for c in response.contracts]
        assert ids == [200]
    finally:
        db.close()


def _seed_fits_case(db):
    """A small league with enough roster context so team_fit_v3 produces
    qualified roster rows for at least one alternative team."""
    _team(db, 1, "BOS", "Boston Celtics")
    _team(db, 2, "ORL", "Orlando Magic")
    _team(db, 3, "LAL", "Los Angeles Lakers")
    _team(db, 4, "CHI", "Chicago Bulls")
    # Wide league filler to stabilise season z-scores.
    for i in range(24):
        team = ["CHI", "LAL", "ORL", "BOS"][i % 4]
        _player(db, 1000 + i, "Filler {0}".format(i), position=["Guard", "Forward", "Center"][i % 3])
        _row(
            db,
            1000 + i,
            team,
            usg_pct=13.0 + (i % 8) * 2.0,
            pts_pg=9.0 + (i % 9) * 2.0,
            ast_pg=1.5 + (i % 6) * 0.8,
            reb_pg=3.0 + (i % 7) * 1.0,
            stl_pg=0.4 + (i % 5) * 0.25,
            blk_pg=0.1 + (i % 5) * 0.25,
            ts_pct=0.50 + (i % 8) * 0.015,
            per=10.0 + (i % 9) * 1.5,
            par3=0.18 + (i % 7) * 0.07,
            ftr=0.14 + (i % 6) * 0.05,
        )
    # Subject — a high-usage wing on BOS.
    _player(db, 9001, "Subject Wing", position="Forward", team_id=1)
    _row(
        db,
        9001,
        "BOS",
        usg_pct=30.0,
        pts_pg=27.0,
        ast_pg=7.0,
        reb_pg=7.0,
        stl_pg=1.5,
        blk_pg=0.8,
        ts_pct=0.61,
        per=24.0,
        par3=0.48,
        ftr=0.38,
    )
    # A teammate that overlaps so BOS roster has size >= 3.
    _player(db, 9002, "Boston Spacer", position="Forward", team_id=1)
    _row(db, 9002, "BOS", usg_pct=15.0, pts_pg=10.0, ast_pg=2.0, par3=0.52)
    _player(db, 9003, "Boston Big", position="Center", team_id=1)
    _row(db, 9003, "BOS", usg_pct=13.0, pts_pg=8.0, ast_pg=1.2, reb_pg=9.0, blk_pg=1.2)
    db.commit()


def test_top_team_fits_for_player_returns_ranked_alternatives():
    db = make_session()
    try:
        _seed_fits_case(db)
        # Subject is "expiring" so the FA detail panel sees a contract too.
        _contract(db, player_id=9001, salary=42_000_000, years_remaining=1, team_id=1)
        db.commit()

        response = top_team_fits_for_player(db, 9001, season=SEASON, k=10)
        assert response.player_id == 9001
        # At least one alternative team passed the team_fit_v3 roster gate.
        assert len(response.fits) >= 1
        assert len(response.fits) <= 10
        # Rankings are 1..N.
        assert [fit.rank for fit in response.fits] == list(range(1, len(response.fits) + 1))
        # Alternatives never include the player's own team.
        assert all(fit.team_abbreviation != "BOS" for fit in response.fits)
        # Each ranked fit carries at least one rationale chip when drivers exist.
        assert any(fit.rationale_chips for fit in response.fits)
        # Contract panel hydrated.
        assert response.contract is not None
        assert response.contract.tier == "max"
    finally:
        db.close()
