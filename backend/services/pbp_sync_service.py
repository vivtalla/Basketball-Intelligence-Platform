"""Reusable play-by-play sync routines for player and season level imports."""

from __future__ import annotations

import time
from collections import defaultdict

from sqlalchemy.orm import Session

from data.nba_client import (
    get_game_box_score,
    get_play_by_play,
    get_player_game_ids,
    get_season_game_ids,
)
from db.database import SessionLocal
from db.models import GameLog, LineupStats, PlayByPlay, Player, PlayerOnOff, SeasonStat, Team
from services.pbp_service import (
    build_stints,
    compute_clutch_stats,
    compute_lineup_stats,
    compute_on_off,
    compute_second_chance_and_fast_break,
)

PBP_REQUEST_DELAY = 1.0
PBP_TIMEOUT = 60
MAX_RETRIES = 3

PBP_SEASON_FIELDS = [
    "clutch_pts",
    "clutch_fga",
    "clutch_fg_pct",
    "clutch_plus_minus",
    "second_chance_pts",
    "fast_break_pts",
]


def _fetch_with_retry(fn, *args, **kwargs):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except Exception:
            if attempt == MAX_RETRIES:
                raise
            time.sleep(attempt * 3)
    return None


def _get_or_create_game_log(db: Session, game_id: str, season: str, box_score: dict) -> GameLog:
    row = db.query(GameLog).filter_by(game_id=game_id).first()
    if not row:
        row = GameLog(
            game_id=game_id,
            season=season,
            home_team_id=box_score.get("home_team_id"),
            away_team_id=box_score.get("away_team_id"),
            home_score=box_score.get("home_score"),
            away_score=box_score.get("away_score"),
        )
        db.add(row)
    else:
        row.season = season
        row.home_team_id = box_score.get("home_team_id")
        row.away_team_id = box_score.get("away_team_id")
        row.home_score = box_score.get("home_score")
        row.away_score = box_score.get("away_score")
    return row


def _ensure_box_score_entities(db: Session, box_score: dict) -> None:
    team_specs = [
        (
            box_score.get("home_team_id"),
            box_score.get("home_team_abbreviation"),
            box_score.get("home_team_name"),
        ),
        (
            box_score.get("away_team_id"),
            box_score.get("away_team_abbreviation"),
            box_score.get("away_team_name"),
        ),
    ]

    for team_id, abbreviation, name in team_specs:
        if not team_id:
            continue
        team = db.query(Team).filter_by(id=team_id).first()
        if not team:
            team = Team(
                id=team_id,
                abbreviation=abbreviation or f"T{team_id}",
                name=name or abbreviation or f"Team {team_id}",
            )
            db.add(team)
        else:
            if abbreviation:
                team.abbreviation = abbreviation
            if name:
                team.name = name

    player_ids = [player.get("player_id") for player in box_score.get("players", []) if player.get("player_id")]
    if not player_ids:
        return

    existing_players = {
        row.id: row
        for row in db.query(Player).filter(Player.id.in_(player_ids)).all()
    }
    for player in box_score.get("players", []):
        player_id = player.get("player_id")
        if not player_id:
            continue
        existing = existing_players.get(player_id)
        if not existing:
            db.add(
                Player(
                    id=player_id,
                    full_name=player.get("player_name") or f"Player {player_id}",
                    team_id=player.get("team_id"),
                    is_active=True,
                )
            )
        else:
            if player.get("player_name") and not existing.full_name:
                existing.full_name = player.get("player_name")
            if player.get("team_id"):
                existing.team_id = player.get("team_id")

    db.flush()


def _store_pbp_events(
    db: Session,
    game_id: str,
    events: list[dict],
    valid_player_ids: set[int] | None = None,
) -> None:
    existing = {
        row.action_number
        for row in db.query(PlayByPlay.action_number).filter_by(game_id=game_id)
    }

    for event in events:
        action_num = event.get("actionId") or event.get("actionNumber")
        if action_num in existing:
            continue

        try:
            score_home = int(event["scoreHome"]) if event.get("scoreHome") is not None else None
            score_away = int(event["scoreAway"]) if event.get("scoreAway") is not None else None
        except (TypeError, ValueError):
            score_home, score_away = None, None

        raw_player_id = event.get("personId") or None
        player_id = raw_player_id if valid_player_ids is None or raw_player_id in valid_player_ids else None

        db.add(
            PlayByPlay(
                game_id=game_id,
                action_number=action_num,
                period=event.get("period"),
                clock=event.get("clock", ""),
                team_id=event.get("teamId") or None,
                player_id=player_id,
                action_type=(event.get("actionType") or "")[:50],
                sub_type=(event.get("subType") or "")[:50],
                description=(event.get("description") or "")[:500],
                score_home=score_home,
                score_away=score_away,
            )
        )


def _replace_pbp_events(
    db: Session,
    game_id: str,
    events: list[dict],
    valid_player_ids: set[int] | None = None,
) -> None:
    db.query(PlayByPlay).filter_by(game_id=game_id).delete(synchronize_session=False)
    _store_pbp_events(db, game_id, events, valid_player_ids=valid_player_ids)


def _load_stored_pbp_events(db: Session, game_id: str) -> list[dict]:
    rows = (
        db.query(PlayByPlay)
        .filter_by(game_id=game_id)
        .order_by(PlayByPlay.action_number.asc())
        .all()
    )
    return [
        {
            "actionNumber": row.action_number,
            "period": row.period,
            "clock": row.clock,
            "teamId": row.team_id,
            "personId": row.player_id,
            "actionType": row.action_type,
            "subType": row.sub_type,
            "description": row.description,
            "scoreHome": row.score_home,
            "scoreAway": row.score_away,
        }
        for row in rows
    ]


def _accumulate_clutch(all_clutch: dict[int, dict], game_clutch: dict[int, dict], allowed: set[int] | None) -> None:
    for player_id, stats in game_clutch.items():
        if allowed is not None and player_id not in allowed:
            continue
        acc = all_clutch[player_id]
        acc["clutch_pts"] = acc.get("clutch_pts", 0) + stats.get("clutch_pts", 0)
        acc["clutch_fga"] = acc.get("clutch_fga", 0) + stats.get("clutch_fga", 0)
        acc["clutch_fgm"] = acc.get("clutch_fgm", 0) + stats.get("clutch_fgm", 0)


def _accumulate_pbp_stats(all_pbp: dict[int, dict], game_pbp: dict[int, dict], allowed: set[int] | None) -> None:
    for player_id, stats in game_pbp.items():
        if allowed is not None and player_id not in allowed:
            continue
        acc = all_pbp[player_id]
        acc["second_chance_pts"] = acc.get("second_chance_pts", 0) + stats.get("second_chance_pts", 0)
        acc["fast_break_pts"] = acc.get("fast_break_pts", 0) + stats.get("fast_break_pts", 0)


def _clear_player_outputs(db: Session, player_ids: set[int], season: str) -> None:
    db.query(PlayerOnOff).filter(
        PlayerOnOff.player_id.in_(player_ids),
        PlayerOnOff.season == season,
        PlayerOnOff.is_playoff == False,
    ).delete(synchronize_session=False)

    rows = db.query(SeasonStat).filter(
        SeasonStat.player_id.in_(player_ids),
        SeasonStat.season == season,
        SeasonStat.is_playoff == False,
    ).all()
    for row in rows:
        for field in PBP_SEASON_FIELDS:
            setattr(row, field, None)


def _clear_season_outputs(db: Session, season: str) -> None:
    db.query(PlayerOnOff).filter(
        PlayerOnOff.season == season,
        PlayerOnOff.is_playoff == False,
    ).delete(synchronize_session=False)
    db.query(LineupStats).filter(LineupStats.season == season).delete(synchronize_session=False)

    rows = db.query(SeasonStat).filter(
        SeasonStat.season == season,
        SeasonStat.is_playoff == False,
    ).all()
    for row in rows:
        for field in PBP_SEASON_FIELDS:
            setattr(row, field, None)


def _update_season_stats(db: Session, season: str, player_id: int, stats: dict) -> bool:
    rows = db.query(SeasonStat).filter_by(
        player_id=player_id,
        season=season,
        is_playoff=False,
    ).all()
    for row in rows:
        for column, value in stats.items():
            if hasattr(row, column):
                setattr(row, column, value)
    return bool(rows)


def _upsert_on_off(db: Session, player_id: int, season: str, data: dict) -> None:
    row = db.query(PlayerOnOff).filter_by(
        player_id=player_id,
        season=season,
        is_playoff=False,
    ).first()
    if not row:
        row = PlayerOnOff(player_id=player_id, season=season, is_playoff=False)
        db.add(row)

    row.on_minutes = data.get("on_minutes")
    row.off_minutes = data.get("off_minutes")
    row.on_net_rating = data.get("on_net_rating")
    row.off_net_rating = data.get("off_net_rating")
    row.on_off_net = data.get("on_off_net")
    row.on_ortg = data.get("on_ortg")
    row.on_drtg = data.get("on_drtg")
    row.off_ortg = data.get("off_ortg")
    row.off_drtg = data.get("off_drtg")


def _upsert_lineup(db: Session, lineup_key: str, season: str, team_id: int | None, acc) -> None:
    row = db.query(LineupStats).filter_by(lineup_key=lineup_key, season=season).first()
    if not row:
        row = LineupStats(lineup_key=lineup_key, season=season, team_id=team_id)
        db.add(row)

    possessions = acc.possessions
    ortg = round(acc.team_pts / possessions * 100, 1) if possessions else None
    drtg = round(acc.opp_pts / possessions * 100, 1) if possessions else None

    row.team_id = team_id
    row.possessions = possessions
    row.plus_minus = acc.plus_minus
    row.ortg = ortg
    row.drtg = drtg
    row.net_rating = round(ortg - drtg, 1) if ortg is not None and drtg is not None else None
    row.minutes = round(possessions / 2.0, 1) if possessions else None


def _team_player_map(box_score: dict) -> dict[int, set[int]]:
    team_players: dict[int, set[int]] = defaultdict(set)
    for player in box_score.get("players", []):
        player_id = player.get("player_id")
        team_id = player.get("team_id")
        if player_id and team_id:
            team_players[team_id].add(player_id)
    return team_players


def _sync_games(
    season: str,
    game_ids: list[str],
    *,
    target_player_ids: set[int] | None = None,
    force_refresh: bool = False,
    include_lineups: bool = False,
) -> dict:
    db = SessionLocal()

    clutch_season: dict[int, dict] = defaultdict(dict)
    pbp_season: dict[int, dict] = defaultdict(dict)
    on_off_accum: dict[int, dict] = {}
    lineup_accum = {}
    season_team_players: dict[int, set[int]] = defaultdict(set)
    players_updated: set[int] = set()

    games_processed = 0
    games_fetched = 0
    games_reused = 0
    games_failed = 0

    try:
        for game_id in game_ids:
            try:
                time.sleep(PBP_REQUEST_DELAY)
                box_score = _fetch_with_retry(get_game_box_score, game_id, timeout=PBP_TIMEOUT)
                _ensure_box_score_entities(db, box_score)
                team_players = _team_player_map(box_score)
                for team_id, roster in team_players.items():
                    season_team_players[team_id].update(roster)

                if target_player_ids is not None:
                    players_in_game = {
                        player.get("player_id")
                        for player in box_score.get("players", [])
                        if player.get("player_id") in target_player_ids
                    }
                    if not players_in_game:
                        continue

                existing_raw = db.query(PlayByPlay.id).filter_by(game_id=game_id).first()
                if existing_raw and not force_refresh:
                    pbp_events = _load_stored_pbp_events(db, game_id)
                    games_reused += 1
                else:
                    time.sleep(PBP_REQUEST_DELAY)
                    pbp_events = _fetch_with_retry(get_play_by_play, game_id, timeout=PBP_TIMEOUT)
                    valid_player_ids = {
                        player_id
                        for roster in team_players.values()
                        for player_id in roster
                    }
                    _get_or_create_game_log(db, game_id, season, box_score)
                    if force_refresh and existing_raw:
                        _replace_pbp_events(
                            db,
                            game_id,
                            pbp_events,
                            valid_player_ids=valid_player_ids,
                        )
                    else:
                        _store_pbp_events(
                            db,
                            game_id,
                            pbp_events,
                            valid_player_ids=valid_player_ids,
                        )
                    db.commit()
                    games_fetched += 1

                _get_or_create_game_log(db, game_id, season, box_score)
                db.commit()

                home_team_id = box_score.get("home_team_id")
                away_team_id = box_score.get("away_team_id")
                stints = build_stints(pbp_events, box_score)

                for team_id in [home_team_id, away_team_id]:
                    if not team_id:
                        continue
                    _accumulate_clutch(
                        clutch_season,
                        compute_clutch_stats(pbp_events, team_id),
                        target_player_ids,
                    )
                    _accumulate_pbp_stats(
                        pbp_season,
                        compute_second_chance_and_fast_break(pbp_events, team_id),
                        target_player_ids,
                    )

                if include_lineups and stints:
                    for lineup_key, acc in compute_lineup_stats(stints, home_team_id).items():
                        existing = lineup_accum.get(lineup_key)
                        if not existing:
                            lineup_accum[lineup_key] = acc
                        else:
                            existing.plus_minus += acc.plus_minus
                            existing.possessions += acc.possessions
                            existing.team_pts += acc.team_pts
                            existing.opp_pts += acc.opp_pts

                if stints:
                    for team_id in [home_team_id, away_team_id]:
                        if not team_id:
                            continue
                        full_roster = team_players.get(team_id, set())
                        if not full_roster:
                            continue
                        game_on_off = compute_on_off(stints, full_roster)
                        for player_id, acc in game_on_off.items():
                            if target_player_ids is not None and player_id not in target_player_ids:
                                continue
                            existing = on_off_accum.get(player_id)
                            if not existing:
                                on_off_accum[player_id] = {
                                    "on_possessions": acc.on_possessions,
                                    "off_possessions": acc.off_possessions,
                                    "on_team_pts": acc.on_team_pts,
                                    "on_opp_pts": acc.on_opp_pts,
                                    "off_team_pts": acc.off_team_pts,
                                    "off_opp_pts": acc.off_opp_pts,
                                }
                            else:
                                existing["on_possessions"] += acc.on_possessions
                                existing["off_possessions"] += acc.off_possessions
                                existing["on_team_pts"] += acc.on_team_pts
                                existing["on_opp_pts"] += acc.on_opp_pts
                                existing["off_team_pts"] += acc.off_team_pts
                                existing["off_opp_pts"] += acc.off_opp_pts

                games_processed += 1
            except Exception:
                db.rollback()
                games_failed += 1
                continue

        if target_player_ids is None:
            _clear_season_outputs(db, season)
        else:
            _clear_player_outputs(db, target_player_ids, season)

        for player_id, stats in clutch_season.items():
            fga = stats.get("clutch_fga", 0)
            fgm = stats.get("clutch_fgm", 0)
            updated = _update_season_stats(
                db,
                season,
                player_id,
                {
                    "clutch_pts": stats.get("clutch_pts"),
                    "clutch_fga": fga if fga > 0 else None,
                    "clutch_fg_pct": round(fgm / fga, 3) if fga > 0 else None,
                },
            )
            if updated:
                players_updated.add(player_id)

        for player_id, stats in pbp_season.items():
            updated = _update_season_stats(db, season, player_id, stats)
            if updated:
                players_updated.add(player_id)

        for player_id, acc in on_off_accum.items():
            on_poss = acc["on_possessions"]
            off_poss = acc["off_possessions"]

            def _net(team_pts, opp_pts, possessions):
                return round((team_pts - opp_pts) / possessions * 100, 1) if possessions else None

            def _ortg(team_pts, possessions):
                return round(team_pts / possessions * 100, 1) if possessions else None

            def _drtg(opp_pts, possessions):
                return round(opp_pts / possessions * 100, 1) if possessions else None

            on_net = _net(acc["on_team_pts"], acc["on_opp_pts"], on_poss)
            off_net = _net(acc["off_team_pts"], acc["off_opp_pts"], off_poss)

            _upsert_on_off(
                db,
                player_id,
                season,
                {
                    "on_minutes": round(on_poss / 2.0, 1),
                    "off_minutes": round(off_poss / 2.0, 1),
                    "on_net_rating": on_net,
                    "off_net_rating": off_net,
                    "on_off_net": round(on_net - off_net, 1)
                    if on_net is not None and off_net is not None
                    else None,
                    "on_ortg": _ortg(acc["on_team_pts"], on_poss),
                    "on_drtg": _drtg(acc["on_opp_pts"], on_poss),
                    "off_ortg": _ortg(acc["off_team_pts"], off_poss),
                    "off_drtg": _drtg(acc["off_opp_pts"], off_poss),
                },
            )
            players_updated.add(player_id)

        if include_lineups:
            for lineup_key, acc in lineup_accum.items():
                first_player = int(lineup_key.split("-")[0])
                team_id = next(
                    (team_id for team_id, roster in season_team_players.items() if first_player in roster),
                    None,
                )
                _upsert_lineup(db, lineup_key, season, team_id, acc)

        db.commit()
        return {
            "status": "ok",
            "season": season,
            "games_requested": len(game_ids),
            "games_processed": games_processed,
            "games_fetched": games_fetched,
            "games_reused": games_reused,
            "games_failed": games_failed,
            "players_updated": len(players_updated),
            "lineups_updated": len(lineup_accum) if include_lineups else 0,
        }
    finally:
        db.close()


def sync_pbp_for_player(player_id: int, season: str, force_refresh: bool = False) -> dict:
    game_ids = _fetch_with_retry(get_player_game_ids, player_id, season, timeout=PBP_TIMEOUT)
    return _sync_games(
        season,
        game_ids,
        target_player_ids={player_id},
        force_refresh=force_refresh,
        include_lineups=False,
    )


def sync_pbp_for_season(season: str, force_refresh: bool = False) -> dict:
    game_ids = _fetch_with_retry(get_season_game_ids, season, timeout=PBP_TIMEOUT)
    return _sync_games(
        season,
        game_ids,
        target_player_ids=None,
        force_refresh=force_refresh,
        include_lineups=True,
    )
