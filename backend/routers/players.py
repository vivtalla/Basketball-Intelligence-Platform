from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from data.nba_client import _active_nba_season
from db.database import get_db
from db.models import PlayTypeStat, Player, PlayerSplitStat
from dependencies import require_admin_key
from models.mvp import MvpGravityProfile
from models.analysis_context import (
    AnalysisContextCreate,
    AnalysisContextListResponse,
    AnalysisContextResponse,
    AnalysisContextUpdate,
)
from models.player import PlayerProfile, PlayerSearchResult, PlayerTrendReport
from services.analysis_context_service import (
    create_analysis_context,
    delete_analysis_context,
    list_analysis_contexts,
    update_analysis_context,
)
from services.gravity_service import build_gravity_profile
from services.player_trend_service import build_player_trend_report
from services.sync_service import canonical_player_name

router = APIRouter()

_PROFILE_STALE_AFTER = timedelta(days=14)


def _profile_data_status(player: Player) -> str:
    if not player:
        return "missing"
    updated_at = getattr(player, "updated_at", None)
    if player.is_active and updated_at and (datetime.utcnow() - updated_at) > _PROFILE_STALE_AFTER:
        return "stale"
    return "ready"


def _empty_profile(player_id: int) -> PlayerProfile:
    return PlayerProfile(
        id=player_id,
        full_name="",
        first_name="",
        last_name="",
        team_name="",
        team_abbreviation="",
        team_id=None,
        jersey="",
        position="",
        height="",
        weight="",
        birth_date="",
        country="",
        school=None,
        draft_year=None,
        draft_round=None,
        draft_number=None,
        from_year=None,
        to_year=None,
        headshot_url="",
        data_status="missing",
        last_synced_at=None,
    )


@router.get("/search", response_model=List[PlayerSearchResult])
def search(
    q: str = Query(..., min_length=2, description="Player name to search"),
    db: Session = Depends(get_db),
):
    query = f"%{q.strip()}%"
    rows = (
        db.query(Player)
        .filter(
            or_(
                Player.full_name.ilike(query),
                Player.first_name.ilike(query),
                Player.last_name.ilike(query),
            )
        )
        .order_by(Player.is_active.desc(), Player.full_name.asc())
        .limit(20)
        .all()
    )
    return [
        PlayerSearchResult(
            id=row.id,
            full_name=canonical_player_name(row.full_name, row.first_name or "", row.last_name or ""),
            is_active=bool(row.is_active),
        )
        for row in rows
    ]


@router.get("/{player_id}", response_model=PlayerProfile)
def get_player(player_id: int, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        return _empty_profile(player_id)

    team_abbr = ""
    team_name = ""
    if player.team:
        team_abbr = player.team.abbreviation
        team_name = player.team.name

    return PlayerProfile(
        id=player.id,
        full_name=canonical_player_name(player.full_name, player.first_name or "", player.last_name or ""),
        first_name=player.first_name or "",
        last_name=player.last_name or "",
        team_name=team_name,
        team_abbreviation=team_abbr,
        team_id=player.team_id,
        jersey=player.jersey or "",
        position=player.position or "",
        height=player.height or "",
        weight=player.weight or "",
        birth_date=player.birth_date or "",
        country=player.country or "",
        school=player.school,
        draft_year=player.draft_year,
        draft_round=player.draft_round,
        draft_number=player.draft_number,
        from_year=player.from_year,
        to_year=player.to_year,
        headshot_url=player.headshot_url or "",
        data_status=_profile_data_status(player),
        last_synced_at=player.updated_at.isoformat() if player.updated_at else None,
    )


@router.get("/{player_id}/gravity", response_model=MvpGravityProfile)
def get_player_gravity(
    player_id: int,
    season: str = Query(default=None, description="Season string, e.g. 2025-26"),
    season_type: str = Query(default="Regular Season"),
    db: Session = Depends(get_db),
) -> MvpGravityProfile:
    """Return one player's DB-first Gravity profile for player pages and stat workspaces."""
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail=f"Player {player_id} not found in local warehouse.")
    resolved_season = season or _active_nba_season()
    return build_gravity_profile(db, player_id=player_id, season=resolved_season, season_type=season_type)


@router.post("/{player_id}/sync")
def resync_player(
    player_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_key),
):
    """Force re-sync a player's data from NBA.com.

    Sprint 98 C2 — admin-key gated. Triggers a stats.nba.com fetch that
    can take 3-30s and is not for user paths.
    """
    from services.sync_service import sync_player
    try:
        sync_player(db, player_id)
        return {"status": "ok", "message": f"Player {player_id} synced"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")


@router.get("/{player_id}/trend-report", response_model=PlayerTrendReport)
def get_player_trend_report(
    player_id: int,
    season: str = Query("2024-25"),
    db: Session = Depends(get_db),
):
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail=f"Player {player_id} not found in local warehouse.")

    return build_player_trend_report(db=db, player=player, season=season)


@router.get("/{player_id}/splits")
def get_player_splits(
    player_id: int,
    season: str = Query("2024-25"),
    is_playoff: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Sprint 81: PlayerSplitStat rows grouped by split family.

    Returns ``{ player_id, season, families: { family: [rows...] } }``. Empty
    families return an empty list rather than 404 — the frontend can decide
    whether to render a "no data" state.
    """
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail=f"Player {player_id} not found.")

    rows = (
        db.query(PlayerSplitStat)
        .filter(
            PlayerSplitStat.player_id == player_id,
            PlayerSplitStat.season == season,
            PlayerSplitStat.is_playoff == is_playoff,
        )
        .order_by(PlayerSplitStat.split_family, PlayerSplitStat.split_value)
        .all()
    )

    families: dict = {}
    for row in rows:
        families.setdefault(row.split_family, []).append({
            "split_value": row.split_value,
            "label": row.label,
            "gp": row.gp, "w": row.w, "l": row.l, "w_pct": row.w_pct,
            "min": row.min, "pts": row.pts, "reb": row.reb, "ast": row.ast,
            "tov": row.tov, "stl": row.stl, "blk": row.blk,
            "fg_pct": row.fg_pct, "fg3_pct": row.fg3_pct, "ft_pct": row.ft_pct,
            "ts_pct": row.ts_pct, "usg_pct": row.usg_pct,
            "plus_minus": row.plus_minus,
        })
    return {
        "player_id": player_id,
        "season": season,
        "is_playoff": is_playoff,
        "families": families,
    }


@router.get("/{player_id}/play-types")
def get_player_play_types(
    player_id: int,
    season: str = Query("2024-25"),
    is_playoff: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Sprint 81: PlayTypeStat rows for a player, sorted by possession volume.

    Returns ``{ player_id, season, play_types: [...] }``. Each row carries the
    Synergy possession + efficiency triplet (poss, ppp, percentile).
    """
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail=f"Player {player_id} not found.")

    rows = (
        db.query(PlayTypeStat)
        .filter(
            PlayTypeStat.player_id == player_id,
            PlayTypeStat.season == season,
            PlayTypeStat.is_playoff == is_playoff,
        )
        .order_by(PlayTypeStat.poss.desc())
        .all()
    )
    return {
        "player_id": player_id,
        "season": season,
        "is_playoff": is_playoff,
        "play_types": [
            {
                "play_type": row.play_type,
                "play_role": row.play_role,
                "gp": row.gp,
                "poss": row.poss,
                "poss_pct": row.poss_pct,
                "pts": row.pts,
                "fg_pct": row.fg_pct,
                "efg_pct": row.efg_pct,
                "ts_pct": row.ts_pct,
                "ppp": row.ppp,
                "percentile": row.percentile,
                "score_freq_pct": row.score_freq_pct,
                "tov_freq_pct": row.tov_freq_pct,
            }
            for row in rows
        ],
    }


@router.get("/{player_id}/tracking")
def get_player_tracking_endpoint(
    player_id: int,
    season: str = Query("2024-25"),
    is_playoff: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Sprint 85 (C): Player tracking dashboard rows grouped by family.

    Returns ``{ player_id, season, is_playoff, families: { ... } }`` where
    families always include ``Shot Creation``, ``Passing``, ``Shot Defense``
    (each may be empty if no upstream data is persisted).
    """
    from services.player_tracking_service import get_player_tracking
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail=f"Player {player_id} not found.")
    return get_player_tracking(db, player_id=player_id, season=season, is_playoff=is_playoff)


@router.get("/{player_id}/hustle")
def get_player_hustle_endpoint(
    player_id: int,
    season: str = Query("2024-25"),
    is_playoff: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Sprint 85 (C): Player hustle aggregate (single panel, no families).

    Returns ``{ player_id, season, is_playoff, stats }`` where ``stats`` is
    null if no upstream row is persisted. Stats include contested_shots,
    deflections, charges_drawn, screen_assists, screen_assist_points,
    loose_balls_recovered, box_outs.
    """
    from services.player_hustle_service import get_player_hustle
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail=f"Player {player_id} not found.")
    return get_player_hustle(db, player_id=player_id, season=season, is_playoff=is_playoff)


@router.get("/{player_id}/analysis-contexts", response_model=AnalysisContextListResponse)
def get_player_analysis_contexts(
    player_id: int,
    season: str = Query("2024-25"),
    include_auto: bool = Query(True),
    db: Session = Depends(get_db),
):
    if not db.query(Player).filter(Player.id == player_id).first():
        raise HTTPException(status_code=404, detail=f"Player {player_id} not found in local warehouse.")
    return AnalysisContextListResponse(
        player_id=player_id,
        season=season,
        contexts=list_analysis_contexts(db, player_id, season, include_auto=include_auto),
    )


@router.post("/{player_id}/analysis-contexts", response_model=AnalysisContextResponse)
def create_player_analysis_context(
    player_id: int,
    payload: AnalysisContextCreate,
    db: Session = Depends(get_db),
):
    return create_analysis_context(db, player_id, payload)


@router.patch("/{player_id}/analysis-contexts/{context_id}", response_model=AnalysisContextResponse)
def update_player_analysis_context(
    player_id: int,
    context_id: int,
    payload: AnalysisContextUpdate,
    db: Session = Depends(get_db),
):
    return update_analysis_context(db, player_id, context_id, payload)


@router.delete("/{player_id}/analysis-contexts/{context_id}")
def delete_player_analysis_context(
    player_id: int,
    context_id: int,
    db: Session = Depends(get_db),
):
    delete_analysis_context(db, player_id, context_id)
    return {"status": "deleted", "context_id": context_id}


@router.get("/{player_id}/scouting-brief")
def get_player_scouting_brief(
    player_id: int,
    season: str = Query("2024-25"),
    db: Session = Depends(get_db),
):
    """Sprint 67 (B8) — one-minute scouting brief.

    Five composed cards (Role, Strengths, Usage & Efficiency, Shot Profile,
    Trajectory). Any source service that can't supply its card is skipped
    silently; `warnings` in the response surfaces what was missing.
    """
    from services.scouting_brief_service import build_scouting_brief
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail=f"Player {player_id} not found in local warehouse.")
    return build_scouting_brief(db=db, player_id=player_id, season=season)
