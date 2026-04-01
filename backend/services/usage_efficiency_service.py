from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from db.models import Player, SeasonStat
from models.insights import UsageEfficiencyPlayerRow, UsageEfficiencyResponse, UsageEfficiencySuggestion


def _avg(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return sum(values) / float(len(values))


def _dedupe_player_rows(rows):
    """Keep one season row per player.

    Trade seasons can create multiple team rows for the same player. Prefer the
    aggregate TOT row when it exists; otherwise keep the row with the largest
    game count, then the largest minute load.
    """
    best = {}
    for stat, player in rows:
        current = best.get(player.id)
        if current is None:
            best[player.id] = (stat, player)
            continue

        current_stat, _ = current
        candidate_rank = (
            1 if (stat.team_abbreviation or "").upper() == "TOT" else 0,
            int(stat.gp or 0),
            float(stat.min_pg or 0.0),
        )
        current_rank = (
            1 if (current_stat.team_abbreviation or "").upper() == "TOT" else 0,
            int(current_stat.gp or 0),
            float(current_stat.min_pg or 0.0),
        )
        if candidate_rank > current_rank:
            best[player.id] = (stat, player)

    return list(best.values())


def build_usage_efficiency_report(
    db: Session,
    season: str,
    team: Optional[str],
    min_minutes: float,
) -> UsageEfficiencyResponse:
    query = (
        db.query(SeasonStat, Player)
        .join(Player, Player.id == SeasonStat.player_id)
        .filter(
            SeasonStat.season == season,
            SeasonStat.is_playoff == False,  # noqa: E712
            SeasonStat.min_pg >= min_minutes,
            SeasonStat.usg_pct.isnot(None),
            SeasonStat.ts_pct.isnot(None),
        )
    )
    if team:
        query = query.filter(SeasonStat.team_abbreviation == team.upper())

    rows = _dedupe_player_rows(query.all())
    if not rows:
        return UsageEfficiencyResponse(
            season=season,
            team=team.upper() if team else None,
            min_minutes=min_minutes,
            overused_inefficients=[],
            underused_efficients=[],
            suggestions=[],
            warnings=["No qualifying players matched the current season/team/minutes filters."],
        )

    usage_values = [float(stat.usg_pct or 0.0) for stat, _ in rows]
    ts_values = [float(stat.ts_pct or 0.0) for stat, _ in rows]
    avg_usg = _avg(usage_values) or 0.0
    avg_ts = _avg(ts_values) or 0.0

    overused: List[UsageEfficiencyPlayerRow] = []
    underused: List[UsageEfficiencyPlayerRow] = []

    for stat, player in rows:
        usage_delta = float(stat.usg_pct or 0.0) - avg_usg
        efficiency_delta = float(stat.ts_pct or 0.0) - avg_ts
        row = UsageEfficiencyPlayerRow(
            player_id=player.id,
            player_name=player.full_name,
            team_abbreviation=stat.team_abbreviation,
            minutes_pg=round(float(stat.min_pg or 0.0), 1) if stat.min_pg is not None else None,
            usg_pct=round(float(stat.usg_pct or 0.0), 1) if stat.usg_pct is not None else None,
            ts_pct=round(float(stat.ts_pct or 0.0), 3) if stat.ts_pct is not None else None,
            off_rating=round(float(stat.off_rating or 0.0), 1) if stat.off_rating is not None else None,
            pts_pg=round(float(stat.pts_pg or 0.0), 1) if stat.pts_pg is not None else None,
            ast_pg=round(float(stat.ast_pg or 0.0), 1) if stat.ast_pg is not None else None,
            tov_pg=round(float(stat.tov_pg or 0.0), 1) if stat.tov_pg is not None else None,
            burden_score=round(usage_delta, 2),
            efficiency_score=round(efficiency_delta * 100.0, 2),
            category="overused",
        )

        if usage_delta >= 0.03 and efficiency_delta <= -0.01:
            overused.append(row)
        elif usage_delta <= -0.02 and efficiency_delta >= 0.02:
            underused.append(row.copy(update={"category": "underused"}))

    overused.sort(key=lambda row: ((row.burden_score or 0.0) - (row.efficiency_score or 0.0)), reverse=True)
    underused.sort(key=lambda row: ((row.efficiency_score or 0.0) - (row.burden_score or 0.0)), reverse=True)

    suggestions: List[UsageEfficiencySuggestion] = []
    for row in overused[:3]:
        suggestions.append(
            UsageEfficiencySuggestion(
                player_name=row.player_name,
                category="overused",
                suggestion="Consider shaving a few high-difficulty possessions from {0} while keeping the ball moving through cleaner advantages.".format(row.player_name),
            )
        )
    for row in underused[:3]:
        suggestions.append(
            UsageEfficiencySuggestion(
                player_name=row.player_name,
                category="underused",
                suggestion="Find 2-3 extra actions a night for {0}; the current efficiency profile suggests more room for offensive burden.".format(row.player_name),
            )
        )

    warnings: List[str] = []
    if len(overused) == 0:
        warnings.append("No over-used inefficients crossed the current threshold.")
    if len(underused) == 0:
        warnings.append("No under-used efficient players crossed the current threshold.")

    return UsageEfficiencyResponse(
        season=season,
        team=team.upper() if team else None,
        min_minutes=min_minutes,
        overused_inefficients=overused[:10],
        underused_efficients=underused[:10],
        suggestions=suggestions,
        warnings=warnings,
    )
