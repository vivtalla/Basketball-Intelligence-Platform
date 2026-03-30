import type {
  PlayerSearchResult,
  PlayerProfile,
  CareerStatsResponse,
  ShotChartResponse,
  LeaderboardResponse,
  TeamSummary,
  TeamRosterResponse,
  TeamAnalytics,
  TeamIntelligence,
  StandingsEntry,
  BreakoutsResponse,
  PercentileResult,
  OnOffStats,
  PbpCoverage,
  PbpCoverageDashboard,
  PbpCoverageSeasonSummary,
  ClutchStats,
  LineupsResult,
  OnOffLeaderboardResult,
  PbpSyncResult,
  GameLogResponse,
  GameDetailResponse,
  SimilarityResponse,
  LeagueContext,
  CareerLeaderboardResponse,
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
  limit = 25,
  team?: string
): Promise<LeaderboardResponse> {
  const params = new URLSearchParams({
    stat,
    season,
    season_type: seasonType,
    limit: String(limit),
  });
  if (team) params.set("team", team);
  return fetchApi<LeaderboardResponse>(`/api/leaderboards?${params.toString()}`);
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

export async function getPlayerPbpCoverage(
  playerId: number,
  season: string
): Promise<PbpCoverage> {
  return fetchApi<PbpCoverage>(
    `/api/advanced/${playerId}/pbp-coverage?season=${encodeURIComponent(season)}`
  );
}

export async function getPbpCoverageDashboard(
  season: string
): Promise<PbpCoverageDashboard> {
  return fetchApi<PbpCoverageDashboard>(
    `/api/advanced/pbp-dashboard?season=${encodeURIComponent(season)}`
  );
}

export async function getPbpCoverageSeasons(): Promise<PbpCoverageSeasonSummary[]> {
  return fetchApi<PbpCoverageSeasonSummary[]>("/api/advanced/pbp-dashboard-seasons");
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

export async function getPlayerGameLogs(
  playerId: number,
  season: string,
  seasonType = "Regular Season"
): Promise<GameLogResponse> {
  return fetchApi<GameLogResponse>(
    `/api/gamelogs/${playerId}?season=${encodeURIComponent(season)}&season_type=${encodeURIComponent(seasonType)}`
  );
}

export async function getGameDetail(gameId: string): Promise<GameDetailResponse> {
  return fetchApi<GameDetailResponse>(`/api/games/${encodeURIComponent(gameId)}`);
}

export async function getBreakouts(
  season: string,
  minGp = 20,
  limit = 25
): Promise<BreakoutsResponse> {
  return fetchApi<BreakoutsResponse>(
    `/api/insights/breakouts?season=${encodeURIComponent(season)}&min_gp=${minGp}&limit=${limit}`
  );
}

export async function getStandings(season: string): Promise<StandingsEntry[]> {
  return fetchApi<StandingsEntry[]>(
    `/api/standings?season=${encodeURIComponent(season)}`
  );
}

export async function getTeamAnalytics(
  teamAbbreviation: string,
  season: string
): Promise<TeamAnalytics> {
  return fetchApi<TeamAnalytics>(
    `/api/teams/${encodeURIComponent(teamAbbreviation)}/analytics?season=${encodeURIComponent(season)}`
  );
}

export async function getTeamIntelligence(
  teamAbbreviation: string,
  season: string
): Promise<TeamIntelligence> {
  return fetchApi<TeamIntelligence>(
    `/api/teams/${encodeURIComponent(teamAbbreviation)}/intelligence?season=${encodeURIComponent(season)}`
  );
}

export async function getSimilarPlayers(
  playerId: number,
  season: string,
  n = 8,
  crossEra = true
): Promise<SimilarityResponse> {
  return fetchApi<SimilarityResponse>(
    `/api/similarity/${playerId}?season=${encodeURIComponent(season)}&n=${n}&cross_era=${crossEra}`
  );
}

export async function getLeagueContext(
  season: string,
  position?: string
): Promise<LeagueContext> {
  const params = new URLSearchParams({ season });
  if (position) params.set("position", position);
  return fetchApi<LeagueContext>(`/api/stats/context?${params.toString()}`);
}

export async function getCareerLeaderboard(
  stat: string,
  minGp = 15,
  limit = 25
): Promise<CareerLeaderboardResponse> {
  const params = new URLSearchParams({ stat, min_gp: String(minGp), limit: String(limit) });
  return fetchApi<CareerLeaderboardResponse>(`/api/leaderboards/career?${params.toString()}`);
}

export async function getLeaderboardTeams(season: string): Promise<string[]> {
  return fetchApi<string[]>(`/api/leaderboards/teams?season=${encodeURIComponent(season)}`);
}

// ── Warehouse pipeline API ────────────────────────────────────────────────────

import type { WarehouseSeasonHealth, IngestionJobResponse } from "./types";

export async function getWarehouseSeasonHealth(season: string): Promise<WarehouseSeasonHealth> {
  return fetchApi<WarehouseSeasonHealth>(`/api/warehouse/health/${encodeURIComponent(season)}`);
}

export async function getWarehouseJobs(
  status?: string,
  season?: string,
  limit = 50
): Promise<IngestionJobResponse[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (status) params.set("status", status);
  if (season) params.set("season", season);
  return fetchApi<IngestionJobResponse[]>(`/api/warehouse/jobs?${params.toString()}`);
}

export async function queueSeasonBackfill(season: string): Promise<{ queued: number }> {
  return fetchApi<{ queued: number }>(
    `/api/warehouse/queue/season-backfill?season=${encodeURIComponent(season)}`,
    { method: "POST" }
  );
}

export async function queueCurrentSeason(season: string): Promise<{ queued: number }> {
  return fetchApi<{ queued: number }>(
    `/api/warehouse/queue/current-season?season=${encodeURIComponent(season)}`,
    { method: "POST" }
  );
}

export async function runNextWarehouseJob(
  season?: string
): Promise<{ status: string; result?: Record<string, unknown> }> {
  const params = season ? `?season=${encodeURIComponent(season)}` : "";
  return fetchApi<{ status: string; result?: Record<string, unknown> }>(
    `/api/warehouse/run-next${params}`,
    { method: "POST" }
  );
}

export async function retryFailedJobs(season: string): Promise<{ queued: number }> {
  return fetchApi<{ queued: number }>(
    `/api/warehouse/retry-failed?season=${encodeURIComponent(season)}`,
    { method: "POST" }
  );
}

export async function getWarehouseJobSummary(
  season?: string
): Promise<import("./types").WarehouseJobSummary> {
  const params = season ? `?season=${encodeURIComponent(season)}` : "";
  return fetchApi<import("./types").WarehouseJobSummary>(
    `/api/warehouse/jobs/summary${params}`
  );
}

export async function resetStaleWarehouseJobs(
  season?: string
): Promise<{ queued: number }> {
  const params = season ? `?season=${encodeURIComponent(season)}` : "";
  return fetchApi<{ queued: number }>(
    `/api/warehouse/reset-stale${params}`,
    { method: "POST" }
  );
}

export async function getGameSummary(
  gameId: string
): Promise<import("./types").GameSummaryResponse> {
  return fetchApi<import("./types").GameSummaryResponse>(
    `/api/games/${encodeURIComponent(gameId)}/summary`
  );
}
