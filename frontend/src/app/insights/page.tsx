"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import { useBreakouts } from "@/hooks/usePlayerStats";
import type { BreakoutEntry } from "@/lib/types";

const DEFAULT_SEASON = "2024-25";

type Mode = "improvers" | "decliners";

function signed(v: number | null, digits = 1, isPercent = false): string {
  if (v == null) return "—";
  const formatted = isPercent
    ? `${(v * 100).toFixed(digits)}%`
    : v.toFixed(digits);
  return v > 0 ? `+${formatted}` : formatted;
}

function deltaColor(v: number | null, lowerIsBetter = false): string {
  if (v == null) return "text-gray-400 dark:text-gray-500";
  const positive = lowerIsBetter ? v < 0 : v > 0;
  return positive
    ? "text-emerald-600 dark:text-emerald-400"
    : "text-red-500 dark:text-red-400";
}

interface StatBarProps {
  label: string;
  prior: number | null;
  current: number | null;
  max: number;
  isPercent?: boolean;
}

function StatBar({ label, prior, current, max, isPercent }: StatBarProps) {
  if (prior == null || current == null) return null;
  const fmt = (v: number) =>
    isPercent ? `${(v * 100).toFixed(1)}%` : v.toFixed(1);
  const priorPct = Math.min(100, (Math.abs(prior) / max) * 100);
  const curPct = Math.min(100, (Math.abs(current) / max) * 100);
  const improved = current > prior;

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-500 uppercase tracking-wide">
        <span>{label}</span>
        <span className={deltaColor(current - prior)}>
          {signed(current - prior, 1, isPercent)}
        </span>
      </div>
      <div className="relative h-4 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
        {/* Prior bar */}
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-gray-300 dark:bg-gray-600"
          style={{ width: `${priorPct}%` }}
        />
        {/* Current bar overlay */}
        <div
          className={`absolute inset-y-0 left-0 rounded-full transition-all ${
            improved ? "bg-emerald-500" : "bg-red-400"
          }`}
          style={{ width: `${curPct}%` }}
        />
      </div>
      <div className="flex justify-between text-[10px] tabular-nums text-gray-500 dark:text-gray-400">
        <span className="text-gray-400">{fmt(prior)}</span>
        <span className={improved ? "text-emerald-600 dark:text-emerald-400 font-medium" : "text-red-500 dark:text-red-400 font-medium"}>
          {fmt(current)}
        </span>
      </div>
    </div>
  );
}

function BreakoutCard({ entry, mode }: { entry: BreakoutEntry; mode: Mode }) {
  const isImproving = mode === "improvers";

  return (
    <div className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden hover:border-blue-400 dark:hover:border-blue-500 hover:shadow-sm transition-all">
      {/* Header */}
      <div className="flex items-center gap-3 p-4 border-b border-gray-100 dark:border-gray-700/60">
        <div className="relative w-12 h-12 rounded-full overflow-hidden bg-gray-100 dark:bg-gray-700 shrink-0">
          {entry.headshot_url && (
            <Image
              src={entry.headshot_url}
              alt={entry.full_name}
              fill
              className="object-cover object-top"
              onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
            />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <Link
            href={`/players/${entry.player_id}`}
            className="font-semibold text-gray-900 dark:text-gray-100 hover:text-blue-500 dark:hover:text-blue-400 transition-colors truncate block"
          >
            {entry.full_name}
          </Link>
          <div className="text-xs text-gray-400 dark:text-gray-500">
            {entry.current.team_abbreviation} · {entry.prior.season} → {entry.current.season} · {entry.current.gp}G
          </div>
        </div>
        {/* Score badge */}
        <div className={`shrink-0 rounded-xl px-3 py-1.5 text-center ${
          isImproving ? "bg-emerald-50 dark:bg-emerald-950/40" : "bg-red-50 dark:bg-red-950/40"
        }`}>
          <div className={`text-xs uppercase tracking-wide font-medium ${
            isImproving ? "text-emerald-600 dark:text-emerald-400" : "text-red-500 dark:text-red-400"
          }`}>
            {isImproving ? "↑ Rise" : "↓ Drop"}
          </div>
          <div className={`text-lg font-bold tabular-nums ${
            isImproving ? "text-emerald-700 dark:text-emerald-300" : "text-red-600 dark:text-red-300"
          }`}>
            {Math.abs(entry.improvement_score - 50).toFixed(0)}
          </div>
        </div>
      </div>

      {/* Key delta pills */}
      <div className="flex flex-wrap gap-2 px-4 py-3 border-b border-gray-100 dark:border-gray-700/60">
        {[
          { label: "PER", val: entry.delta_per },
          { label: "BPM", val: entry.delta_bpm },
          { label: "PTS", val: entry.delta_pts_pg },
          { label: "TS%", val: entry.delta_ts_pct, pct: true },
          { label: "AST", val: entry.delta_ast_pg },
          { label: "REB", val: entry.delta_reb_pg },
        ].filter(d => d.val != null).map(({ label, val, pct }) => (
          <div
            key={label}
            className={`flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${
              (val ?? 0) > 0
                ? "bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-300"
                : "bg-red-50 dark:bg-red-950/30 text-red-600 dark:text-red-300"
            }`}
          >
            <span className="text-gray-400 dark:text-gray-500">{label}</span>
            <span>{signed(val ?? null, 1, pct)}</span>
          </div>
        ))}
      </div>

      {/* Before/after stat bars */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-3 px-4 py-3">
        <StatBar label="PER" prior={entry.prior.per} current={entry.current.per} max={35} />
        <StatBar label="BPM" prior={entry.prior.bpm} current={entry.current.bpm} max={10} />
        <StatBar label="PPG" prior={entry.prior.pts_pg} current={entry.current.pts_pg} max={40} />
        <StatBar label="TS%" prior={entry.prior.ts_pct} current={entry.current.ts_pct} max={0.8} isPercent />
      </div>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {Array.from({ length: 9 }).map((_, i) => (
        <div key={i} className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 animate-pulse space-y-3">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-gray-200 dark:bg-gray-700" />
            <div className="flex-1 space-y-2">
              <div className="h-3.5 w-32 rounded bg-gray-200 dark:bg-gray-700" />
              <div className="h-3 w-24 rounded bg-gray-200 dark:bg-gray-700" />
            </div>
            <div className="w-14 h-12 rounded-xl bg-gray-200 dark:bg-gray-700" />
          </div>
          <div className="flex gap-2">
            {[1,2,3,4].map(j => <div key={j} className="h-5 w-14 rounded-full bg-gray-200 dark:bg-gray-700" />)}
          </div>
          <div className="space-y-2">
            {[1,2,3,4].map(j => <div key={j} className="h-8 rounded bg-gray-200 dark:bg-gray-700" />)}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function InsightsPage() {
  const [season, setSeason] = useState(DEFAULT_SEASON);
  const [mode, setMode] = useState<Mode>("improvers");
  const [minGp, setMinGp] = useState(20);

  const { data, isLoading, error } = useBreakouts(season, minGp, 25);

  const entries = data ? data[mode] : [];

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.24em] text-blue-500 mb-1">
            Discovery
          </p>
          <h1 className="text-4xl font-bold text-gray-900 dark:text-gray-100">
            Breakout Tracker
          </h1>
          <p className="mt-2 text-gray-500 dark:text-gray-400 max-w-xl">
            Players whose statistical profile changed most dramatically year-over-year.
            Ranked by weighted z-score improvement across PER, BPM, TS%, PPG, AST, REB.
          </p>
          {data && (
            <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">
              Comparing {data.prior_season} → {data.season} · min {minGp} games played
            </p>
          )}
        </div>

        {/* Controls */}
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={minGp}
            onChange={(e) => setMinGp(Number(e.target.value))}
            className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value={10}>Min 10 GP</option>
            <option value={20}>Min 20 GP</option>
            <option value={30}>Min 30 GP</option>
            <option value={41}>Min 41 GP</option>
          </select>
          <select
            value={season}
            onChange={(e) => setSeason(e.target.value)}
            className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {["2024-25", "2023-24", "2022-23", "2021-22", "2020-21"].map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Mode toggle */}
      <div className="flex rounded-xl overflow-hidden border border-gray-200 dark:border-gray-700 w-fit text-sm">
        <button
          onClick={() => setMode("improvers")}
          className={`px-5 py-2 transition-colors ${
            mode === "improvers"
              ? "bg-emerald-500 text-white"
              : "bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700"
          }`}
        >
          Most Improved
        </button>
        <button
          onClick={() => setMode("decliners")}
          className={`px-5 py-2 transition-colors ${
            mode === "decliners"
              ? "bg-red-500 text-white"
              : "bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700"
          }`}
        >
          Biggest Declines
        </button>
      </div>

      {isLoading && <LoadingSkeleton />}

      {error && (
        <div className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-8 text-center text-gray-500 dark:text-gray-400">
          Could not load breakout data. Make sure the backend is running and players are synced.
        </div>
      )}

      {!isLoading && !error && entries.length === 0 && (
        <div className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-8 text-center text-gray-500 dark:text-gray-400">
          Not enough players with stats in both {data?.prior_season} and {data?.season}.
          Try syncing more players or lowering the min games threshold.
        </div>
      )}

      {!isLoading && entries.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {entries.map((entry) => (
            <BreakoutCard key={entry.player_id} entry={entry} mode={mode} />
          ))}
        </div>
      )}
    </div>
  );
}
