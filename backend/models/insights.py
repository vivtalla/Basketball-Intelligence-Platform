from typing import Dict, List

from pydantic import BaseModel


class TrajectoryPlayerRow(BaseModel):
    rank: int
    player_name: str
    team: str
    trajectory_label: str
    trajectory_score: float
    key_stat_deltas: Dict[str, float]
    narrative: str
    context_flags: List[str]


class TrajectoryResponse(BaseModel):
    window: str
    breakout_leaders: List[TrajectoryPlayerRow]
    decline_watch: List[TrajectoryPlayerRow]
    excluded_players: List[str]
    warnings: List[str]
