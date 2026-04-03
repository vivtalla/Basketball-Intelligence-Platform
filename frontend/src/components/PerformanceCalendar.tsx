"use client";

import { useState } from "react";
import { usePlayerGameLogs } from "@/hooks/usePlayerStats";
import type { GameLogEntry } from "@/lib/types";

type CalMetric = "pts" | "reb" | "ast" | "fg_pct" | "plus_minus";

interface MetricOption {
  key: CalMetric;
  label: string;
  format: (v: number) => string;
}

const METRIC_OPTIONS: MetricOption[] = [
  { key: "pts",        label: "PTS",  format: (v) => v.toFixed(0) },
  { key: "reb",        label: "REB",  format: (v) => v.toFixed(0) },
  { key: "ast",        label: "AST",  format: (v) => v.toFixed(0) },
  { key: "fg_pct",     label: "FG%",  format: (v) => `${(v * 100).toFixed(1)}%` },
  { key: "plus_minus", label: "+/-",  format: (v) => (v >= 0 ? `+${v.toFixed(0)}` : v.toFixed(0)) },
];

const GAMES_PER_ROW = 20;

// 5-tier color scale: elite → poor
const TIER_COLORS = ["#16a34a", "#86efac", "#d4d4d4", "#fca5a5", "#dc2626"];
const NULL_COLOR = "#e8e0d0";

function quantileThresholds(values: number[]): [number, number, number, number] {
  const sorted = [...values].sort((a, b) => a - b);
  const q = (p: number) => sorted[Math.max(0, Math.floor(p * sorted.length) - 1)] ?? 0;
  return [q(0.2), q(0.4), q(0.6), q(0.8)];
}

function calColor(
  value: number | null,
  thresholds: [number, number, number, number],
  isNegativeGood: boolean
): string {
  if (value === null) return NULL_COLOR;
  const [t1, t2, t3, t4] = thresholds;
  const cmp = isNegativeGood ? -value : value;
  const [ct1, ct2, ct3, ct4] = isNegativeGood
    ? [-t4, -t3, -t2, -t1]
    : [t1, t2, t3, t4];
  if (cmp >= ct4) return TIER_COLORS[0];
  if (cmp >= ct3) return TIER_COLORS[1];
  if (cmp >= ct2) return TIER_COLORS[2];
  if (cmp >= ct1) return TIER_COLORS[3];
  return TIER_COLORS[4];
}

function chunkGames(games: GameLogEntry[], size: number): GameLogEntry[][] {
  const rows: GameLogEntry[][] = [];
  for (let i = 0; i < games.length; i += size) {
    rows.push(games.slice(i, i + size));
  }
  return rows;
}

interface PerformanceCalendarProps {
  playerId: number;
  season: string | null;
}

export default function PerformanceCalendar({ playerId, season }: PerformanceCalendarProps) {
  const [metric, setMetric] = useState<CalMetric>("pts");

  const { data, isLoading } = usePlayerGameLogs(
    season ? playerId : null,
    season,
    "Regular Season"
  );

  const games = data?.games ?? [];
  const values = games.map((g) => g[metric]).filter((v): v is number => v !== null);
  const thresholds = values.length >= 4 ? quantileThresholds(values) : ([0, 0, 0, 0] as [number, number, number, number]);
  const isNegativeGood = false; // no metric here is negative-good

  const rows = chunkGames(games, GAMES_PER_ROW);
  const metricOpt = METRIC_OPTIONS.find((m) => m.key === metric)!;

  return (
    <div className="rounded-[2rem] border border-[var(--border)] bg-[linear-gradient(145deg,rgba(247,243,232,0.96),rgba(228,236,232,0.92))] p-6 shadow-[0_18px_48px_rgba(47,43,36,0.07)]">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
        <div>
          <p className="bip-kicker">Game-by-Game</p>
          <h3 className="mt-1 text-xl font-semibold text-[var(--foreground)]">Performance Calendar</h3>
        </div>
        <div className="flex rounded-lg overflow-hidden border border-[var(--border)] text-xs">
          {METRIC_OPTIONS.map((opt) => (
            <button
              key={opt.key}
              onClick={() => setMetric(opt.key)}
              className={`px-3 py-1.5 transition-colors ${
                metric === opt.key ? "bip-toggle-active" : "bip-toggle"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Calendar grid */}
      {isLoading ? (
        <div className="flex items-center justify-center h-24">
          <div className="w-7 h-7 border-2 border-[var(--accent)] border-t-transparent rounded-full animate-spin" />
        </div>
      ) : games.length === 0 ? (
        <p className="text-sm text-[var(--muted)] py-6 text-center">No game log data available for this season.</p>
      ) : (
        <div className="space-y-[3px] overflow-x-auto pb-1">
          {rows.map((rowGames, ri) => (
            <div key={ri} className="flex gap-[3px]">
              {rowGames.map((game) => {
                const val = game[metric];
                const color = calColor(val, thresholds, isNegativeGood);
                const fmtVal = val !== null ? metricOpt.format(val) : "—";
                const title = `${game.game_date} · ${game.matchup} · ${game.wl ?? ""}\n${metricOpt.label}: ${fmtVal}`;
                return (
                  <div
                    key={game.game_id}
                    title={title}
                    className="rounded-[3px] cursor-default shrink-0 transition-transform hover:scale-110"
                    style={{ width: 11, height: 11, backgroundColor: color }}
                  />
                );
              })}
            </div>
          ))}
        </div>
      )}

      {/* Legend */}
      {games.length > 0 && (
        <div className="flex flex-wrap items-center gap-4 mt-4 text-[10px] text-[var(--muted)]">
          {["Elite", "Good", "Avg", "Below", "Poor"].map((label, i) => (
            <span key={label} className="flex items-center gap-1">
              <span
                className="inline-block rounded-[2px] shrink-0"
                style={{ width: 10, height: 10, backgroundColor: TIER_COLORS[i] }}
              />
              {label}
            </span>
          ))}
          <span className="ml-auto">{games.length} games · hover for details</span>
        </div>
      )}
    </div>
  );
}
