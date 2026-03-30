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
  if (value == null) return <span className="text-[var(--muted)]">—</span>;
  const abs = Math.min(Math.abs(value), 20);
  const pct = (abs / 20) * 100;
  const positive = value >= 0;
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-16 flex-shrink-0 overflow-hidden rounded-full bg-[var(--surface-alt)]">
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
    <div className="px-5 py-4 transition-colors hover:bg-[rgba(216,228,221,0.24)]">
      <div className="flex items-start gap-4">
        {/* Rank */}
        <div className="w-6 flex-shrink-0 pt-0.5 text-xs tabular-nums text-[var(--muted)]">
          {rank}
        </div>

        {/* Player names */}
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap gap-x-2 gap-y-1">
            {lineup.player_names.map((name, i) => (
              <span
                key={i}
                className="text-sm text-[var(--foreground)]"
              >
                {name}
                {i < lineup.player_names.length - 1 && (
                  <span className="ml-2 text-[var(--muted)]/50">·</span>
                )}
              </span>
            ))}
          </div>
          <div className="mt-1 flex flex-wrap gap-3 text-xs text-[var(--muted)]">
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
    <div className="bip-table-shell overflow-hidden rounded-[2rem]">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--border)] px-6 py-5">
        <div>
          <h2 className="bip-display text-2xl font-semibold text-[var(--foreground)]">
            5-Man Lineups
          </h2>
          <p className="text-sm text-[var(--muted)]">
            {season} · Net rating by 5-man combination
          </p>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          {/* Min possessions filter */}
          <select
            value={minPoss}
            onChange={(e) => setMinPoss(Number(e.target.value))}
            className="bip-input rounded-xl px-3 py-1.5 text-sm"
          >
            <option value={10}>Min 10 poss</option>
            <option value={20}>Min 20 poss</option>
            <option value={50}>Min 50 poss</option>
            <option value={100}>Min 100 poss</option>
          </select>

          {/* Best / Worst toggle */}
          <div className="flex overflow-hidden rounded-xl border border-[var(--border)] text-sm">
            <button
              onClick={() => setView("best")}
              className={`px-4 py-1.5 transition-colors ${
                view === "best"
                  ? "bip-toggle-active"
                  : "bip-toggle"
              }`}
            >
              Best 10
            </button>
            <button
              onClick={() => setView("worst")}
              className={`px-4 py-1.5 transition-colors ${
                view === "worst"
                  ? "bg-[var(--danger-ink)] text-white"
                  : "bip-toggle"
              }`}
            >
              Worst 10
            </button>
          </div>
        </div>
      </div>

      {/* Column headers */}
      <div className="bip-table-head flex items-center gap-4 border-b border-[var(--border)] px-5 py-2">
        <div className="w-6 flex-shrink-0" />
        <div className="flex-1 text-xs uppercase tracking-wide">
          Players
        </div>
        <div className="flex-shrink-0 text-xs uppercase tracking-wide">
          Net Rtg
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="divide-y divide-[var(--border)]">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="px-5 py-4 animate-pulse flex gap-4">
              <div className="h-4 w-6 rounded bg-[var(--surface-alt)]" />
              <div className="flex-1 space-y-2">
                <div className="h-4 w-3/4 rounded bg-[var(--surface-alt)]" />
                <div className="h-3 w-1/3 rounded bg-[var(--surface-alt)]" />
              </div>
              <div className="h-4 w-24 rounded bg-[var(--surface-alt)]" />
            </div>
          ))}
        </div>
      )}

      {/* Error */}
      {error && !isLoading && (
        <div className="px-6 py-10 text-center text-sm text-[var(--muted)]">
          Could not load lineup data. Make sure play-by-play data has been synced for this team.
        </div>
      )}

      {/* Empty */}
      {!isLoading && !error && displayed.length === 0 && (
        <div className="px-6 py-10 text-center text-sm text-[var(--muted)]">
          No lineups with {minPoss}+ possessions found for {season}.{" "}
          <span className="text-[var(--accent)]">Try lowering the minimum possessions filter.</span>
        </div>
      )}

      {/* Lineup rows */}
      {!isLoading && displayed.length > 0 && (
        <div className="divide-y divide-[var(--border)]">
          {displayed.map((lineup, i) => (
            <LineupRow key={lineup.lineup_key} lineup={lineup} rank={i + 1} />
          ))}
        </div>
      )}

      {/* Footer note */}
      {!isLoading && displayed.length > 0 && (
        <div className="border-t border-[var(--border)] px-6 py-3 text-xs text-[var(--muted)]">
          Net rating = (ORTG − DRTG) per 100 possessions · Requires play-by-play sync ·{" "}
          <Link href="/learn" className="bip-link">
            Learn more
          </Link>
        </div>
      )}
    </div>
  );
}
