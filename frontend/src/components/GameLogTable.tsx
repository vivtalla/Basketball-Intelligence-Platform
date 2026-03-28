"use client";

import { useState, useMemo } from "react";
import { usePlayerGameLogs } from "@/hooks/usePlayerStats";
import type { GameLogEntry } from "@/lib/types";

interface GameLogTableProps {
  playerId: number;
  season: string | null;
}

type SortKey = "game_date" | "pts" | "reb" | "ast" | "stl" | "blk" | "tov" | "fg_pct" | "fg3_pct" | "min" | "plus_minus";

function fmtPct(v: number | null): string {
  if (v == null) return "-";
  return `${(v * 100).toFixed(1)}%`;
}

function fmtNum(v: number | null, digits = 0): string {
  if (v == null) return "-";
  return v.toFixed(digits);
}

function fmtSigned(v: number | null): string {
  if (v == null) return "-";
  return `${v > 0 ? "+" : ""}${v}`;
}

/** Tiny inline sparkline — renders a bar proportional to value vs. max. */
function Sparkline({ value, max, colorClass }: { value: number | null; max: number; colorClass: string }) {
  if (value == null || max === 0) return <div className="w-12 h-1.5 bg-gray-100 dark:bg-gray-700 rounded-full" />;
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="w-12 h-1.5 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
      <div className={`h-full rounded-full ${colorClass}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

function SortableHeader({
  label,
  sortKey,
  current,
  dir,
  onSort,
  className = "",
}: {
  label: string;
  sortKey: SortKey;
  current: SortKey;
  dir: "asc" | "desc";
  onSort: (k: SortKey) => void;
  className?: string;
}) {
  const active = current === sortKey;
  return (
    <th
      className={`text-right text-xs font-semibold uppercase tracking-wider px-3 py-3 cursor-pointer select-none whitespace-nowrap ${
        active
          ? "text-blue-500 dark:text-blue-400"
          : "text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300"
      } ${className}`}
      onClick={() => onSort(sortKey)}
    >
      {label}
      {active && <span className="ml-0.5 text-xs">{dir === "desc" ? "↓" : "↑"}</span>}
    </th>
  );
}

export default function GameLogTable({ playerId, season }: GameLogTableProps) {
  const [seasonType, setSeasonType] = useState<"Regular Season" | "Playoffs">("Regular Season");
  const [sortKey, setSortKey] = useState<SortKey>("game_date");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [showLast, setShowLast] = useState<number | "all">(20);

  const { data, error, isLoading } = usePlayerGameLogs(playerId, season, seasonType);

  const sorted = useMemo(() => {
    if (!data?.games) return [];
    const games = [...data.games];
    games.sort((a, b) => {
      const av = a[sortKey as keyof GameLogEntry];
      const bv = b[sortKey as keyof GameLogEntry];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      const cmp = av < bv ? -1 : av > bv ? 1 : 0;
      return sortDir === "desc" ? -cmp : cmp;
    });
    return games;
  }, [data, sortKey, sortDir]);

  const displayed = showLast === "all" ? sorted : sorted.slice(0, showLast);

  const maxPts = useMemo(() => Math.max(...(data?.games.map((g) => g.pts ?? 0) ?? [0])), [data]);
  const maxReb = useMemo(() => Math.max(...(data?.games.map((g) => g.reb ?? 0) ?? [0])), [data]);
  const maxAst = useMemo(() => Math.max(...(data?.games.map((g) => g.ast ?? 0) ?? [0])), [data]);

  function handleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === "desc" ? "asc" : "desc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  if (!season) return null;

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Game Log</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {data ? `${data.gp} games · ${season}` : season}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Season type toggle */}
          <div className="flex rounded-lg overflow-hidden border border-gray-200 dark:border-gray-600 text-sm">
            {(["Regular Season", "Playoffs"] as const).map((type) => (
              <button
                key={type}
                onClick={() => setSeasonType(type)}
                className={`px-3 py-1.5 transition-colors ${
                  seasonType === type
                    ? "bg-blue-500 text-white"
                    : "bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700"
                }`}
              >
                {type === "Regular Season" ? "Regular" : "Playoffs"}
              </button>
            ))}
          </div>

          {/* Show N games selector */}
          <select
            value={String(showLast)}
            onChange={(e) => setShowLast(e.target.value === "all" ? "all" : Number(e.target.value))}
            className="text-sm border border-gray-200 dark:border-gray-600 rounded-lg px-2 py-1.5 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
          >
            <option value="10">Last 10</option>
            <option value="20">Last 20</option>
            <option value="all">All games</option>
          </select>
        </div>
      </div>

      {/* Season averages summary bar */}
      {data?.season_averages && (
        <div className="grid grid-cols-4 sm:grid-cols-7 gap-2">
          {[
            { label: "PTS", value: fmtNum(data.season_averages.pts, 1) },
            { label: "REB", value: fmtNum(data.season_averages.reb, 1) },
            { label: "AST", value: fmtNum(data.season_averages.ast, 1) },
            { label: "STL", value: fmtNum(data.season_averages.stl, 1) },
            { label: "BLK", value: fmtNum(data.season_averages.blk, 1) },
            { label: "FG%", value: fmtPct(data.season_averages.fg_pct) },
            { label: "+/-", value: fmtSigned(data.season_averages.plus_minus) },
          ].map(({ label, value }) => (
            <div key={label} className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-2 text-center">
              <div className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">{label}</div>
              <div className="text-base font-semibold tabular-nums text-gray-900 dark:text-gray-100">{value}</div>
            </div>
          ))}
        </div>
      )}

      <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        {isLoading && (
          <div className="divide-y divide-gray-100 dark:divide-gray-700/50">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="flex gap-4 px-4 py-3 animate-pulse">
                <div className="h-4 w-24 bg-gray-200 dark:bg-gray-700 rounded" />
                <div className="h-4 w-28 bg-gray-200 dark:bg-gray-700 rounded" />
                <div className="ml-auto flex gap-4">
                  {[1, 2, 3, 4].map((j) => (
                    <div key={j} className="h-4 w-8 bg-gray-200 dark:bg-gray-700 rounded" />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {error && (
          <div className="p-6 text-center text-sm text-gray-400 dark:text-gray-500">
            {seasonType === "Playoffs"
              ? "No playoff data available for this season."
              : "Could not load game logs."}
          </div>
        )}

        {!isLoading && !error && displayed.length === 0 && (
          <div className="p-6 text-center text-sm text-gray-400 dark:text-gray-500">
            No games found.
          </div>
        )}

        {!isLoading && !error && displayed.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="text-left text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-4 py-3 whitespace-nowrap">Date</th>
                  <th className="text-left text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-3 py-3">Matchup</th>
                  <th className="text-center text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-3 py-3">W/L</th>
                  <SortableHeader label="MIN" sortKey="min" current={sortKey} dir={sortDir} onSort={handleSort} />
                  <SortableHeader label="PTS" sortKey="pts" current={sortKey} dir={sortDir} onSort={handleSort} />
                  <SortableHeader label="REB" sortKey="reb" current={sortKey} dir={sortDir} onSort={handleSort} />
                  <SortableHeader label="AST" sortKey="ast" current={sortKey} dir={sortDir} onSort={handleSort} />
                  <SortableHeader label="STL" sortKey="stl" current={sortKey} dir={sortDir} onSort={handleSort} className="hidden sm:table-cell" />
                  <SortableHeader label="BLK" sortKey="blk" current={sortKey} dir={sortDir} onSort={handleSort} className="hidden sm:table-cell" />
                  <SortableHeader label="TOV" sortKey="tov" current={sortKey} dir={sortDir} onSort={handleSort} className="hidden sm:table-cell" />
                  <SortableHeader label="FG%" sortKey="fg_pct" current={sortKey} dir={sortDir} onSort={handleSort} className="hidden md:table-cell" />
                  <SortableHeader label="3P%" sortKey="fg3_pct" current={sortKey} dir={sortDir} onSort={handleSort} className="hidden md:table-cell" />
                  <SortableHeader label="+/-" sortKey="plus_minus" current={sortKey} dir={sortDir} onSort={handleSort} />
                </tr>
              </thead>
              <tbody>
                {displayed.map((game) => {
                  const isWin = game.wl === "W";
                  const pmColor =
                    (game.plus_minus ?? 0) > 0
                      ? "text-green-600 dark:text-green-400"
                      : (game.plus_minus ?? 0) < 0
                      ? "text-red-500 dark:text-red-400"
                      : "text-gray-500 dark:text-gray-400";

                  return (
                    <tr
                      key={game.game_id}
                      className="border-b border-gray-100 dark:border-gray-700/50 last:border-0 hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors"
                    >
                      <td className="px-4 py-2.5 text-gray-500 dark:text-gray-400 whitespace-nowrap tabular-nums text-xs">
                        {game.game_date}
                      </td>
                      <td className="px-3 py-2.5 text-gray-700 dark:text-gray-300 whitespace-nowrap text-xs">
                        {game.matchup}
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        <span className={`text-xs font-semibold ${isWin ? "text-green-600 dark:text-green-400" : "text-red-500 dark:text-red-400"}`}>
                          {game.wl}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 text-right tabular-nums text-gray-600 dark:text-gray-400">
                        {fmtNum(game.min, 0)}
                      </td>
                      {/* PTS with sparkline */}
                      <td className="px-3 py-2.5 text-right">
                        <div className="flex flex-col items-end gap-0.5">
                          <span className="tabular-nums font-semibold text-gray-900 dark:text-gray-100">{fmtNum(game.pts)}</span>
                          <Sparkline value={game.pts} max={maxPts} colorClass="bg-blue-400" />
                        </div>
                      </td>
                      {/* REB with sparkline */}
                      <td className="px-3 py-2.5 text-right">
                        <div className="flex flex-col items-end gap-0.5">
                          <span className="tabular-nums text-gray-700 dark:text-gray-300">{fmtNum(game.reb)}</span>
                          <Sparkline value={game.reb} max={maxReb} colorClass="bg-emerald-400" />
                        </div>
                      </td>
                      {/* AST with sparkline */}
                      <td className="px-3 py-2.5 text-right">
                        <div className="flex flex-col items-end gap-0.5">
                          <span className="tabular-nums text-gray-700 dark:text-gray-300">{fmtNum(game.ast)}</span>
                          <Sparkline value={game.ast} max={maxAst} colorClass="bg-violet-400" />
                        </div>
                      </td>
                      <td className="px-3 py-2.5 text-right tabular-nums text-gray-600 dark:text-gray-400 hidden sm:table-cell">{fmtNum(game.stl)}</td>
                      <td className="px-3 py-2.5 text-right tabular-nums text-gray-600 dark:text-gray-400 hidden sm:table-cell">{fmtNum(game.blk)}</td>
                      <td className="px-3 py-2.5 text-right tabular-nums text-gray-600 dark:text-gray-400 hidden sm:table-cell">{fmtNum(game.tov)}</td>
                      <td className="px-3 py-2.5 text-right tabular-nums text-gray-500 dark:text-gray-400 hidden md:table-cell">{fmtPct(game.fg_pct)}</td>
                      <td className="px-3 py-2.5 text-right tabular-nums text-gray-500 dark:text-gray-400 hidden md:table-cell">{fmtPct(game.fg3_pct)}</td>
                      <td className={`px-3 py-2.5 text-right tabular-nums font-semibold ${pmColor}`}>
                        {fmtSigned(game.plus_minus)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {!isLoading && !error && data && showLast !== "all" && data.gp > (showLast as number) && (
          <div className="px-4 py-3 border-t border-gray-100 dark:border-gray-700/50 text-center">
            <button
              onClick={() => setShowLast("all")}
              className="text-sm text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300"
            >
              Show all {data.gp} games
            </button>
          </div>
        )}
      </div>
    </section>
  );
}
