"""Sprint 77 — Possession Diary + per-player per-quarter +/- aggregator.

Pure functions over `play_by_play` (and warehouse `play_by_play_events`) for a
single game. The diary groups raw PBP rows into possessions following the
project's possession-counting rule and returns the top 24 most lead-impactful
possessions. The +/- aggregator walks substitutions to track on-court lineups
per team and assigns home_score - away_score deltas to every player on the
floor at the time of a scoring event.

These functions intentionally have no side effects and never call the NBA API —
they only read existing rows from the session.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from db.models import (
    GameLog,
    PlayByPlay,
    PlayByPlayEvent,
    Player,
    PlayerGameLog,
    Team,
)
from models.game import PlayerQuarterImpact, PossessionEntry


# ---------------------------------------------------------------------------
# Clock helpers
# ---------------------------------------------------------------------------

_CLOCK_PT_RE = re.compile(r"PT(\d+)M([\d.]+)S")
_CLOCK_MMSS_RE = re.compile(r"^(\d+):([\d.]+)$")
_LAST_FT_RE = re.compile(r"\b(\d) of \1\b")


def _parse_clock_seconds(clock: Optional[str]) -> Optional[float]:
    """Convert a PBP clock string to remaining-seconds-in-period.

    Supports "PT05M30.00S" (warehouse) and "MM:SS" (legacy).
    Returns ``None`` if the clock is missing/unparseable so callers can ignore
    it instead of treating it as 0.
    """

    if not clock:
        return None
    m = _CLOCK_PT_RE.match(clock)
    if m:
        return int(m.group(1)) * 60 + float(m.group(2))
    m2 = _CLOCK_MMSS_RE.match(clock)
    if m2:
        try:
            return int(m2.group(1)) * 60 + float(m2.group(2))
        except ValueError:
            return None
    return None


def _format_mmss(seconds: Optional[float]) -> str:
    if seconds is None:
        return "00:00"
    total = max(0, int(round(seconds)))
    return "{:02d}:{:02d}".format(total // 60, total % 60)


# ---------------------------------------------------------------------------
# Event loading + iteration
# ---------------------------------------------------------------------------


def _iter_events(db: Session, game_id: str) -> List[object]:
    """Return PBP rows for the game ordered by (period, action_number).

    Prefers the canonical `play_by_play_events` table when present; otherwise
    falls back to the legacy `play_by_play` rows. Each returned row exposes
    the same attribute names regardless of source: ``period``, ``clock``,
    ``team_id``, ``player_id``, ``action_type``, ``sub_type``, ``description``,
    ``score_home``, ``score_away``, and ``action_number``.
    """

    canonical = (
        db.query(PlayByPlayEvent)
        .filter_by(game_id=game_id)
        .order_by(
            PlayByPlayEvent.period.asc(),
            PlayByPlayEvent.order_index.asc(),
        )
        .all()
    )
    if canonical:
        return list(canonical)

    legacy = (
        db.query(PlayByPlay)
        .filter_by(game_id=game_id)
        .order_by(
            PlayByPlay.period.asc(),
            PlayByPlay.action_number.asc(),
        )
        .all()
    )
    return list(legacy)


def _normalize_action(action_type: Optional[str], sub_type: Optional[str]) -> Tuple[str, str]:
    return ((action_type or "").lower(), (sub_type or "").lower())


# ---------------------------------------------------------------------------
# Substitution + lineup helpers
# ---------------------------------------------------------------------------


def _extract_substitutions(
    events: Iterable[object],
) -> List[Tuple[int, Optional[float], Optional[int], Optional[int], Optional[int]]]:
    """Return a list of (period, clock_seconds, player_in, player_out, team_id).

    Substitution rows in NBA PBP carry one direction per row (sub_type "in" or
    "out") with the affected player on the row's `player_id`. We surface them
    as a tuple so the on-court tracker can apply them in event order.
    """

    subs: List[Tuple[int, Optional[float], Optional[int], Optional[int], Optional[int]]] = []
    for event in events:
        action_type, sub_type = _normalize_action(event.action_type, event.sub_type)
        if action_type != "substitution":
            continue
        if not event.player_id:
            continue
        period = event.period or 0
        clock_seconds = _parse_clock_seconds(event.clock)
        player_in = event.player_id if sub_type == "in" else None
        player_out = event.player_id if sub_type == "out" else None
        subs.append((period, clock_seconds, player_in, player_out, event.team_id))
    return subs


def _resolve_starters(
    db: Session,
    game_id: str,
    home_team_id: Optional[int],
    away_team_id: Optional[int],
    events: List[object],
) -> Tuple[Set[int], Set[int]]:
    """Best-effort starters resolution.

    1. Use ``PlayerGameLog`` rows for the game with positive minutes; if at
       least 5 per team, pick the 5 highest-min for each team.
    2. Otherwise, fall back to the first 5 unique player_ids per team to
       appear in PBP events.
    """

    home_starters: Set[int] = set()
    away_starters: Set[int] = set()

    if home_team_id and away_team_id:
        rows = (
            db.query(PlayerGameLog, Player)
            .join(Player, Player.id == PlayerGameLog.player_id)
            .filter(PlayerGameLog.game_id == game_id)
            .all()
        )
        per_team: Dict[int, List[Tuple[float, int]]] = defaultdict(list)
        for game_log, player in rows:
            minutes = float(game_log.min or 0.0)
            if minutes <= 0:
                continue
            team_id = player.team_id
            if team_id is None:
                continue
            per_team[team_id].append((minutes, player.id))
        if len(per_team.get(home_team_id, [])) >= 5:
            ranked = sorted(per_team[home_team_id], reverse=True)
            home_starters = {pid for _, pid in ranked[:5]}
        if len(per_team.get(away_team_id, [])) >= 5:
            ranked = sorted(per_team[away_team_id], reverse=True)
            away_starters = {pid for _, pid in ranked[:5]}

    # Fallback: first 5 unique players per team to show up in PBP.
    if len(home_starters) < 5 or len(away_starters) < 5:
        seen_home: List[int] = []
        seen_away: List[int] = []
        for event in events:
            pid = event.player_id
            if not pid:
                continue
            if event.team_id == home_team_id and pid not in seen_home:
                seen_home.append(pid)
            elif event.team_id == away_team_id and pid not in seen_away:
                seen_away.append(pid)
            if len(seen_home) >= 5 and len(seen_away) >= 5:
                break
        if len(home_starters) < 5:
            home_starters = set(seen_home[:5])
        if len(away_starters) < 5:
            away_starters = set(seen_away[:5])

    # Last-resort fallback for sparse fixtures / tests: if either side still
    # has fewer than 5 starters, top up from any roster players associated
    # with the team via ``Player.team_id``. This keeps the +/- aggregator
    # usable for synthetic test games while preserving the PBP-first
    # behavior for real games.
    if len(home_starters) < 5 and home_team_id is not None:
        roster_home = (
            db.query(Player.id)
            .filter(Player.team_id == home_team_id)
            .order_by(Player.id.asc())
            .all()
        )
        for (pid,) in roster_home:
            if len(home_starters) >= 5:
                break
            home_starters.add(pid)
    if len(away_starters) < 5 and away_team_id is not None:
        roster_away = (
            db.query(Player.id)
            .filter(Player.team_id == away_team_id)
            .order_by(Player.id.asc())
            .all()
        )
        for (pid,) in roster_away:
            if len(away_starters) >= 5:
                break
            away_starters.add(pid)

    return home_starters, away_starters


def _on_court_at(
    period: int,
    clock_seconds: Optional[float],
    substitutions: List[Tuple[int, Optional[float], Optional[int], Optional[int], Optional[int]]],
    starters: Set[int],
    team_id: int,
) -> Set[int]:
    """Return the set of player_ids on court for ``team_id`` at the given moment.

    Walks substitutions for that team in chronological order up to and
    including the moment of interest. Clocks count down within a period, so a
    sub at clock=350 (5:50 left) precedes clock=200 (3:20 left) within the
    same period.
    """

    on_court = set(starters)
    for sub_period, sub_clock, player_in, player_out, sub_team in substitutions:
        if sub_team != team_id:
            continue
        if sub_period < period:
            applied = True
        elif sub_period > period:
            applied = False
        else:
            # Same period: apply if sub happened earlier (higher clock_seconds)
            if clock_seconds is None or sub_clock is None:
                applied = True
            else:
                applied = sub_clock >= clock_seconds
        if not applied:
            continue
        if player_in:
            on_court.add(player_in)
        if player_out:
            on_court.discard(player_out)
    return on_court


# ---------------------------------------------------------------------------
# Possession diary
# ---------------------------------------------------------------------------


def _action_label(action_type: str, sub_type: str, points: int, was_and_one: bool) -> str:
    if action_type == "3pt" and sub_type == "made":
        return "Made 3PT"
    if action_type == "2pt" and sub_type == "made":
        return "And-1 2PT" if was_and_one else "Made 2PT"
    if action_type == "freethrow" and sub_type == "made":
        return "Made FT"
    if action_type == "turnover":
        return "Turnover"
    if action_type == "rebound" and sub_type == "defensive":
        return "Defensive Rebound"
    if action_type == "rebound" and sub_type == "offensive":
        return "Offensive Rebound"
    if action_type == "block":
        return "Block"
    if action_type == "steal":
        return "Steal"
    if action_type:
        label = action_type.upper() if action_type in ("2pt", "3pt") else action_type.title()
        return label if not sub_type else "{} {}".format(label, sub_type.title())
    return "Possession"


def _classify_impact(
    action_type: str,
    sub_type: str,
    period: Optional[int],
    seconds_remaining: Optional[float],
    home_score: int,
    away_score: int,
    seconds_since_prev_close: Optional[float],
) -> str:
    is_clutch = (
        period is not None
        and period >= 4
        and seconds_remaining is not None
        and seconds_remaining <= 300
        and abs(home_score - away_score) <= 5
    )
    if is_clutch:
        return "clutch"
    if (
        seconds_since_prev_close is not None
        and 0.0 <= seconds_since_prev_close <= 8.0
        and action_type in ("2pt", "3pt")
        and sub_type == "made"
    ):
        return "transition"
    if action_type in ("2pt", "3pt") and sub_type == "made":
        return "shot"
    if action_type == "turnover":
        return "turnover"
    if action_type == "rebound" and sub_type == "defensive":
        return "defense"
    if action_type == "block":
        return "defense"
    return "shot"


def compute_possession_diary(db: Session, game_id: str) -> List[PossessionEntry]:
    """Group PBP rows into possessions, return top 24 by absolute lead swing.

    Possessions terminate on:
      * made FG (with and-1 rolled into the shot when applicable)
      * turnover
      * last FT in sequence (excluding technicals and and-ones)
      * defensive rebound after a missed shot
      * end of period
    """

    events = _iter_events(db, game_id)
    if not events:
        return []

    game = db.query(GameLog).filter_by(game_id=game_id).first()
    home_team_id = game.home_team_id if game else None
    away_team_id = game.away_team_id if game else None

    teams: Dict[int, Team] = {}
    if home_team_id or away_team_id:
        team_ids = [tid for tid in (home_team_id, away_team_id) if tid is not None]
        if team_ids:
            teams = {
                team.id: team
                for team in db.query(Team).filter(Team.id.in_(team_ids)).all()
            }

    player_ids = sorted({event.player_id for event in events if event.player_id})
    players: Dict[int, Player] = {}
    if player_ids:
        players = {
            player.id: player
            for player in db.query(Player).filter(Player.id.in_(player_ids)).all()
        }

    diary: List[PossessionEntry] = []

    poss_start_score_home = 0
    poss_start_score_away = 0
    poss_start_clock: Optional[float] = None
    poss_start_period: Optional[int] = None
    poss_offense_team_id: Optional[int] = None
    poss_had_fga = False

    last_terminator: Dict[str, object] = {}
    prev_poss_close_clock: Optional[float] = None
    prev_poss_close_period: Optional[int] = None

    # Index set of events that have been folded into an and-1 possession and
    # should be skipped on the main loop (otherwise the made-FT-of-1 would
    # also flush as a standalone shooting-foul possession).
    consumed_and_one_indices: set = set()

    score_home = 0
    score_away = 0

    def _flush_possession(
        terminator: Dict[str, object],
        score_home_now: int,
        score_away_now: int,
        prev_close_clock: Optional[float],
        prev_close_period: Optional[int],
    ) -> None:
        if not terminator:
            return
        action_type = terminator.get("action_type", "")
        sub_type = terminator.get("sub_type", "")
        was_and_one = bool(terminator.get("and_one"))
        period = terminator.get("period") or poss_start_period or 1
        offense_team_id = terminator.get("team_id") or poss_offense_team_id
        primary_player_id = terminator.get("player_id")
        clock_seconds = terminator.get("clock_seconds")

        offense_team = teams.get(offense_team_id) if offense_team_id else None
        offense_abbr = offense_team.abbreviation if offense_team else "—"

        primary_player = players.get(primary_player_id) if primary_player_id else None
        primary_name = primary_player.full_name if primary_player else "—"

        points_scored = int(terminator.get("points_scored") or 0)

        if offense_team_id == home_team_id:
            lead_swing = (score_home_now - poss_start_score_home) - (score_away_now - poss_start_score_away)
        elif offense_team_id == away_team_id:
            lead_swing = (score_away_now - poss_start_score_away) - (score_home_now - poss_start_score_home)
        else:
            lead_swing = 0

        seconds_since_prev_close: Optional[float] = None
        if (
            prev_close_clock is not None
            and prev_close_period is not None
            and poss_start_clock is not None
            and prev_close_period == poss_start_period
        ):
            seconds_since_prev_close = max(0.0, prev_close_clock - poss_start_clock)

        impact_tag = _classify_impact(
            action_type=action_type,
            sub_type=sub_type,
            period=period,
            seconds_remaining=clock_seconds,
            home_score=score_home_now,
            away_score=score_away_now,
            seconds_since_prev_close=seconds_since_prev_close,
        )

        diary.append(
            PossessionEntry(
                quarter=int(period),
                time_remaining=_format_mmss(poss_start_clock),
                offense_team_abbr=offense_abbr,
                primary_action_type=_action_label(action_type, sub_type, points_scored, was_and_one),
                primary_player_name=primary_name,
                points_scored=points_scored,
                impact_tag=impact_tag,
                lead_swing=int(lead_swing),
            )
        )

    for index, event in enumerate(events):
        if index in consumed_and_one_indices:
            # Update running score and continue — this event was already
            # rolled up into a prior and-1 possession.
            if event.score_home is not None:
                try:
                    score_home = int(event.score_home)
                except (TypeError, ValueError):
                    pass
            if event.score_away is not None:
                try:
                    score_away = int(event.score_away)
                except (TypeError, ValueError):
                    pass
            continue

        action_type, sub_type = _normalize_action(event.action_type, event.sub_type)
        team_id = event.team_id
        clock_seconds = _parse_clock_seconds(event.clock)

        # Possession start: take first non-substitution / non-foul event so
        # mid-possession fouls don't reset the offense team.
        if (
            poss_start_period is None
            and action_type not in ("substitution", "period", "foul")
        ):
            poss_start_period = event.period
            poss_start_clock = clock_seconds
            poss_start_score_home = score_home
            poss_start_score_away = score_away
            poss_offense_team_id = team_id

        # Update running scores when this event reports them
        if event.score_home is not None:
            try:
                score_home = int(event.score_home)
            except (TypeError, ValueError):
                pass
        if event.score_away is not None:
            try:
                score_away = int(event.score_away)
            except (TypeError, ValueError):
                pass

        # Track shot attempts on the possession (for FT possession-counting)
        if action_type in ("2pt", "3pt"):
            poss_had_fga = True

        terminator = last_terminator
        flushed = False

        if action_type in ("2pt", "3pt") and sub_type == "made":
            points = 3 if action_type == "3pt" else 2
            terminator = {
                "action_type": action_type,
                "sub_type": sub_type,
                "team_id": team_id,
                "player_id": event.player_id,
                "period": event.period,
                "clock_seconds": clock_seconds,
                "points_scored": points,
                "and_one": False,
            }
            # Look ahead for and-1: same team scoring player + foul + made FT (1 of 1).
            # When we detect one, mark the foul + FT indices as consumed so the
            # main loop skips them rather than emitting a separate FT possession.
            j = index + 1
            saw_foul_index: Optional[int] = None
            and_one_ft_index: Optional[int] = None
            while j < len(events):
                next_event = events[j]
                next_a, next_s = _normalize_action(next_event.action_type, next_event.sub_type)
                if next_a == "foul":
                    saw_foul_index = j
                    j += 1
                    continue
                if next_a == "freethrow" and saw_foul_index is not None:
                    desc = next_event.description or ""
                    if "1 of 1" in desc and "technical" not in desc.lower():
                        if next_s == "made":
                            terminator["points_scored"] = points + 1
                            terminator["and_one"] = True
                            and_one_ft_index = j
                    break
                if next_a in ("2pt", "3pt", "turnover", "rebound", "period", "substitution", "freethrow"):
                    break
                j += 1
            if terminator["and_one"]:
                if saw_foul_index is not None:
                    consumed_and_one_indices.add(saw_foul_index)
                if and_one_ft_index is not None:
                    consumed_and_one_indices.add(and_one_ft_index)
            last_terminator = terminator
            _flush_possession(
                terminator,
                score_home if not terminator["and_one"] else score_home + (1 if team_id == home_team_id else 0),
                score_away if not terminator["and_one"] else score_away + (1 if team_id == away_team_id else 0),
                prev_poss_close_clock,
                prev_poss_close_period,
            )
            flushed = True

        elif action_type == "turnover":
            terminator = {
                "action_type": action_type,
                "sub_type": sub_type,
                "team_id": team_id,
                "player_id": event.player_id,
                "period": event.period,
                "clock_seconds": clock_seconds,
                "points_scored": 0,
                "and_one": False,
            }
            last_terminator = terminator
            _flush_possession(
                terminator,
                score_home,
                score_away,
                prev_poss_close_clock,
                prev_poss_close_period,
            )
            flushed = True

        elif action_type == "rebound" and sub_type == "defensive":
            # Defensive rebound after a missed shot closes the prior possession.
            # The offense_team_id of the closed possession was the missed-shot team
            # (i.e. NOT the rebounding team). Emit only if we have a prior offense.
            if poss_offense_team_id is not None and poss_offense_team_id != team_id:
                terminator = {
                    "action_type": "rebound",
                    "sub_type": "defensive",
                    "team_id": poss_offense_team_id,
                    "player_id": event.player_id,
                    "period": event.period,
                    "clock_seconds": clock_seconds,
                    "points_scored": 0,
                    "and_one": False,
                }
                last_terminator = terminator
                _flush_possession(
                    terminator,
                    score_home,
                    score_away,
                    prev_poss_close_clock,
                    prev_poss_close_period,
                )
                flushed = True

        elif action_type == "freethrow":
            desc = event.description or ""
            is_last_ft = bool(_LAST_FT_RE.search(desc))
            is_technical = "technical" in desc.lower()
            if is_last_ft and not is_technical and not poss_had_fga:
                # Shooting-foul possession with no FGA — close on last FT.
                points = 0
                # Sum FT points in this sequence
                total = re.search(r"\b(\d) of (\d)\b", desc)
                if total:
                    pass
                if sub_type == "made":
                    points = 1
                terminator = {
                    "action_type": action_type,
                    "sub_type": sub_type,
                    "team_id": team_id,
                    "player_id": event.player_id,
                    "period": event.period,
                    "clock_seconds": clock_seconds,
                    "points_scored": points,
                    "and_one": False,
                }
                last_terminator = terminator
                _flush_possession(
                    terminator,
                    score_home,
                    score_away,
                    prev_poss_close_clock,
                    prev_poss_close_period,
                )
                flushed = True

        elif action_type == "period":
            # End of period closes whatever is open.
            if poss_start_period is not None and last_terminator:
                terminator_period = {
                    **last_terminator,
                    "period": event.period or last_terminator.get("period"),
                    "clock_seconds": clock_seconds,
                }
                _flush_possession(
                    terminator_period,
                    score_home,
                    score_away,
                    prev_poss_close_clock,
                    prev_poss_close_period,
                )
                flushed = True

        if flushed:
            prev_poss_close_clock = clock_seconds
            prev_poss_close_period = event.period
            poss_start_period = None
            poss_start_clock = None
            poss_offense_team_id = None
            poss_had_fga = False
            poss_start_score_home = score_home
            poss_start_score_away = score_away
            last_terminator = {}

    diary.sort(key=lambda entry: abs(entry.lead_swing), reverse=True)
    return diary[:24]


# ---------------------------------------------------------------------------
# Per-quarter +/-
# ---------------------------------------------------------------------------


def compute_player_quarter_plus_minus(
    db: Session, game_id: str
) -> List[PlayerQuarterImpact]:
    """Per-player per-quarter +/- and minutes for one game.

    Walks PBP events in order, tracks on-court 5-man lineups per team via
    substitutions, and applies (home_score - away_score) deltas to every
    player on the floor based on which team they're on.
    """

    events = _iter_events(db, game_id)
    if not events:
        return []

    game = db.query(GameLog).filter_by(game_id=game_id).first()
    if not game or game.home_team_id is None or game.away_team_id is None:
        return []
    home_team_id = game.home_team_id
    away_team_id = game.away_team_id

    home_starters, away_starters = _resolve_starters(
        db, game_id, home_team_id, away_team_id, events
    )
    if len(home_starters) < 5 or len(away_starters) < 5:
        return []

    player_ids = sorted(
        {event.player_id for event in events if event.player_id}
        | home_starters
        | away_starters
    )
    teams = {
        team.id: team
        for team in db.query(Team).filter(Team.id.in_([home_team_id, away_team_id])).all()
    }
    players = {
        player.id: player
        for player in db.query(Player).filter(Player.id.in_(player_ids)).all()
    }

    home_on_court: Set[int] = set(home_starters)
    away_on_court: Set[int] = set(away_starters)

    # Aggregators keyed by (player_id, quarter)
    plus_minus_acc: Dict[Tuple[int, int], int] = defaultdict(int)
    seconds_acc: Dict[Tuple[int, int], float] = defaultdict(float)
    player_team: Dict[int, int] = {}
    for pid in home_starters:
        player_team[pid] = home_team_id
    for pid in away_starters:
        player_team[pid] = away_team_id

    score_home = 0
    score_away = 0
    last_diff = 0
    cur_period: Optional[int] = None
    last_clock_in_period: Optional[float] = None

    def _accumulate_minutes(period: int, end_clock: Optional[float]) -> None:
        nonlocal last_clock_in_period
        if last_clock_in_period is None or end_clock is None:
            last_clock_in_period = end_clock
            return
        elapsed = max(0.0, last_clock_in_period - end_clock)
        if elapsed > 0:
            for pid in home_on_court | away_on_court:
                seconds_acc[(pid, period)] += elapsed
        last_clock_in_period = end_clock

    for event in events:
        action_type, sub_type = _normalize_action(event.action_type, event.sub_type)
        period = event.period or 1
        clock_seconds = _parse_clock_seconds(event.clock)

        if cur_period is None:
            cur_period = period
            last_clock_in_period = clock_seconds
        elif period != cur_period:
            cur_period = period
            last_clock_in_period = clock_seconds
        else:
            _accumulate_minutes(period, clock_seconds)

        # Update running scores when this event reports them.
        if event.score_home is not None:
            try:
                score_home = int(event.score_home)
            except (TypeError, ValueError):
                pass
        if event.score_away is not None:
            try:
                score_away = int(event.score_away)
            except (TypeError, ValueError):
                pass

        cur_diff = score_home - score_away
        delta = cur_diff - last_diff
        if delta != 0:
            for pid in home_on_court:
                plus_minus_acc[(pid, period)] += delta
            for pid in away_on_court:
                plus_minus_acc[(pid, period)] -= delta
            last_diff = cur_diff

        if action_type == "substitution":
            pid = event.player_id
            if pid:
                if event.team_id == home_team_id:
                    if sub_type == "in":
                        home_on_court.add(pid)
                    elif sub_type == "out":
                        home_on_court.discard(pid)
                    player_team[pid] = home_team_id
                elif event.team_id == away_team_id:
                    if sub_type == "in":
                        away_on_court.add(pid)
                    elif sub_type == "out":
                        away_on_court.discard(pid)
                    player_team[pid] = away_team_id

    impacts: List[PlayerQuarterImpact] = []
    keys = sorted(set(plus_minus_acc.keys()) | set(seconds_acc.keys()), key=lambda k: (k[1], k[0]))
    for player_id, quarter in keys:
        seconds = seconds_acc.get((player_id, quarter), 0.0)
        plus_minus = plus_minus_acc.get((player_id, quarter), 0)
        if seconds <= 0.0 and plus_minus == 0:
            # No on-court time and no impact: drop.
            continue
        team_id = player_team.get(player_id)
        team = teams.get(team_id) if team_id else None
        team_abbr = team.abbreviation if team else ""
        player = players.get(player_id)
        player_name = player.full_name if player else ""
        impacts.append(
            PlayerQuarterImpact(
                player_id=int(player_id),
                player_name=player_name,
                team_abbreviation=team_abbr,
                quarter=int(quarter),
                plus_minus=int(plus_minus),
                minutes=round(seconds / 60.0, 2),
            )
        )
    return impacts
