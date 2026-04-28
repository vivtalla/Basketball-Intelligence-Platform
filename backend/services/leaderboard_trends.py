"""Leaderboard trend service.

Computes per-player rolling per-game values for a leaderboard stat using the
last N games stored in `player_game_logs`. Designed to feed the home-page
league-leader sparkline column.

Notes
-----
- Box-score per-game stats (e.g. ``pts_pg``, ``ast_pg``) collapse to the raw
  per-game column on ``PlayerGameLog`` (e.g. ``pts``, ``ast``).
- Percentage stats (``fg_pct``, ``ts_pct``, ``efg_pct``, ``fg3_pct``, ``ft_pct``)
  are recomputed per game from the box-score counts. If a game has zero
  attempts, the season percentage from ``season_stats`` is used as a stable
  placeholder so the sparkline doesn't drop a point.
- Players with fewer than 3 logged games are returned with an empty
  ``rolling_values`` array and ``sample_size=0`` so the frontend can render a
  placeholder.
- Zero-attempts games on a percentage stat are dropped from
  ``rolling_values`` when no season placeholder exists, which causes
  ``sample_size`` to drift below ``window``. Callers should treat
  ``sample_size`` as the count of usable games, not the requested window.
"""

from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from db.models import Player, PlayerGameLog, SeasonStat
from models.leaderboard import LeaderboardTrendEntry, LeaderboardTrendResponse
from services.sync_service import canonical_player_name

MIN_GAMES_FOR_TREND = 3

# Map per-game season stat keys to their per-game ``PlayerGameLog`` field.
_PER_GAME_STAT_TO_LOG_FIELD: Dict[str, str] = {
    "pts_pg": "pts",
    "reb_pg": "reb",
    "ast_pg": "ast",
    "stl_pg": "stl",
    "blk_pg": "blk",
    "tov_pg": "tov",
    "min_pg": "min",
}

# Percentage stats compute on (made, attempted) per game.
_PCT_STAT_TO_PAIR: Dict[str, Tuple[str, str]] = {
    "fg_pct": ("fgm", "fga"),
    "fg3_pct": ("fg3m", "fg3a"),
    "ft_pct": ("ftm", "fta"),
}


def _per_game_value_from_log(log: PlayerGameLog, stat: str) -> Optional[float]:
    """Return the rolling per-game value for ``stat`` from a single game log."""
    if stat in _PER_GAME_STAT_TO_LOG_FIELD:
        raw = getattr(log, _PER_GAME_STAT_TO_LOG_FIELD[stat], None)
        return float(raw) if raw is not None else None
    if stat in _PCT_STAT_TO_PAIR:
        made_field, att_field = _PCT_STAT_TO_PAIR[stat]
        made = getattr(log, made_field, None) or 0
        att = getattr(log, att_field, None) or 0
        if att <= 0:
            return None
        return round(float(made) / float(att), 4)
    if stat == "efg_pct":
        fga = getattr(log, "fga", None) or 0
        if not fga:
            return None
        fgm = getattr(log, "fgm", None) or 0
        fg3m = getattr(log, "fg3m", None) or 0
        return round((float(fgm) + 0.5 * float(fg3m)) / float(fga), 4)
    if stat == "ts_pct":
        pts = getattr(log, "pts", None) or 0
        fga = getattr(log, "fga", None) or 0
        fta = getattr(log, "fta", None) or 0
        denom = 2.0 * (float(fga) + 0.44 * float(fta))
        if denom <= 0:
            return None
        return round(float(pts) / denom, 4)
    # Direct fallback — try the same column on the game log (e.g. raw box stats).
    raw = getattr(log, stat, None)
    return float(raw) if raw is not None else None


def _season_percentage_placeholder(
    season_row: Optional[SeasonStat], stat: str
) -> Optional[float]:
    """Fall-back for percentage stats when a game has zero attempts."""
    if season_row is None:
        return None
    value = getattr(season_row, stat, None)
    return float(value) if value is not None else None


def _season_baseline(season_row: Optional[SeasonStat], stat: str) -> Optional[float]:
    """Season-average baseline for the requested stat, derived from ``season_stats``."""
    if season_row is None:
        return None
    value = getattr(season_row, stat, None)
    if value is not None:
        return float(value)
    if stat in _PCT_STAT_TO_PAIR:
        made_field, att_field = _PCT_STAT_TO_PAIR[stat]
        made = getattr(season_row, made_field, None) or 0
        att = getattr(season_row, att_field, None) or 0
        if att <= 0:
            return None
        return round(float(made) / float(att), 4)
    if stat == "efg_pct":
        fga = getattr(season_row, "fga", None) or 0
        if not fga:
            return None
        fgm = getattr(season_row, "fgm", None) or 0
        fg3m = getattr(season_row, "fg3m", None) or 0
        return round((float(fgm) + 0.5 * float(fg3m)) / float(fga), 4)
    if stat == "ts_pct":
        pts = getattr(season_row, "pts", None) or 0
        fga = getattr(season_row, "fga", None) or 0
        fta = getattr(season_row, "fta", None) or 0
        denom = 2.0 * (float(fga) + 0.44 * float(fta))
        if denom <= 0:
            return None
        return round(float(pts) / denom, 4)
    return None


def _build_entry(
    player: Player,
    season: str,
    stat: str,
    logs: List[PlayerGameLog],
    season_row: Optional[SeasonStat],
    window: int,
) -> LeaderboardTrendEntry:
    team_abbreviation = season_row.team_abbreviation if season_row else None

    if len(logs) < MIN_GAMES_FOR_TREND:
        return LeaderboardTrendEntry(
            player_id=player.id,
            player_name=canonical_player_name(
                player.full_name,
                player.first_name or "",
                player.last_name or "",
            ),
            team_abbreviation=team_abbreviation,
            season=season,
            stat=stat,
            rolling_values=[],
            sample_size=0,
            latest_value=None,
            delta_vs_baseline=None,
        )

    sorted_logs = sorted(
        logs,
        key=lambda r: (r.game_date or date.min, r.game_id),
    )
    window_logs = sorted_logs[-window:]
    pct_placeholder = (
        _season_percentage_placeholder(season_row, stat)
        if stat in _PCT_STAT_TO_PAIR or stat in {"efg_pct", "ts_pct"}
        else None
    )

    rolling_values: List[float] = []
    for log in window_logs:
        value = _per_game_value_from_log(log, stat)
        if value is None and pct_placeholder is not None:
            value = pct_placeholder
        if value is not None:
            rolling_values.append(round(float(value), 4))

    sample_size = len(rolling_values)
    latest_value = rolling_values[-1] if rolling_values else None
    baseline = _season_baseline(season_row, stat)
    delta_vs_baseline: Optional[float]
    if latest_value is not None and baseline is not None:
        delta_vs_baseline = round(latest_value - baseline, 4)
    else:
        delta_vs_baseline = None

    return LeaderboardTrendEntry(
        player_id=player.id,
        player_name=canonical_player_name(
            player.full_name,
            player.first_name or "",
            player.last_name or "",
        ),
        team_abbreviation=team_abbreviation,
        season=season,
        stat=stat,
        rolling_values=rolling_values,
        sample_size=sample_size,
        latest_value=latest_value,
        delta_vs_baseline=delta_vs_baseline,
    )


def compute_leaderboard_trends(
    db: Session,
    stat: str,
    player_ids: List[int],
    season: str,
    window: int,
) -> LeaderboardTrendResponse:
    """Compute rolling-window trends for the requested players + stat."""
    deduped_ids: List[int] = []
    seen = set()
    for pid in player_ids:
        if pid not in seen:
            seen.add(pid)
            deduped_ids.append(pid)

    entries: List[LeaderboardTrendEntry] = []
    if not deduped_ids:
        return LeaderboardTrendResponse(
            season=season,
            stat=stat,
            window=window,
            entries=entries,
        )

    players = (
        db.query(Player)
        .filter(Player.id.in_(deduped_ids))
        .all()
    )
    player_by_id = {p.id: p for p in players}

    logs = (
        db.query(PlayerGameLog)
        .filter(
            PlayerGameLog.player_id.in_(deduped_ids),
            PlayerGameLog.season == season,
            PlayerGameLog.season_type == "Regular Season",
        )
        .all()
    )
    logs_by_player: Dict[int, List[PlayerGameLog]] = {pid: [] for pid in deduped_ids}
    for log in logs:
        logs_by_player.setdefault(log.player_id, []).append(log)

    season_rows = (
        db.query(SeasonStat)
        .filter(
            SeasonStat.player_id.in_(deduped_ids),
            SeasonStat.season == season,
            SeasonStat.is_playoff == False,  # noqa: E712
        )
        .all()
    )
    # If a player was traded mid-season, prefer the row with the most games played.
    season_by_player: Dict[int, SeasonStat] = {}
    for row in season_rows:
        existing = season_by_player.get(row.player_id)
        if existing is None or (row.gp or 0) > (existing.gp or 0):
            season_by_player[row.player_id] = row

    for pid in deduped_ids:
        player = player_by_id.get(pid)
        if player is None:
            continue
        entries.append(
            _build_entry(
                player=player,
                season=season,
                stat=stat,
                logs=logs_by_player.get(pid, []),
                season_row=season_by_player.get(pid),
                window=window,
            )
        )

    return LeaderboardTrendResponse(
        season=season,
        stat=stat,
        window=window,
        entries=entries,
    )
