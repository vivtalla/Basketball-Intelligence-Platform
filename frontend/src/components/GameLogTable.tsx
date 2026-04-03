"use client";

import Link from "next/link";
import { useState, useMemo } from "react";
import { usePlayerGameLogs } from "@/hooks/usePlayerStats";
import type { GameLogEntry } from "@/lib/types";
import ChartStatusBadge from "./ChartStatusBadge";

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
  if (value == null || max === 0) return <div className="h-1.5 w-12 rounded-full bg-[var(--surface-alt)]" />;
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="h-1.5 w-12 overflow-hidden rounded-full bg-[var(--surface-alt)]">
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
          ? "text-[var(--accent)]"
          : "text-[var(--muted)] hover:text-[var(--foreground)]"
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
          <h2 className="bip-display text-lg font-semibold text-[var(--foreground)]">Game Log</h2>
          <p className="text-sm text-[var(--muted)]">
            {data ? `${data.gp} games · ${season}` : season}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {data && <ChartStatusBadge status={data.data_status} compact />}
          {/* Season type toggle */}
          <div className="flex overflow-hidden rounded-lg border border-[var(--border)] text-sm">
            {(["Regular Season", "Playoffs"] as const).map((type) => (
              <button
                key={type}
                onClick={() => setSeasonType(type)}
                className={`px-3 py-1.5 transition-colors ${
                  seasonType === type
                    ? "bip-toggle-active"
                    : "bip-toggle"
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
            className="bip-input rounded-lg px-2 py-1.5 text-sm"
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
            <div key={label} className="bip-metric rounded-lg p-2 text-center">
              <div className="text-xs uppercase tracking-wide text-[var(--muted)]">{label}</div>
              <div className="text-base font-semibold tabular-nums text-[var(--foreground)]">{value}</div>
            </div>
          ))}
        </div>
      )}

      <div className="bip-table-shell overflow-hidden rounded-2xl">
        {isLoading && (
          <div className="divide-y divide-[var(--border)]">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="flex gap-4 px-4 py-3 animate-pulse">
                <div className="h-4 w-24 rounded bg-[var(--surface-alt)]" />
                <div className="h-4 w-28 rounded bg-[var(--surface-alt)]" />
                <div className="ml-auto flex gap-4">
                  {[1, 2, 3, 4].map((j) => (
                    <div key={j} className="h-4 w-8 rounded bg-[var(--surface-alt)]" />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {error && (
          <div className="p-6 text-center text-sm text-[var(--muted)]">
            {seasonType === "Playoffs"
              ? "No playoff data available for this season."
              : "Could not load game logs."}
          </div>
        )}

        {!isLoading && !error && displayed.length === 0 && (
          <div className="p-6 text-center text-sm text-[var(--muted)]">
            {data?.data_status === "missing"
              ? "Game logs have not been synced for this player-season yet."
              : "No games found."}
          </div>
        )}

        {!isLoading && !error && displayed.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bip-table-head border-b border-[var(--border)]">
                  <th className="whitespace-nowrap px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider">Date</th>
                  <th className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wider">Matchup</th>
                  <th className="px-3 py-3 text-center text-xs font-semibold uppercase tracking-wider">W/L</th>
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
                      : "text-[var(--muted)]";

                  return (
                    <tr
                      key={game.game_id}
                      className="border-b border-[var(--border)] transition-colors last:border-0 hover:bg-[rgba(216,228,221,0.22)]"
                    >
                      <td className="whitespace-nowrap px-4 py-2.5 text-xs tabular-nums text-[var(--muted)]">
                        <Link
                          href={`/games/${game.game_id}`}
                          className="font-medium text-[var(--foreground)] transition-colors hover:text-[var(--accent)]"
                        >
                          {game.game_date}
                        </Link>
                      </td>
                      <td className="whitespace-nowrap px-3 py-2.5 text-xs text-[var(--foreground)]">
                        {game.matchup}
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        <span className={`text-xs font-semibold ${isWin ? "text-green-600 dark:text-green-400" : "text-red-500 dark:text-red-400"}`}>
                          {game.wl}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 text-right tabular-nums text-[var(--muted)]">
                        {fmtNum(game.min, 0)}
                      </td>
                      {/* PTS with sparkline */}
                      <td className="px-3 py-2.5 text-right">
                        <div className="flex flex-col items-end gap-0.5">
                          <span className="font-semibold tabular-nums text-[var(--foreground)]">{fmtNum(game.pts)}</span>
                          <Sparkline value={game.pts} max={maxPts} colorClass="bg-[var(--accent)]" />
                        </div>
                      </td>
                      {/* REB with sparkline */}
                      <td className="px-3 py-2.5 text-right">
                        <div className="flex flex-col items-end gap-0.5">
                          <span className="tabular-nums text-[var(--foreground)]">{fmtNum(game.reb)}</span>
                          <Sparkline value={game.reb} max={maxReb} colorClass="bg-emerald-400" />
                        </div>
                      </td>
                      {/* AST with sparkline */}
                      <td className="px-3 py-2.5 text-right">
                        <div className="flex flex-col items-end gap-0.5">
                          <span className="tabular-nums text-[var(--foreground)]">{fmtNum(game.ast)}</span>
                          <Sparkline value={game.ast} max={maxAst} colorClass="bg-violet-400" />
                        </div>
                      </td>
                      <td className="hidden px-3 py-2.5 text-right tabular-nums text-[var(--muted)] sm:table-cell">{fmtNum(game.stl)}</td>
                      <td className="hidden px-3 py-2.5 text-right tabular-nums text-[var(--muted)] sm:table-cell">{fmtNum(game.blk)}</td>
                      <td className="hidden px-3 py-2.5 text-right tabular-nums text-[var(--muted)] sm:table-cell">{fmtNum(game.tov)}</td>
                      <td className="hidden px-3 py-2.5 text-right tabular-nums text-[var(--muted)] md:table-cell">{fmtPct(game.fg_pct)}</td>
                      <td className="hidden px-3 py-2.5 text-right tabular-nums text-[var(--muted)] md:table-cell">{fmtPct(game.fg3_pct)}</td>
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
          <div className="border-t border-[var(--border)] px-4 py-3 text-center">
            <button
              onClick={() => setShowLast("all")}
              className="bip-link text-sm"
            >
              Show all {data.gp} games
            </button>
          </div>
        )}
      </div>

      {data?.data_status === "stale" && (
        <div className="rounded-xl border border-[rgba(194,122,44,0.2)] bg-[rgba(194,122,44,0.06)] px-4 py-3 text-sm text-[var(--muted-strong)]">
          Showing cached game logs while the queued refresh catches up.
        </div>
      )}
    </section>
  );
}
