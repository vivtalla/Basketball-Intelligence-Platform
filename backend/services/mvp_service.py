"""MVP Award Race case-building service."""
from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import date
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from fastapi import HTTPException
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from db.models import (
    PlayByPlayEvent,
    GamePlayerStat,
    Player,
    PlayerGameLog,
    PlayerOnOff,
    SeasonStat,
    Team,
    TeamSeasonStat,
)
from models.mvp import (
    MvpAdvancedProfile,
    MvpCandidate,
    MvpCandidateCaseResponse,
    MvpClutchAndPaceProfile,
    MvpDataCoverage,
    MvpNearbyCandidate,
    MvpOnOffProfile,
    MvpPlayStyleRow,
    MvpRaceResponse,
    MvpScorePillar,
    MvpTeamContext,
)

SCORING_PROFILE = "mvp_case_v1"
MVP_WEIGHTS: Dict[str, float] = {
    "production": 0.25,
    "efficiency": 0.20,
    "impact": 0.25,
    "team_context": 0.15,
    "momentum": 0.10,
    "play_style": 0.05,
}

MIN_GP = 20
TREND_WINDOW = 10
HOT_THRESHOLD = 3.0
COLD_THRESHOLD = -3.0

ACTION_FAMILIES: Dict[str, str] = {
    "perimeter_creation": "Isolation / Perimeter Creation",
    "rim_pressure": "Rim Pressure",
    "transition": "Transition",
    "spot_up_proxy": "Spot-Up Proxy",
    "post_mismatch": "Post / Mismatch",
    "handoff_pnr_proxy": "Handoff / PNR Proxy",
}


def _safe_float(value) -> Optional[float]:
    return float(value) if value is not None else None


def _round(value: Optional[float], digits: int = 1) -> Optional[float]:
    return round(float(value), digits) if value is not None else None


def _avg(values: Iterable[Optional[float]]) -> Optional[float]:
    filtered = [float(v) for v in values if v is not None]
    return statistics.mean(filtered) if filtered else None


def _zscore_pool(values: List[Optional[float]]) -> List[float]:
    non_null = [v for v in values if v is not None]
    if len(non_null) < 2:
        return [0.0] * len(values)
    mu = statistics.mean(non_null)
    sigma = statistics.stdev(non_null)
    if sigma == 0:
        return [0.0] * len(values)
    return [(float(v) - mu) / sigma if v is not None else 0.0 for v in values]


def _display_score(raw: float) -> float:
    return round(max(0.0, min(100.0, ((raw + 3.0) / 6.0) * 100.0)), 1)


def _derive_ts_pct(row: SeasonStat) -> Optional[float]:
    if row.ts_pct is not None:
        return float(row.ts_pct)
    pts = row.pts or 0
    fga = row.fga or 0
    fta = row.fta or 0
    denom = 2 * (fga + 0.44 * fta)
    return (pts / denom) if denom > 0 else None


def _derive_efg_pct(row: SeasonStat) -> Optional[float]:
    if row.efg_pct is not None:
        return float(row.efg_pct)
    fga = row.fga or 0
    if fga <= 0:
        return None
    return ((row.fgm or 0) + (0.5 * (row.fg3m or 0))) / fga


def _usage_adjusted_efficiency(row: SeasonStat) -> Optional[float]:
    ts = _derive_ts_pct(row)
    if ts is None:
        return None
    usage = float(row.usg_pct) if row.usg_pct is not None else 20.0
    return ts + max(0.0, usage - 20.0) * 0.004


def _win_shares_per_48(row: SeasonStat) -> Optional[float]:
    if row.ws is None or not row.min_total:
        return None
    minutes = float(row.min_total or 0.0)
    if minutes <= 0:
        return None
    return (float(row.ws) * 48.0) / minutes


def _dedupe_player_rows(rows: Sequence[Tuple[SeasonStat, Player]]) -> List[Tuple[SeasonStat, Player]]:
    best: Dict[int, Tuple[SeasonStat, Player]] = {}
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


def _resolve_team(db: Session, stat: SeasonStat, player: Player) -> Optional[Team]:
    if stat.team_abbreviation and stat.team_abbreviation.upper() != "TOT":
        team = db.query(Team).filter(Team.abbreviation == stat.team_abbreviation.upper()).first()
        if team:
            return team
    if player.team_id:
        return db.query(Team).filter(Team.id == player.team_id).first()
    return None


def _team_context_maps(db: Session, season: str) -> Tuple[Dict[int, TeamSeasonStat], Dict[int, int], Dict[int, int]]:
    rows = db.query(TeamSeasonStat).filter_by(season=season, is_playoff=False).all()
    by_team = {row.team_id: row for row in rows}
    win_rank = {
        row.team_id: index
        for index, row in enumerate(sorted(rows, key=lambda r: float(r.w_pct or 0.0), reverse=True), start=1)
    }
    net_rank = {
        row.team_id: index
        for index, row in enumerate(sorted(rows, key=lambda r: float(r.net_rating or -999.0), reverse=True), start=1)
    }
    return by_team, win_rank, net_rank


def _trend_data(
    db: Session,
    player_ids: List[int],
    season: str,
    window: int,
) -> Dict[int, Tuple[Optional[float], Optional[float], Optional[float], Optional[float], str, int, Optional[date]]]:
    if not player_ids:
        return {}
    logs = (
        db.query(PlayerGameLog)
        .filter(
            PlayerGameLog.player_id.in_(player_ids),
            PlayerGameLog.season == season,
            PlayerGameLog.season_type == "Regular Season",
        )
        .order_by(PlayerGameLog.player_id, desc(PlayerGameLog.game_date))
        .all()
    )

    by_player: Dict[int, List[PlayerGameLog]] = defaultdict(list)
    for log in logs:
        by_player[log.player_id].append(log)

    result = {}
    for pid in player_ids:
        all_logs = by_player.get(pid, [])
        recent = all_logs[:window]
        if not recent:
            result[pid] = (None, None, None, None, "steady", 0, None)
            continue

        def _log_ts(row: PlayerGameLog) -> Optional[float]:
            pts = row.pts or 0
            fga = row.fga or 0
            fta = row.fta or 0
            denom = 2 * (fga + 0.44 * fta)
            return (pts / denom) if denom > 0 else None

        season_pts = _avg([r.pts for r in all_logs])
        season_reb = _avg([r.reb for r in all_logs])
        season_ast = _avg([r.ast for r in all_logs])
        season_ts = _avg([_log_ts(r) for r in all_logs])
        recent_pts = _avg([r.pts for r in recent])
        recent_reb = _avg([r.reb for r in recent])
        recent_ast = _avg([r.ast for r in recent])
        recent_ts = _avg([_log_ts(r) for r in recent])

        pts_delta = (recent_pts - season_pts) if recent_pts is not None and season_pts is not None else None
        reb_delta = (recent_reb - season_reb) if recent_reb is not None and season_reb is not None else None
        ast_delta = (recent_ast - season_ast) if recent_ast is not None and season_ast is not None else None
        ts_delta = (recent_ts - season_ts) if recent_ts is not None and season_ts is not None else None
        if pts_delta is not None and pts_delta > HOT_THRESHOLD:
            momentum = "hot"
        elif pts_delta is not None and pts_delta < COLD_THRESHOLD:
            momentum = "cold"
        else:
            momentum = "steady"
        result[pid] = (pts_delta, reb_delta, ast_delta, ts_delta, momentum, len(recent), recent[0].game_date)
    return result


def _family_for_event(event: PlayByPlayEvent) -> Optional[str]:
    description = (event.description or "").lower()
    action_type = (event.action_type or "").lower()
    action_family = (event.action_family or "").lower()
    if "fast break" in description or "transition" in description:
        return "transition"
    if "handoff" in description or "pick and roll" in description or "pnr" in description or "screen" in description:
        return "handoff_pnr_proxy"
    if "corner" in description or "catch and shoot" in description or "spot-up" in description or "spot up" in description:
        return "spot_up_proxy"
    if "post" in description or "hook" in description or "mismatch" in description or "back to basket" in description:
        return "post_mismatch"
    if "iso" in description or "isolation" in description or "step back" in description or "pull-up" in description or "pull up" in description:
        return "perimeter_creation"
    if action_family == "shot":
        if action_type == "3pt":
            return "spot_up_proxy"
        if action_type == "2pt":
            if "paint" in description or "rim" in description or "layup" in description or "dunk" in description or "floater" in description:
                return "rim_pressure"
            return "perimeter_creation"
        if action_type == "freethrow":
            return "rim_pressure"
    if action_family == "turnover" or action_type == "turnover":
        return "perimeter_creation"
    return None


def _play_style_profiles(db: Session, player_ids: List[int], season: str) -> Dict[int, List[MvpPlayStyleRow]]:
    if not player_ids:
        return {}
    game_ids = [
        game_id
        for game_id, in db.query(GamePlayerStat.game_id)
        .filter(
            GamePlayerStat.season == season,
            GamePlayerStat.player_id.in_(player_ids),
        )
        .distinct()
        .all()
    ]
    event_query = db.query(PlayByPlayEvent).filter(PlayByPlayEvent.player_id.in_(player_ids))
    if game_ids:
        event_query = event_query.filter(PlayByPlayEvent.game_id.in_(game_ids))
    else:
        event_query = event_query.filter(PlayByPlayEvent.season == season)
    events = (
        event_query
        .order_by(PlayByPlayEvent.player_id.asc(), PlayByPlayEvent.game_id.asc(), PlayByPlayEvent.order_index.asc())
        .all()
    )
    stats: Dict[int, Dict[str, Dict[str, float]]] = defaultdict(
        lambda: defaultdict(lambda: {"usage": 0.0, "points": 0.0, "turnovers": 0.0})
    )
    totals: Dict[int, float] = defaultdict(float)
    for event in events:
        family = _family_for_event(event)
        if not family:
            continue
        row = stats[event.player_id][family]
        action_type = (event.action_type or "").lower()
        sub_type = (event.sub_type or "").lower()
        if action_type in {"2pt", "3pt", "freethrow"}:
            row["usage"] += 1.0
            totals[event.player_id] += 1.0
            if sub_type == "made":
                row["points"] += 3.0 if action_type == "3pt" else 2.0 if action_type == "2pt" else 1.0
        elif action_type == "turnover":
            row["usage"] += 1.0
            row["turnovers"] += 1.0
            totals[event.player_id] += 1.0

    result: Dict[int, List[MvpPlayStyleRow]] = {}
    for player_id, families in stats.items():
        rows = []
        total_usage = totals.get(player_id, 0.0)
        for family, label in ACTION_FAMILIES.items():
            payload = families.get(family)
            if not payload:
                continue
            usage = payload["usage"]
            turnovers = payload["turnovers"]
            possessions = max(usage, 1.0)
            ppp = payload["points"] / possessions
            tov_rate = turnovers / possessions
            ev = ppp - tov_rate
            confidence = "high" if usage >= 100 else "medium" if usage >= 40 else "low"
            rows.append(
                MvpPlayStyleRow(
                    action_family=family,
                    label=label,
                    usage_share=_round((usage / total_usage) if total_usage else None, 3),
                    points_per_possession=_round(ppp, 3),
                    turnover_rate=_round(tov_rate, 3),
                    ev_score=_round(ev, 3),
                    raw_volume=int(usage),
                    confidence=confidence,
                    note="Inferred from play-by-play descriptions and event outcomes; not a native Synergy label.",
                )
            )
        rows.sort(key=lambda r: (r.ev_score if r.ev_score is not None else -999.0, r.raw_volume), reverse=True)
        result[player_id] = rows[:6]
    return result


def _play_style_value(rows: List[MvpPlayStyleRow]) -> Optional[float]:
    if not rows:
        return None
    weighted = 0.0
    usage = 0.0
    for row in rows:
        if row.ev_score is None or row.usage_share is None:
            continue
        weighted += row.ev_score * row.usage_share
        usage += row.usage_share
    if usage <= 0:
        return None
    return max(-1.0, min(1.5, weighted / usage))


def _on_off_confidence(row: Optional[PlayerOnOff]) -> str:
    minutes = float(row.on_minutes or 0.0) if row else 0.0
    if minutes >= 1500:
        return "high"
    if minutes >= 700:
        return "medium"
    return "low"


def _coverage(stat: SeasonStat, team_context: Optional[MvpTeamContext], on_off: Optional[MvpOnOffProfile], play_style: List[MvpPlayStyleRow]) -> MvpDataCoverage:
    has_pbp_splits = any(
        value is not None
        for value in [stat.clutch_pts, stat.clutch_fg_pct, stat.second_chance_pts, stat.fast_break_pts]
    )
    warnings: List[str] = []
    if team_context is None or team_context.win_pct is None:
        warnings.append("Team context is partial for this candidate.")
    if on_off is None or on_off.on_off_net is None:
        warnings.append("On/off impact is missing for this candidate.")
    if not has_pbp_splits:
        warnings.append("Clutch and pace-derived scoring splits are missing.")
    if not play_style:
        warnings.append("Play-style proxy has no qualifying play-by-play events.")
    return MvpDataCoverage(
        has_season_stats=True,
        has_team_context=team_context is not None and team_context.win_pct is not None,
        has_on_off=on_off is not None and on_off.on_off_net is not None,
        has_pbp_splits=has_pbp_splits,
        has_play_style=bool(play_style),
        warnings=warnings,
    )


def _case_summary(candidate: MvpCandidate) -> List[str]:
    summary = [
        "{0:.1f} PPG, {1:.1f} RPG, {2:.1f} APG with {3} games played.".format(
            candidate.pts_pg, candidate.reb_pg, candidate.ast_pg, candidate.gp
        )
    ]
    if candidate.ts_pct is not None:
        summary.append("{0:.1f}% true shooting anchors the efficiency case.".format(candidate.ts_pct * 100.0))
    if candidate.team_context and candidate.team_context.win_pct is not None:
        record = ""
        if candidate.team_context.wins is not None and candidate.team_context.losses is not None:
            record = " ({0}-{1})".format(candidate.team_context.wins, candidate.team_context.losses)
        summary.append("{0}{1} owns a {2:.1f}% win rate.".format(candidate.team_abbreviation, record, candidate.team_context.win_pct * 100.0))
    if candidate.on_off and candidate.on_off.on_off_net is not None:
        summary.append("Team is {0:+.1f} points per 100 better with him on the floor.".format(candidate.on_off.on_off_net))
    if candidate.play_style:
        style = candidate.play_style[0]
        if style.ev_score is not None:
            summary.append("{0} leads his inferred style mix at {1:.2f} EV.".format(style.label, style.ev_score))
    if candidate.pts_delta is not None and abs(candidate.pts_delta) >= 1.0:
        summary.append("Recent scoring trend is {0:+.1f} PPG over the last {1} games.".format(candidate.pts_delta, candidate.last_games))
    return summary[:5]


def _candidate_rows(
    db: Session,
    season: str,
    min_gp: int,
    position: Optional[str],
) -> List[Tuple[SeasonStat, Player]]:
    query = (
        db.query(SeasonStat, Player)
        .join(Player, SeasonStat.player_id == Player.id)
        .filter(
            SeasonStat.season == season,
            SeasonStat.is_playoff == False,  # noqa: E712
            SeasonStat.gp >= min_gp,
        )
    )
    if position:
        token = position.strip().upper()
        query = query.filter(func.upper(Player.position).like("%{0}%".format(token)))
    return _dedupe_player_rows(query.all())


def _build_ranked_candidates(
    db: Session,
    season: str,
    top: int,
    min_gp: int,
    position: Optional[str],
) -> Tuple[List[MvpCandidate], str]:
    stat_rows = _candidate_rows(db, season, min_gp=min_gp, position=position)
    if not stat_rows:
        return [], str(date.today())

    player_ids = [player.id for _, player in stat_rows]
    on_off_by_player = {
        row.player_id: row
        for row in db.query(PlayerOnOff)
        .filter(
            PlayerOnOff.season == season,
            PlayerOnOff.is_playoff == False,  # noqa: E712
            PlayerOnOff.player_id.in_(player_ids),
        )
        .all()
    }
    team_stats_by_id, win_ranks, net_ranks = _team_context_maps(db, season)
    team_by_key: Dict[int, Optional[Team]] = {player.id: _resolve_team(db, stat, player) for stat, player in stat_rows}
    trend = _trend_data(db, player_ids, season, TREND_WINDOW)

    pts_vals = [_safe_float(s.pts_pg) for s, _ in stat_rows]
    reb_vals = [_safe_float(s.reb_pg) for s, _ in stat_rows]
    ast_vals = [_safe_float(s.ast_pg) for s, _ in stat_rows]
    ts_vals = [_derive_ts_pct(s) for s, _ in stat_rows]
    efg_vals = [_derive_efg_pct(s) for s, _ in stat_rows]
    usage_eff_vals = [_usage_adjusted_efficiency(s) for s, _ in stat_rows]
    bpm_vals = [_safe_float(s.bpm) for s, _ in stat_rows]
    vorp_vals = [_safe_float(s.vorp) for s, _ in stat_rows]
    ws_vals = [_safe_float(s.ws) for s, _ in stat_rows]
    on_off_vals = [_safe_float(on_off_by_player.get(p.id).on_off_net) if on_off_by_player.get(p.id) else None for _, p in stat_rows]
    win_vals = []
    net_vals = []
    momentum_vals = []
    for stat, player in stat_rows:
        team = team_by_key[player.id]
        team_row = team_stats_by_id.get(team.id) if team else None
        win_vals.append(_safe_float(team_row.w_pct) if team_row else None)
        net_vals.append(_safe_float(team_row.net_rating) if team_row else None)
        pts_delta, reb_delta, ast_delta, ts_delta, _, _, _ = trend.get(player.id, (None, None, None, None, "steady", 0, None))
        momentum_vals.append(_avg([pts_delta, reb_delta, ast_delta, (ts_delta * 100.0) if ts_delta is not None else None]))

    z = {
        "pts": _zscore_pool(pts_vals),
        "reb": _zscore_pool(reb_vals),
        "ast": _zscore_pool(ast_vals),
        "ts": _zscore_pool(ts_vals),
        "efg": _zscore_pool(efg_vals),
        "usage_eff": _zscore_pool(usage_eff_vals),
        "bpm": _zscore_pool(bpm_vals),
        "vorp": _zscore_pool(vorp_vals),
        "ws": _zscore_pool(ws_vals),
        "on_off": _zscore_pool(on_off_vals),
        "win": _zscore_pool(win_vals),
        "net": _zscore_pool(net_vals),
        "momentum": _zscore_pool(momentum_vals),
    }

    preliminary_scores: List[float] = []
    for i in range(len(stat_rows)):
        preliminary_scores.append(
            MVP_WEIGHTS["production"] * (_avg([z["pts"][i], z["reb"][i], z["ast"][i]]) or 0.0)
            + MVP_WEIGHTS["efficiency"] * (_avg([z["ts"][i], z["efg"][i], z["usage_eff"][i]]) or 0.0)
            + MVP_WEIGHTS["impact"] * (_avg([z["bpm"][i], z["vorp"][i], z["ws"][i], z["on_off"][i]]) or 0.0)
            + MVP_WEIGHTS["team_context"] * (_avg([z["win"][i], z["net"][i]]) or 0.0)
            + MVP_WEIGHTS["momentum"] * z["momentum"][i]
        )
    preliminary_size = min(len(stat_rows), max(top * 3, 30))
    preliminary_indices = [
        idx for idx, _ in sorted(enumerate(preliminary_scores), key=lambda item: item[1], reverse=True)[:preliminary_size]
    ]
    preliminary_player_ids = [stat_rows[i][1].id for i in preliminary_indices]
    play_styles = _play_style_profiles(db, preliminary_player_ids, season)
    preliminary_play_values = [_play_style_value(play_styles.get(pid, [])) for pid in preliminary_player_ids]
    preliminary_play_z = _zscore_pool(preliminary_play_values)
    play_z_by_player = {
        player_id: preliminary_play_z[index]
        for index, player_id in enumerate(preliminary_player_ids)
    }

    pillar_raw: List[Dict[str, float]] = []
    raw_scores: List[float] = []
    for i in range(len(stat_rows)):
        player_id = stat_rows[i][1].id
        pillars = {
            "production": _avg([z["pts"][i], z["reb"][i], z["ast"][i]]) or 0.0,
            "efficiency": _avg([z["ts"][i], z["efg"][i], z["usage_eff"][i]]) or 0.0,
            "impact": _avg([z["bpm"][i], z["vorp"][i], z["ws"][i], z["on_off"][i]]) or 0.0,
            "team_context": _avg([z["win"][i], z["net"][i]]) or 0.0,
            "momentum": z["momentum"][i],
            "play_style": play_z_by_player.get(player_id, 0.0),
        }
        pillar_raw.append(pillars)
        raw_scores.append(sum(MVP_WEIGHTS[key] * value for key, value in pillars.items()))

    indexed = sorted(enumerate(raw_scores), key=lambda item: item[1], reverse=True)
    top_indices = [idx for idx, _ in indexed[:top]]
    selected_scores = [raw_scores[i] for i in top_indices]
    max_score = selected_scores[0] if selected_scores else 1.0
    min_score = selected_scores[-1] if len(selected_scores) > 1 else 0.0
    score_range = max_score - min_score if max_score != min_score else 1.0

    def _normalized(raw: float) -> float:
        return round(((raw - min_score) / score_range) * 100.0, 1)

    latest_date = None
    candidates: List[MvpCandidate] = []
    for rank, arr_idx in enumerate(top_indices, start=1):
        stat, player = stat_rows[arr_idx]
        team = team_by_key[player.id]
        team_row = team_stats_by_id.get(team.id) if team else None
        on_off_row = on_off_by_player.get(player.id)
        pts_delta, reb_delta, ast_delta, ts_delta, momentum, last_games, last_date = trend.get(
            player.id, (None, None, None, None, "steady", 0, None)
        )
        if last_date and (latest_date is None or last_date > latest_date):
            latest_date = last_date

        team_context = None
        if team and team_row:
            team_context = MvpTeamContext(
                team_id=team.id,
                team_name=team.name,
                wins=team_row.w,
                losses=team_row.l,
                win_pct=_round(team_row.w_pct, 3),
                net_rating=_round(team_row.net_rating, 1),
                off_rating=_round(team_row.off_rating, 1),
                def_rating=_round(team_row.def_rating, 1),
                win_pct_rank=win_ranks.get(team.id),
                net_rating_rank=net_ranks.get(team.id),
            )
        on_off = None
        if on_off_row:
            on_off = MvpOnOffProfile(
                on_minutes=_round(on_off_row.on_minutes, 1),
                off_minutes=_round(on_off_row.off_minutes, 1),
                on_net_rating=_round(on_off_row.on_net_rating, 1),
                off_net_rating=_round(on_off_row.off_net_rating, 1),
                on_off_net=_round(on_off_row.on_off_net, 1),
                on_ortg=_round(on_off_row.on_ortg, 1),
                on_drtg=_round(on_off_row.on_drtg, 1),
                off_ortg=_round(on_off_row.off_ortg, 1),
                off_drtg=_round(on_off_row.off_drtg, 1),
                confidence=_on_off_confidence(on_off_row),
            )
        advanced = MvpAdvancedProfile(
            usg_pct=_round(stat.usg_pct, 1),
            ts_pct=_round(_derive_ts_pct(stat), 3),
            efg_pct=_round(_derive_efg_pct(stat), 3),
            bpm=_round(stat.bpm, 1),
            obpm=_round(stat.obpm, 1),
            dbpm=_round(stat.dbpm, 1),
            vorp=_round(stat.vorp, 1),
            ws=_round(stat.ws, 1),
            win_shares_per_48=_round(_win_shares_per_48(stat), 3),
            pie=_round(stat.pie, 3),
            net_rating=_round(stat.net_rating, 1),
            off_rating=_round(stat.off_rating, 1),
            def_rating=_round(stat.def_rating, 1),
            epm=_round(stat.epm, 1),
            raptor=_round(stat.raptor, 1),
            lebron=_round(stat.lebron, 1),
        )
        clutch = MvpClutchAndPaceProfile(
            clutch_pts=_round(stat.clutch_pts, 1),
            clutch_fga=stat.clutch_fga,
            clutch_fg_pct=_round(stat.clutch_fg_pct, 3),
            second_chance_pts=_round(stat.second_chance_pts, 1),
            fast_break_pts=_round(stat.fast_break_pts, 1),
        )
        play_style = play_styles.get(player.id, [])
        score_pillars = {
            key: MvpScorePillar(
                label=key.replace("_", " ").title(),
                weight=MVP_WEIGHTS[key],
                raw_score=_round(pillar_raw[arr_idx][key], 3) or 0.0,
                weighted_score=_round(pillar_raw[arr_idx][key] * MVP_WEIGHTS[key], 3) or 0.0,
                display_score=_display_score(pillar_raw[arr_idx][key]),
            )
            for key in MVP_WEIGHTS
        }
        candidate = MvpCandidate(
            rank=rank,
            player_id=player.id,
            player_name=player.full_name,
            team_abbreviation=stat.team_abbreviation,
            headshot_url=player.headshot_url or "",
            gp=stat.gp or 0,
            composite_score=_normalized(raw_scores[arr_idx]),
            pts_pg=float(stat.pts_pg or 0.0),
            reb_pg=float(stat.reb_pg or 0.0),
            ast_pg=float(stat.ast_pg or 0.0),
            ts_pct=_round(_derive_ts_pct(stat), 3),
            bpm=_round(stat.bpm, 1),
            pts_delta=_round(pts_delta, 1),
            reb_delta=_round(reb_delta, 1),
            ast_delta=_round(ast_delta, 1),
            ts_delta=_round(ts_delta, 3),
            momentum=momentum,
            last_games=last_games,
            score_pillars=score_pillars,
            team_context=team_context,
            on_off=on_off,
            advanced_profile=advanced,
            clutch_and_pace=clutch,
            play_style=play_style,
            data_coverage=_coverage(stat, team_context, on_off, play_style),
        )
        candidate.case_summary = _case_summary(candidate)
        candidates.append(candidate)

    return candidates, str(latest_date) if latest_date else str(date.today())


def build_mvp_race(
    db: Session,
    season: str,
    top: int = 10,
    min_gp: int = MIN_GP,
    position: Optional[str] = None,
) -> MvpRaceResponse:
    candidates, as_of = _build_ranked_candidates(
        db=db,
        season=season,
        top=top,
        min_gp=min_gp,
        position=position,
    )
    return MvpRaceResponse(
        season=season,
        as_of_date=as_of,
        candidates=candidates,
        weights=MVP_WEIGHTS,
        scoring_profile=SCORING_PROFILE,
    )


def build_mvp_candidate_case(
    db: Session,
    season: str,
    player_id: int,
    min_gp: int = MIN_GP,
    position: Optional[str] = None,
) -> MvpCandidateCaseResponse:
    candidates, as_of = _build_ranked_candidates(
        db=db,
        season=season,
        top=25,
        min_gp=min_gp,
        position=position,
    )
    candidate = next((row for row in candidates if row.player_id == player_id), None)
    if candidate is None:
        raise HTTPException(status_code=404, detail="MVP candidate case not found for this season/filter.")
    nearby = [
        MvpNearbyCandidate(
            rank=row.rank,
            player_id=row.player_id,
            player_name=row.player_name,
            team_abbreviation=row.team_abbreviation,
            composite_score=row.composite_score,
        )
        for row in candidates
        if abs(row.rank - candidate.rank) <= 2
    ]
    return MvpCandidateCaseResponse(
        season=season,
        as_of_date=as_of,
        candidate=candidate,
        nearby=nearby,
        weights=MVP_WEIGHTS,
        scoring_profile=SCORING_PROFILE,
    )
