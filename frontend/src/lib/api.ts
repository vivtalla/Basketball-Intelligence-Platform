import type {
  PlayerSearchResult,
  PlayerProfile,
  CareerStatsResponse,
  ShotChartResponse,
  LeaderboardResponse,
  TeamSummary,
  TeamRosterResponse,
  PercentileResult,
  OnOffStats,
  ClutchStats,
  LineupsResult,
  OnOffLeaderboardResult,
  PbpSyncResult,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchApi<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
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

export async function getTeams(): Promise<TeamSummary[]> {
  return fetchApi<TeamSummary[]>("/api/teams");
}

export async function getTeamRoster(
  teamAbbreviation: string
): Promise<TeamRosterResponse> {
  return fetchApi<TeamRosterResponse>(
    `/api/teams/${encodeURIComponent(teamAbbreviation)}`
  );
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

export async function getPlayerPercentiles(
  playerId: number,
  season: string
): Promise<PercentileResult> {
  return fetchApi<PercentileResult>(
    `/api/stats/${playerId}/percentiles?season=${encodeURIComponent(season)}`
  );
}

export async function getPlayerOnOff(
  playerId: number,
  season: string
): Promise<OnOffStats> {
  return fetchApi<OnOffStats>(
    `/api/advanced/${playerId}/on-off?season=${encodeURIComponent(season)}`
  );
}

export async function getPlayerClutch(
  playerId: number,
  season: string
): Promise<ClutchStats> {
  return fetchApi<ClutchStats>(
    `/api/advanced/${playerId}/clutch?season=${encodeURIComponent(season)}`
  );
}

export async function getLineups(
  season: string,
  teamId?: number,
  minMinutes = 5,
  limit = 25
): Promise<LineupsResult> {
  const params = new URLSearchParams({
    season,
    min_minutes: String(minMinutes),
    limit: String(limit),
  });
  if (teamId != null) params.set("team_id", String(teamId));

  return fetchApi<LineupsResult>(`/api/advanced/lineups?${params.toString()}`);
}

export async function getOnOffLeaderboard(
  season: string,
  minMinutes = 200,
  limit = 25
): Promise<OnOffLeaderboardResult> {
  const params = new URLSearchParams({
    season,
    min_minutes: String(minMinutes),
    limit: String(limit),
  });
  return fetchApi<OnOffLeaderboardResult>(
    `/api/advanced/on-off-leaderboard?${params.toString()}`
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

export async function syncPlayerPbp(
  playerId: number,
  season: string,
  forceRefresh = false
): Promise<PbpSyncResult> {
  return fetchApi<PbpSyncResult>(
    `/api/advanced/${playerId}/sync-pbp?season=${encodeURIComponent(season)}&force_refresh=${forceRefresh}`,
    { method: "POST" }
  );
}

export async function syncSeasonPbp(
  season: string,
  forceRefresh = false
): Promise<PbpSyncResult> {
  return fetchApi<PbpSyncResult>(
    `/api/advanced/sync-season?season=${encodeURIComponent(season)}&force_refresh=${forceRefresh}`,
    { method: "POST" }
  );
}
