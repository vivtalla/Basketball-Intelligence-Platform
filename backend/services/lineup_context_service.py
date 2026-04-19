from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from db.models import LineupStats, Player, PlayerOnOff
from models.insights import LineupContextResponse, TeammateOnOff

_MIN_LINEUP_POSSESSIONS = 100  # per CLAUDE.md analytics rule


def _on_off_confidence(on_minutes: Optional[float]) -> str:
    if on_minutes is None:
        return "insufficient"
    if on_minutes >= 800:
        return "high"
    if on_minutes >= 300:
        return "medium"
    if on_minutes >= 100:
        return "low"
    return "insufficient"


def _teammate_confidence(possessions: int) -> str:
    if possessions >= 500:
        return "high"
    if possessions >= 200:
        return "medium"
    return "low"


def build_lineup_context(
    db: Session,
    player_id: int,
    season: str,
) -> LineupContextResponse:
    player = db.query(Player).filter(Player.id == player_id).first()
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found.")

    # Fetch season on/off split.
    on_off_row = (
        db.query(PlayerOnOff)
        .filter(
            PlayerOnOff.player_id == player_id,
            PlayerOnOff.season == season,
            PlayerOnOff.is_playoff == False,  # noqa: E712
        )
        .first()
    )

    # Find all 5-man lineups containing this player with enough possessions.
    # lineup_key is sorted player IDs joined by "-".
    player_id_str = str(player_id)
    lineup_rows = (
        db.query(LineupStats)
        .filter(
            LineupStats.season == season,
            LineupStats.lineup_key.like("%{0}%".format(player_id_str)),
        )
        .all()
    )

    # Accumulate shared minutes and weighted net_rating per teammate.
    teammate_minutes: Dict[int, float] = defaultdict(float)
    teammate_possessions: Dict[int, int] = defaultdict(int)
    teammate_weighted_nr: Dict[int, List[Tuple[float, int]]] = defaultdict(list)

    for lineup in lineup_rows:
        raw_ids = lineup.lineup_key.split("-")
        try:
            ids = [int(x.strip()) for x in raw_ids if x.strip()]
        except ValueError:
            continue

        if player_id not in ids:
            # LIKE match on partial ID string (e.g. "123" matches "1234"); skip false positives.
            continue

        poss = lineup.possessions or 0
        if poss < _MIN_LINEUP_POSSESSIONS:
            continue

        mins = lineup.minutes or 0.0
        for tid in ids:
            if tid == player_id:
                continue
            teammate_minutes[tid] += mins
            teammate_possessions[tid] += poss
            if lineup.net_rating is not None:
                teammate_weighted_nr[tid].append((lineup.net_rating, poss))

    top_teammate_ids = sorted(
        teammate_minutes.keys(),
        key=lambda tid: teammate_minutes[tid],
        reverse=True,
    )[:5]

    # Resolve player names in one query.
    name_lookup: Dict[int, str] = {}
    if top_teammate_ids:
        teammate_players = (
            db.query(Player)
            .filter(Player.id.in_(top_teammate_ids))
            .all()
        )
        name_lookup = {p.id: p.full_name for p in teammate_players}

    top_teammates: List[TeammateOnOff] = []
    for tid in top_teammate_ids:
        weighted_nr_entries = teammate_weighted_nr.get(tid, [])
        net_rating_with: Optional[float] = None
        if weighted_nr_entries:
            total_poss = sum(w for _, w in weighted_nr_entries)
            if total_poss > 0:
                net_rating_with = round(
                    sum(nr * w for nr, w in weighted_nr_entries) / total_poss, 1
                )

        poss = teammate_possessions[tid]
        top_teammates.append(TeammateOnOff(
            teammate_id=tid,
            teammate_name=name_lookup.get(tid, str(tid)),
            shared_minutes=round(teammate_minutes[tid], 1),
            possessions=poss,
            net_rating_with=net_rating_with,
            confidence=_teammate_confidence(poss),
        ))

    notes: List[str] = [
        "Min. {0} possessions required per lineup to appear in teammate context.".format(
            _MIN_LINEUP_POSSESSIONS
        ),
        "Lineup data sourced from play-by-play stints.",
    ]
    if not top_teammates:
        notes.append("No qualifying lineup data found for this player this season.")

    return LineupContextResponse(
        player_id=player_id,
        player_name=player.full_name,
        season=season,
        on_off_net=(
            round(on_off_row.on_off_net, 1)
            if on_off_row is not None and on_off_row.on_off_net is not None
            else None
        ),
        on_minutes=on_off_row.on_minutes if on_off_row is not None else None,
        off_minutes=on_off_row.off_minutes if on_off_row is not None else None,
        top_teammates=top_teammates,
        notes=notes,
    )
