from datetime import datetime, timedelta
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import (  # noqa: E402
    Player,
    PlayerShotChart,
    ShotQualityBaseline,
    Team,
)
from services.shot_intelligence_ops_service import build_shot_intelligence_ops  # noqa: E402


def _session():
    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    return Session()


def _seed_team(db, team_id: int, abbr: str, name: str):
    team = Team(id=team_id, abbreviation=abbr, name=name)
    db.add(team)
    db.flush()
    return team


def _seed_player(db, player_id: int, team_id: int, name: str):
    p = Player(id=player_id, full_name=name, team_id=team_id, is_active=True)
    db.add(p)
    db.flush()
    return p


def _ready_shot(game_id: str, action_number: int) -> dict:
    return {
        "loc_x": 10,
        "loc_y": 10,
        "shot_made": True,
        "shot_type": "3PT Field Goal",
        "action_type": "Jump Shot",
        "zone_basic": "Above the Break 3",
        "zone_area": "Center",
        "distance": 25,
        "game_id": game_id,
        "game_date": "2025-12-01",
        "period": 3,
        "clock": "5:12",
        "minutes_remaining": 5,
        "seconds_remaining": 12,
        "shot_value": 3,
        "shot_event_id": f"evt-{action_number}",
        "event_order_index": action_number,
        "action_number": action_number,
        "linkage_mode": "exact",
        "team_id": 1,
        "team_abbreviation": "OKC",
        "opponent_team_id": 2,
        "opponent_team_abbreviation": "DAL",
    }


def test_ops_marks_missing_player_and_stale_player():
    db = _session()
    _seed_team(db, 1, "OKC", "Oklahoma City Thunder")
    _seed_player(db, 100, 1, "Ready Shooter")
    _seed_player(db, 101, 1, "Stale Shooter")
    _seed_player(db, 102, 1, "Missing Shooter")
    db.commit()

    now = datetime.utcnow()
    db.add(
        PlayerShotChart(
            player_id=100,
            season="2024-25",
            season_type="Regular Season",
            shots=[_ready_shot("0022400001", 5), _ready_shot("0022400002", 11)],
            shot_count=2,
            fetched_at=now,
            expires_at=now + timedelta(hours=6),
        )
    )
    db.add(
        PlayerShotChart(
            player_id=101,
            season="2024-25",
            season_type="Regular Season",
            shots=[_ready_shot("0022400003", 7)],
            shot_count=1,
            fetched_at=now - timedelta(days=5),
            expires_at=now + timedelta(hours=6),
        )
    )
    db.commit()

    ops = build_shot_intelligence_ops(db, season="2024-25")

    assert ops.totals["roster"] == 3
    assert ops.totals["ready"] == 1
    assert ops.totals["stale"] == 1
    assert ops.totals["missing"] == 1

    okc = next(t for t in ops.teams if t.team_abbreviation == "OKC")
    assert okc.roster_size == 3
    assert okc.ready_count == 1
    assert okc.stale_count == 1
    assert okc.missing_count == 1
    assert okc.readiness in ("partial", "stale")

    stale_names = sorted(p.player_name for p in ops.stale_players)
    assert stale_names == ["Missing Shooter", "Stale Shooter"]


def test_ops_reports_baseline_missing_and_ready():
    db = _session()
    _seed_team(db, 1, "OKC", "Oklahoma City Thunder")
    _seed_player(db, 100, 1, "Shooter")
    db.commit()

    ops = build_shot_intelligence_ops(db, season="2024-25")
    assert ops.baseline.status == "missing"
    assert ops.baseline.sample_n == 0

    db.add(
        ShotQualityBaseline(
            season="2024-25",
            season_type="Regular Season",
            methodology_version="shot_quality_v2",
            sample_n=1234,
            payload={"league": [1234, 500, 1400]},
            computed_at=datetime.utcnow(),
        )
    )
    db.commit()

    ops = build_shot_intelligence_ops(db, season="2024-25")
    assert ops.baseline.status == "ready"
    assert ops.baseline.sample_n == 1234


def test_ops_missing_context_histogram_counts_fields():
    db = _session()
    _seed_team(db, 1, "OKC", "Oklahoma City Thunder")
    _seed_player(db, 100, 1, "Legacy Shooter")
    db.commit()

    shot = _ready_shot("0022400001", 5)
    shot["period"] = None  # break context
    shot["clock"] = None
    now = datetime.utcnow()
    db.add(
        PlayerShotChart(
            player_id=100,
            season="2024-25",
            season_type="Regular Season",
            shots=[shot],
            shot_count=1,
            fetched_at=now,
            expires_at=now + timedelta(hours=6),
        )
    )
    db.commit()

    ops = build_shot_intelligence_ops(db, season="2024-25")
    # missing_context_histogram has at least one field flagged
    assert sum(ops.missing_context_histogram.values()) >= 1
