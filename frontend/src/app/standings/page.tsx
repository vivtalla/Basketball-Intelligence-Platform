"use client";

import Link from "next/link";
import { Fragment, useState } from "react";
import { useStandings } from "@/hooks/usePlayerStats";
import type { StandingsEntry } from "@/lib/types";

const DEFAULT_SEASON = "2024-25";

// Clinch indicator labels
const CLINCH_LABELS: Record<string, { label: string; color: string }> = {
  x: { label: "x", color: "text-emerald-600 dark:text-emerald-400" },
  y: { label: "y", color: "text-blue-600 dark:text-blue-400" },
  z: { label: "z", color: "text-purple-600 dark:text-purple-400" },
  e: { label: "e", color: "text-red-400 dark:text-red-500" },
  pi: { label: "pi", color: "text-yellow-600 dark:text-yellow-400" },
};

function StreakBadge({ streak }: { streak: string }) {
  if (!streak) return null;
  const isWin = streak.startsWith("W");
  return (
    <span
      className={`text-xs font-semibold tabular-nums ${
        isWin
          ? "text-emerald-600 dark:text-emerald-400"
          : "text-red-500 dark:text-red-400"
      }`}
    >
      {streak}
    </span>
  );
}

function DiffCell({ diff }: { diff: number | null }) {
  if (diff == null) return <span className="text-gray-400">—</span>;
  const color =
    diff > 0
      ? "text-emerald-600 dark:text-emerald-400"
      : diff < 0
      ? "text-red-500 dark:text-red-400"
      : "text-gray-500 dark:text-gray-400";
  return (
    <span className={`font-medium tabular-nums ${color}`}>
      {diff > 0 ? "+" : ""}
      {diff.toFixed(1)}
    </span>
  );
}

function StandingsTable({
  entries,
  conference,
}: {
  entries: StandingsEntry[];
  conference: string;
}) {
  const sorted = entries
    .filter((e) => e.conference === conference)
    .sort((a, b) => a.playoff_rank - b.playoff_rank);

  return (
    <div className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          {conference}ern Conference
        </h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 dark:border-gray-700 text-xs uppercase tracking-[0.15em] text-gray-400 dark:text-gray-500">
              <th className="text-left px-4 py-3 w-8">#</th>
              <th className="text-left px-4 py-3">Team</th>
              <th className="text-right px-4 py-3">W</th>
              <th className="text-right px-4 py-3">L</th>
              <th className="text-right px-4 py-3">PCT</th>
              <th className="text-right px-4 py-3">GB</th>
              <th className="text-right px-4 py-3">L10</th>
              <th className="text-right px-4 py-3 hidden sm:table-cell">Home</th>
              <th className="text-right px-4 py-3 hidden sm:table-cell">Away</th>
              <th className="text-right px-4 py-3 hidden md:table-cell">PPG</th>
              <th className="text-right px-4 py-3 hidden md:table-cell">Diff</th>
              <th className="text-right px-4 py-3">Strk</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700/60">
            {sorted.map((entry, idx) => {
              const isPlayoffLine = idx === 5; // between 6th and 7th
              const isPlayInLine = idx === 9; // between 10th and 11th
              const clinch = entry.clinch_indicator
                ? CLINCH_LABELS[entry.clinch_indicator]
                : null;

              return (
                <Fragment key={entry.team_id}>
                  {isPlayoffLine && (
                    <tr>
                      <td
                        colSpan={12}
                        className="h-0 border-t-2 border-blue-400/60 dark:border-blue-500/40"
                      />
                    </tr>
                  )}
                  {isPlayInLine && (
                    <tr>
                      <td
                        colSpan={12}
                        className="h-0 border-t-2 border-dashed border-gray-300 dark:border-gray-600"
                      />
                    </tr>
                  )}
                  <tr
                    className="hover:bg-gray-50 dark:hover:bg-gray-700/40 transition-colors"
                  >
                    <td className="px-4 py-3 text-gray-400 dark:text-gray-500 tabular-nums text-xs">
                      {entry.playoff_rank}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {entry.abbreviation ? (
                          <Link
                            href={`/teams/${entry.abbreviation}`}
                            className="font-medium text-gray-900 dark:text-gray-100 hover:text-blue-500 dark:hover:text-blue-400 transition-colors"
                          >
                            {entry.team_city} {entry.team_name}
                          </Link>
                        ) : (
                          <span className="font-medium text-gray-900 dark:text-gray-100">
                            {entry.team_city} {entry.team_name}
                          </span>
                        )}
                        {clinch && (
                          <span
                            className={`text-[10px] font-bold ${clinch.color}`}
                            title={`Clinch: ${entry.clinch_indicator}`}
                          >
                            -{clinch.label}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right font-medium tabular-nums text-gray-900 dark:text-gray-100">
                      {entry.wins}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-gray-500 dark:text-gray-400">
                      {entry.losses}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-gray-700 dark:text-gray-300">
                      {(entry.win_pct * 100).toFixed(1)}%
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-gray-500 dark:text-gray-400">
                      {entry.games_back != null
                        ? entry.games_back === 0
                          ? "—"
                          : entry.games_back.toFixed(1)
                        : "—"}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-gray-700 dark:text-gray-300">
                      {entry.l10 || "—"}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-gray-500 dark:text-gray-400 hidden sm:table-cell">
                      {entry.home_record || "—"}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-gray-500 dark:text-gray-400 hidden sm:table-cell">
                      {entry.road_record || "—"}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-gray-700 dark:text-gray-300 hidden md:table-cell">
                      {entry.pts_pg?.toFixed(1) ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-right hidden md:table-cell">
                      <DiffCell diff={entry.diff_pts_pg} />
                    </td>
                    <td className="px-4 py-3 text-right">
                      <StreakBadge streak={entry.current_streak} />
                    </td>
                  </tr>
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
      {/* Legend */}
      <div className="px-5 py-3 border-t border-gray-200 dark:border-gray-700 flex flex-wrap gap-4 text-[10px] text-gray-400 dark:text-gray-500">
        <span><span className="text-blue-400 font-bold border-t-2 border-blue-400 pr-1">—</span> Playoff line (top 6)</span>
        <span><span className="font-bold border-t-2 border-dashed border-gray-400 pr-1">- -</span> Play-in line (7-10)</span>
        <span><span className="text-emerald-500 font-bold">x</span> clinched playoff · <span className="text-blue-500 font-bold">y</span> clinched division · <span className="text-red-400 font-bold">e</span> eliminated</span>
      </div>
    </div>
  );
}

export default function StandingsPage() {
  const [season, setSeason] = useState(DEFAULT_SEASON);
  const { data, isLoading, error } = useStandings(season);

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.24em] text-blue-500 mb-1">
            League
          </p>
          <h1 className="text-4xl font-bold text-gray-900 dark:text-gray-100">
            Standings
          </h1>
          <p className="mt-2 text-gray-500 dark:text-gray-400">
            Conference standings with record, last 10, home/away splits, and scoring differential.
          </p>
        </div>
        <select
          value={season}
          onChange={(e) => setSeason(e.target.value)}
          className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {["2024-25", "2023-24", "2022-23", "2021-22", "2020-21"].map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      {/* Loading skeleton */}
      {isLoading && (
        <div className="space-y-6">
          {["East", "West"].map((conf) => (
            <div
              key={conf}
              className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden animate-pulse"
            >
              <div className="px-5 py-4 border-b border-gray-200 dark:border-gray-700">
                <div className="h-5 w-40 rounded bg-gray-200 dark:bg-gray-700" />
              </div>
              <div className="divide-y divide-gray-100 dark:divide-gray-700/60">
                {Array.from({ length: 15 }).map((_, i) => (
                  <div key={i} className="flex items-center gap-4 px-4 py-3">
                    <div className="h-3 w-4 rounded bg-gray-200 dark:bg-gray-700" />
                    <div className="h-3 w-36 rounded bg-gray-200 dark:bg-gray-700" />
                    <div className="flex-1" />
                    <div className="h-3 w-8 rounded bg-gray-200 dark:bg-gray-700" />
                    <div className="h-3 w-8 rounded bg-gray-200 dark:bg-gray-700" />
                    <div className="h-3 w-12 rounded bg-gray-200 dark:bg-gray-700" />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-8 text-center text-gray-500 dark:text-gray-400">
          Could not load standings for {season}. The NBA API may be temporarily unavailable.
        </div>
      )}

      {!isLoading && data && (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <StandingsTable entries={data} conference="East" />
          <StandingsTable entries={data} conference="West" />
        </div>
      )}
    </div>
  );
}
