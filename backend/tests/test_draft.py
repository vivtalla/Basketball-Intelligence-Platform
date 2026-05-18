"""Sprint 78 / FO3 — draft prospect ingestion + workspace tests.

Three scenarios:

1. Seed CSV upsert is idempotent — re-running the sync doesn't duplicate
   prospects, stats, or measurements.
2. The translation service produces a sensible per-100 line and a
   confidence value in [0, 1] for the seeded NCAA prospects.
3. The board route returns the seeded class sorted by ``consensus_rank``
   ascending and the detail route returns NBA comps when an NBA pool is
   present.

Same in-memory SQLite + StaticPool harness used by ``test_playoff_routes``
so each test is hermetic.
"""
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import (  # noqa: E402
    DraftProspect,
    DraftProspectMeasurement,
    DraftProspectStat,
    Player,
    SeasonStat,
)
from data.sync_draft_prospects import sync_seed_csv  # noqa: E402
from routers.draft import get_board, get_prospect_detail  # noqa: E402
from services.draft_translation_service import translate_prospect_to_nba  # noqa: E402


SEED_CSV = str(
    Path(__file__).resolve().parents[1]
    / "data"
    / "seed"
    / "draft_prospects_2026.csv"
)


def _make_session_factory():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _seed_minimal_nba_pool(session, season="2025-26", n_players=40):
    """Create a tiny NBA pool so the comp service has 5+ candidates."""
    from db.models import Team  # local import to avoid double-decl warnings

    team = Team(id=1610612747, abbreviation="LAL", name="LA Lakers")
    session.add(team)
    session.commit()

    for i in range(n_players):
        pid = 1_000_000 + i
        session.add(Player(
            id=pid,
            full_name=f"NBA Player {i:02d}",
            is_active=True,
            team_id=team.id,
            position="SF",
            headshot_url=f"https://example.com/{pid}.png",
        ))
        # Stagger stats so the pool has variance.
        session.add(SeasonStat(
            player_id=pid,
            season=season,
            team_abbreviation="LAL",
            is_playoff=False,
            gp=70,
            min_pg=30.0,
            pts_pg=10.0 + i * 0.4,
            reb_pg=4.0 + i * 0.1,
            ast_pg=3.0 + i * 0.1,
            stl_pg=0.8 + (i % 5) * 0.1,
            blk_pg=0.5 + (i % 4) * 0.1,
            tov_pg=1.5 + (i % 3) * 0.2,
            ts_pct=0.55 + (i % 7) * 0.005,
            usg_pct=20.0 + i * 0.3,
            per=14.0 + i * 0.2,
            par3=0.35,
            ftr=0.25,
            oreb_pct=0.05,
            dbpm=0.0,
            obpm=0.0,
        ))
    session.commit()


def test_seed_csv_upsert_is_idempotent():
    SessionLocal = _make_session_factory()
    session = SessionLocal()
    try:
        first = sync_seed_csv(session, SEED_CSV, draft_year=2026, season="2025-26")
        second = sync_seed_csv(session, SEED_CSV, draft_year=2026, season="2025-26")

        prospect_count = session.query(DraftProspect).count()
        stat_count = session.query(DraftProspectStat).count()
        meas_count = session.query(DraftProspectMeasurement).count()
    finally:
        session.close()

    assert first["prospects"] >= 30
    assert first == second  # second pass returns identical counts
    assert prospect_count == first["prospects"]  # no dupes
    assert stat_count == first["stats"]
    assert meas_count == first["measurements"]


def test_translation_returns_per100_and_confidence():
    SessionLocal = _make_session_factory()
    session = SessionLocal()
    try:
        sync_seed_csv(session, SEED_CSV, draft_year=2026, season="2025-26")
        prospect = session.query(DraftProspect).filter(
            DraftProspect.external_id == "ncaa-2026-001"
        ).one()
        translation = translate_prospect_to_nba(session, prospect.id)
    finally:
        session.close()

    assert translation is not None
    assert 0.0 <= translation.translation_confidence <= 1.0
    # NCAA pace ≈ 70 → multiplier ≈ 100/70 ≈ 1.43
    assert 1.3 <= translation.pace_multiplier <= 1.5
    # 19.1 ppg * ~1.43 ≈ 27.3 per-100
    assert translation.projected_pts_per100 is not None
    assert translation.projected_pts_per100 > translation.projected_reb_per100
    # rate stats carry through (matches ncaa-2026-001 ts_pct in seed CSV)
    assert translation.projected_ts_pct == 0.591
    assert translation.confidence_factors  # at least one factor narrative


def test_board_route_and_detail_with_comps():
    SessionLocal = _make_session_factory()
    session = SessionLocal()
    try:
        sync_seed_csv(session, SEED_CSV, draft_year=2026, season="2025-26")
        _seed_minimal_nba_pool(session, season="2025-26")

        board = get_board(year=2026, limit=60, position=None, school_type=None, db=session)

        # Board has 30 prospects sorted by consensus_rank ascending.
        assert board.draft_year == 2026
        assert board.count == 30
        assert board.prospects[0].consensus_rank == 1
        assert board.prospects[-1].consensus_rank == 30

        # Filter by school_type narrows the list.
        ncaa_only = get_board(year=2026, limit=60, position=None, school_type="ncaa", db=session)
        assert ncaa_only.count < board.count
        assert all(p.school_type == "ncaa" for p in ncaa_only.prospects)

        # Detail endpoint resolves the per-100 translation + comps.
        first_id = board.prospects[0].prospect_id
        detail = get_prospect_detail(prospect_id=first_id, db=session)
        assert detail.summary.prospect_id == first_id
        assert detail.translation is not None
        assert len(detail.college_stats) >= 1
        assert detail.measurement is not None
        assert len(detail.nba_comps) == 5
        for comp in detail.nba_comps:
            assert 0.0 <= comp.similarity_score <= 100.0
            assert comp.rationale  # non-empty rationale chip
    finally:
        session.close()
