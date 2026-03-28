"use client";

import { useState } from "react";
import Link from "next/link";
import { useLineups } from "@/hooks/usePlayerStats";
import type { LineupStatsResponse } from "@/lib/types";

interface TeamLineupsPanelProps {
  teamId: number;
  season: string;
}

type View = "best" | "worst";

function NetBar({ value }: { value: number | null }) {
  if (value == null) return <span className="text-gray-400">—</span>;
  const abs = Math.min(Math.abs(value), 20);
  const pct = (abs / 20) * 100;
  const positive = value >= 0;
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-2 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden flex-shrink-0">
        <div
          className={`h-full rounded-full ${positive ? "bg-emerald-500" : "bg-red-400"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span
        className={`tabular-nums text-xs font-semibold ${
          positive ? "text-emerald-600 dark:text-emerald-400" : "text-red-500 dark:text-red-400"
        }`}
      >
        {value > 0 ? "+" : ""}
        {value.toFixed(1)}
      </span>
    </div>
  );
}

function fmt(v: number | null | undefined, digits = 1): string {
  if (v == null) return "—";
  return v.toFixed(digits);
}

function LineupRow({
  lineup,
  rank,
}: {
  lineup: LineupStatsResponse;
  rank: number;
}) {
  return (
    <div className="px-5 py-4 hover:bg-gray-50 dark:hover:bg-gray-800/60 transition-colors">
      <div className="flex items-start gap-4">
        {/* Rank */}
        <div className="w-6 flex-shrink-0 text-xs text-gray-400 dark:text-gray-500 tabular-nums pt-0.5">
          {rank}
        </div>

        {/* Player names */}
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap gap-x-2 gap-y-1">
            {lineup.player_names.map((name, i) => (
              <span
                key={i}
                className="text-sm text-gray-800 dark:text-gray-200"
              >
                {name}
                {i < lineup.player_names.length - 1 && (
                  <span className="text-gray-300 dark:text-gray-600 ml-2">·</span>
                )}
              </span>
            ))}
          </div>
          <div className="mt-1 flex flex-wrap gap-3 text-xs text-gray-400 dark:text-gray-500">
            <span>{fmt(lineup.minutes)} MIN</span>
            <span>{lineup.possessions ?? "—"} POSS</span>
            <span>ORTG {fmt(lineup.ortg)}</span>
            <span>DRTG {fmt(lineup.drtg)}</span>
            <span>+/- {lineup.plus_minus != null ? (lineup.plus_minus > 0 ? "+" : "") + lineup.plus_minus.toFixed(0) : "—"}</span>
          </div>
        </div>

        {/* Net rating bar */}
        <div className="flex-shrink-0 pt-0.5">
          <NetBar value={lineup.net_rating ?? null} />
        </div>
      </div>
    </div>
  );
}

export default function TeamLineupsPanel({ teamId, season }: TeamLineupsPanelProps) {
  const [view, setView] = useState<View>("best");
  const [minPoss, setMinPoss] = useState(20);

  // Fetch enough lineups to split into best/worst
  const { data, isLoading, error } = useLineups(season, teamId, 1, 100);

  const lineups = data?.lineups ?? [];

  // Filter by min possessions, then sort
  const filtered = lineups
    .filter((l) => (l.possessions ?? 0) >= minPoss && l.net_rating != null)
    .sort((a, b) => (b.net_rating ?? 0) - (a.net_rating ?? 0));

  const displayed =
    view === "best" ? filtered.slice(0, 10) : [...filtered].reverse().slice(0, 10);

  return (
    <div className="rounded-[2rem] border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 overflow-hidden">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-200 dark:border-gray-800 px-6 py-5">
        <div>
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
            5-Man Lineups
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {season} · Net rating by 5-man combination
          </p>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          {/* Min possessions filter */}
          <select
            value={minPoss}
            onChange={(e) => setMinPoss(Number(e.target.value))}
            className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value={10}>Min 10 poss</option>
            <option value={20}>Min 20 poss</option>
            <option value={50}>Min 50 poss</option>
            <option value={100}>Min 100 poss</option>
          </select>

          {/* Best / Worst toggle */}
          <div className="flex rounded-xl overflow-hidden border border-gray-200 dark:border-gray-700 text-sm">
            <button
              onClick={() => setView("best")}
              className={`px-4 py-1.5 transition-colors ${
                view === "best"
                  ? "bg-emerald-500 text-white"
                  : "bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700"
              }`}
            >
              Best 10
            </button>
            <button
              onClick={() => setView("worst")}
              className={`px-4 py-1.5 transition-colors ${
                view === "worst"
                  ? "bg-red-500 text-white"
                  : "bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700"
              }`}
            >
              Worst 10
            </button>
          </div>
        </div>
      </div>

      {/* Column headers */}
      <div className="flex items-center gap-4 px-5 py-2 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-100 dark:border-gray-800">
        <div className="w-6 flex-shrink-0" />
        <div className="flex-1 text-xs uppercase tracking-wide text-gray-400 dark:text-gray-500">
          Players
        </div>
        <div className="flex-shrink-0 text-xs uppercase tracking-wide text-gray-400 dark:text-gray-500">
          Net Rtg
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="divide-y divide-gray-100 dark:divide-gray-800">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="px-5 py-4 animate-pulse flex gap-4">
              <div className="w-6 h-4 rounded bg-gray-200 dark:bg-gray-700" />
              <div className="flex-1 space-y-2">
                <div className="h-4 w-3/4 rounded bg-gray-200 dark:bg-gray-700" />
                <div className="h-3 w-1/3 rounded bg-gray-200 dark:bg-gray-700" />
              </div>
              <div className="w-24 h-4 rounded bg-gray-200 dark:bg-gray-700" />
            </div>
          ))}
        </div>
      )}

      {/* Error */}
      {error && !isLoading && (
        <div className="px-6 py-10 text-center text-gray-400 dark:text-gray-500 text-sm">
          Could not load lineup data. Make sure play-by-play data has been synced for this team.
        </div>
      )}

      {/* Empty */}
      {!isLoading && !error && displayed.length === 0 && (
        <div className="px-6 py-10 text-center text-gray-400 dark:text-gray-500 text-sm">
          No lineups with {minPoss}+ possessions found for {season}.{" "}
          <span className="text-blue-500">Try lowering the minimum possessions filter.</span>
        </div>
      )}

      {/* Lineup rows */}
      {!isLoading && displayed.length > 0 && (
        <div className="divide-y divide-gray-100 dark:divide-gray-800">
          {displayed.map((lineup, i) => (
            <LineupRow key={lineup.lineup_key} lineup={lineup} rank={i + 1} />
          ))}
        </div>
      )}

      {/* Footer note */}
      {!isLoading && displayed.length > 0 && (
        <div className="px-6 py-3 border-t border-gray-100 dark:border-gray-800 text-xs text-gray-400 dark:text-gray-500">
          Net rating = (ORTG − DRTG) per 100 possessions · Requires play-by-play sync ·{" "}
          <Link href="/learn" className="text-blue-400 hover:text-blue-500">
            Learn more
          </Link>
        </div>
      )}
    </div>
  );
}
