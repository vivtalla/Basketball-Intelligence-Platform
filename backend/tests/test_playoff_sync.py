"""Sprint 73a — playoff sync coverage.

Covers:
  1. Team-splits sync threads ``is_playoff=True`` into the nba_client wrapper
     (verified via ``season_type="Playoffs"``) and persists rows tagged
     accordingly.
  2. The bracket service derives correct series state from raw GameLog rows.
  3. ``_cache_ttl_for_season`` returns the playoff TTL when the season-phase
     service reports an active playoff phase.
  4. ``daily_sync.sh --post-game --dry-run`` exits 0 and emits the bracket
     refresh signal.
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import date
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from db.database import Base  # noqa: E402
from db.models import GameLog, Team, TeamSeasonStat, TeamSplitStat  # noqa: E402
# Importing the bracket service registers PlayoffSeries on Base.metadata via
# its EA1-fallback path so SQLite tests can `create_all` the playoff_series
# table.
from services.playoff_bracket_service import (  # noqa: E402
    PlayoffSeries,
    build_or_refresh_bracket,
)
from services.sync_service import sync_official_team_general_splits  # noqa: E402


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return Session()


# ---------------------------------------------------------------------------
# Test 1 — sync_official_team_general_splits respects is_playoff.
# ---------------------------------------------------------------------------
def test_team_splits_sync_respects_is_playoff(monkeypatch):
    session = make_session()
    try:
        session.add(Team(id=1610612760, abbreviation="OKC", name="Oklahoma City Thunder"))
        session.commit()

        observed_kwargs = {}

        def fake_get_team_general_splits(season, team_id, season_type="Regular Season"):
            observed_kwargs["season"] = season
            observed_kwargs["team_id"] = team_id
            observed_kwargs["season_type"] = season_type
            return [
                {
                    "team_id": team_id,
                    "season": season,
                    "is_playoff": season_type == "Playoffs",
                    "split_family": "LocationTeamDashboard",
                    "split_value": "Home",
                    "label": "Home",
                    "gp": 6,
                    "w": 5,
                    "l": 1,
                    "w_pct": 0.833,
                    "min": 290.0,
                    "pts": 720.0,
                    "reb": 285.0,
                    "ast": 175.0,
                    "tov": 78.0,
                    "stl": 48.0,
                    "blk": 33.0,
                    "fg_pct": 0.512,
                    "fg3_pct": 0.398,
                    "ft_pct": 0.83,
                    "plus_minus": 88.0,
                }
            ]

        monkeypatch.setattr(
            "services.sync_service.get_team_general_splits",
            fake_get_team_general_splits,
        )

        result = sync_official_team_general_splits(
            session, "2024-25", team_ids=[1610612760], is_playoff=True
        )

        assert observed_kwargs.get("season_type") == "Playoffs"
        assert result["status"] == "ok"
        assert result["is_playoff"] is True
        assert result["split_rows_synced"] == 1

        rows = (
            session.query(TeamSplitStat)
            .filter_by(team_id=1610612760, season="2024-25", is_playoff=True)
            .all()
        )
        assert len(rows) == 1
        assert rows[0].is_playoff is True
        assert rows[0].split_family == "LocationTeamDashboard"
        assert rows[0].pts == 720.0
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Test 2 — bracket service computes wins / status from raw GameLog rows.
# ---------------------------------------------------------------------------
def test_bracket_service_builds_correct_series():
    session = make_session()
    try:
        okc = Team(
            id=1610612760, abbreviation="OKC", name="Oklahoma City Thunder",
            conference="West",
        )
        minn = Team(
            id=1610612750, abbreviation="MIN", name="Minnesota Timberwolves",
            conference="West",
        )
        session.add_all([okc, minn])
        # Seed via regular-season W% so seed lookup picks OKC as the higher seed.
        session.add_all([
            TeamSeasonStat(team_id=okc.id, season="2024-25", is_playoff=False, w_pct=0.80),
            TeamSeasonStat(team_id=minn.id, season="2024-25", is_playoff=False, w_pct=0.65),
        ])
        # 5 playoff games: OKC wins 1, 2, 4 (3 wins); MIN wins 3, 5 (2 wins).
        # Series remains active (3-2 in favor of OKC).
        games_data = [
            ("0042400201", date(2025, 5, 6),  okc.id, minn.id, 117, 96),   # OKC W
            ("0042400202", date(2025, 5, 8),  okc.id, minn.id, 118, 103),  # OKC W
            ("0042400203", date(2025, 5, 10), minn.id, okc.id, 131, 80),   # MIN W
            ("0042400204", date(2025, 5, 12), minn.id, okc.id, 92, 128),   # OKC W (away)
            ("0042400205", date(2025, 5, 14), okc.id, minn.id, 100, 105),  # MIN W (away)
        ]
        for game_id, game_date, home_id, away_id, home_pts, away_pts in games_data:
            game = GameLog(
                game_id=game_id,
                season="2024-25",
                game_date=game_date,
                home_team_id=home_id,
                away_team_id=away_id,
                home_score=home_pts,
                away_score=away_pts,
            )
            if hasattr(GameLog, "season_type"):
                setattr(game, "season_type", "Playoffs")
            session.add(game)
        session.commit()

        refreshed = build_or_refresh_bracket(session, "2024-25")
        assert refreshed == 1

        rows = session.query(PlayoffSeries).filter_by(season="2024-25").all()
        assert len(rows) == 1
        series = rows[0]
        assert series.top_seed_team_id == okc.id
        assert series.bottom_seed_team_id == minn.id
        assert series.top_wins == 3
        assert series.bottom_wins == 2
        assert series.status == "active"
        assert series.winner_team_id is None
        assert series.series_id.startswith("2024-25-")

        # Idempotency: a second run produces the same row, no duplicates.
        refreshed_again = build_or_refresh_bracket(session, "2024-25")
        assert refreshed_again == 1
        assert session.query(PlayoffSeries).count() == 1
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Test 3 — _cache_ttl_for_season returns 7200 during the playoff window.
# ---------------------------------------------------------------------------
def test_cache_ttl_drops_during_playoffs(monkeypatch):
    from data import nba_client

    # Stub the lazy phase importer so the cache TTL gate sees an active
    # playoff window without depending on EA4's module being on disk.
    def fake_phase_check(_bucket: int) -> bool:
        return True

    monkeypatch.setattr(
        nba_client, "_active_phase_is_playoffs_cached", fake_phase_check
    )
    monkeypatch.setattr(
        nba_client, "_active_nba_season", lambda: "2025-26"
    )

    assert nba_client._cache_ttl_for_season("2025-26") == 7200
    # Sanity: a historical season still returns the long TTL even when the
    # phase service says we're in the playoffs.
    assert (
        nba_client._cache_ttl_for_season("2018-19")
        == nba_client.HISTORICAL_SEASON_CACHE_TTL
    )


# ---------------------------------------------------------------------------
# Test 4 — daily_sync.sh --post-game --dry-run exits 0 and reports bracket.
# ---------------------------------------------------------------------------
def test_daily_sync_post_game_dry_run():
    script = BACKEND_ROOT / "data" / "daily_sync.sh"
    assert script.exists()

    env = os.environ.copy()
    env.setdefault("PATH", os.environ.get("PATH", ""))
    result = subprocess.run(
        ["bash", str(script), "--post-game", "--dry-run"],
        capture_output=True,
        text=True,
        cwd=str(BACKEND_ROOT),
        env=env,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"daily_sync dry-run failed: stdout={result.stdout} stderr={result.stderr}"
    )
    assert "bracket refreshed" in result.stdout, (
        f"expected 'bracket refreshed' in dry-run output, got: {result.stdout}"
    )
