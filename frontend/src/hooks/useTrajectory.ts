"use client";

import useSWR from "swr";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface TrajectoryPlayerRow {
  rank: number;
  player_name: string;
  team: string;
  trajectory_label: string;
  trajectory_score: number;
  key_stat_deltas: Record<string, number>;
  narrative: string;
  context_flags: string[];
}

export interface TrajectoryResponse {
  window: string;
  breakout_leaders: TrajectoryPlayerRow[];
  decline_watch: TrajectoryPlayerRow[];
  excluded_players: string[];
  warnings: string[];
}

async function fetchTrajectory(path: string): Promise<TrajectoryResponse> {
  const response = await fetch(`${API_BASE}${path}`);
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(payload?.detail || `API error: ${response.status}`);
  }
  return payload as TrajectoryResponse;
}

export function useTrajectory(
  season: string,
  lastNGames: number,
  playerPool: "all" | "position_filter" | "team_filter",
  minMinutesPerGame: number,
  teamAbbreviation?: string,
  position?: string
) {
  const params = new URLSearchParams({
    season,
    last_n_games: String(lastNGames),
    player_pool: playerPool,
    min_minutes_per_game: String(minMinutesPerGame),
  });
  if (teamAbbreviation) params.set("team_abbreviation", teamAbbreviation);
  if (position) params.set("position", position);

  return useSWR<TrajectoryResponse>(
    season ? `trajectory-${params.toString()}` : null,
    () => fetchTrajectory(`/api/insights/trajectory?${params.toString()}`)
  );
}
