"use client";

import { useState, useMemo } from "react";
import { usePlayerGameLogs } from "@/hooks/usePlayerStats";
import type { GameLogEntry } from "@/lib/types";

interface SeasonSplitsProps {
  playerId: number;
  season: string | null;
}

// NBA season months in display order
const MONTH_ORDER = ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun"];

type StatKey = "pts" | "reb" | "ast";
const STAT_LABELS: Record<StatKey, string> = { pts: "PPG", reb: "RPG", ast: "APG" };
const STAT_COLORS: Record<StatKey, string> = {
  pts: "bg-blue-500",
  reb: "bg-emerald-500",
  ast: "bg-amber-500",
};

function avg(games: GameLogEntry[], key: StatKey): number | null {
  const vals = games.map((g) => g[key]).filter((v): v is number => v != null);
  if (vals.length === 0) return null;
  return vals.reduce((a, b) => a + b, 0) / vals.length;
}

function avgFgPct(games: GameLogEntry[]): number | null {
  const made = games.reduce((s, g) => s + (g.fgm ?? 0), 0);
  const att = games.reduce((s, g) => s + (g.fga ?? 0), 0);
  return att > 0 ? made / att : null;
}

function avgFg3Pct(games: GameLogEntry[]): number | null {
  const made = games.reduce((s, g) => s + (g.fg3m ?? 0), 0);
  const att = games.reduce((s, g) => s + (g.fg3a ?? 0), 0);
  return att > 0 ? made / att : null;
}

function avgPlusMinus(games: GameLogEntry[]): number | null {
  const vals = games.map((g) => g.plus_minus).filter((v): v is number => v != null);
  if (vals.length === 0) return null;
  return vals.reduce((a, b) => a + b, 0) / vals.length;
}

function fmt(v: number | null, digits = 1): string {
  return v == null ? "—" : v.toFixed(digits);
}

function fmtPct(v: number | null): string {
  return v == null ? "—" : `${(v * 100).toFixed(1)}%`;
}

function monthLabel(dateStr: string): string {
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleString("en-US", { month: "short" });
}

// Best and worst 5-game windows by avg PPG
function findStreak(games: GameLogEntry[], mode: "best" | "worst") {
  if (games.length < 5) return null;
  let bestIdx = 0;
  let bestAvg = mode === "best" ? -Infinity : Infinity;

  for (let i = 0; i <= games.length - 5; i++) {
    const window = games.slice(i, i + 5);
    const a = avg(window, "pts") ?? 0;
    if ((mode === "best" && a > bestAvg) || (mode === "worst" && a < bestAvg)) {
      bestAvg = a;
      bestIdx = i;
    }
  }

  const window = games.slice(bestIdx, bestIdx + 5);
  return {
    games: window,
    pts: avg(window, "pts"),
    reb: avg(window, "reb"),
    ast: avg(window, "ast"),
    startDate: window[0].game_date,
    endDate: window[window.length - 1].game_date,
  };
}

interface StatRowProps {
  label: string;
  first: number | null;
  second: number | null;
  formatFn?: (v: number | null) => string;
  higherIsBetter?: boolean;
}

function StatRow({ label, first, second, formatFn = fmt, higherIsBetter = true }: StatRowProps) {
  const diff = first != null && second != null ? second - first : null;
  const improved = diff != null && (higherIsBetter ? diff > 0.05 : diff < -0.05);
  const declined = diff != null && (higherIsBetter ? diff < -0.05 : diff > 0.05);

  return (
    <div className="flex items-center justify-between py-1.5 border-b border-gray-50 dark:border-gray-700/50 last:border-0 text-sm">
      <span className="text-gray-500 dark:text-gray-400 w-16">{label}</span>
      <span className="tabular-nums text-gray-700 dark:text-gray-300 w-14 text-center">
        {formatFn(first)}
      </span>
      <div className="flex items-center gap-1 w-20 justify-end">
        <span className={`tabular-nums font-medium ${
          improved ? "text-emerald-600 dark:text-emerald-400" :
          declined ? "text-red-500 dark:text-red-400" :
          "text-gray-700 dark:text-gray-300"
        }`}>
          {formatFn(second)}
        </span>
        {diff != null && Math.abs(diff) > 0.05 && (
          <span className={`text-xs ${improved ? "text-emerald-500" : declined ? "text-red-400" : "text-gray-400"}`}>
            {improved ? "↑" : declined ? "↓" : ""}
          </span>
        )}
      </div>
    </div>
  );
}

export default function SeasonSplits({ playerId, season }: SeasonSplitsProps) {
  const [activeStat, setActiveStat] = useState<StatKey>("pts");
  const { data } = usePlayerGameLogs(playerId, season, "Regular Season");

  const games = useMemo(
    () => (data?.games ?? []).slice().sort((a, b) => a.game_date.localeCompare(b.game_date)),
    [data]
  );

  // Need at least 10 games to show splits
  if (!data || games.length < 10) return null;

  // Monthly groupings
  const byMonth = useMemo(() => {
    const map: Record<string, GameLogEntry[]> = {};
    for (const g of games) {
      const m = monthLabel(g.game_date);
      if (!map[m]) map[m] = [];
      map[m].push(g);
    }
    return map;
  }, [games]);

  const months = MONTH_ORDER.filter((m) => byMonth[m]);

  // Monthly averages for active stat
  const monthlyAvgs = months.map((m) => ({
    month: m,
    value: avg(byMonth[m], activeStat),
    gp: byMonth[m].length,
  }));

  // Bar scale
  const maxVal = Math.max(...monthlyAvgs.map((m) => m.value ?? 0), 1);

  // Season average for reference line
  const seasonAvg = avg(games, activeStat);

  // First / second half split
  const midpoint = Math.floor(games.length / 2);
  const firstHalf = games.slice(0, midpoint);
  const secondHalf = games.slice(midpoint);

  // Best / worst 5-game stretches
  const bestStreak = findStreak(games, "best");
  const worstStreak = findStreak(games, "worst");

  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 p-6 space-y-7">
      <h3 className="font-semibold text-gray-900 dark:text-gray-100">Season Splits</h3>

      {/* ── Monthly trend ── */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">
            Monthly Averages
          </p>
          <div className="flex gap-1">
            {(Object.keys(STAT_LABELS) as StatKey[]).map((k) => (
              <button
                key={k}
                onClick={() => setActiveStat(k)}
                className={`px-2.5 py-1 rounded-full text-xs transition-colors ${
                  activeStat === k
                    ? "text-white bg-blue-500"
                    : "text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300"
                }`}
              >
                {STAT_LABELS[k]}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-end gap-2 h-28">
          {monthlyAvgs.map(({ month, value, gp }) => {
            const barPct = value != null ? (value / maxVal) * 100 : 0;
            const aboveAvg = value != null && seasonAvg != null && value >= seasonAvg - 0.5;
            return (
              <div key={month} className="flex-1 flex flex-col items-center gap-1">
                {/* Value label */}
                <span className="text-[10px] tabular-nums text-gray-500 dark:text-gray-400">
                  {value != null ? value.toFixed(1) : "—"}
                </span>
                {/* Bar */}
                <div className="w-full flex flex-col justify-end" style={{ height: "72px" }}>
                  <div
                    className={`w-full rounded-t-md transition-all ${aboveAvg ? STAT_COLORS[activeStat] : "bg-gray-300 dark:bg-gray-600"}`}
                    style={{ height: `${barPct}%`, minHeight: value != null ? 4 : 0 }}
                    title={`${month}: ${value?.toFixed(1)} ${STAT_LABELS[activeStat]} (${gp}G)`}
                  />
                </div>
                {/* Month label */}
                <span className="text-[10px] text-gray-400 dark:text-gray-500">{month}</span>
              </div>
            );
          })}
        </div>

        {/* Reference line annotation */}
        {seasonAvg != null && (
          <p className="text-[10px] text-gray-400 dark:text-gray-500 mt-1 text-center">
            Season avg: {seasonAvg.toFixed(1)} {STAT_LABELS[activeStat]} ·{" "}
            colored bars = at or above avg
          </p>
        )}
      </div>

      {/* ── First half / Second half ── */}
      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-3">
          First Half vs Second Half
        </p>
        <div className="grid grid-cols-3 gap-x-3 mb-2">
          <div className="text-xs text-gray-400 dark:text-gray-500" />
          <div className="text-xs font-medium text-center text-gray-500 dark:text-gray-400">
            First {firstHalf.length}G
          </div>
          <div className="text-xs font-medium text-right text-gray-500 dark:text-gray-400">
            Last {secondHalf.length}G
          </div>
        </div>
        <StatRow label="PTS" first={avg(firstHalf, "pts")} second={avg(secondHalf, "pts")} />
        <StatRow label="REB" first={avg(firstHalf, "reb")} second={avg(secondHalf, "reb")} />
        <StatRow label="AST" first={avg(firstHalf, "ast")} second={avg(secondHalf, "ast")} />
        <StatRow
          label="FG%"
          first={avgFgPct(firstHalf)}
          second={avgFgPct(secondHalf)}
          formatFn={fmtPct}
        />
        <StatRow
          label="3P%"
          first={avgFg3Pct(firstHalf)}
          second={avgFg3Pct(secondHalf)}
          formatFn={fmtPct}
        />
        <StatRow
          label="+/-"
          first={avgPlusMinus(firstHalf)}
          second={avgPlusMinus(secondHalf)}
        />
      </div>

      {/* ── Hot / Cold streaks ── */}
      {(bestStreak || worstStreak) && (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-3">
            5-Game Peaks
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {bestStreak && (
              <div className="rounded-xl border border-emerald-200 dark:border-emerald-900/60 bg-emerald-50 dark:bg-emerald-950/30 p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-300 uppercase tracking-wide">
                    Hot streak
                  </span>
                  <span className="text-[10px] text-emerald-600/70 dark:text-emerald-400/70">
                    {bestStreak.startDate} – {bestStreak.endDate}
                  </span>
                </div>
                <div className="flex gap-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-emerald-700 dark:text-emerald-300 tabular-nums">
                      {fmt(bestStreak.pts)}
                    </div>
                    <div className="text-[10px] text-emerald-600/70 dark:text-emerald-400/70 uppercase">PPG</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-emerald-700 dark:text-emerald-300 tabular-nums">
                      {fmt(bestStreak.reb)}
                    </div>
                    <div className="text-[10px] text-emerald-600/70 dark:text-emerald-400/70 uppercase">RPG</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-emerald-700 dark:text-emerald-300 tabular-nums">
                      {fmt(bestStreak.ast)}
                    </div>
                    <div className="text-[10px] text-emerald-600/70 dark:text-emerald-400/70 uppercase">APG</div>
                  </div>
                </div>
              </div>
            )}

            {worstStreak && (
              <div className="rounded-xl border border-red-200 dark:border-red-900/60 bg-red-50 dark:bg-red-950/30 p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-semibold text-red-600 dark:text-red-400 uppercase tracking-wide">
                    Cold stretch
                  </span>
                  <span className="text-[10px] text-red-500/70 dark:text-red-400/70">
                    {worstStreak.startDate} – {worstStreak.endDate}
                  </span>
                </div>
                <div className="flex gap-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-red-600 dark:text-red-400 tabular-nums">
                      {fmt(worstStreak.pts)}
                    </div>
                    <div className="text-[10px] text-red-500/70 dark:text-red-400/70 uppercase">PPG</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-red-600 dark:text-red-400 tabular-nums">
                      {fmt(worstStreak.reb)}
                    </div>
                    <div className="text-[10px] text-red-500/70 dark:text-red-400/70 uppercase">RPG</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-red-600 dark:text-red-400 tabular-nums">
                      {fmt(worstStreak.ast)}
                    </div>
                    <div className="text-[10px] text-red-500/70 dark:text-red-400/70 uppercase">APG</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
