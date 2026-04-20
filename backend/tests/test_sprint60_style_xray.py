"""Sprint 60 — Play-Style X-Ray taxonomy, neighbor quality, movement narrative."""

from routers.styles import (
    _archetype_confidence,
    build_style_movement,
    classify_archetype,
    classify_neighbor_quality,
)


def test_spread_pick_and_roll_fires_on_movement_spacing_efficiency():
    archetype, reason, magnitudes = classify_archetype(
        {"assist_rate": 1.2, "three_point_rate": 0.9, "ts_pct": 0.5}
    )
    assert archetype == "Spread Pick-and-Roll"
    assert magnitudes  # non-empty → confidence > low
    assert "spread" in reason.lower() or "pnr" in reason.lower() or "perimeter" in reason.lower()


def test_transition_defense_disruptors_requires_both_transition_and_defense():
    archetype, _, _ = classify_archetype({"transition_rate": 0.9, "def_rating": -0.8})
    assert archetype == "Transition Defense Disruptors"


def test_transition_defense_not_fired_without_defense_signal():
    archetype, _, _ = classify_archetype({"transition_rate": 0.9, "def_rating": 0.2})
    assert archetype != "Transition Defense Disruptors"


def test_iso_heavy_halfcourt_fires_on_slow_low_assist_low_three():
    archetype, _, _ = classify_archetype(
        {"pace": -0.5, "assist_rate": -0.8, "three_point_rate": -0.2}
    )
    assert archetype == "Iso-Heavy Halfcourt"


def test_tempo_spacing_still_fires():
    archetype, _, _ = classify_archetype({"pace": 1.1, "three_point_rate": 0.9})
    assert archetype == "Tempo + Spacing"


def test_defensive_anchor_fires_when_only_defense_strong():
    archetype, _, _ = classify_archetype({"def_rating": -1.1})
    assert archetype == "Defensive Anchor"


def test_balanced_default_when_no_rules_fire():
    archetype, _, magnitudes = classify_archetype({"pace": 0.1, "ts_pct": 0.1})
    assert archetype == "Balanced"
    assert magnitudes == []


def test_archetype_confidence_bands():
    assert _archetype_confidence([]) == "low"
    assert _archetype_confidence([0.4, 0.4]) == "low"
    assert _archetype_confidence([0.7, 0.7]) == "medium"
    assert _archetype_confidence([1.1, 1.2]) == "high"


def test_neighbor_quality_closest_third_is_high():
    distances = [0.5, 0.6, 0.9, 1.4, 2.0, 2.8, 3.5, 4.1, 5.0]
    assert classify_neighbor_quality(0.5, distances) == "high"
    assert classify_neighbor_quality(2.0, distances) == "medium"
    assert classify_neighbor_quality(5.0, distances) == "low"


def test_neighbor_quality_handles_tiny_league():
    assert classify_neighbor_quality(0.3, []) == "medium"
    assert classify_neighbor_quality(0.3, [0.3, 0.9]) == "high"


def test_movement_narrative_flags_gaining_feature():
    baseline = {"pace": 0.0, "three_point_rate": 0.0, "ts_pct": 0.0}
    recent = {"pace": 0.7, "three_point_rate": 0.0, "ts_pct": 0.0}
    movement = build_style_movement(baseline, recent, drift_archetype=None, archetype="Balanced", window_games=10)
    pace_feature = next(f for f in movement.features if f.metric_id == "pace")
    assert pace_feature.direction == "gaining"
    assert "pace" in movement.narrative.lower()


def test_movement_narrative_flags_fading_and_stable():
    baseline = {"pace": 0.5, "three_point_rate": 0.5}
    recent = {"pace": 0.5, "three_point_rate": -0.4}
    movement = build_style_movement(baseline, recent, drift_archetype=None, archetype="Balanced", window_games=10)
    pace_feature = next(f for f in movement.features if f.metric_id == "pace")
    three_feature = next(f for f in movement.features if f.metric_id == "three_point_rate")
    assert pace_feature.direction == "stable"
    assert three_feature.direction == "fading"


def test_movement_surfaces_drift_archetype_when_different():
    baseline = {"pace": 0.0, "three_point_rate": 0.0}
    recent = {"pace": 1.0, "three_point_rate": 1.0}
    movement = build_style_movement(
        baseline, recent, drift_archetype="Tempo + Spacing", archetype="Balanced", window_games=10
    )
    assert movement.drift_archetype == "Tempo + Spacing"
    assert "tempo" in movement.narrative.lower()


def test_movement_hides_drift_archetype_when_matches_current():
    baseline = {"pace": 0.0}
    recent = {"pace": 0.5}
    movement = build_style_movement(
        baseline, recent, drift_archetype="Tempo + Spacing", archetype="Tempo + Spacing", window_games=10
    )
    assert movement.drift_archetype is None


def test_movement_stable_when_no_feature_moves():
    baseline = {"pace": 0.5, "ts_pct": 0.3}
    recent = {"pace": 0.55, "ts_pct": 0.25}
    movement = build_style_movement(baseline, recent, drift_archetype=None, archetype="Balanced", window_games=10)
    assert all(f.direction == "stable" for f in movement.features)
    assert "stable" in movement.narrative.lower()
