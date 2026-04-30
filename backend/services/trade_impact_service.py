"""Trade impact projection — Sprint 78 FO1.

For each team in a multi-team trade, rebuild a quick "post-trade" rotation
projection by:

 1. Computing the team's baseline net rating from `TeamSeasonStat`.
 2. Subtracting outgoing players' on/off net swing weighted by minutes.
 3. Adding incoming players' on/off net swing weighted by minutes (re-sourced
    from the *current* team they came off of).
 4. Computing a rotation-health score from the count of remaining ≥20mpg
    players + minutes balance across position bands.
 5. Diffing position/archetype frequency before vs after to surface up to
    three "added/lost/shifted" gap callouts.

Every value is best-effort. When the underlying signal is missing we set
``confidence`` accordingly and still return a row — the front-of-house
renders thin-sample notes rather than dropping the team.
"""
from __future__ import annotations

import logging
from collections import Counter
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from db.models import (
    Player,
    PlayerOnOff,
    SeasonStat,
    Team,
    TeamSeasonStat,
)
from models.trade import (
    ArchetypeGap,
    TeamImpactProjection,
    TradeImpactResult,
    TradePackage,
)

logger = logging.getLogger(__name__)

ROTATION_MIN_MPG = 20.0
ROTATION_TARGET = 9


def _team_baseline_net_rating(db: Session, team: Team, season: str) -> Optional[float]:
    row = (
        db.query(TeamSeasonStat)
        .filter(
            TeamSeasonStat.team_id == team.id,
            TeamSeasonStat.season == season,
        )
        .first()
    )
    if row and row.net_rating is not None:
        return float(row.net_rating)
    return None


def _player_on_off_lookup(
    db: Session,
    player_ids: List[int],
    season: str,
) -> Dict[int, PlayerOnOff]:
    if not player_ids:
        return {}
    rows = (
        db.query(PlayerOnOff)
        .filter(
            PlayerOnOff.player_id.in_(player_ids),
            PlayerOnOff.season == season,
            PlayerOnOff.is_playoff == False,  # noqa: E712
        )
        .all()
    )
    return dict((row.player_id, row) for row in rows)


def _season_stat_lookup(
    db: Session,
    player_ids: List[int],
    season: str,
) -> Dict[int, SeasonStat]:
    if not player_ids:
        return {}
    rows = (
        db.query(SeasonStat)
        .filter(
            SeasonStat.player_id.in_(player_ids),
            SeasonStat.season == season,
            SeasonStat.is_playoff == False,  # noqa: E712
        )
        .all()
    )
    # Use the most-minutes row per player when a player has multiple team rows.
    keep: Dict[int, SeasonStat] = {}
    for row in rows:
        cur = keep.get(row.player_id)
        if cur is None or (row.min_total or 0) > (cur.min_total or 0):
            keep[row.player_id] = row
    return keep


def _swing_contribution(
    on_off_row: Optional[PlayerOnOff],
    season_row: Optional[SeasonStat],
) -> Optional[float]:
    """Weight a player's on/off net by their share of available minutes.

    The intuition: a +6 swing matters more for a 34mpg star than a 14mpg
    role player. We weight by ``min_pg / 48`` and clip to [-12, 12] to
    prevent a single garbage-time hot streak from ballooning the
    projection.
    """
    if on_off_row is None or on_off_row.on_off_net is None:
        return None
    minutes = float(season_row.min_pg) if season_row and season_row.min_pg else 24.0
    weight = max(0.0, min(1.0, minutes / 48.0))
    raw = float(on_off_row.on_off_net) * weight
    return max(-12.0, min(12.0, raw))


def _rotation_health(
    remaining_players: List[SeasonStat],
) -> float:
    """Fraction of an "ideal" 9-deep ≥20mpg rotation present after the
    trade. Capped at 1.0; values below 0.6 should be treated as a roster
    flag.
    """
    if not remaining_players:
        return 0.0
    qualifying = [
        row for row in remaining_players
        if (row.min_pg or 0) >= ROTATION_MIN_MPG
    ]
    return round(min(1.0, len(qualifying) / float(ROTATION_TARGET)), 2)


def _classify_band(season_row: SeasonStat, player: Optional[Player]) -> str:
    """Coarse archetype band from position + 3PA rate — full archetype
    inference is in `player_archetype_service`, but pulling it in here
    blows up the projection cost. We use the cheap proxy.
    """
    pos = (player.position if player and player.position else "").upper()
    par3 = season_row.par3 or 0.0
    if "C" in pos:
        return "Big" if par3 < 0.18 else "Stretch Big"
    if "F" in pos and "G" not in pos:
        return "Wing" if par3 >= 0.30 else "Connector Forward"
    if "G" in pos:
        return "Lead Guard" if (season_row.ast_pg or 0) >= 5.5 else "Wing Guard"
    return "Wing"


def _archetype_gaps(
    outgoing_band_count: Counter,
    incoming_band_count: Counter,
) -> List[ArchetypeGap]:
    gaps: List[ArchetypeGap] = []
    seen_bands: Set[str] = set(outgoing_band_count.keys()) | set(incoming_band_count.keys())
    scored: List[Tuple[int, ArchetypeGap]] = []
    for band in seen_bands:
        delta = incoming_band_count.get(band, 0) - outgoing_band_count.get(band, 0)
        if delta == 0:
            continue
        if delta > 0:
            note = "Added %s %s" % (delta, band + ("s" if delta > 1 else ""))
            gap = ArchetypeGap(archetype=band, direction="added", note=note)
        else:
            note = "Lost %s %s" % (-delta, band + ("s" if -delta > 1 else ""))
            gap = ArchetypeGap(archetype=band, direction="lost", note=note)
        scored.append((abs(delta), gap))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in scored[:3]]


def _project_team(
    db: Session,
    pkg: TradePackage,
    season: str,
) -> TeamImpactProjection:
    team = db.query(Team).filter(Team.abbreviation == pkg.team_abbr).first()
    if team is None:
        return TeamImpactProjection(
            team_abbr=pkg.team_abbr,
            confidence="no_data",
            notes=["Team not found in roster table."],
        )

    baseline = _team_baseline_net_rating(db, team, season)
    pids_outgoing = list(pkg.outgoing_player_ids or [])
    pids_incoming = list(pkg.incoming_player_ids or [])

    on_off_map = _player_on_off_lookup(db, pids_outgoing + pids_incoming, season)
    season_stat_map = _season_stat_lookup(db, pids_outgoing + pids_incoming, season)
    players_map = dict(
        (p.id, p)
        for p in db.query(Player).filter(
            Player.id.in_(pids_outgoing + pids_incoming) if (pids_outgoing + pids_incoming) else False
        ).all()
    ) if (pids_outgoing or pids_incoming) else {}

    outgoing_swing = 0.0
    outgoing_band_count: Counter = Counter()
    incoming_swing = 0.0
    incoming_band_count: Counter = Counter()
    notes: List[str] = []

    contributions = 0
    for pid in pids_outgoing:
        season_row = season_stat_map.get(pid)
        on_off_row = on_off_map.get(pid)
        contribution = _swing_contribution(on_off_row, season_row)
        if contribution is not None:
            outgoing_swing += contribution
            contributions += 1
        if season_row is not None:
            band = _classify_band(season_row, players_map.get(pid))
            outgoing_band_count[band] += 1

    for pid in pids_incoming:
        season_row = season_stat_map.get(pid)
        on_off_row = on_off_map.get(pid)
        contribution = _swing_contribution(on_off_row, season_row)
        if contribution is not None:
            incoming_swing += contribution
            contributions += 1
        if season_row is not None:
            band = _classify_band(season_row, players_map.get(pid))
            incoming_band_count[band] += 1

    if contributions == 0:
        notes.append("No on/off rows for any player in this package — projection skipped.")
        confidence = "thin_sample" if (pids_outgoing or pids_incoming) else "no_data"
        return TeamImpactProjection(
            team_abbr=pkg.team_abbr,
            confidence=confidence,
            baseline_net_rating=baseline,
            projected_net_rating=baseline,
            net_rating_delta=0.0 if baseline is not None else None,
            rotation_health_score=None,
            notes=notes,
        )

    delta = round((incoming_swing - outgoing_swing), 2)
    projected = round((baseline if baseline is not None else 0.0) + delta, 2) if baseline is not None else None

    # Rotation-health uses the team's full season_stats roster minus outgoing players.
    roster_rows = (
        db.query(SeasonStat)
        .filter(
            SeasonStat.season == season,
            SeasonStat.team_abbreviation == team.abbreviation,
            SeasonStat.is_playoff == False,  # noqa: E712
        )
        .all()
    )
    remaining = [row for row in roster_rows if row.player_id not in set(pids_outgoing)]
    # Add incoming season rows (their min_pg comes from their previous team).
    for pid in pids_incoming:
        row = season_stat_map.get(pid)
        if row is not None:
            remaining.append(row)
    rotation_health = _rotation_health(remaining)

    confidence = "ready"
    if contributions < max(1, (len(pids_outgoing) + len(pids_incoming)) // 2):
        confidence = "thin_sample"
        notes.append("Some players missing on/off data — delta is partial.")

    gaps = _archetype_gaps(outgoing_band_count, incoming_band_count)

    return TeamImpactProjection(
        team_abbr=pkg.team_abbr,
        confidence=confidence,
        baseline_net_rating=baseline,
        projected_net_rating=projected,
        net_rating_delta=delta,
        rotation_health_score=rotation_health,
        archetype_gaps=gaps,
        notes=notes,
    )


def project_trade_impact(
    db: Session,
    packages: List[TradePackage],
    season: str = "2025-26",
) -> TradeImpactResult:
    teams: List[TeamImpactProjection] = []
    for pkg in packages:
        try:
            teams.append(_project_team(db, pkg, season))
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("trade impact projection failed for %s: %s", pkg.team_abbr, exc)
            teams.append(TeamImpactProjection(
                team_abbr=pkg.team_abbr,
                confidence="no_data",
                notes=["Projection failed: %s" % exc],
            ))
    return TradeImpactResult(season=season, teams=teams)
