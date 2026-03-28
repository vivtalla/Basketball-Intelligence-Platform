"""Play-by-play processing: stint building, on/off splits, clutch/2nd-chance/fast-break stats."""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Clock helpers
# ---------------------------------------------------------------------------

def _parse_clock_seconds(clock: str) -> float:
    """Convert NBA clock string ('PT05M30.00S' or 'PT00M05.50S') to total seconds."""
    if not clock:
        return 0.0
    m = re.match(r"PT(\d+)M([\d.]+)S", clock)
    if m:
        return int(m.group(1)) * 60 + float(m.group(2))
    # Fallback: try MM:SS format
    m2 = re.match(r"(\d+):(\d+)", clock)
    if m2:
        return int(m2.group(1)) * 60 + int(m2.group(2))
    return 0.0


def _canonical_name(name: str) -> str:
    if not name:
        return ""
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return " ".join(normalized.lower().replace(".", "").split())


# ---------------------------------------------------------------------------
# Stint data structure
# ---------------------------------------------------------------------------

@dataclass
class Stint:
    """A continuous stretch of play with fixed 5-man lineups for both teams."""
    home_players: frozenset[int]
    away_players: frozenset[int]
    start_score_home: int
    start_score_away: int
    end_score_home: int
    end_score_away: int
    home_possessions: int = 0
    away_possessions: int = 0
    seconds: float = 0.0  # estimated duration

    @property
    def home_plus_minus(self) -> int:
        return (self.end_score_home - self.start_score_home) - (self.end_score_away - self.start_score_away)

    @property
    def away_plus_minus(self) -> int:
        return -self.home_plus_minus


# ---------------------------------------------------------------------------
# Stint builder
# ---------------------------------------------------------------------------

def build_stints(pbp_events: list[dict], box_score: dict) -> list[Stint]:
    """Parse PBP events and build a list of Stints.

    Args:
        pbp_events: output of nba_client.get_play_by_play()
        box_score:  output of nba_client.get_game_box_score()
    """
    home_team_id = box_score.get("home_team_id")
    away_team_id = box_score.get("away_team_id")

    # Build starting lineups from box score starter flags
    home_starters: set[int] = set()
    away_starters: set[int] = set()
    for p in box_score.get("players", []):
        pid = p.get("player_id")
        if not pid:
            continue
        if p.get("start_position", ""):
            if p.get("team_id") == home_team_id:
                home_starters.add(pid)
            elif p.get("team_id") == away_team_id:
                away_starters.add(pid)

    home_name_map: dict[str, int] = {}
    away_name_map: dict[str, int] = {}
    for p in box_score.get("players", []):
        pid = p.get("player_id")
        player_name = _canonical_name(p.get("player_name", ""))
        if not pid or not player_name:
            continue
        parts = player_name.split()
        candidates = {player_name}
        if parts:
            candidates.add(parts[-1])
            if len(parts) >= 2:
                candidates.add(f"{parts[0][0]} {parts[-1]}")
        target_map = home_name_map if p.get("team_id") == home_team_id else away_name_map
        for candidate in candidates:
            target_map.setdefault(candidate, pid)

    # Fall back: if we couldn't determine starters, skip (no stints)
    if len(home_starters) < 5 or len(away_starters) < 5:
        return []

    home_on_court: set[int] = set(home_starters)
    away_on_court: set[int] = set(away_starters)

    stints: list[Stint] = []
    current_score_home = 0
    current_score_away = 0
    stint_start_home = 0
    stint_start_away = 0

    def _close_stint(end_h: int, end_a: int, home_poss: int, away_poss: int):
        if len(home_on_court) == 5 and len(away_on_court) == 5:
            stints.append(Stint(
                home_players=frozenset(home_on_court),
                away_players=frozenset(away_on_court),
                start_score_home=stint_start_home,
                start_score_away=stint_start_away,
                end_score_home=end_h,
                end_score_away=end_a,
                home_possessions=home_poss,
                away_possessions=away_poss,
            ))

    home_poss_acc = 0
    away_poss_acc = 0

    def _apply_substitution(lineup: set[int], event: dict, name_map: dict[str, int], current_player_id: int | None):
        sub_type = (event.get("subType") or "").lower()
        if sub_type == "in" and current_player_id:
            lineup.add(current_player_id)
            return
        if sub_type == "out" and current_player_id:
            lineup.discard(current_player_id)
            return

        outgoing_id = current_player_id
        incoming_id = name_map.get(_canonical_name(event.get("incomingPlayerName", "")))
        if not outgoing_id:
            outgoing_id = name_map.get(_canonical_name(event.get("outgoingPlayerName", "")))

        if outgoing_id:
            lineup.discard(outgoing_id)
        if incoming_id:
            lineup.add(incoming_id)

    for event in pbp_events:
        action_type = (event.get("actionType") or "").lower()
        sub_type = (event.get("subType") or "").lower()
        team_id = event.get("teamId")
        player_id = event.get("personId")

        # Update scores
        sh = event.get("scoreHome")
        sa = event.get("scoreAway")
        try:
            sh = int(sh) if sh is not None else current_score_home
            sa = int(sa) if sa is not None else current_score_away
        except (ValueError, TypeError):
            sh, sa = current_score_home, current_score_away

        # Count possessions (field goal attempt, turnover, or final free throw)
        if action_type in ("2pt", "3pt"):
            if team_id == home_team_id:
                home_poss_acc += 1
            else:
                away_poss_acc += 1
        elif action_type == "turnover":
            if team_id == home_team_id:
                home_poss_acc += 1
            else:
                away_poss_acc += 1

        if action_type == "substitution":
            # Close current stint, open new one
            _close_stint(sh, sa, home_poss_acc, away_poss_acc)
            home_poss_acc = 0
            away_poss_acc = 0

            # Apply substitution
            if team_id == home_team_id:
                _apply_substitution(home_on_court, event, home_name_map, player_id)
            elif team_id == away_team_id:
                _apply_substitution(away_on_court, event, away_name_map, player_id)

            stint_start_home = sh
            stint_start_away = sa

        elif action_type == "period":
            # End of period — close stint, reset
            _close_stint(sh, sa, home_poss_acc, away_poss_acc)
            home_poss_acc = 0
            away_poss_acc = 0
            stint_start_home = sh
            stint_start_away = sa

        current_score_home = sh
        current_score_away = sa

    # Close final stint
    _close_stint(current_score_home, current_score_away, home_poss_acc, away_poss_acc)

    return stints


# ---------------------------------------------------------------------------
# On/Off aggregation
# ---------------------------------------------------------------------------

@dataclass
class PlayerOnOffAccumulator:
    on_plus_minus: float = 0.0
    off_plus_minus: float = 0.0
    on_possessions: int = 0
    off_possessions: int = 0
    on_team_pts: int = 0
    on_opp_pts: int = 0
    off_team_pts: int = 0
    off_opp_pts: int = 0
    # minutes approximated from possessions (avg ~1 poss per ~15s ≈ 4 per min)
    on_seconds: float = 0.0
    off_seconds: float = 0.0


def compute_on_off(stints: list[Stint], team_player_ids: set[int]) -> dict[int, PlayerOnOffAccumulator]:
    """Aggregate on/off stats for all players in team_player_ids from stints."""
    accum: dict[int, PlayerOnOffAccumulator] = defaultdict(PlayerOnOffAccumulator)

    for stint in stints:
        # Determine which team these players belong to
        home_overlap = stint.home_players & team_player_ids
        away_overlap = stint.away_players & team_player_ids

        if home_overlap:
            team_players_on = stint.home_players & team_player_ids
            team_pts = (stint.end_score_home - stint.start_score_home)
            opp_pts = (stint.end_score_away - stint.start_score_away)
            pm = stint.home_plus_minus
            poss = stint.home_possessions
        elif away_overlap:
            team_players_on = stint.away_players & team_player_ids
            team_pts = (stint.end_score_away - stint.start_score_away)
            opp_pts = (stint.end_score_home - stint.start_score_home)
            pm = stint.away_plus_minus
            poss = stint.away_possessions
        else:
            continue

        for pid in team_player_ids:
            acc = accum[pid]
            if pid in team_players_on:
                acc.on_plus_minus += pm
                acc.on_possessions += poss
                acc.on_team_pts += team_pts
                acc.on_opp_pts += opp_pts
            else:
                acc.off_plus_minus += pm
                acc.off_possessions += poss
                acc.off_team_pts += team_pts
                acc.off_opp_pts += opp_pts

    return accum


def finalize_on_off(accum: dict[int, PlayerOnOffAccumulator]) -> dict[int, dict]:
    """Convert raw accumulators into per-100-possession ratings."""
    results = {}
    for pid, acc in accum.items():
        def _net_rating(team_pts, opp_pts, poss):
            if poss == 0:
                return None
            return round((team_pts - opp_pts) / poss * 100, 1)

        def _ortg(team_pts, poss):
            if poss == 0:
                return None
            return round(team_pts / poss * 100, 1)

        def _drtg(opp_pts, poss):
            if poss == 0:
                return None
            return round(opp_pts / poss * 100, 1)

        on_net = _net_rating(acc.on_team_pts, acc.on_opp_pts, acc.on_possessions)
        off_net = _net_rating(acc.off_team_pts, acc.off_opp_pts, acc.off_possessions)
        on_off = round(on_net - off_net, 1) if on_net is not None and off_net is not None else None

        # Approximate minutes: NBA averages ~97 possessions/48 min ≈ 2 poss/min
        on_min = round(acc.on_possessions / 2.0, 1)
        off_min = round(acc.off_possessions / 2.0, 1)

        results[pid] = {
            "on_minutes": on_min,
            "off_minutes": off_min,
            "on_net_rating": on_net,
            "off_net_rating": off_net,
            "on_off_net": on_off,
            "on_ortg": _ortg(acc.on_team_pts, acc.on_possessions),
            "on_drtg": _drtg(acc.on_opp_pts, acc.on_possessions),
            "off_ortg": _ortg(acc.off_team_pts, acc.off_possessions),
            "off_drtg": _drtg(acc.off_opp_pts, acc.off_possessions),
        }
    return results


# ---------------------------------------------------------------------------
# Clutch stats
# ---------------------------------------------------------------------------

def compute_clutch_stats(pbp_events: list[dict], team_id: int) -> dict[int, dict]:
    """Clutch = Q4+OT, <=5 min remaining, margin <=5 pts.

    Returns per-player
    { player_id: {clutch_pts, clutch_fga, clutch_fgm, clutch_plus_minus, clutch_fg_pct} }.
    """
    player_stats: dict[int, dict] = defaultdict(lambda: {"pts": 0, "fga": 0, "fgm": 0, "plus_minus": 0})

    for event in pbp_events:
        period = event.get("period", 0)
        clock = event.get("clock", "")
        action_type = (event.get("actionType") or "").lower()
        sub_type = (event.get("subType") or "").lower()
        ev_team_id = event.get("teamId")
        player_id = event.get("personId")

        if period < 4:
            continue

        secs_remaining = _parse_clock_seconds(clock)
        if secs_remaining > 300:  # more than 5 minutes left
            continue

        try:
            sh = int(event.get("scoreHome") or 0)
            sa = int(event.get("scoreAway") or 0)
        except (ValueError, TypeError):
            continue

        margin = abs(sh - sa)
        if margin > 5:
            continue

        if not player_id or ev_team_id != team_id:
            continue

        if action_type in ("2pt", "3pt"):
            pts_value = 3 if action_type == "3pt" else 2
            player_stats[player_id]["fga"] += 1
            if sub_type == "made":
                player_stats[player_id]["fgm"] += 1
                player_stats[player_id]["pts"] += pts_value

        elif action_type == "freethrow" and sub_type == "made":
            player_stats[player_id]["pts"] += 1

    # Compute FG%
    result = {}
    for pid, s in player_stats.items():
        fg_pct = round(s["fgm"] / s["fga"], 3) if s["fga"] > 0 else None
        result[pid] = {
            "clutch_pts": s["pts"],
            "clutch_fga": s["fga"],
            "clutch_fgm": s["fgm"],
            "clutch_fg_pct": fg_pct,
            "clutch_plus_minus": None,  # populated later from stints
        }
    return result


# ---------------------------------------------------------------------------
# Second chance & fast break points
# ---------------------------------------------------------------------------

def compute_second_chance_and_fast_break(pbp_events: list[dict], team_id: int) -> dict[int, dict]:
    """Compute second-chance and fast-break points per player for a team.

    Returns { player_id: {second_chance_pts, fast_break_pts} }
    """
    player_stats: dict[int, dict] = defaultdict(lambda: {"second_chance_pts": 0, "fast_break_pts": 0})

    # State machine flags
    oreb_pending = False   # offensive rebound just happened for our team
    drb_or_tov_pending = False  # we got the ball via def rebound or opponent turnover
    transition_clock: Optional[float] = None
    transition_period: Optional[int] = None

    for event in pbp_events:
        action_type = (event.get("actionType") or "").lower()
        sub_type = (event.get("subType") or "").lower()
        ev_team_id = event.get("teamId")
        player_id = event.get("personId")
        period = event.get("period", 0)
        clock_secs = _parse_clock_seconds(event.get("clock", ""))

        is_our_team = (ev_team_id == team_id)
        is_opp_team = (ev_team_id is not None and ev_team_id != team_id)

        # --- OFFENSIVE REBOUND ---
        if action_type == "rebound" and sub_type == "offensive" and is_our_team:
            oreb_pending = True
            drb_or_tov_pending = False

        # --- DEFENSIVE REBOUND or OPPONENT TURNOVER → transition opportunity ---
        elif (action_type == "rebound" and sub_type == "defensive" and is_our_team) or \
             (action_type == "turnover" and is_opp_team):
            drb_or_tov_pending = True
            oreb_pending = False
            transition_clock = clock_secs
            transition_period = period

        # --- SCORING EVENTS ---
        elif action_type in ("2pt", "3pt") and is_our_team and player_id:
            pts = 3 if action_type == "3pt" else 2
            if sub_type == "made":
                if oreb_pending:
                    player_stats[player_id]["second_chance_pts"] += pts
                if drb_or_tov_pending and transition_period == period:
                    elapsed = (transition_clock or 0) - clock_secs
                    if elapsed <= 8:  # within ~8 seconds = fast break window
                        player_stats[player_id]["fast_break_pts"] += pts
            oreb_pending = False
            drb_or_tov_pending = False

        elif action_type == "freethrow" and sub_type == "made" and is_our_team and player_id:
            if oreb_pending:
                player_stats[player_id]["second_chance_pts"] += 1
            if drb_or_tov_pending and transition_period == period:
                elapsed = (transition_clock or 0) - clock_secs
                if elapsed <= 8:
                    player_stats[player_id]["fast_break_pts"] += 1

        # --- ANY OTHER POSSESSION-ENDING EVENT resets flags ---
        elif action_type in ("2pt", "3pt", "turnover") and is_opp_team:
            oreb_pending = False
            drb_or_tov_pending = False

    return {pid: dict(s) for pid, s in player_stats.items()}


# ---------------------------------------------------------------------------
# Lineup accumulation
# ---------------------------------------------------------------------------

@dataclass
class LineupAccumulator:
    plus_minus: float = 0.0
    possessions: int = 0
    team_pts: int = 0
    opp_pts: int = 0


def compute_lineup_stats(stints: list[Stint], home_team_id: int) -> dict[str, LineupAccumulator]:
    """Build a map of lineup_key → accumulated stats for all 5-man lineups."""
    lineups: dict[str, LineupAccumulator] = defaultdict(LineupAccumulator)

    for stint in stints:
        for players, is_home in [(stint.home_players, True), (stint.away_players, False)]:
            if len(players) != 5:
                continue
            key = "-".join(str(p) for p in sorted(players))
            acc = lineups[key]
            if is_home:
                acc.plus_minus += stint.home_plus_minus
                acc.possessions += stint.home_possessions
                acc.team_pts += (stint.end_score_home - stint.start_score_home)
                acc.opp_pts += (stint.end_score_away - stint.start_score_away)
            else:
                acc.plus_minus += stint.away_plus_minus
                acc.possessions += stint.away_possessions
                acc.team_pts += (stint.end_score_away - stint.start_score_away)
                acc.opp_pts += (stint.end_score_home - stint.start_score_home)

    return lineups
