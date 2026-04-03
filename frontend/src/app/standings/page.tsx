"use client";

import Link from "next/link";
import { Fragment, useMemo, useState } from "react";
import { useStandings, useStandingsHistory } from "@/hooks/usePlayerStats";
import type { StandingsEntry, StandingsHistoryEntry } from "@/lib/types";
import WinPctSparkline from "@/components/WinPctSparkline";
import StandingsBumpChart from "@/components/StandingsBumpChart";

const DEFAULT_SEASON = "2024-25";

// Clinch indicator labels
const CLINCH_LABELS: Record<string, { label: string; color: string }> = {
  x: { label: "x", color: "text-emerald-600 dark:text-emerald-400" },
  y: { label: "y", color: "text-[var(--accent)]" },
  z: { label: "z", color: "text-[var(--signal-ink)]" },
  e: { label: "e", color: "text-red-400 dark:text-red-500" },
  pi: { label: "pi", color: "text-[var(--signal)]" },
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
  if (diff == null) return <span className="text-[var(--muted)]">—</span>;
  const color =
    diff > 0
      ? "text-emerald-600 dark:text-emerald-400"
      : diff < 0
      ? "text-red-500 dark:text-red-400"
      : "text-[var(--muted)]";
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
  historyMap,
}: {
  entries: StandingsEntry[];
  conference: string;
  historyMap: Record<number, StandingsHistoryEntry>;
}) {
  const sorted = entries
    .filter((e) => e.conference === conference)
    .sort((a, b) => a.playoff_rank - b.playoff_rank);

  return (
    <div className="bip-table-shell overflow-hidden rounded-2xl">
      <div className="border-b border-[var(--border)] px-5 py-4">
        <h2 className="bip-display text-lg font-semibold text-[var(--foreground)]">
          {conference}ern Conference
        </h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bip-table-head border-b border-[var(--border)] text-xs uppercase tracking-[0.15em]">
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
              <th className="text-right px-4 py-3 hidden md:table-cell">Trend</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border)]">
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
                        colSpan={13}
                        className="h-0 border-t-2 border-[rgba(33,72,59,0.42)]"
                      />
                    </tr>
                  )}
                  {isPlayInLine && (
                    <tr>
                      <td
                        colSpan={13}
                        className="h-0 border-t-2 border-dashed border-[rgba(111,101,90,0.45)]"
                      />
                    </tr>
                  )}
                  <tr
                    className="transition-colors hover:bg-[rgba(216,228,221,0.26)]"
                  >
                    <td className="px-4 py-3 text-xs tabular-nums text-[var(--muted)]">
                      {entry.playoff_rank}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {entry.abbreviation ? (
                          <Link
                            href={`/teams/${entry.abbreviation}`}
                            className="font-medium text-[var(--foreground)] transition-colors hover:text-[var(--accent)]"
                          >
                            {entry.team_city} {entry.team_name}
                          </Link>
                        ) : (
                          <span className="font-medium text-[var(--foreground)]">
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
                    <td className="px-4 py-3 text-right font-medium tabular-nums text-[var(--foreground)]">
                      {entry.wins}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-[var(--muted)]">
                      {entry.losses}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-[var(--foreground)]">
                      {(entry.win_pct * 100).toFixed(1)}%
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-[var(--muted)]">
                      {entry.games_back != null
                        ? entry.games_back === 0
                          ? "—"
                          : entry.games_back.toFixed(1)
                        : "—"}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-[var(--foreground)]">
                      {entry.l10 || "—"}
                    </td>
                    <td className="hidden px-4 py-3 text-right tabular-nums text-[var(--muted)] sm:table-cell">
                      {entry.home_record || "—"}
                    </td>
                    <td className="hidden px-4 py-3 text-right tabular-nums text-[var(--muted)] sm:table-cell">
                      {entry.road_record || "—"}
                    </td>
                    <td className="hidden px-4 py-3 text-right tabular-nums text-[var(--foreground)] md:table-cell">
                      {entry.pts_pg?.toFixed(1) ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-right hidden md:table-cell">
                      <DiffCell diff={entry.diff_pts_pg} />
                    </td>
                    <td className="px-4 py-3 text-right">
                      <StreakBadge streak={entry.current_streak} />
                    </td>
                    <td className="hidden px-4 py-3 text-right md:table-cell">
                      <WinPctSparkline
                        snapshots={historyMap[entry.team_id]?.snapshots ?? []}
                      />
                    </td>
                  </tr>
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
      {/* Legend */}
      <div className="flex flex-wrap gap-4 border-t border-[var(--border)] px-5 py-3 text-[10px] text-[var(--muted)]">
        <span><span className="border-t-2 border-[var(--accent)] pr-1 font-bold text-[var(--accent)]">—</span> Playoff line (top 6)</span>
        <span><span className="border-t-2 border-dashed border-[var(--muted)] pr-1 font-bold">- -</span> Play-in line (7-10)</span>
        <span><span className="font-bold text-emerald-500">x</span> clinched playoff · <span className="font-bold text-[var(--accent)]">y</span> clinched division · <span className="font-bold text-red-400">e</span> eliminated</span>
      </div>
    </div>
  );
}

export default function StandingsPage() {
  const [season, setSeason] = useState(DEFAULT_SEASON);
  const { data, isLoading, error } = useStandings(season);
  const { data: historyData } = useStandingsHistory(season, 30);

  const historyMap = useMemo<Record<number, StandingsHistoryEntry>>(() => {
    if (!historyData) return {};
    return Object.fromEntries(historyData.map((e) => [e.team_id, e]));
  }, [historyData]);

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="bip-kicker mb-1">
            League
          </p>
          <h1 className="bip-display text-4xl font-semibold text-[var(--foreground)]">
            Standings
          </h1>
          <p className="mt-2 text-[var(--muted)]">
            Conference standings with record, last 10, home/away splits, and scoring differential.
          </p>
        </div>
        <select
          value={season}
          onChange={(e) => setSeason(e.target.value)}
          className="bip-input rounded-xl px-3 py-2 text-sm"
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
              className="bip-table-shell overflow-hidden rounded-2xl animate-pulse"
            >
              <div className="border-b border-[var(--border)] px-5 py-4">
                <div className="h-5 w-40 rounded bg-[var(--surface-alt)]" />
              </div>
              <div className="divide-y divide-[var(--border)]">
                {Array.from({ length: 15 }).map((_, i) => (
                  <div key={i} className="flex items-center gap-4 px-4 py-3">
                    <div className="h-3 w-4 rounded bg-[var(--surface-alt)]" />
                    <div className="h-3 w-36 rounded bg-[var(--surface-alt)]" />
                    <div className="flex-1" />
                    <div className="h-3 w-8 rounded bg-[var(--surface-alt)]" />
                    <div className="h-3 w-8 rounded bg-[var(--surface-alt)]" />
                    <div className="h-3 w-12 rounded bg-[var(--surface-alt)]" />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="bip-empty rounded-2xl p-8 text-center">
          Could not load standings for {season}. The NBA API may be temporarily unavailable.
        </div>
      )}

      {!isLoading && data && (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <StandingsTable entries={data} conference="East" historyMap={historyMap} />
          <StandingsTable entries={data} conference="West" historyMap={historyMap} />
        </div>
      )}

      {/* Standings bump charts — conference rank over last 30 days */}
      {!isLoading && historyData && historyData.length > 0 && (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <StandingsBumpChart historyData={historyData} conference="East" expanded />
          <StandingsBumpChart historyData={historyData} conference="West" expanded />
        </div>
      )}
    </div>
  );
}
