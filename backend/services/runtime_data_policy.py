from __future__ import annotations


MODERN_WAREHOUSE_START_SEASON = 2024


def is_modern_warehouse_season(season: str) -> bool:
    try:
        return int(season[:4]) >= MODERN_WAREHOUSE_START_SEASON
    except (TypeError, ValueError):
        return False


def runtime_policy_for_season(season: str) -> str:
    return "warehouse-first" if is_modern_warehouse_season(season) else "legacy-compatibility"


def canonical_source_for_season(season: str) -> str:
    return "warehouse" if is_modern_warehouse_season(season) else "legacy-compatibility"
