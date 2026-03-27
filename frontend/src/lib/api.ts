import type {
  PlayerSearchResult,
  PlayerProfile,
  CareerStatsResponse,
  ShotChartResponse,
  LeaderboardResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchApi<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function searchPlayers(
  query: string
): Promise<PlayerSearchResult[]> {
  return fetchApi<PlayerSearchResult[]>(
    `/api/players/search?q=${encodeURIComponent(query)}`
  );
}

export async function getPlayerProfile(
  playerId: number
): Promise<PlayerProfile> {
  return fetchApi<PlayerProfile>(`/api/players/${playerId}`);
}

export async function getPlayerCareerStats(
  playerId: number
): Promise<CareerStatsResponse> {
  return fetchApi<CareerStatsResponse>(`/api/stats/${playerId}/career`);
}

export async function getAvailableSeasons(): Promise<string[]> {
  return fetchApi<string[]>("/api/leaderboards/seasons");
}

export async function getLeaderboard(
  stat: string,
  season: string,
  seasonType = "Regular Season",
  limit = 25
): Promise<LeaderboardResponse> {
  return fetchApi<LeaderboardResponse>(
    `/api/leaderboards?stat=${encodeURIComponent(stat)}&season=${encodeURIComponent(season)}&season_type=${encodeURIComponent(seasonType)}&limit=${limit}`
  );
}

export async function getPlayerShotChart(
  playerId: number,
  season: string,
  seasonType = "Regular Season"
): Promise<ShotChartResponse> {
  return fetchApi<ShotChartResponse>(
    `/api/shotchart/${playerId}?season=${encodeURIComponent(season)}&season_type=${encodeURIComponent(seasonType)}`
  );
}
