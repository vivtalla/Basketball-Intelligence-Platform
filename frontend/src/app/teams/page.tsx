"use client";

import Link from "next/link";
import { useMemo } from "react";
import { useTeams } from "@/hooks/usePlayerStats";

export default function TeamsPage() {
  const { data: teams, error } = useTeams();

  const sortedTeams = useMemo(
    () => [...(teams ?? [])].sort((a, b) => b.player_count - a.player_count),
    [teams]
  );

  if (error) {
    return (
      <div className="max-w-5xl mx-auto py-16 text-center">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
          Team Explorer
        </h1>
        <p className="mt-4 text-gray-500 dark:text-gray-400">
          Team data could not be loaded right now.
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <div className="space-y-3">
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-blue-500 dark:text-gray-400 dark:hover:text-blue-400 transition-colors"
        >
          ← Back to Home
        </Link>
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-blue-500">
            Explore Teams
          </p>
          <h1 className="text-4xl font-bold text-gray-900 dark:text-gray-100">
            Team Explorer
          </h1>
          <p className="mt-2 max-w-2xl text-gray-500 dark:text-gray-400">
            Browse synced NBA rosters and jump into player-level intelligence
            from each team context.
          </p>
        </div>
      </div>

      {!teams && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="h-40 rounded-3xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 animate-pulse"
            />
          ))}
        </div>
      )}

      {teams && teams.length === 0 && (
        <div className="rounded-3xl border border-dashed border-gray-300 dark:border-gray-700 p-10 text-center">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            No teams have been synced yet
          </h2>
          <p className="mt-2 text-gray-500 dark:text-gray-400">
            Open a few player pages first and their teams will appear here.
          </p>
        </div>
      )}

      {sortedTeams.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {sortedTeams.map((team) => (
            <Link
              key={team.team_id}
              href={`/teams/${team.abbreviation}`}
              className="group rounded-3xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6 hover:border-blue-400 hover:shadow-xl transition-all"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-blue-500">
                    {team.abbreviation}
                  </p>
                  <h2 className="mt-2 text-2xl font-semibold text-gray-900 dark:text-gray-100">
                    {team.name}
                  </h2>
                </div>
                <div className="rounded-2xl bg-blue-50 dark:bg-blue-950/40 px-3 py-2 text-right">
                  <div className="text-2xl font-bold text-blue-600 dark:text-blue-300">
                    {team.player_count}
                  </div>
                  <div className="text-xs text-blue-600/80 dark:text-blue-300/80">
                    active players
                  </div>
                </div>
              </div>
              <p className="mt-6 text-sm text-gray-500 dark:text-gray-400">
                Open the roster, identify leading scorers and creators, and
                jump straight into player dashboards.
              </p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
