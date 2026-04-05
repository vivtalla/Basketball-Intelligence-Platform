from __future__ import annotations

from typing import List

from models.shotchart import ShotCompletenessSummary
from services.shot_lab_service import summarize_shot_completeness


def build_shot_completeness(raw_shots: List[dict]) -> ShotCompletenessSummary:
    return summarize_shot_completeness(raw_shots)
