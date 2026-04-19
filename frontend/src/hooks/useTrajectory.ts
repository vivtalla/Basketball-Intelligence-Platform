"use client";

import useSWR from "swr";
import { fetchLineupContext, fetchTrajectorySeries } from "@/lib/api";
import type {
  LineupContextResponse,
  TrajectoryResponse,
  TrajectorySeriesResponse,
} from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

export function useTrajectorySeries(
  playerId: number | null,
  season: string,
  lastNGames: number
) {
  return useSWR<TrajectorySeriesResponse>(
    playerId !== null ? `trajectory-series-${playerId}-${season}-${lastNGames}` : null,
    () => fetchTrajectorySeries(playerId!, season, lastNGames)
  );
}

export function useLineupContext(playerId: number | null, season: string) {
  return useSWR<LineupContextResponse>(
    playerId !== null ? `lineup-context-${playerId}-${season}` : null,
    () => fetchLineupContext(playerId!, season)
  );
}
