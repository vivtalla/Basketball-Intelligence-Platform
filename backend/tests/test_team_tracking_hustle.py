"""Sprint 86 Stream C — team_tracking_stats + team_hustle_stats endpoint tests.

Calls the team router handlers directly with an in-memory SQLite session,
mirroring the Sprint 81/85 player-tracking + hustle test approach. Avoids
spinning up FastAPI's TestClient because httpx isn't a pinned dev dep.
"""
from __future__ import annotations

import os
import sys
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from db.database import Base  # noqa: E402
from db.models import Team, TeamHustleStat, TeamTrackingStat  # noqa: E402
from routers.teams import (  # noqa: E402
    team_hustle_endpoint,
    team_tracking_endpoint,
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


def _seed_team(session, team_id: int = 1610612760, abbr: str = "OKC", name: str = "Oklahoma City Thunder") -> Team:
    team = Team(id=team_id, abbreviation=abbr, name=name)
    session.add(team)
    session.commit()
    return team


# ---------------------------------------------------------------------------
# Tracking
# ---------------------------------------------------------------------------


def test_team_tracking_endpoint_returns_three_families(session) -> None:
    team = _seed_team(session)
    session.add_all([
        TeamTrackingStat(
            team_id=team.id, season="2024-25", season_type="Regular Season",
            tracking_family="shots", split_key="Drives",
            team_abbreviation="OKC", gp=70, touches=480.5, drives=52.0,
        ),
        TeamTrackingStat(
            team_id=team.id, season="2024-25", season_type="Regular Season",
            tracking_family="passing", split_key="overall",
            team_abbreviation="OKC", gp=70,
            passes_made=295.0, passes_received=295.0,
        ),
        TeamTrackingStat(
            team_id=team.id, season="2024-25", season_type="Regular Season",
            tracking_family="shot_defense", split_key="Less Than 6Ft",
            team_abbreviation="OKC", gp=70,
        ),
    ])
    session.commit()

    body = team_tracking_endpoint(
        abbr="OKC", season="2024-25", is_playoff=False, db=session
    )
    assert body["team_id"] == team.id
    assert body["season"] == "2024-25"
    assert body["is_playoff"] is False

    families = body["families"]
    # Public family labels are always present, even when empty.
    assert "Shot Creation" in families
    assert "Passing" in families
    assert "Shot Defense" in families

    # Raw `shots` family maps to `Shot Creation`.
    assert len(families["Shot Creation"]) == 1
    assert families["Shot Creation"][0]["touches"] == 480.5
    assert families["Shot Creation"][0]["drives"] == 52.0
    assert families["Passing"][0]["passes_made"] == 295.0
    assert families["Shot Defense"][0]["split_key"] == "Less Than 6Ft"


def test_team_tracking_endpoint_404s_for_unknown_team(session) -> None:
    with pytest.raises(HTTPException) as exc_info:
        team_tracking_endpoint(abbr="ZZZ", season="2024-25", is_playoff=False, db=session)
    assert exc_info.value.status_code == 404


def test_team_tracking_endpoint_resolves_lowercase_abbr(session) -> None:
    team = _seed_team(session, abbr="BOS", name="Boston Celtics")
    session.add(TeamTrackingStat(
        team_id=team.id, season="2024-25", season_type="Regular Season",
        tracking_family="shots", split_key="Drives",
        team_abbreviation="BOS", gp=82, drives=40.5,
    ))
    session.commit()

    body = team_tracking_endpoint(abbr="bos", season="2024-25", is_playoff=False, db=session)
    assert body["team_id"] == team.id
    assert body["families"]["Shot Creation"][0]["drives"] == 40.5


# ---------------------------------------------------------------------------
# Hustle
# ---------------------------------------------------------------------------


def test_team_hustle_endpoint_returns_aggregate(session) -> None:
    team = _seed_team(session)
    session.add(TeamHustleStat(
        team_id=team.id, season="2024-25", season_type="Regular Season",
        team_abbreviation="OKC", gp=70, minutes=16800.0,
        contested_shots=4200.0, deflections=1180.0, charges_drawn=42.0,
        screen_assists=320.0, screen_assist_points=720.0,
        loose_balls_recovered=510.0, box_outs=2200.0,
    ))
    session.commit()

    body = team_hustle_endpoint(
        abbr="OKC", season="2024-25", is_playoff=False, db=session
    )
    assert body["team_id"] == team.id
    assert body["season"] == "2024-25"
    assert body["is_playoff"] is False
    stats = body["stats"]
    assert stats is not None
    assert stats["contested_shots"] == 4200.0
    assert stats["deflections"] == 1180.0
    assert stats["charges_drawn"] == 42.0
    assert stats["screen_assists"] == 320.0
    assert stats["screen_assist_points"] == 720.0
    assert stats["loose_balls_recovered"] == 510.0
    assert stats["box_outs"] == 2200.0
    assert stats["team_abbreviation"] == "OKC"
    assert stats["gp"] == 70


def test_team_hustle_endpoint_returns_null_stats_when_missing(session) -> None:
    _seed_team(session)
    # No TeamHustleStat row, but on-demand sync will be attempted. Patch the
    # sync to be a no-op so we exercise the empty-payload path
    # deterministically without hitting the network.
    with patch(
        "services.team_hustle_service.sync_team_hustle_stats",
        return_value={"status": "ok", "rows_synced": 0, "rows_created": 0},
    ):
        body = team_hustle_endpoint(
            abbr="OKC", season="2024-25", is_playoff=False, db=session
        )
    assert body["stats"] is None


def test_team_hustle_endpoint_404s_for_unknown_team(session) -> None:
    with pytest.raises(HTTPException) as exc_info:
        team_hustle_endpoint(abbr="ZZZ", season="2024-25", is_playoff=False, db=session)
    assert exc_info.value.status_code == 404
