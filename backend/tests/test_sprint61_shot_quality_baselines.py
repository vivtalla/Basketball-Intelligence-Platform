from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.shot_intelligence_service import (  # noqa: E402
    _Baseline,
    _BaselineStore,
    _deserialize_baselines,
    _serialize_baselines,
)


def _sample_store() -> _BaselineStore:
    store = _BaselineStore()
    store.exact = {("Above the Break 3", "Center", "24-27", "3"): _Baseline(50, 18, 54)}
    store.zone_value = {("Above the Break 3", "3"): _Baseline(200, 72, 216)}
    store.zone_distance_value = {("Above the Break 3", "24-27", "3"): _Baseline(120, 45, 135)}
    store.value = {("3",): _Baseline(800, 300, 900)}
    store.league = _Baseline(2000, 900, 2100)
    return store


def test_serialize_roundtrip_preserves_baselines():
    store = _sample_store()
    payload = _serialize_baselines(store)
    rebuilt = _deserialize_baselines(payload)

    assert rebuilt.league.attempts == store.league.attempts
    assert rebuilt.league.made == store.league.made
    assert rebuilt.league.points == store.league.points

    exact_key = ("Above the Break 3", "Center", "24-27", "3")
    assert rebuilt.exact[exact_key].attempts == 50
    assert rebuilt.exact[exact_key].points == 54

    zv_key = ("Above the Break 3", "3")
    assert rebuilt.zone_value[zv_key].made == 72


def test_deserialize_tolerates_missing_sections():
    rebuilt = _deserialize_baselines({})
    assert rebuilt.league.attempts == 0
    assert rebuilt.exact == {}
    assert rebuilt.zone_value == {}


def test_serialize_uses_string_keys():
    payload = _serialize_baselines(_sample_store())
    assert all(isinstance(k, str) for k in payload["exact"].keys())
    assert "||" in next(iter(payload["exact"].keys()))
