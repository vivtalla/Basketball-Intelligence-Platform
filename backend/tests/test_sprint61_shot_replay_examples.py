from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.shot_intelligence_service import _sample_replay_examples, _BaselineStore  # noqa: E402


def _empty_store() -> _BaselineStore:
    return _BaselineStore()


def _make_shot(
    *,
    game_id,
    action_number=None,
    shot_event_id=None,
    linkage_mode="exact",
    shot_made=True,
    shot_value=3,
    distance=25,
    zone_basic="Above the Break 3",
    opponent="DAL",
    team="OKC",
    game_date="2025-12-01",
):
    return {
        "game_id": game_id,
        "action_number": action_number,
        "shot_event_id": shot_event_id,
        "linkage_mode": linkage_mode,
        "shot_made": shot_made,
        "shot_value": shot_value,
        "distance": distance,
        "zone_basic": zone_basic,
        "zone_area": "Center",
        "opponent_team_abbreviation": opponent,
        "team_abbreviation": team,
        "game_date": game_date,
        "shot_type": "3PT Field Goal" if shot_value == 3 else "2PT Field Goal",
        "period": 3,
        "clock": "5:12",
    }


def test_sampler_skips_shots_without_game_id():
    shots = [
        _make_shot(game_id=None, action_number=5),
        _make_shot(game_id="0022400001", action_number=12),
    ]
    examples = _sample_replay_examples(shots, "Regular Season", _empty_store())
    assert len(examples) == 1
    assert examples[0].game_id == "0022400001"


def test_sampler_skips_shots_without_event_linkage():
    shots = [
        _make_shot(game_id="0022400001", action_number=None, shot_event_id=None),
        _make_shot(game_id="0022400002", action_number=7),
    ]
    examples = _sample_replay_examples(shots, "Regular Season", _empty_store())
    assert len(examples) == 1
    assert examples[0].game_id == "0022400002"
    assert examples[0].action_number == 7


def test_sampler_prefers_exact_over_derived_linkage():
    shots = [
        _make_shot(game_id="0022400001", action_number=5, linkage_mode="derived"),
        _make_shot(game_id="0022400002", action_number=6, linkage_mode="exact"),
    ]
    examples = _sample_replay_examples(shots, "Regular Season", _empty_store())
    assert [e.linkage_quality for e in examples] == ["exact", "derived"]
    assert examples[0].game_id == "0022400002"


def test_sampler_caps_at_three_and_dedupes_by_game():
    shots = [
        _make_shot(game_id="0022400001", action_number=i, linkage_mode="exact")
        for i in range(1, 6)
    ] + [
        _make_shot(game_id="0022400002", action_number=11, linkage_mode="exact"),
        _make_shot(game_id="0022400003", action_number=22, linkage_mode="exact"),
        _make_shot(game_id="0022400004", action_number=33, linkage_mode="exact"),
    ]
    examples = _sample_replay_examples(shots, "Regular Season", _empty_store())
    game_ids = [e.game_id for e in examples]
    assert len(examples) == 3
    assert len(set(game_ids)) == 3


def test_sampler_builds_game_explorer_deep_link():
    shots = [_make_shot(game_id="0022400001", action_number=42)]
    examples = _sample_replay_examples(shots, "Regular Season", _empty_store())
    assert examples[0].deep_link_url == "/games/0022400001?team=OKC&event_num=42"


def test_sampler_falls_back_to_event_id_when_action_number_missing():
    shots = [_make_shot(game_id="0022400001", shot_event_id="evt-123")]
    examples = _sample_replay_examples(shots, "Regular Season", _empty_store())
    assert examples[0].shot_event_id == "evt-123"
    assert "event_id=evt-123" in examples[0].deep_link_url


def test_sampler_marks_timeline_linkage_for_unknown_mode():
    shots = [_make_shot(game_id="0022400001", action_number=5, linkage_mode="")]
    examples = _sample_replay_examples(shots, "Regular Season", _empty_store())
    assert examples[0].linkage_quality == "timeline"


def test_sampler_returns_empty_list_for_no_shots():
    examples = _sample_replay_examples([], "Regular Season", _empty_store())
    assert examples == []
