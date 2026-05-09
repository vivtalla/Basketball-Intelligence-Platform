"""On/Off Impact Command Center service (Sprint 94).

Computes enriched on/off metrics for coaching-grade analysis:
  - ORTG/DRTG impact decomposition (side-of-ball contribution)
  - Marginal net rating vs team baseline
  - Confidence tiers based on sample size (on-court minutes)
  - Impact classification (Two-Way Elite, Offensive Engine, etc.)
  - Top/worst 5-man lineup context from LineupStats
  - External validation (RAPM, EPM, PIPM) with agreement note

No schema changes required — all fields derived at query time from
PlayerOnOff, LineupStats, SeasonStat, TeamSeasonStat, Team, and Player.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from db.models import LineupStats, Player, PlayerOnOff, SeasonStat, Team, TeamSeasonStat
from models.stats import (
    ConfidenceTier,
    EnhancedLeaderboardEntry,
    EnhancedOnOffLeaderboardResult,
    EnhancedOnOffStats,
    ExternalValidation,
    ImpactClassification,
    LineupSlot,
    OnOffDecomposition,
)

_MIN_LINEUP_POSSESSIONS = 100


def _classify_impact(
    ortg_impact: Optional[float],
    drtg_impact: Optional[float],
) -> Optional[ImpactClassification]:
    if ortg_impact is None or drtg_impact is None:
        return None
    if ortg_impact > 3.0 and drtg_impact > 3.0:
        return ImpactClassification.TWO_WAY_ELITE
    if ortg_impact > 3.0 and drtg_impact < 1.0:
        return ImpactClassification.OFFENSIVE_ENGINE
    if drtg_impact > 3.0 and ortg_impact < 1.0:
        return ImpactClassification.DEFENSIVE_ANCHOR
    if ortg_impact < -2.0 and drtg_impact < -2.0:
        return ImpactClassification.LIABILITY
    return ImpactClassification.NEUTRAL


def _confidence_tier(on_minutes: Optional[float]) -> ConfidenceTier:
    if on_minutes is None:
        return ConfidenceTier.INSUFFICIENT
    if on_minutes >= 800:
        return ConfidenceTier.HIGH
    if on_minutes >= 400:
        return ConfidenceTier.MEDIUM
    if on_minutes >= 200:
        return ConfidenceTier.LOW
    return ConfidenceTier.INSUFFICIENT


def _lineup_slots_for_player(
    db: Session,
    player_id: int,
    season: str,
    is_playoff: bool,
    name_map: Dict[int, str],
    limit: int = 3,
    worst: bool = False,
) -> List[LineupSlot]:
    """Return top or worst N lineup slots for the given player with >= 100 possessions.

    Uses LIKE for initial filtering, then post-filters false positives by
    parsing the lineup_key (e.g. player_id=12 must not match key "112-120").
    """
    player_id_str = str(player_id)
    order_col = LineupStats.net_rating.asc() if worst else LineupStats.net_rating.desc()

    rows = (
        db.query(LineupStats)
        .filter(
            LineupStats.season == season,
            LineupStats.is_playoff == is_playoff,
            LineupStats.lineup_key.like("%{0}%".format(player_id_str)),
            LineupStats.possessions >= _MIN_LINEUP_POSSESSIONS,
            LineupStats.net_rating.isnot(None),
        )
        .order_by(order_col)
        .limit(limit * 3)  # over-fetch to account for LIKE false positives
        .all()
    )

    slots: List[LineupSlot] = []
    for row in rows:
        if len(slots) >= limit:
            break
        try:
            ids = [int(x) for x in row.lineup_key.split("-") if x.strip()]
        except ValueError:
            continue
        if player_id not in ids:
            continue  # LIKE false positive
        slots.append(
            LineupSlot(
                lineup_key=row.lineup_key,
                player_ids=ids,
                player_names=[name_map.get(i, str(i)) for i in ids],
                net_rating=row.net_rating,
                ortg=row.ortg,
                drtg=row.drtg,
                possessions=row.possessions,
                minutes=row.minutes,
            )
        )
    return slots


def build_enhanced_on_off(
    db: Session,
    player_id: int,
    season: str,
    season_type: str = "Regular Season",
) -> EnhancedOnOffStats:
    """Assemble full enhanced on/off impact payload for one player."""
    is_playoff = season_type == "Playoffs"

    on_off_row = (
        db.query(PlayerOnOff)
        .filter(
            PlayerOnOff.player_id == player_id,
            PlayerOnOff.season == season,
            PlayerOnOff.is_playoff == is_playoff,
        )
        .first()
    )
    if on_off_row is None:
        raise HTTPException(
            status_code=404,
            detail="No on/off data for player {0} in {1}. Run pbp_import.py first.".format(
                player_id, season
            ),
        )

    # External metrics from SeasonStat (highest-GP row for multi-team seasons)
    season_stat = (
        db.query(SeasonStat)
        .filter(
            SeasonStat.player_id == player_id,
            SeasonStat.season == season,
            SeasonStat.is_playoff == is_playoff,
        )
        .order_by(SeasonStat.gp.desc())
        .first()
    )

    # Team net_rating via Team.abbreviation join
    team_net_rating: Optional[float] = None
    if season_stat and season_stat.team_abbreviation:
        team_row = (
            db.query(TeamSeasonStat)
            .join(Team, TeamSeasonStat.team_id == Team.id)
            .filter(
                Team.abbreviation == season_stat.team_abbreviation,
                TeamSeasonStat.season == season,
                TeamSeasonStat.is_playoff == is_playoff,
            )
            .first()
        )
        if team_row:
            team_net_rating = team_row.net_rating

    # Compute derived fields
    ortg_impact: Optional[float] = None
    drtg_impact: Optional[float] = None
    marginal_net: Optional[float] = None

    if on_off_row.on_ortg is not None and on_off_row.off_ortg is not None:
        ortg_impact = round(on_off_row.on_ortg - on_off_row.off_ortg, 1)
    if on_off_row.on_drtg is not None and on_off_row.off_drtg is not None:
        drtg_impact = round(on_off_row.off_drtg - on_off_row.on_drtg, 1)
    if on_off_row.on_net_rating is not None and team_net_rating is not None:
        marginal_net = round(on_off_row.on_net_rating - team_net_rating, 1)

    confidence = _confidence_tier(on_off_row.on_minutes)
    classification = _classify_impact(ortg_impact, drtg_impact)

    # Build name_map for lineup slots in one batch query (avoid N+1)
    player_id_str = str(player_id)
    lineup_rows = (
        db.query(LineupStats)
        .filter(
            LineupStats.season == season,
            LineupStats.is_playoff == is_playoff,
            LineupStats.lineup_key.like("%{0}%".format(player_id_str)),
            LineupStats.possessions >= _MIN_LINEUP_POSSESSIONS,
        )
        .all()
    )
    all_ids: set = set()
    for row in lineup_rows:
        try:
            all_ids.update(int(x) for x in row.lineup_key.split("-") if x.strip())
        except ValueError:
            pass

    name_map: Dict[int, str] = {}
    if all_ids:
        name_map = {
            p.id: p.full_name
            for p in db.query(Player).filter(Player.id.in_(list(all_ids))).all()
        }

    top_lineups = _lineup_slots_for_player(
        db, player_id, season, is_playoff, name_map, limit=3, worst=False
    )
    worst_lineups = _lineup_slots_for_player(
        db, player_id, season, is_playoff, name_map, limit=3, worst=True
    )

    # External validation
    ext_val: Optional[ExternalValidation] = None
    if season_stat and any(
        v is not None for v in [season_stat.rapm, season_stat.epm, season_stat.pipm]
    ):
        agreement_note: Optional[str] = None
        if season_stat.rapm is not None and on_off_row.on_off_net is not None:
            diff = abs(season_stat.rapm - on_off_row.on_off_net)
            if diff < 3.0:
                agreement_note = "Consistent with RAPM ({0:+.1f})".format(season_stat.rapm)
            elif diff >= 8.0:
                agreement_note = "Diverges from RAPM ({0:+.1f}) — small sample likely".format(
                    season_stat.rapm
                )
        ext_val = ExternalValidation(
            rapm=season_stat.rapm,
            epm=season_stat.epm,
            pipm=season_stat.pipm,
            agreement_note=agreement_note,
        )

    decomp: Optional[OnOffDecomposition] = None
    if any(v is not None for v in [ortg_impact, drtg_impact, marginal_net]):
        decomp = OnOffDecomposition(
            ortg_impact=ortg_impact,
            drtg_impact=drtg_impact,
            marginal_net=marginal_net,
        )

    return EnhancedOnOffStats(
        player_id=player_id,
        season=season,
        on_minutes=on_off_row.on_minutes,
        off_minutes=on_off_row.off_minutes,
        on_net_rating=on_off_row.on_net_rating,
        off_net_rating=on_off_row.off_net_rating,
        on_off_net=on_off_row.on_off_net,
        on_ortg=on_off_row.on_ortg,
        on_drtg=on_off_row.on_drtg,
        off_ortg=on_off_row.off_ortg,
        off_drtg=on_off_row.off_drtg,
        confidence_tier=confidence,
        impact_classification=classification,
        decomposition=decomp,
        top_lineups=top_lineups,
        worst_lineups=worst_lineups,
        external_validation=ext_val,
        team_net_rating=team_net_rating,
    )


def build_enhanced_on_off_leaderboard(
    db: Session,
    season: str,
    season_type: str = "Regular Season",
    min_minutes: float = 200.0,
    limit: int = 25,
) -> EnhancedOnOffLeaderboardResult:
    """Build leaderboard with ORTG/DRTG decomposition, classification, and external metrics.

    All DB access uses batch queries — no N+1 loops.
    """
    is_playoff = season_type == "Playoffs"

    rows = (
        db.query(PlayerOnOff)
        .filter(
            PlayerOnOff.season == season,
            PlayerOnOff.is_playoff == is_playoff,
            PlayerOnOff.on_minutes >= min_minutes,
            PlayerOnOff.on_off_net.isnot(None),
        )
        .order_by(PlayerOnOff.on_off_net.desc())
        .limit(limit)
        .all()
    )

    player_ids = [r.player_id for r in rows]

    # Batch player name lookup
    players_by_id: Dict[int, Player] = {}
    if player_ids:
        players_by_id = {
            p.id: p
            for p in db.query(Player).filter(Player.id.in_(player_ids)).all()
        }

    # Batch SeasonStat for external metrics (highest-GP per player)
    season_stat_by_id: Dict[int, SeasonStat] = {}
    if player_ids:
        for ss in (
            db.query(SeasonStat)
            .filter(
                SeasonStat.player_id.in_(player_ids),
                SeasonStat.season == season,
                SeasonStat.is_playoff == is_playoff,
            )
            .all()
        ):
            existing = season_stat_by_id.get(ss.player_id)
            if existing is None or (ss.gp or 0) > (existing.gp or 0):
                season_stat_by_id[ss.player_id] = ss

    # Batch team net_ratings (all teams in season, one JOIN query)
    team_net_ratings: Dict[str, float] = {}
    for tss, team in (
        db.query(TeamSeasonStat, Team)
        .join(Team, TeamSeasonStat.team_id == Team.id)
        .filter(
            TeamSeasonStat.season == season,
            TeamSeasonStat.is_playoff == is_playoff,
        )
        .all()
    ):
        if tss.net_rating is not None:
            team_net_ratings[team.abbreviation] = tss.net_rating

    entries: List[EnhancedLeaderboardEntry] = []
    for row in rows:
        player = players_by_id.get(row.player_id)
        ss = season_stat_by_id.get(row.player_id)
        team_abbr = ss.team_abbreviation if ss else None

        ortg_impact: Optional[float] = None
        drtg_impact: Optional[float] = None
        if row.on_ortg is not None and row.off_ortg is not None:
            ortg_impact = round(row.on_ortg - row.off_ortg, 1)
        if row.on_drtg is not None and row.off_drtg is not None:
            drtg_impact = round(row.off_drtg - row.on_drtg, 1)

        team_nr = team_net_ratings.get(team_abbr) if team_abbr else None
        marginal_net: Optional[float] = None
        if row.on_net_rating is not None and team_nr is not None:
            marginal_net = round(row.on_net_rating - team_nr, 1)

        entries.append(
            EnhancedLeaderboardEntry(
                player_id=row.player_id,
                player_name=player.full_name if player else str(row.player_id),
                team_abbreviation=team_abbr,
                on_minutes=row.on_minutes,
                on_net_rating=row.on_net_rating,
                off_net_rating=row.off_net_rating,
                on_off_net=row.on_off_net,
                on_ortg=row.on_ortg,
                on_drtg=row.on_drtg,
                off_ortg=row.off_ortg,
                off_drtg=row.off_drtg,
                ortg_impact=ortg_impact,
                drtg_impact=drtg_impact,
                marginal_net=marginal_net,
                confidence_tier=_confidence_tier(row.on_minutes),
                impact_classification=_classify_impact(ortg_impact, drtg_impact),
                rapm=ss.rapm if ss else None,
                epm=ss.epm if ss else None,
            )
        )

    return EnhancedOnOffLeaderboardResult(season=season, players=entries)
