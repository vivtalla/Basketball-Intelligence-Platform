"use client";

import Image from "next/image";
import Link from "next/link";
import { useMemo } from "react";
import { useParams } from "next/navigation";
import { useTeamRoster } from "@/hooks/usePlayerStats";
import type { TeamRosterPlayer } from "@/lib/types";

function formatValue(value: number | null | undefined, digits = 1) {
  return value == null ? "-" : value.toFixed(digits);
}

export default function TeamDetailPage() {
  const params = useParams<{ abbr: string }>();
  const teamAbbreviation = params.abbr?.toUpperCase() ?? null;
  const { data: roster, error } = useTeamRoster(teamAbbreviation);

  const sortedPlayers = useMemo(
    () =>
      [...(roster?.players ?? [])].sort(
        (a, b) => (b.pts_pg ?? -1) - (a.pts_pg ?? -1)
      ),
    [roster]
  );

  const leaders = useMemo(() => {
    if (!roster) return [];

    const getLeader = (
      label: string,
      selector: (player: TeamRosterPlayer) => number | null | undefined,
      digits = 1
    ) => {
      const player = [...roster.players]
        .filter((entry) => selector(entry) != null)
        .sort((a, b) => (selector(b) ?? -Infinity) - (selector(a) ?? -Infinity))[0];

      return {
        label,
        player,
        value: player ? formatValue(selector(player), digits) : "-",
      };
    };

    return [
      getLeader("Scoring leader", (player) => player.pts_pg),
      getLeader("Top playmaker", (player) => player.ast_pg),
      getLeader("Best BPM", (player) => player.bpm),
      getLeader("Best PER", (player) => player.per),
    ];
  }, [roster]);

  const syncCoverage =
    roster && roster.players.length > 0
      ? Math.round((roster.synced_count / roster.players.length) * 100)
      : 0;

  if (error) {
    return (
      <div className="max-w-6xl mx-auto py-16 text-center">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
          Team not available
        </h1>
        <p className="mt-4 text-gray-500 dark:text-gray-400">
          This team has not been synced yet, or the backend could not return it.
        </p>
        <Link
          href="/teams"
          className="mt-6 inline-flex rounded-full bg-blue-500 px-5 py-2 text-sm font-medium text-white hover:bg-blue-600 transition-colors"
        >
          Browse synced teams
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <div className="space-y-3">
        <Link
          href="/teams"
          className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-blue-500 dark:text-gray-400 dark:hover:text-blue-400 transition-colors"
        >
          ← Back to Teams
        </Link>

        {!roster ? (
          <div className="space-y-3 animate-pulse">
            <div className="h-6 w-24 rounded-full bg-gray-200 dark:bg-gray-800" />
            <div className="h-12 w-80 rounded-2xl bg-gray-200 dark:bg-gray-800" />
            <div className="h-5 w-full max-w-2xl rounded-xl bg-gray-200 dark:bg-gray-800" />
          </div>
        ) : (
          <div className="rounded-[2rem] border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-8">
            <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <p className="text-sm font-medium uppercase tracking-[0.24em] text-blue-500">
                  {roster.abbreviation}
                </p>
                <h1 className="mt-3 text-4xl font-bold text-gray-900 dark:text-gray-100">
                  {roster.name}
                </h1>
                <p className="mt-3 max-w-2xl text-gray-500 dark:text-gray-400">
                  Team context for player exploration, including current synced
                  roster coverage and quick leaders across scoring, playmaking,
                  and impact metrics.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                <div className="rounded-2xl bg-gray-50 dark:bg-gray-800 p-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400">
                    Active roster
                  </div>
                  <div className="mt-2 text-3xl font-semibold text-gray-900 dark:text-gray-100">
                    {roster.players.length}
                  </div>
                </div>
                <div className="rounded-2xl bg-gray-50 dark:bg-gray-800 p-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400">
                    Synced
                  </div>
                  <div className="mt-2 text-3xl font-semibold text-gray-900 dark:text-gray-100">
                    {roster.synced_count}
                  </div>
                </div>
                <div className="rounded-2xl bg-blue-50 dark:bg-blue-950/40 p-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-blue-600 dark:text-blue-300">
                    Coverage
                  </div>
                  <div className="mt-2 text-3xl font-semibold text-blue-700 dark:text-blue-200">
                    {syncCoverage}%
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {roster && (
        <>
          <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            {leaders.map((leader) => (
              <div
                key={leader.label}
                className="rounded-3xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5"
              >
                <div className="text-xs font-medium uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400">
                  {leader.label}
                </div>
                <div className="mt-4 text-lg font-semibold text-gray-900 dark:text-gray-100">
                  {leader.player?.full_name ?? "No synced data yet"}
                </div>
                <div className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  {leader.player?.position || "Add more player syncs to unlock"}
                </div>
                <div className="mt-6 text-3xl font-bold text-blue-600 dark:text-blue-300">
                  {leader.value}
                </div>
              </div>
            ))}
          </section>

          <section className="rounded-[2rem] border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 overflow-hidden">
            <div className="flex flex-col gap-2 border-b border-gray-200 dark:border-gray-800 px-6 py-5 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                  Roster Board
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Sorted by points per game using the latest synced regular-season stats.
                </p>
              </div>
              <Link
                href="/leaderboards"
                className="text-sm text-blue-500 hover:text-blue-600 transition-colors"
              >
                Cross-team leaderboards →
              </Link>
            </div>

            <div className="divide-y divide-gray-200 dark:divide-gray-800">
              {sortedPlayers.map((player) => (
                <Link
                  key={player.player_id}
                  href={`/players/${player.player_id}`}
                  className="block px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-800/70 transition-colors"
                >
                  <div className="flex flex-col gap-4 lg:grid lg:grid-cols-[minmax(0,1.4fr)_repeat(4,minmax(64px,0.6fr))] lg:items-center lg:gap-3">
                    <div className="flex min-w-0 items-center gap-3">
                      <div className="relative h-14 w-14 overflow-hidden rounded-2xl bg-gray-100 dark:bg-gray-800">
                        {player.headshot_url ? (
                          <Image
                            src={player.headshot_url}
                            alt={player.full_name}
                            fill
                            className="object-cover object-top"
                          />
                        ) : null}
                      </div>
                      <div className="min-w-0">
                        <div className="truncate font-semibold text-gray-900 dark:text-gray-100">
                          {player.full_name}
                        </div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">
                          {player.position || "N/A"}{player.jersey ? ` · #${player.jersey}` : ""}
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                      <div className="rounded-2xl bg-gray-50 dark:bg-gray-800/80 px-3 py-2 text-right">
                        <div className="text-xs uppercase tracking-[0.18em] text-gray-400">
                          PTS
                        </div>
                        <div className="font-semibold text-gray-900 dark:text-gray-100">
                          {formatValue(player.pts_pg)}
                        </div>
                      </div>
                      <div className="rounded-2xl bg-gray-50 dark:bg-gray-800/80 px-3 py-2 text-right">
                        <div className="text-xs uppercase tracking-[0.18em] text-gray-400">
                          REB
                        </div>
                        <div className="font-semibold text-gray-900 dark:text-gray-100">
                          {formatValue(player.reb_pg)}
                        </div>
                      </div>
                      <div className="rounded-2xl bg-gray-50 dark:bg-gray-800/80 px-3 py-2 text-right">
                        <div className="text-xs uppercase tracking-[0.18em] text-gray-400">
                          AST
                        </div>
                        <div className="font-semibold text-gray-900 dark:text-gray-100">
                          {formatValue(player.ast_pg)}
                        </div>
                      </div>
                      <div className="rounded-2xl bg-gray-50 dark:bg-gray-800/80 px-3 py-2 text-right">
                        <div className="text-xs uppercase tracking-[0.18em] text-gray-400">
                          BPM
                        </div>
                        <div className="font-semibold text-gray-900 dark:text-gray-100">
                          {formatValue(player.bpm)}
                        </div>
                      </div>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
