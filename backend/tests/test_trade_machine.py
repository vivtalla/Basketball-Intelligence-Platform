"""Tests for Sprint 78 FO1 — Trade Machine + salary ingestion + impact projection."""
from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import (  # noqa: E402
    Player,
    PlayerContract,
    PlayerOnOff,
    SeasonStat,
    Team,
    TeamSeasonStat,
)
from models.trade import TradePackage  # noqa: E402
from services.salary_ingestion_service import sync_salary_data  # noqa: E402
from services.trade_impact_service import project_trade_impact  # noqa: E402
from services.trade_machine_service import validate_trade  # noqa: E402


def make_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


def seed_two_teams(session):
    bos = Team(id=1610612738, abbreviation="BOS", name="Boston Celtics")
    okc = Team(id=1610612760, abbreviation="OKC", name="Oklahoma City Thunder")
    session.add_all([bos, okc])

    # Big BOS contract.
    session.add(Player(id=1628369, full_name="Jayson Tatum", team_id=bos.id, position="F"))
    session.add(PlayerContract(
        player_id=1628369,
        team_id=bos.id,
        season="2025-26",
        salary=37_000_000,
        years_remaining=4,
        contract_type="supermax",
    ))

    # OKC contract worth ~ same.
    session.add(Player(id=1628983, full_name="Shai Gilgeous-Alexander", team_id=okc.id, position="G"))
    session.add(PlayerContract(
        player_id=1628983,
        team_id=okc.id,
        season="2025-26",
        salary=42_000_000,
        years_remaining=4,
        contract_type="supermax",
    ))

    # Filler players to break salary match in some tests.
    session.add(Player(id=99999, full_name="Veteran Filler", team_id=bos.id, position="G"))
    session.add(PlayerContract(
        player_id=99999,
        team_id=bos.id,
        season="2025-26",
        salary=2_000_000,
        years_remaining=1,
        contract_type="veteran-min",
    ))
    session.add(Player(id=99998, full_name="OKC Vet", team_id=okc.id, position="F"))
    session.add(PlayerContract(
        player_id=99998,
        team_id=okc.id,
        season="2025-26",
        salary=2_500_000,
        years_remaining=1,
        contract_type="veteran-min",
    ))

    # Team baselines + on/off + season stats so impact projection can compute.
    session.add(TeamSeasonStat(team_id=bos.id, season="2025-26", is_playoff=False, net_rating=8.0))
    session.add(TeamSeasonStat(team_id=okc.id, season="2025-26", is_playoff=False, net_rating=10.5))
    session.add(PlayerOnOff(
        player_id=1628369,
        season="2025-26",
        is_playoff=False,
        on_minutes=2200.0,
        off_minutes=600.0,
        on_off_net=6.0,
    ))
    session.add(PlayerOnOff(
        player_id=1628983,
        season="2025-26",
        is_playoff=False,
        on_minutes=2400.0,
        off_minutes=400.0,
        on_off_net=12.0,
    ))
    session.add(SeasonStat(
        player_id=1628369, season="2025-26", team_abbreviation="BOS",
        is_playoff=False, min_pg=36.0, ast_pg=4.5, par3=0.42,
    ))
    session.add(SeasonStat(
        player_id=1628983, season="2025-26", team_abbreviation="OKC",
        is_playoff=False, min_pg=34.5, ast_pg=6.5, par3=0.30,
    ))
    session.commit()


def test_validate_trade_within_125_percent_passes():
    session = make_session()
    try:
        seed_two_teams(session)
        result = validate_trade(
            session,
            packages=[
                TradePackage(team_abbr="BOS", outgoing_player_ids=[1628369], incoming_player_ids=[1628983]),
                TradePackage(team_abbr="OKC", outgoing_player_ids=[1628983], incoming_player_ids=[1628369]),
            ],
            season="2025-26",
        )
        assert result.valid is True
        assert result.team_count == 2
        # Each team should record outgoing/incoming totals.
        bos_line = next(line for line in result.team_salary_lines if line.team_abbr == "BOS")
        assert bos_line.outgoing_salary == 37_000_000
        assert bos_line.incoming_salary == 42_000_000
        # No hard-block warnings.
        assert all(w.severity != "hard_block" for w in result.warnings)
    finally:
        session.close()


def test_validate_trade_outside_125_percent_blocks():
    session = make_session()
    try:
        seed_two_teams(session)
        # BOS sends $37M, gets $2.5M back — way outside ±125%.
        result = validate_trade(
            session,
            packages=[
                TradePackage(team_abbr="BOS", outgoing_player_ids=[1628369], incoming_player_ids=[99998]),
                TradePackage(team_abbr="OKC", outgoing_player_ids=[99998], incoming_player_ids=[1628369]),
            ],
            season="2025-26",
        )
        assert result.valid is False
        hard_blocks = [w for w in result.warnings if w.severity == "hard_block"]
        assert hard_blocks
        assert any(w.rule == "salary_match" for w in hard_blocks)
    finally:
        session.close()


def test_validate_trade_requires_at_least_two_teams():
    session = make_session()
    try:
        seed_two_teams(session)
        result = validate_trade(
            session,
            packages=[TradePackage(team_abbr="BOS", outgoing_player_ids=[1628369], incoming_player_ids=[])],
            season="2025-26",
        )
        assert result.valid is False
        assert any(w.rule == "structure" for w in result.warnings)
    finally:
        session.close()


def test_project_trade_impact_returns_per_team_delta():
    session = make_session()
    try:
        seed_two_teams(session)
        impact = project_trade_impact(
            session,
            packages=[
                TradePackage(team_abbr="BOS", outgoing_player_ids=[1628369], incoming_player_ids=[1628983]),
                TradePackage(team_abbr="OKC", outgoing_player_ids=[1628983], incoming_player_ids=[1628369]),
            ],
            season="2025-26",
        )
        assert len(impact.teams) == 2
        bos = next(t for t in impact.teams if t.team_abbr == "BOS")
        okc = next(t for t in impact.teams if t.team_abbr == "OKC")
        # BOS swaps a +6 swing for a +12 swing — net positive delta.
        assert bos.net_rating_delta is not None
        assert bos.net_rating_delta > 0
        assert okc.net_rating_delta is not None
        assert okc.net_rating_delta < 0
        # Baselines came through.
        assert bos.baseline_net_rating == 8.0
        assert okc.baseline_net_rating == 10.5
        # Projected reflects baseline + delta.
        assert bos.projected_net_rating is not None
        assert okc.projected_net_rating is not None
    finally:
        session.close()


def test_project_trade_impact_thin_sample_when_no_on_off():
    session = make_session()
    try:
        seed_two_teams(session)
        # Wipe on/off so the projection has no signal to work with.
        session.query(PlayerOnOff).delete()
        session.commit()
        impact = project_trade_impact(
            session,
            packages=[
                TradePackage(team_abbr="BOS", outgoing_player_ids=[1628369], incoming_player_ids=[1628983]),
                TradePackage(team_abbr="OKC", outgoing_player_ids=[1628983], incoming_player_ids=[1628369]),
            ],
            season="2025-26",
        )
        for team in impact.teams:
            assert team.confidence in {"thin_sample", "no_data"}
    finally:
        session.close()


def test_salary_ingestion_seed_csv_upserts(tmp_path):
    session = make_session()
    try:
        bos = Team(id=1610612738, abbreviation="BOS", name="Boston Celtics")
        session.add(bos)
        session.add(Player(id=1628369, full_name="Jayson Tatum", team_id=bos.id, position="F"))
        session.commit()

        csv_path = tmp_path / "seed.csv"
        csv_path.write_text(
            "nba_player_id,team_abbr,season,salary,years_remaining,is_player_option,is_team_option,contract_type\n"
            "1628369,BOS,2025-26,37000000,4,false,false,supermax\n"
            "9999999,XXX,2025-26,5000000,1,false,false,standard\n"  # unknown player, should skip
        )
        result = sync_salary_data(session, source="seed_csv", seed_path=str(csv_path))
        assert result["rows_upserted"] == 1
        assert result["rows_skipped"] >= 1

        rows = session.query(PlayerContract).all()
        assert len(rows) == 1
        assert rows[0].player_id == 1628369
        assert rows[0].salary == 37_000_000
        assert rows[0].contract_type == "supermax"

        # Re-run is idempotent — still one row, salary unchanged.
        sync_salary_data(session, source="seed_csv", seed_path=str(csv_path))
        rows = session.query(PlayerContract).all()
        assert len(rows) == 1
    finally:
        session.close()
