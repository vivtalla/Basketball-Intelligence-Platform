"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useSWRConfig } from "swr";
import { syncPlayerPbp, syncSeasonPbp } from "@/lib/api";
import {
  usePbpCoverageDashboard,
  usePbpCoverageSeasons,
  useWarehouseJobSummary,
} from "@/hooks/usePlayerStats";
import WarehousePipelinePanel from "@/components/WarehousePipelinePanel";

const DEFAULT_SEASONS = ["2025-26", "2024-25", "2023-24", "2022-23"];

function coverageTone(status: "none" | "partial" | "ready") {
  if (status === "ready") return "text-emerald-700 bg-emerald-50 dark:text-emerald-300 dark:bg-emerald-950/30";
  if (status === "partial") return "text-amber-700 bg-amber-50 dark:text-amber-300 dark:bg-amber-950/30";
  return "text-gray-600 bg-gray-100 dark:text-gray-300 dark:bg-gray-800";
}

function pct(numerator: number, denominator: number) {
  if (!denominator) return "0%";
  return `${Math.round((numerator / denominator) * 100)}%`;
}

function syncSummary(result: {
  games_processed: number;
  games_fetched: number;
  games_reused: number;
  games_failed: number;
  players_updated: number;
}) {
  return `${result.games_processed} games processed, ${result.games_fetched} fetched, ${result.games_reused} reused, ${result.games_failed} failed, ${result.players_updated} players updated`;
}

export default function CoveragePage() {
  const [selectedSeason, setSelectedSeason] = useState<string>("");
  const [isSeasonSyncing, setIsSeasonSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);
  const [syncingPlayerId, setSyncingPlayerId] = useState<number | null>(null);
  const { mutate } = useSWRConfig();
  const { data: seasonOptions } = usePbpCoverageSeasons();

  const seasons = useMemo(() => {
    const found = new Set(DEFAULT_SEASONS);
    for (const summary of seasonOptions ?? []) found.add(summary.season);
    return Array.from(found);
  }, [seasonOptions]);

  const recommendedSeason = useMemo(() => {
    if (!seasonOptions?.length) return DEFAULT_SEASONS[0];
    const ranked = [...seasonOptions].sort((a, b) => {
      const aSignal = a.synced_games + a.players_ready * 3 + a.players_partial;
      const bSignal = b.synced_games + b.players_ready * 3 + b.players_partial;
      if (bSignal !== aSignal) return bSignal - aSignal;
      if (b.eligible_games !== a.eligible_games) return b.eligible_games - a.eligible_games;
      return b.season.localeCompare(a.season);
    });
    return ranked[0]?.season ?? DEFAULT_SEASONS[0];
  }, [seasonOptions]);

  const season =
    selectedSeason && seasons.includes(selectedSeason) ? selectedSeason : recommendedSeason;
  const { data, error, isLoading } = usePbpCoverageDashboard(season);
  const { data: warehouseSummary } = useWarehouseJobSummary(season);

  const teamRows = useMemo(() => data?.teams ?? [], [data]);
  const playerRows = useMemo(() => data?.players ?? [], [data]);
  const focusTeam = useMemo(() => {
    const ranked = [...teamRows].sort((a, b) => {
      const aMissing = a.eligible_games - a.synced_games;
      const bMissing = b.eligible_games - b.synced_games;
      if (a.status !== b.status) {
        const rank = { none: 0, partial: 1, ready: 2 } as const;
        return rank[a.status] - rank[b.status];
      }
      if (bMissing !== aMissing) return bMissing - aMissing;
      return b.players_none - a.players_none;
    });
    return ranked[0] ?? null;
  }, [teamRows]);
  const focusPlayer = useMemo(() => {
    const ranked = [...playerRows].sort((a, b) => {
      const aMissing = a.eligible_games - a.synced_games;
      const bMissing = b.eligible_games - b.synced_games;
      if (a.status !== b.status) {
        const rank = { none: 0, partial: 1, ready: 2 } as const;
        return rank[a.status] - rank[b.status];
      }
      if (bMissing !== aMissing) return bMissing - aMissing;
      return a.player_name.localeCompare(b.player_name);
    });
    return ranked[0] ?? null;
  }, [playerRows]);
  const activeWarehouseJobType = useMemo(
    () => warehouseSummary?.job_types.find((row) => row.queued > 0 || row.running > 0) ?? null,
    [warehouseSummary]
  );

  async function refreshCoverageState(teamAbbreviation?: string | null) {
    await Promise.all([
      mutate(`pbp-dashboard-${season}`),
      mutate("pbp-dashboard-seasons"),
      teamAbbreviation ? mutate(`team-intelligence-${teamAbbreviation}-${season}`) : Promise.resolve(),
    ]);
  }

  async function handleSeasonSync(forceRefresh = false) {
    setIsSeasonSyncing(true);
    setSyncError(null);
    setSyncMessage(null);
    try {
      const result = await syncSeasonPbp(season, forceRefresh);
      setSyncMessage(
        `${forceRefresh ? "Force refresh completed" : "Season sync completed"} for ${season}: ${syncSummary(result)}.`
      );
      await refreshCoverageState();
    } catch (err) {
      setSyncError(err instanceof Error ? err.message : "Season sync failed.");
    } finally {
      setIsSeasonSyncing(false);
    }
  }

  async function handlePlayerSync(playerId: number, teamAbbreviation?: string | null) {
    setSyncingPlayerId(playerId);
    setSyncError(null);
    setSyncMessage(null);
    try {
      const result = await syncPlayerPbp(playerId, season);
      setSyncMessage(`Player sync completed: ${syncSummary(result)}.`);
      await refreshCoverageState(teamAbbreviation);
    } catch (err) {
      setSyncError(err instanceof Error ? err.message : "Player sync failed.");
    } finally {
      setSyncingPlayerId(null);
    }
  }

  return (
    <div className="mx-auto max-w-7xl space-y-8">
      <section className="rounded-[2rem] border border-gray-200 bg-white p-8 dark:border-gray-800 dark:bg-gray-900">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.24em] text-blue-500">
              Operations
            </p>
            <h1 className="mt-3 text-4xl font-bold text-gray-900 dark:text-gray-100">
              PBP Coverage Dashboard
            </h1>
            <p className="mt-3 max-w-3xl text-gray-500 dark:text-gray-400">
              Track play-by-play sync readiness across teams and players, spot stale
              gaps quickly, and jump into the right team or player workflow.
            </p>
          </div>

          <div className="flex flex-col items-start gap-3 sm:items-end">
            <div className="flex items-center gap-3">
              <label
                htmlFor="coverage-season"
                className="text-xs font-medium uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400"
              >
                Season
              </label>
              <select
                id="coverage-season"
                value={season}
                onChange={(e) => setSelectedSeason(e.target.value)}
                className="rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
              >
                {seasons.map((entry) => (
                  <option key={entry} value={entry}>
                    {entry}
                  </option>
                ))}
              </select>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                Suggested: {recommendedSeason}
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => handleSeasonSync(false)}
                disabled={isSeasonSyncing || !season}
                className="rounded-full bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-300 dark:disabled:bg-blue-900/40"
              >
                {isSeasonSyncing ? "Syncing season..." : "Sync season PBP"}
              </button>
              <button
                type="button"
                onClick={() => handleSeasonSync(true)}
                disabled={isSeasonSyncing || !season}
                className="rounded-full border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:border-gray-300 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-gray-700 dark:text-gray-200 dark:hover:border-gray-600 dark:hover:bg-gray-800"
              >
                Force refresh
              </button>
            </div>
          </div>
        </div>

        <div className="mt-6 grid gap-4 lg:grid-cols-[1.1fr,0.9fr]">
          <div className="rounded-3xl bg-blue-50 p-5 dark:bg-blue-950/30">
            <div className="text-xs font-medium uppercase tracking-[0.18em] text-blue-700 dark:text-blue-300">
              Recommended Team Focus
            </div>
            <div className="mt-3 text-2xl font-semibold text-gray-900 dark:text-gray-100">
              {focusTeam ? focusTeam.name : "Waiting for coverage data"}
            </div>
            <div className="mt-2 text-sm text-gray-600 dark:text-gray-300">
              {focusTeam
                ? `${focusTeam.eligible_games - focusTeam.synced_games} games still missing, with ${focusTeam.players_none} players still at zero derived coverage.`
                : "Once coverage loads, this panel will point to the highest-value team to unlock next."}
            </div>
            {focusTeam ? (
              <div className="mt-4">
                <Link
                  href={`/teams/${focusTeam.abbreviation}`}
                  className="inline-flex rounded-full bg-white px-4 py-2 text-sm font-medium text-blue-700 transition-colors hover:bg-blue-100 dark:bg-blue-900/40 dark:text-blue-200 dark:hover:bg-blue-900/60"
                >
                  Open {focusTeam.abbreviation} team room
                </Link>
              </div>
            ) : null}
          </div>

          <div className="rounded-3xl border border-gray-200 p-5 dark:border-gray-800">
            <div className="text-xs font-medium uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400">
              Next Player Unlock
            </div>
            <div className="mt-3 text-2xl font-semibold text-gray-900 dark:text-gray-100">
              {focusPlayer ? focusPlayer.player_name : "Waiting for coverage data"}
            </div>
            <div className="mt-2 text-sm text-gray-500 dark:text-gray-400">
              {focusPlayer
                ? `${focusPlayer.team_abbreviation ?? "FA"} · ${focusPlayer.synced_games}/${focusPlayer.eligible_games} games synced · ${focusPlayer.has_on_off ? "on/off ready" : "needs on/off"}`
                : "Use this to quickly identify the next single-player sync that will raise team coverage."}
            </div>
          </div>
        </div>

        {warehouseSummary && (
          <div className="mt-6 rounded-3xl border border-gray-200 bg-gray-50 p-5 dark:border-gray-800 dark:bg-gray-950/40">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <div className="text-xs font-medium uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400">
                  Ops Snapshot
                </div>
                <div className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                  Real-time queue posture for {season}, including stalled jobs and the oldest blocked item.
                </div>
              </div>
              <div className="flex flex-wrap gap-2 text-xs">
                <span className="rounded-full bg-gray-200 px-3 py-1 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                  {warehouseSummary.status_counts.queued ?? 0} queued
                </span>
                <span className="rounded-full bg-blue-100 px-3 py-1 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300">
                  {warehouseSummary.status_counts.running ?? 0} running
                </span>
                <span className="rounded-full bg-red-100 px-3 py-1 text-red-700 dark:bg-red-900/20 dark:text-red-300">
                  {warehouseSummary.status_counts.failed ?? 0} failed
                </span>
                {(warehouseSummary.stalled_running_count ?? 0) > 0 && (
                  <span className="rounded-full bg-amber-100 px-3 py-1 text-amber-700 dark:bg-amber-900/20 dark:text-amber-300">
                    {warehouseSummary.stalled_running_count} stalled
                  </span>
                )}
              </div>
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <div className="rounded-2xl bg-white p-4 dark:bg-gray-900">
                <div className="text-[11px] uppercase tracking-[0.18em] text-gray-400 dark:text-gray-500">
                  Oldest queued
                </div>
                <div className="mt-2 font-mono text-sm text-gray-900 dark:text-gray-100">
                  {warehouseSummary.oldest_queued_job?.job_type ?? "—"}
                </div>
                <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  {warehouseSummary.oldest_queued_job?.job_key ?? "No queued job"}
                </div>
              </div>
              <div className="rounded-2xl bg-white p-4 dark:bg-gray-900">
                <div className="text-[11px] uppercase tracking-[0.18em] text-gray-400 dark:text-gray-500">
                  Hottest queue
                </div>
                <div className="mt-2 font-mono text-sm text-gray-900 dark:text-gray-100">
                  {activeWarehouseJobType?.job_type ?? "—"}
                </div>
                <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  {activeWarehouseJobType
                    ? `${activeWarehouseJobType.queued} queued · ${activeWarehouseJobType.running} running`
                    : "No active warehouse jobs"}
                </div>
              </div>
              <div className="rounded-2xl bg-white p-4 dark:bg-gray-900">
                <div className="text-[11px] uppercase tracking-[0.18em] text-gray-400 dark:text-gray-500">
                  Shared throttle
                </div>
                <div className="mt-2 text-sm font-semibold text-gray-900 dark:text-gray-100">
                  {warehouseSummary.global_request_throttle
                    ? `${warehouseSummary.global_request_throttle.seconds_until_available.toFixed(1)}s`
                    : "Awaiting new workers"}
                </div>
                <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  {warehouseSummary.global_request_throttle?.last_request_at
                    ? `Last request ${new Date(warehouseSummary.global_request_throttle.last_request_at).toLocaleTimeString()}`
                    : "Current workers were started before shared-throttle rollout"}
                </div>
              </div>
            </div>
          </div>
        )}

        {(syncMessage || syncError) && (
          <div
            className={`mt-6 rounded-2xl border px-4 py-3 text-sm ${
              syncError
                ? "border-red-200 bg-red-50 text-red-700 dark:border-red-900/60 dark:bg-red-950/20 dark:text-red-200"
                : "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/20 dark:text-emerald-200"
            }`}
          >
            {syncError ?? syncMessage}
          </div>
        )}
      </section>

      {error && (
        <div className="rounded-2xl border border-gray-200 bg-white p-6 text-center text-gray-500 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400">
          Could not load PBP coverage for {season}. Try again after the backend finishes syncing.
        </div>
      )}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[
          {
            label: "Teams Ready",
            value: data ? `${data.teams_ready}/${data.total_teams}` : "—",
            note: data ? pct(data.teams_ready, data.total_teams) : "Waiting for data",
          },
          {
            label: "Players Ready",
            value: data ? `${data.players_ready}/${data.total_players}` : "—",
            note: data ? pct(data.players_ready, data.total_players) : "Waiting for data",
          },
          {
            label: "Games Synced",
            value: data ? `${data.synced_games}/${data.eligible_games}` : "—",
            note: data ? pct(data.synced_games, data.eligible_games) : "Waiting for data",
          },
          {
            label: "Coverage Mix",
            value: data ? `${data.teams_partial} partial` : "—",
            note: data ? `${data.teams_none} none · ${data.teams_ready} ready` : "Waiting for data",
          },
        ].map((card) => (
          <div
            key={card.label}
            className="rounded-3xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-900"
          >
            <div className="text-xs uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400">
              {card.label}
            </div>
            <div className="mt-3 text-3xl font-bold text-gray-900 dark:text-gray-100">
              {isLoading ? "…" : card.value}
            </div>
            <div className="mt-2 text-sm text-gray-500 dark:text-gray-400">{card.note}</div>
          </div>
        ))}
      </section>

      <WarehousePipelinePanel season={season} />

      <div className="grid gap-6 xl:grid-cols-[1.05fr,0.95fr]">
        <section className="rounded-[2rem] border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-900">
          <div className="flex items-end justify-between gap-4">
            <div>
              <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                Team Coverage
              </h2>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                Team-level sync state, driven by active-player readiness and locally stored games.
              </p>
            </div>
          </div>

          <div className="mt-5 space-y-3">
            {isLoading &&
              Array.from({ length: 6 }).map((_, index) => (
                <div key={index} className="h-24 animate-pulse rounded-3xl bg-gray-100 dark:bg-gray-800" />
              ))}

            {!isLoading && teamRows.length === 0 && (
              <div className="rounded-3xl border border-dashed border-gray-200 p-6 text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
                No team coverage rows are available for this season yet.
              </div>
            )}

            {!isLoading &&
              teamRows.map((team) => (
                <Link
                  key={`${team.team_id}-${team.season}`}
                  href={`/teams/${team.abbreviation}`}
                  className="block rounded-3xl border border-gray-200 p-4 transition-colors hover:border-blue-300 hover:bg-blue-50/50 dark:border-gray-800 dark:hover:border-blue-800 dark:hover:bg-blue-950/20"
                >
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                    <div>
                      <div className="flex items-center gap-3">
                        <div className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                          {team.name}
                        </div>
                        <span
                          className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${coverageTone(team.status)}`}
                        >
                          {team.status}
                        </span>
                      </div>
                      <div className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                        {team.players_ready} ready · {team.players_partial} partial · {team.players_none} none
                      </div>
                      <div className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                        {team.eligible_games - team.synced_games} games still missing from local PBP coverage.
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3 text-right text-sm tabular-nums text-gray-600 dark:text-gray-300">
                      <div>
                        <div className="text-[11px] uppercase tracking-[0.18em] text-gray-400 dark:text-gray-500">
                          Games
                        </div>
                        <div className="mt-1 font-semibold text-gray-900 dark:text-gray-100">
                          {team.synced_games}/{team.eligible_games}
                        </div>
                      </div>
                      <div>
                        <div className="text-[11px] uppercase tracking-[0.18em] text-gray-400 dark:text-gray-500">
                          Players
                        </div>
                        <div className="mt-1 font-semibold text-gray-900 dark:text-gray-100">
                          {team.player_count}
                        </div>
                      </div>
                    </div>
                  </div>
                </Link>
              ))}
          </div>
        </section>

        <section className="rounded-[2rem] border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-900">
          <div className="flex items-end justify-between gap-4">
            <div>
              <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                Player Coverage
              </h2>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                Highest-signal player rows to identify who is fully derived and who still needs sync work.
              </p>
            </div>
          </div>

          <div className="mt-5 space-y-3">
            {isLoading &&
              Array.from({ length: 8 }).map((_, index) => (
                <div key={index} className="h-20 animate-pulse rounded-3xl bg-gray-100 dark:bg-gray-800" />
              ))}

            {!isLoading && playerRows.length === 0 && (
              <div className="rounded-3xl border border-dashed border-gray-200 p-6 text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
                No player coverage rows are available for this season yet.
              </div>
            )}

            {!isLoading &&
              playerRows.map((player) => (
                <div
                  key={`${player.player_id}-${player.season}`}
                  className="rounded-3xl border border-gray-200 p-4 dark:border-gray-800"
                >
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                    <div className="min-w-0">
                      <div className="flex items-center gap-3">
                        <Link
                          href={`/players/${player.player_id}`}
                          className="truncate text-base font-semibold text-gray-900 transition-colors hover:text-blue-600 dark:text-gray-100 dark:hover:text-blue-300"
                        >
                          {player.player_name}
                        </Link>
                        <span className="text-xs uppercase tracking-[0.18em] text-gray-400 dark:text-gray-500">
                          {player.team_abbreviation ?? "FA"}
                        </span>
                        <span
                          className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${coverageTone(player.status)}`}
                        >
                          {player.status}
                        </span>
                      </div>
                      <div className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                        {player.has_on_off ? "On/off ready" : "No on/off"} ·{" "}
                        {player.has_scoring_splits ? "Scoring splits ready" : "No scoring splits"}
                      </div>
                      <div className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                        {player.eligible_games - player.synced_games} games still missing for full derived coverage.
                      </div>
                    </div>
                    <div className="flex flex-col items-start gap-3 lg:items-end">
                      <div className="grid grid-cols-2 gap-3 text-right text-sm tabular-nums text-gray-600 dark:text-gray-300">
                        <div>
                          <div className="text-[11px] uppercase tracking-[0.18em] text-gray-400 dark:text-gray-500">
                            Games
                          </div>
                          <div className="mt-1 font-semibold text-gray-900 dark:text-gray-100">
                            {player.synced_games}/{player.eligible_games}
                          </div>
                        </div>
                        <div>
                          <div className="text-[11px] uppercase tracking-[0.18em] text-gray-400 dark:text-gray-500">
                            Updated
                          </div>
                          <div className="mt-1 font-semibold text-gray-900 dark:text-gray-100">
                            {player.last_derived_at ? player.last_derived_at.slice(0, 10) : "—"}
                          </div>
                        </div>
                      </div>

                      {player.status !== "ready" ? (
                        <button
                          type="button"
                          onClick={() => handlePlayerSync(player.player_id, player.team_abbreviation)}
                          disabled={syncingPlayerId === player.player_id || isSeasonSyncing}
                          className="rounded-full border border-blue-200 px-4 py-2 text-sm font-medium text-blue-700 transition-colors hover:border-blue-300 hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-blue-900/60 dark:text-blue-200 dark:hover:bg-blue-950/30"
                        >
                          {syncingPlayerId === player.player_id ? "Syncing player..." : "Sync player"}
                        </button>
                      ) : player.team_abbreviation ? (
                        <Link
                          href={`/teams/${player.team_abbreviation}`}
                          className="text-sm font-medium text-blue-500 transition-colors hover:text-blue-600 dark:hover:text-blue-300"
                        >
                          Open team context →
                        </Link>
                      ) : (
                        <Link
                          href={`/players/${player.player_id}`}
                          className="text-sm font-medium text-blue-500 transition-colors hover:text-blue-600 dark:hover:text-blue-300"
                        >
                          Open player view →
                        </Link>
                      )}
                    </div>
                  </div>
                </div>
              ))}
          </div>
        </section>
      </div>
    </div>
  );
}
