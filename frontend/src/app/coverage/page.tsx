"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { usePbpCoverageDashboard, usePbpCoverageSeasons } from "@/hooks/usePlayerStats";

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

export default function CoveragePage() {
  const [selectedSeason, setSelectedSeason] = useState<string>("");
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

  const teamRows = data?.teams ?? [];
  const playerRows = data?.players ?? [];

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
        </div>
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
                <Link
                  key={`${player.player_id}-${player.season}`}
                  href={`/players/${player.player_id}`}
                  className="block rounded-3xl border border-gray-200 p-4 transition-colors hover:border-blue-300 hover:bg-blue-50/50 dark:border-gray-800 dark:hover:border-blue-800 dark:hover:bg-blue-950/20"
                >
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                    <div className="min-w-0">
                      <div className="flex items-center gap-3">
                        <div className="truncate text-base font-semibold text-gray-900 dark:text-gray-100">
                          {player.player_name}
                        </div>
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
                    </div>
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
                  </div>
                </Link>
              ))}
          </div>
        </section>
      </div>
    </div>
  );
}
