from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import math
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from db.models import PlayerShotChart, ShotQualityBaseline
from models.methodology import AnalysisMetadata, DriverBreakdown
from models.shotchart import (
    ShotCreationResponse,
    ShotCreationSplit,
    ShotIdentityCard,
    ShotIdentityResponse,
    ShotIntelligenceCoverage,
    ShotLabFilterEcho,
    ShotMethodologyNote,
    ShotQualityBin,
    ShotQualityResponse,
    ShotQualitySummary,
    ShotQualityZone,
    ShotReplayExample,
)
from services.reliability_service import (
    confidence_from_reliability,
    reliability_score,
    sample_context,
    wilson_interval,
)
from services.shot_lab_service import summarize_shot_completeness

METHODOLOGY_VERSION = "shot_quality_v1"

QUALITY_METHODOLOGY = [
    ShotMethodologyNote(
        title="Expected value",
        body=(
            "Expected shot value is estimated from persisted shot location and available "
            "game/context fields. It is not a tracking-based contest model."
        ),
    ),
    ShotMethodologyNote(
        title="Fallbacks",
        body=(
            "Sparse samples fall back from exact context to zone, shot value, and season-level "
            "baselines so every shot has a transparent expectation."
        ),
    ),
]

CREATION_METHODOLOGY = [
    ShotMethodologyNote(
        title="Creation proxies",
        body=(
            "Creation splits are proxy-labeled from action type, shot type, clock, score, "
            "and linked-event context when available."
        ),
    ),
    ShotMethodologyNote(
        title="Trust labels",
        body=(
            "Linked-subset and inferred labels mean the split is useful for scouting direction, "
            "not an official assisted/self-created classification."
        ),
    ),
]

IDENTITY_METHODOLOGY = [
    ShotMethodologyNote(
        title="Shot identity",
        body=(
            "Identity cards summarize shot diet, quality, making, and creation tendencies. "
            "They are descriptive scouting shortcuts, not replacement metrics."
        ),
    ),
]


@dataclass(frozen=True)
class _Baseline:
    attempts: int
    made: int
    points: int

    @property
    def fg_pct(self) -> float:
        return self.made / self.attempts if self.attempts else 0.45

    @property
    def pps(self) -> float:
        return self.points / self.attempts if self.attempts else 0.95

    @property
    def efg_pct(self) -> float:
        return self.points / (2.0 * self.attempts) if self.attempts else 0.5


class _BaselineStore:
    def __init__(self) -> None:
        self.exact: Dict[Tuple[str, ...], _Baseline] = {}
        self.zone_distance_value: Dict[Tuple[str, ...], _Baseline] = {}
        self.zone_value: Dict[Tuple[str, ...], _Baseline] = {}
        self.value: Dict[Tuple[str, ...], _Baseline] = {}
        self.league = _Baseline(attempts=0, made=0, points=0)


def _safe_float(value: object) -> Optional[float]:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _safe_int(value: object) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _round(value: Optional[float], digits: int = 4) -> Optional[float]:
    if value is None or not math.isfinite(value):
        return None
    return round(value, digits)


def _shot_value(shot: dict) -> int:
    raw_value = _safe_int(shot.get("shot_value"))
    if raw_value in (2, 3):
        return raw_value
    shot_type = str(shot.get("shot_type") or "").upper()
    return 3 if "3PT" in shot_type else 2


def _points(shot: dict) -> int:
    return _shot_value(shot) if bool(shot.get("shot_made")) else 0


def _distance_bucket(shot: dict) -> str:
    distance = _safe_float(shot.get("distance"))
    if distance is None:
        return "unknown"
    if distance <= 4:
        return "0-4"
    if distance <= 8:
        return "5-8"
    if distance <= 14:
        return "9-14"
    if distance <= 19:
        return "15-19"
    if distance <= 23:
        return "20-23"
    if distance <= 27:
        return "24-27"
    return "28+"


def _period_bucket(shot: dict) -> str:
    period = _safe_int(shot.get("period"))
    if period is None:
        return "unknown"
    if period > 4:
        return "ot"
    return f"q{period}"


def _clock_bucket(shot: dict) -> str:
    seconds = _safe_int(shot.get("seconds_remaining"))
    minutes = _safe_int(shot.get("minutes_remaining"))
    if seconds is None and minutes is None:
        clock = str(shot.get("clock") or "")
        parts = clock.split(":")
        if len(parts) == 2:
            minutes = _safe_int(parts[0])
            seconds = _safe_int(parts[1])
    total = ((minutes or 0) * 60) + (seconds or 0) if minutes is not None or seconds is not None else None
    if total is None:
        return "unknown"
    if total <= 7:
        return "late"
    if total <= 120:
        return "closing"
    if total >= 540:
        return "early"
    return "middle"


def _score_margin_bucket(shot: dict) -> str:
    margin = _safe_int(shot.get("score_margin"))
    if margin is None:
        return "unknown"
    if margin <= -10:
        return "trailing_big"
    if margin < -3:
        return "trailing"
    if margin <= 3:
        return "close"
    if margin < 10:
        return "leading"
    return "leading_big"


def _action_family(shot: dict) -> str:
    action = f"{shot.get('action_type') or ''} {shot.get('shot_type') or ''}".lower()
    if any(token in action for token in ("dunk", "layup", "tip")):
        return "rim"
    if "hook" in action or "floating" in action or "floater" in action:
        return "paint_touch"
    if any(token in action for token in ("pullup", "pull-up", "step back", "stepback", "fadeaway", "turnaround")):
        return "self_created_jumper"
    if "catch" in action:
        return "catch_and_shoot"
    if "jump" in action and _shot_value(shot) == 3:
        return "perimeter_jumper"
    if "jump" in action:
        return "jumper"
    return "other"


def _home_road_bucket(shot: dict) -> str:
    # Current enrichment gives team/opponent but not home/road identity on every row.
    return "available" if shot.get("team_id") and shot.get("opponent_team_id") else "unknown"


def _exact_key(shot: dict, season_type: str) -> Tuple[str, ...]:
    return (
        str(shot.get("zone_basic") or "Unknown"),
        str(shot.get("zone_area") or ""),
        _distance_bucket(shot),
        str(_shot_value(shot)),
        _action_family(shot),
        _period_bucket(shot),
        _clock_bucket(shot),
        _score_margin_bucket(shot),
        _home_road_bucket(shot),
        season_type,
    )


def _zone_distance_value_key(shot: dict, season_type: str) -> Tuple[str, ...]:
    return (
        str(shot.get("zone_basic") or "Unknown"),
        _distance_bucket(shot),
        str(_shot_value(shot)),
        season_type,
    )


def _zone_value_key(shot: dict, season_type: str) -> Tuple[str, ...]:
    return (str(shot.get("zone_basic") or "Unknown"), str(_shot_value(shot)), season_type)


def _value_key(shot: dict, season_type: str) -> Tuple[str, ...]:
    return (str(_shot_value(shot)), season_type)


def _accumulate(counter: Dict[Tuple[str, ...], List[int]], key: Tuple[str, ...], shot: dict) -> None:
    row = counter.setdefault(key, [0, 0, 0])
    row[0] += 1
    row[1] += 1 if shot.get("shot_made") else 0
    row[2] += _points(shot)


def _to_baselines(counter: Dict[Tuple[str, ...], List[int]]) -> Dict[Tuple[str, ...], _Baseline]:
    return {
        key: _Baseline(attempts=counts[0], made=counts[1], points=counts[2])
        for key, counts in counter.items()
    }


def _load_baselines(db: Session, season: str, season_type: str) -> _BaselineStore:
    exact: Dict[Tuple[str, ...], List[int]] = {}
    zone_distance_value: Dict[Tuple[str, ...], List[int]] = {}
    zone_value: Dict[Tuple[str, ...], List[int]] = {}
    value: Dict[Tuple[str, ...], List[int]] = {}
    league_counts = [0, 0, 0]

    rows = (
        db.query(PlayerShotChart)
        .filter(
            PlayerShotChart.season == season,
            PlayerShotChart.season_type == season_type,
        )
        .all()
    )
    for row in rows:
        for shot in row.shots or []:
            _accumulate(exact, _exact_key(shot, season_type), shot)
            _accumulate(zone_distance_value, _zone_distance_value_key(shot, season_type), shot)
            _accumulate(zone_value, _zone_value_key(shot, season_type), shot)
            _accumulate(value, _value_key(shot, season_type), shot)
            league_counts[0] += 1
            league_counts[1] += 1 if shot.get("shot_made") else 0
            league_counts[2] += _points(shot)

    store = _BaselineStore()
    store.exact = _to_baselines(exact)
    store.zone_distance_value = _to_baselines(zone_distance_value)
    store.zone_value = _to_baselines(zone_value)
    store.value = _to_baselines(value)
    store.league = _Baseline(attempts=league_counts[0], made=league_counts[1], points=league_counts[2])
    return store


def _serialize_key(key: Tuple[str, ...]) -> str:
    return "||".join(key)


def _deserialize_key(packed: str) -> Tuple[str, ...]:
    return tuple(packed.split("||"))


def _serialize_baselines(store: _BaselineStore) -> dict:
    def _pack(buckets: Dict[Tuple[str, ...], _Baseline]) -> Dict[str, List[int]]:
        return {
            _serialize_key(key): [b.attempts, b.made, b.points]
            for key, b in buckets.items()
        }

    return {
        "exact": _pack(store.exact),
        "zone_distance_value": _pack(store.zone_distance_value),
        "zone_value": _pack(store.zone_value),
        "value": _pack(store.value),
        "league": [store.league.attempts, store.league.made, store.league.points],
    }


def _deserialize_baselines(payload: dict) -> _BaselineStore:
    def _unpack(buckets: dict) -> Dict[Tuple[str, ...], _Baseline]:
        return {
            _deserialize_key(k): _Baseline(attempts=int(v[0]), made=int(v[1]), points=int(v[2]))
            for k, v in (buckets or {}).items()
        }

    store = _BaselineStore()
    store.exact = _unpack(payload.get("exact") or {})
    store.zone_distance_value = _unpack(payload.get("zone_distance_value") or {})
    store.zone_value = _unpack(payload.get("zone_value") or {})
    store.value = _unpack(payload.get("value") or {})
    league = payload.get("league") or [0, 0, 0]
    store.league = _Baseline(attempts=int(league[0]), made=int(league[1]), points=int(league[2]))
    return store


def get_or_build_baseline(
    db: Session,
    season: str,
    season_type: str,
    methodology_version: str = METHODOLOGY_VERSION,
    force_refresh: bool = False,
) -> _BaselineStore:
    """Return the materialized baseline for (season, season_type, methodology_version).

    On cache miss or when force_refresh is True, compute from PlayerShotChart
    and upsert a row in `shot_quality_baselines`.
    """
    row = (
        db.query(ShotQualityBaseline)
        .filter(
            ShotQualityBaseline.season == season,
            ShotQualityBaseline.season_type == season_type,
            ShotQualityBaseline.methodology_version == methodology_version,
        )
        .one_or_none()
    )
    if row is not None and not force_refresh:
        return _deserialize_baselines(row.payload or {})

    store = _load_baselines(db, season, season_type)
    payload = _serialize_baselines(store)
    sample_n = store.league.attempts

    if row is None:
        row = ShotQualityBaseline(
            season=season,
            season_type=season_type,
            methodology_version=methodology_version,
            sample_n=sample_n,
            payload=payload,
        )
        db.add(row)
    else:
        row.payload = payload
        row.sample_n = sample_n
    db.commit()
    return store


def _expected_baseline(shot: dict, season_type: str, store: _BaselineStore) -> Tuple[_Baseline, str]:
    candidates = [
        (store.exact.get(_exact_key(shot, season_type)), "exact_context", 25),
        (store.zone_distance_value.get(_zone_distance_value_key(shot, season_type)), "zone_distance_value", 35),
        (store.zone_value.get(_zone_value_key(shot, season_type)), "zone_value", 50),
        (store.value.get(_value_key(shot, season_type)), "shot_value", 100),
        (store.league, "league", 1),
    ]
    for baseline, label, minimum in candidates:
        if baseline and baseline.attempts >= minimum:
            return baseline, label
    return store.league, "league"


def _coverage(data_status: str, available_shots: Sequence[dict], filtered_shots: Sequence[dict]) -> ShotIntelligenceCoverage:
    summary = summarize_shot_completeness(available_shots)
    if data_status == "missing" or not available_shots:
        state = "missing"
        note = "No persisted shot chart is available for this subject and season."
    elif data_status == "stale":
        state = "stale"
        note = "Persisted shot data exists but is stale; advanced reads remain available."
    elif summary.status == "ready":
        state = "ready"
        note = "Shot location, context, and linked-event coverage are strong."
    elif summary.status == "partial":
        state = "partial"
        note = "Partial coverage means the chart is useful, but some advanced labels use incomplete linkage."
    else:
        state = "legacy"
        note = "Legacy shot payloads support base charting; some context-aware scouting labels are limited."

    return ShotIntelligenceCoverage(
        state=state,
        data_status=data_status,
        total_shots=len(filtered_shots),
        contextual_shots=summary.contextual_shots,
        linked_shots=summary.linked_shots,
        exact_linked_shots=summary.exact_linked_shots,
        derived_linked_shots=summary.derived_linked_shots,
        completeness_pct=summary.completeness_pct,
        linked_pct=summary.linked_pct,
        missing_context_fields=summary.missing_context_fields,
        note=note,
    )


def _filters_echo(
    start_date: Optional[str],
    end_date: Optional[str],
    period_bucket: str,
    result: str,
    shot_value: str,
) -> ShotLabFilterEcho:
    return ShotLabFilterEcho(
        start_date=start_date,
        end_date=end_date,
        period_bucket=period_bucket,
        result=result,
        shot_value=shot_value,
    )


def _quality_summary(attempts: int, made: int, points: int, expected_points: float, expected_makes: float) -> ShotQualitySummary:
    if attempts <= 0:
        return ShotQualitySummary(shots=0, confidence="low", reliability_score=0.0)
    actual_fg = made / attempts
    actual_pps = points / attempts
    actual_efg = points / (2.0 * attempts)
    expected_fg = expected_makes / attempts
    expected_pps = expected_points / attempts
    expected_efg = expected_points / (2.0 * attempts)
    confidence = "high" if attempts >= 300 else "medium" if attempts >= 100 else "low"
    reliability = reliability_score(attempts, 300)
    return ShotQualitySummary(
        shots=attempts,
        actual_fg_pct=_round(actual_fg),
        expected_fg_pct=_round(expected_fg),
        fg_pct_delta=_round(actual_fg - expected_fg),
        actual_efg_pct=_round(actual_efg),
        expected_efg_pct=_round(expected_efg),
        efg_pct_delta=_round(actual_efg - expected_efg),
        actual_pps=_round(actual_pps),
        expected_pps=_round(expected_pps),
        pps_delta=_round(actual_pps - expected_pps),
        confidence=confidence,
        reliability_score=reliability,
        uncertainty_band=wilson_interval(made, attempts),
    )


def _shot_quality_metadata(
    *,
    attempts: int,
    made: int,
    summary: ShotQualitySummary,
    coverage: ShotIntelligenceCoverage,
    available_shots: Sequence[dict],
) -> AnalysisMetadata:
    reliability = reliability_score(attempts, 300)
    notes = [coverage.note]
    if attempts < 100:
        notes.append("Shot-making deltas are sample-sensitive below 100 attempts.")
    return AnalysisMetadata(
        methodology_version=METHODOLOGY_VERSION,
        reliability_score=reliability,
        confidence=confidence_from_reliability(reliability),
        uncertainty_band=wilson_interval(made, attempts),
        sample_context=sample_context(
            sample_size=attempts,
            minimum_recommended=300,
            population_size=len(available_shots),
            notes=notes,
        ),
        driver_breakdown=[
            DriverBreakdown(
                key="coverage",
                label="Context coverage",
                value=coverage.completeness_pct,
                explanation="Higher contextual coverage means expected-shot baselines can use more specific buckets.",
            ),
            DriverBreakdown(
                key="attempts",
                label="Shot sample",
                value=float(attempts),
                explanation="Reliability is scaled toward a 300-shot stabilization target for player/team shot reads.",
            ),
            DriverBreakdown(
                key="pps_delta",
                label="Points over expected",
                value=summary.pps_delta,
                contribution=summary.pps_delta,
                explanation="Actual points per shot minus context-adjusted expected points per shot.",
            ),
        ],
        limitations=[
            "Shot quality is context/location based; it is not a defender-distance or tracking contest model.",
            "Action family and creation context are proxy labels when play-by-play linkage is incomplete.",
            "Small samples can show large make/miss swings, so shot-making reads should use the uncertainty band.",
        ],
        validation_notes=[
            "V1 reliability metadata is descriptive; hierarchical held-out calibration is tracked in specs/methodology-validation.md.",
        ],
    )


def _sample_replay_examples(
    shots: Sequence[dict],
    season_type: str,
    store: "_BaselineStore",
    limit: int = 3,
) -> List[ShotReplayExample]:
    scored: List[Tuple[float, int, str, dict]] = []
    for shot in shots:
        game_id = shot.get("game_id")
        if not game_id:
            continue
        action_number = _safe_int(shot.get("action_number"))
        event_id = shot.get("shot_event_id")
        if action_number is None and not event_id:
            continue
        baseline, _ = _expected_baseline(shot, season_type, store)
        pts_over = float(_points(shot)) - float(baseline.pps)
        linkage_mode = str(shot.get("linkage_mode") or "").lower()
        linkage_rank = 0 if linkage_mode == "exact" else 1 if linkage_mode == "derived" else 2
        scored.append((abs(pts_over), linkage_rank, str(game_id), shot))
        scored[-1] = (abs(pts_over), linkage_rank, str(game_id), shot)

    scored.sort(key=lambda row: (row[1], -row[0], row[2]))
    examples: List[ShotReplayExample] = []
    seen_games: set = set()
    for _, _, game_id, shot in scored:
        if game_id in seen_games:
            continue
        seen_games.add(game_id)
        action_number = _safe_int(shot.get("action_number"))
        event_id = shot.get("shot_event_id")
        linkage_mode = str(shot.get("linkage_mode") or "").lower()
        linkage_quality = linkage_mode if linkage_mode in {"exact", "derived"} else "timeline"
        opponent = shot.get("opponent_team_abbreviation")
        team_abbr = shot.get("team_abbreviation")
        url_parts = [f"/games/{game_id}"]
        query: List[str] = []
        if team_abbr:
            query.append(f"team={team_abbr}")
        if action_number is not None:
            query.append(f"event_num={action_number}")
        elif event_id:
            query.append(f"event_id={event_id}")
        deep_link_url = url_parts[0] + (("?" + "&".join(query)) if query else "")
        baseline, _ = _expected_baseline(shot, season_type, store)
        pts_over = float(_points(shot)) - float(baseline.pps)
        examples.append(
            ShotReplayExample(
                game_id=str(game_id),
                game_date=shot.get("game_date"),
                opponent_abbreviation=str(opponent) if opponent else None,
                shot_distance=_safe_int(shot.get("distance")),
                shot_made=bool(shot.get("shot_made")),
                action_number=action_number,
                shot_event_id=str(event_id) if event_id else None,
                period=_safe_int(shot.get("period")),
                clock=str(shot.get("clock")) if shot.get("clock") else None,
                zone_basic=str(shot.get("zone_basic")) if shot.get("zone_basic") else None,
                points_over_expected=_round(pts_over, 3),
                linkage_quality=linkage_quality,
                deep_link_url=deep_link_url,
            )
        )
        if len(examples) >= limit:
            break
    return examples


def _quality_group(
    *,
    key: str,
    label: str,
    shots: Sequence[dict],
    total_attempts: int,
    season_type: str,
    store: _BaselineStore,
) -> Optional[ShotQualityBin]:
    attempts = len(shots)
    if attempts <= 0:
        return None
    made = sum(1 for shot in shots if shot.get("shot_made"))
    points = sum(_points(shot) for shot in shots)
    expected_points = 0.0
    expected_makes = 0.0
    fallback_labels = []
    loc_x_values = []
    loc_y_values = []
    for shot in shots:
        baseline, fallback = _expected_baseline(shot, season_type, store)
        fallback_labels.append(fallback)
        expected_points += baseline.pps
        expected_makes += baseline.fg_pct
        loc_x = _safe_float(shot.get("loc_x"))
        loc_y = _safe_float(shot.get("loc_y"))
        if loc_x is not None:
            loc_x_values.append(loc_x)
        if loc_y is not None:
            loc_y_values.append(loc_y)
    summary = _quality_summary(attempts, made, points, expected_points, expected_makes)
    confidence = "high" if attempts >= 75 else "medium" if attempts >= 25 else "low"
    dominant_fallback = max(set(fallback_labels), key=fallback_labels.count) if fallback_labels else "league"
    return ShotQualityBin(
        bin_key=key,
        label=label,
        attempts=attempts,
        made=made,
        frequency=_round(attempts / total_attempts if total_attempts else 0.0) or 0.0,
        actual_fg_pct=summary.actual_fg_pct,
        expected_fg_pct=summary.expected_fg_pct,
        fg_pct_delta=summary.fg_pct_delta,
        actual_efg_pct=summary.actual_efg_pct,
        expected_efg_pct=summary.expected_efg_pct,
        efg_pct_delta=summary.efg_pct_delta,
        actual_pps=summary.actual_pps,
        expected_pps=summary.expected_pps,
        pps_delta=summary.pps_delta,
        average_loc_x=_round(sum(loc_x_values) / len(loc_x_values), 2) if loc_x_values else None,
        average_loc_y=_round(sum(loc_y_values) / len(loc_y_values), 2) if loc_y_values else None,
        sample_confidence=confidence,
        coverage_note=f"Expected baseline mostly uses {dominant_fallback.replace('_', ' ')} fallback.",
        replay_examples=_sample_replay_examples(shots, season_type, store),
    )


def _zone_group(
    *,
    zone_basic: str,
    zone_area: str,
    shots: Sequence[dict],
    total_attempts: int,
    season_type: str,
    store: _BaselineStore,
) -> ShotQualityZone:
    attempts = len(shots)
    made = sum(1 for shot in shots if shot.get("shot_made"))
    points = sum(_points(shot) for shot in shots)
    expected_points = 0.0
    expected_makes = 0.0
    for shot in shots:
        baseline, _ = _expected_baseline(shot, season_type, store)
        expected_points += baseline.pps
        expected_makes += baseline.fg_pct
    summary = _quality_summary(attempts, made, points, expected_points, expected_makes)
    confidence = "high" if attempts >= 75 else "medium" if attempts >= 25 else "low"
    return ShotQualityZone(
        zone_basic=zone_basic,
        zone_area=zone_area,
        attempts=attempts,
        made=made,
        frequency=_round(attempts / total_attempts if total_attempts else 0.0) or 0.0,
        actual_fg_pct=summary.actual_fg_pct,
        expected_fg_pct=summary.expected_fg_pct,
        fg_pct_delta=summary.fg_pct_delta,
        actual_pps=summary.actual_pps,
        expected_pps=summary.expected_pps,
        pps_delta=summary.pps_delta,
        sample_confidence=confidence,
    )


def build_shot_quality_response(
    db: Session,
    *,
    subject_type: str,
    subject_id: int,
    season: str,
    season_type: str,
    filtered_shots: Sequence[dict],
    available_shots: Sequence[dict],
    data_status: str,
    start_date: Optional[str],
    end_date: Optional[str],
    period_bucket: str,
    result: str,
    shot_value: str,
) -> ShotQualityResponse:
    store = get_or_build_baseline(db, season, season_type)
    attempts = len(filtered_shots)
    made = sum(1 for shot in filtered_shots if shot.get("shot_made"))
    points = sum(_points(shot) for shot in filtered_shots)
    expected_points = 0.0
    expected_makes = 0.0
    for shot in filtered_shots:
        baseline, _ = _expected_baseline(shot, season_type, store)
        expected_points += baseline.pps
        expected_makes += baseline.fg_pct

    bin_map: Dict[str, List[dict]] = defaultdict(list)
    zone_map: Dict[Tuple[str, str], List[dict]] = defaultdict(list)
    for shot in filtered_shots:
        bin_key = "|".join(
            [
                str(shot.get("zone_basic") or "Unknown"),
                _distance_bucket(shot),
                str(_shot_value(shot)),
                _action_family(shot),
            ]
        )
        bin_map[bin_key].append(shot)
        zone_map[(str(shot.get("zone_basic") or "Unknown"), str(shot.get("zone_area") or ""))].append(shot)

    bins = [
        row
        for key, shots in bin_map.items()
        if (
            row := _quality_group(
                key=key,
                label=key.replace("|", " · "),
                shots=shots,
                total_attempts=attempts,
                season_type=season_type,
                store=store,
            )
        )
    ]
    bins.sort(key=lambda row: (row.attempts, abs(row.pps_delta or 0)), reverse=True)

    zones = [
        _zone_group(
            zone_basic=zone_basic,
            zone_area=zone_area,
            shots=shots,
            total_attempts=attempts,
            season_type=season_type,
            store=store,
        )
        for (zone_basic, zone_area), shots in zone_map.items()
    ]
    zones.sort(key=lambda row: row.frequency, reverse=True)

    coverage = _coverage(data_status, available_shots, filtered_shots)
    summary = _quality_summary(attempts, made, points, expected_points, expected_makes)
    return ShotQualityResponse(
        subject_type=subject_type,
        subject_id=subject_id,
        season=season,
        season_type=season_type,
        filters=_filters_echo(start_date, end_date, period_bucket, result, shot_value),
        methodology_version=METHODOLOGY_VERSION,
        coverage_state=coverage.state,
        coverage=coverage,
        methodology=QUALITY_METHODOLOGY,
        summary=summary,
        bins=bins[:18],
        zones=zones,
        analysis_metadata=_shot_quality_metadata(
            attempts=attempts,
            made=made,
            summary=summary,
            coverage=coverage,
            available_shots=available_shots,
        ),
    )


def _split_stats(
    *,
    split_key: str,
    label: str,
    description: str,
    shots: Sequence[dict],
    total_attempts: int,
    precision: str,
    coverage_note: str,
    season_type: str,
    store: "_BaselineStore",
) -> ShotCreationSplit:
    attempts = len(shots)
    made = sum(1 for shot in shots if shot.get("shot_made"))
    points = sum(_points(shot) for shot in shots)
    return ShotCreationSplit(
        split_key=split_key,
        label=label,
        description=description,
        attempts=attempts,
        made=made,
        frequency=_round(attempts / total_attempts if total_attempts else 0.0) or 0.0,
        fg_pct=_round(made / attempts) if attempts else None,
        efg_pct=_round(points / (2.0 * attempts)) if attempts else None,
        pps=_round(points / attempts) if attempts else None,
        precision=precision,
        coverage_note=coverage_note,
        replay_examples=_sample_replay_examples(shots, season_type, store),
    )


def _is_late_clock(shot: dict) -> bool:
    return _clock_bucket(shot) == "late"


def _is_transition_adjacent(shot: dict) -> bool:
    action = str(shot.get("action_type") or "").lower()
    return any(token in action for token in ("running", "driving", "dunk", "layup")) and _clock_bucket(shot) == "early"


def _is_linked(shot: dict) -> bool:
    return str(shot.get("linkage_mode") or "").lower() in {"exact", "derived"}


def build_shot_creation_response(
    db: Session,
    *,
    subject_type: str,
    subject_id: int,
    season: str,
    season_type: str,
    filtered_shots: Sequence[dict],
    available_shots: Sequence[dict],
    data_status: str,
    start_date: Optional[str],
    end_date: Optional[str],
    period_bucket: str,
    result: str,
    shot_value: str,
) -> ShotCreationResponse:
    store = get_or_build_baseline(db, season, season_type)
    attempts = len(filtered_shots)
    linked = [shot for shot in filtered_shots if _is_linked(shot)]
    catch = [shot for shot in filtered_shots if _action_family(shot) == "catch_and_shoot"]
    pull = [shot for shot in filtered_shots if _action_family(shot) == "self_created_jumper"]
    late = [shot for shot in filtered_shots if _is_late_clock(shot)]
    transition = [shot for shot in filtered_shots if _is_transition_adjacent(shot)]
    rim = [shot for shot in filtered_shots if _action_family(shot) == "rim"]
    paint = [shot for shot in filtered_shots if _action_family(shot) == "paint_touch"]

    linked_share = (len(linked) / attempts) if attempts else 0.0
    precision = "linked_subset" if linked_share >= 0.5 else "partial"
    coverage = _coverage(data_status, available_shots, filtered_shots)
    splits = [
        _split_stats(
            split_key="catch_and_shoot_proxy",
            label="Catch-and-shoot proxy",
            description="Shots with catch-style action labels.",
            shots=catch,
            total_attempts=attempts,
            precision="inferred",
            coverage_note="Proxy label from action_type, not official tracking.",
            season_type=season_type,
            store=store,
        ),
        _split_stats(
            split_key="pull_up_self_created_proxy",
            label="Pull-up / self-created proxy",
            description="Pull-up, step-back, fadeaway, and turnaround jumper actions.",
            shots=pull,
            total_attempts=attempts,
            precision="inferred",
            coverage_note="Proxy label from shot action language.",
            season_type=season_type,
            store=store,
        ),
        _split_stats(
            split_key="late_clock",
            label="Late clock",
            description="Attempts with seven or fewer seconds remaining in the period clock field.",
            shots=late,
            total_attempts=attempts,
            precision="all_shots" if coverage.state in {"ready", "partial"} else "partial",
            coverage_note="Uses persisted clock fields when present.",
            season_type=season_type,
            store=store,
        ),
        _split_stats(
            split_key="transition_adjacent",
            label="Transition-adjacent",
            description="Early-clock running, driving, dunk, or layup actions.",
            shots=transition,
            total_attempts=attempts,
            precision="inferred",
            coverage_note="Directional proxy because possession context is not fully tracking-grade.",
            season_type=season_type,
            store=store,
        ),
        _split_stats(
            split_key="rim_pressure",
            label="Rim pressure",
            description="Layups, dunks, and tip attempts.",
            shots=rim,
            total_attempts=attempts,
            precision="all_shots",
            coverage_note="Uses shot action and zone labels across all visible shots.",
            season_type=season_type,
            store=store,
        ),
        _split_stats(
            split_key="paint_touch",
            label="Paint touch",
            description="Hooks, floaters, and non-rim paint-touch attempts.",
            shots=paint,
            total_attempts=attempts,
            precision="all_shots",
            coverage_note="Uses shot action and zone labels across all visible shots.",
            season_type=season_type,
            store=store,
        ),
    ]
    splits.sort(key=lambda row: row.attempts, reverse=True)
    return ShotCreationResponse(
        subject_type=subject_type,
        subject_id=subject_id,
        season=season,
        season_type=season_type,
        filters=_filters_echo(start_date, end_date, period_bucket, result, shot_value),
        methodology_version=METHODOLOGY_VERSION,
        coverage_state=coverage.state,
        coverage=coverage,
        methodology=CREATION_METHODOLOGY,
        summary={
            "shots": attempts,
            "linked_share": round(linked_share, 4),
            "inferred_share": round(1.0 - linked_share, 4) if attempts else 0.0,
            "primary_precision": precision,
        },
        splits=splits,
    )


def _tier(score: float) -> str:
    if score >= 0.28:
        return "signature"
    if score >= 0.18:
        return "strong"
    if score >= 0.10:
        return "present"
    return "low"


def _identity_card(
    key: str,
    label: str,
    score: float,
    attempts: int,
    evidence: List[str],
    confidence_source: int,
) -> ShotIdentityCard:
    tier = _tier(score)
    confidence = "high" if confidence_source >= 300 else "medium" if confidence_source >= 100 else "low"
    summary = f"{label} tendency is {tier} at {round(score * 100, 1)}% of visible attempts."
    return ShotIdentityCard(
        identity_key=key,
        label=label,
        tier=tier,
        score=round(score, 4),
        summary=summary,
        evidence=evidence,
        confidence=confidence,
    )


def build_shot_identity_response(
    *,
    subject_type: str,
    subject_id: int,
    season: str,
    season_type: str,
    filtered_shots: Sequence[dict],
    available_shots: Sequence[dict],
    data_status: str,
    start_date: Optional[str],
    end_date: Optional[str],
    period_bucket: str,
    result: str,
    shot_value: str,
) -> ShotIdentityResponse:
    attempts = len(filtered_shots)
    if attempts <= 0:
        coverage = _coverage(data_status, available_shots, filtered_shots)
        return ShotIdentityResponse(
            subject_type=subject_type,
            subject_id=subject_id,
            season=season,
            season_type=season_type,
            filters=_filters_echo(start_date, end_date, period_bucket, result, shot_value),
            methodology_version=METHODOLOGY_VERSION,
            coverage_state=coverage.state,
            coverage=coverage,
            methodology=IDENTITY_METHODOLOGY,
            cards=[],
            takeaways=["No shots are available for the selected filters."],
        )

    families: Dict[str, int] = defaultdict(int)
    zones: Dict[str, int] = defaultdict(int)
    for shot in filtered_shots:
        families[_action_family(shot)] += 1
        zones[str(shot.get("zone_basic") or "Unknown")] += 1

    def share(count: int) -> float:
        return count / attempts if attempts else 0.0

    cards = [
        _identity_card(
            "rim_pressure_finisher",
            "Rim pressure finisher",
            share(families["rim"] + zones["Restricted Area"]),
            attempts,
            [f"{families['rim']} rim-action attempts", f"{zones['Restricted Area']} restricted-area attempts"],
            attempts,
        ),
        _identity_card(
            "paint_touch_scorer",
            "Paint touch scorer",
            share(families["paint_touch"] + zones["In The Paint (Non-RA)"]),
            attempts,
            [f"{families['paint_touch']} floater/hook attempts", f"{zones['In The Paint (Non-RA)']} non-RA paint attempts"],
            attempts,
        ),
        _identity_card(
            "midrange_creator",
            "Midrange creator",
            share(zones["Mid-Range"] + families["self_created_jumper"]),
            attempts,
            [f"{zones['Mid-Range']} mid-range attempts", f"{families['self_created_jumper']} self-created jumper proxies"],
            attempts,
        ),
        _identity_card(
            "pull_up_engine",
            "Pull-up engine",
            share(families["self_created_jumper"]),
            attempts,
            [f"{families['self_created_jumper']} pull-up/step-back/fadeaway attempts"],
            attempts,
        ),
        _identity_card(
            "movement_shooter",
            "Movement shooter",
            share(families["catch_and_shoot"] + families["perimeter_jumper"]),
            attempts,
            [f"{families['catch_and_shoot']} catch-style attempts", f"{families['perimeter_jumper']} perimeter jumper attempts"],
            attempts,
        ),
        _identity_card(
            "above_break_volume_spacer",
            "Above-break volume spacer",
            share(zones["Above the Break 3"]),
            attempts,
            [f"{zones['Above the Break 3']} above-break three attempts"],
            attempts,
        ),
        _identity_card(
            "corner_specialist",
            "Corner specialist",
            share(zones["Left Corner 3"] + zones["Right Corner 3"]),
            attempts,
            [f"{zones['Left Corner 3'] + zones['Right Corner 3']} corner three attempts"],
            attempts,
        ),
        _identity_card(
            "balanced_perimeter_scorer",
            "Balanced perimeter scorer",
            min(share(zones["Above the Break 3"] + zones["Mid-Range"]), 0.5),
            attempts,
            [f"{zones['Above the Break 3'] + zones['Mid-Range']} above-break or mid-range attempts"],
            attempts,
        ),
    ]
    cards.sort(key=lambda row: row.score, reverse=True)
    coverage = _coverage(data_status, available_shots, filtered_shots)
    takeaways = [card.summary for card in cards[:3]]
    return ShotIdentityResponse(
        subject_type=subject_type,
        subject_id=subject_id,
        season=season,
        season_type=season_type,
        filters=_filters_echo(start_date, end_date, period_bucket, result, shot_value),
        methodology_version=METHODOLOGY_VERSION,
        coverage_state=coverage.state,
        coverage=coverage,
        methodology=IDENTITY_METHODOLOGY,
        cards=cards,
        takeaways=takeaways,
    )
