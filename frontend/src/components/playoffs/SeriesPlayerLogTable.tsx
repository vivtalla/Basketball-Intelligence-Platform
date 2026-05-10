"use client";

/**
 * Sprint 85 — per-team player game-by-game log table.
 * Sprint 86 (B) — sortable column headers.
 *
 * Renders one section per team for a single playoff series:
 *  - Team header strip (abbreviation + total players logged).
 *  - For each player (sorted by series-totals stat — defaults to MIN desc),
 *    a stacked block of one row per game plus a "Totals" row at the bottom.
 *  - Game# column deep-links to /games/{game_id} for full game detail.
 */

import Link from "next/link";
import { useMemo, useState } from "react";
import type {
  SeriesPlayerGameLine,
  SeriesPlayerLogs,
} from "@/lib/types";

interface SeriesPlayerLogTableProps {
  team: SeriesPlayerLogs[];
  teamAbbr: string;
  teamId: number | null;
}

type SortKey = "min" | "pts" | "reb" | "ast" | "stl" | "blk" | "tov" | "plus_minus";
type SortDir = "asc" | "desc";

function SortableHeader({
  label,
  sortKey,
  activeKey,
  activeDir,
  onSort,
  className = "",
}: {
  label: string;
  sortKey: SortKey;
  activeKey: SortKey;
  activeDir: SortDir;
  onSort: (key: SortKey) => void;
  className?: string;
}) {
  const isActive = activeKey === sortKey;
  const arrow = isActive ? (activeDir === "desc" ? " ↓" : " ↑") : "";
  return (
    <th
      className={`px-3 py-3 text-right text-xs font-semibold uppercase tracking-wider text-[var(--muted)] ${className}`}
    >
      <button
        type="button"
        onClick={() => onSort(sortKey)}
        className={`inline-flex items-center gap-0.5 transition-colors hover:text-[var(--accent)] ${
          isActive ? "text-[var(--foreground)]" : ""
        }`}
        aria-label={`Sort by ${label} ${
          isActive ? (activeDir === "desc" ? "ascending" : "descending") : "descending"
        }`}
      >
        {label}
        <span className="text-[10px] tabular-nums" aria-hidden="true">
          {arrow}
        </span>
      </button>
    </th>
  );
}

function fmtNum(value: number | null | undefined, digits = 0): string {
  if (value == null || Number.isNaN(value)) return "-";
  return value.toFixed(digits);
}

function fmtPct(made: number, attempts: number): string {
  if (!attempts) return "-";
  return `${((made / attempts) * 100).toFixed(1)}%`;
}

function fmtSigned(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "-";
  if (value === 0) return "0";
  return `${value > 0 ? "+" : ""}${value}`;
}

function pmColor(value: number | null | undefined): string {
  const v = value ?? 0;
  if (v > 0) return "text-green-600 dark:text-green-400";
  if (v < 0) return "text-red-500 dark:text-red-400";
  return "text-[var(--muted)]";
}

function PlayerHeaderRow({
  player,
}: {
  player: SeriesPlayerLogs;
}) {
  return (
    <tr className="border-t border-[var(--border)] bg-[var(--surface-alt)]">
      <td colSpan={14} className="px-4 py-2.5">
        <div className="flex items-center gap-3">
          {player.headshot_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={player.headshot_url}
              alt={player.player_name}
              className="h-8 w-8 rounded-full border border-[var(--border)] object-cover"
            />
          ) : (
            <div className="flex h-8 w-8 items-center justify-center rounded-full border border-[var(--border)] bg-[var(--surface)] text-[10px] font-semibold text-[var(--muted)]">
              {player.player_name
                .split(" ")
                .map((s) => s[0])
                .join("")
                .slice(0, 2)}
            </div>
          )}
          <div className="min-w-0 flex-1">
            <Link
              href={`/beta/players/${player.player_id}`}
              className="text-sm font-semibold text-[var(--foreground)] transition-colors hover:text-[var(--accent)]"
            >
              {player.player_name}
            </Link>
            <p className="text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">
              {player.games.length} game{player.games.length === 1 ? "" : "s"} ·{" "}
              {fmtNum(player.series_totals.min, 0)} min
            </p>
          </div>
        </div>
      </td>
    </tr>
  );
}

function GameRow({
  line,
  isTotals = false,
}: {
  line: SeriesPlayerGameLine;
  isTotals?: boolean;
}) {
  const cellBase = isTotals
    ? "px-3 py-2 text-right tabular-nums text-[var(--foreground)] font-semibold"
    : "px-3 py-2 text-right tabular-nums text-[var(--muted-strong)]";

  const gameLabel = isTotals
    ? "Totals"
    : `G${line.series_game_num || "?"}`;

  return (
    <tr
      className={
        isTotals
          ? "border-t border-[var(--border)] bg-[rgba(33,72,59,0.05)]"
          : "border-t border-[var(--border)] hover:bg-[rgba(216,228,221,0.22)]"
      }
    >
      <td className="whitespace-nowrap px-4 py-2 text-left text-xs">
        {isTotals ? (
          <span className="font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">
            Totals
          </span>
        ) : (
          <Link
            href={`/beta/games/${line.game_id}`}
            className="font-semibold text-[var(--accent)] transition-colors hover:underline"
            aria-label={`View full game detail for ${gameLabel}`}
          >
            {gameLabel}
          </Link>
        )}
      </td>
      <td className={cellBase}>{fmtNum(line.min, isTotals ? 0 : 0)}</td>
      <td className={cellBase}>{line.pts}</td>
      <td className={cellBase}>{line.reb}</td>
      <td className={cellBase}>{line.ast}</td>
      <td className={`${cellBase} hidden sm:table-cell`}>{line.stl}</td>
      <td className={`${cellBase} hidden sm:table-cell`}>{line.blk}</td>
      <td className={`${cellBase} hidden sm:table-cell`}>{line.tov}</td>
      <td className={`${cellBase} hidden md:table-cell`}>
        <span>
          {line.fgm}/{line.fga}
        </span>
        <span className="ml-1 text-[10px] text-[var(--muted)]">
          {fmtPct(line.fgm, line.fga)}
        </span>
      </td>
      <td className={`${cellBase} hidden md:table-cell`}>
        <span>
          {line.fg3m}/{line.fg3a}
        </span>
        <span className="ml-1 text-[10px] text-[var(--muted)]">
          {fmtPct(line.fg3m, line.fg3a)}
        </span>
      </td>
      <td className={`${cellBase} hidden md:table-cell`}>
        <span>
          {line.ftm}/{line.fta}
        </span>
        <span className="ml-1 text-[10px] text-[var(--muted)]">
          {fmtPct(line.ftm, line.fta)}
        </span>
      </td>
      <td
        className={`px-3 py-2 text-right tabular-nums font-semibold ${pmColor(
          line.plus_minus
        )}`}
      >
        {fmtSigned(line.plus_minus)}
      </td>
    </tr>
  );
}

export default function SeriesPlayerLogTable({
  team,
  teamAbbr,
  teamId,
}: SeriesPlayerLogTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("min");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const handleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDir((d) => (d === "desc" ? "asc" : "desc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const sortedTeam = useMemo(() => {
    const arr = [...team];
    arr.sort((a, b) => {
      const av = a.series_totals[sortKey] ?? 0;
      const bv = b.series_totals[sortKey] ?? 0;
      return sortDir === "desc" ? bv - av : av - bv;
    });
    return arr;
  }, [team, sortKey, sortDir]);

  if (team.length === 0) {
    return (
      <section className="bip-panel rounded-[1.4rem] p-6">
        <div className="flex items-center gap-3">
          {teamId != null ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={`https://cdn.nba.com/logos/nba/${teamId}/global/L/logo.svg`}
              alt={teamAbbr}
              className="h-10 w-10 object-contain"
            />
          ) : null}
          <div>
            <p className="bip-kicker">Team roster</p>
            <h2 className="bip-display text-xl font-semibold text-[var(--foreground)]">
              {teamAbbr}
            </h2>
          </div>
        </div>
        <p className="mt-4 text-sm text-[var(--muted)]">
          No per-game player logs synced for this team yet. Logs populate as
          games complete and the daily sync ingests the box scores.
        </p>
      </section>
    );
  }

  return (
    <section className="bip-panel rounded-[1.4rem] p-4 sm:p-6">
      <div className="mb-4 flex items-center gap-3">
        {teamId != null ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={`https://cdn.nba.com/logos/nba/${teamId}/global/L/logo.svg`}
            alt={teamAbbr}
            className="h-10 w-10 object-contain"
          />
        ) : null}
        <div>
          <p className="bip-kicker">Team rotation</p>
          <h2 className="bip-display text-xl font-semibold text-[var(--foreground)]">
            {teamAbbr}
          </h2>
          <p className="text-[11px] text-[var(--muted)]">
            {team.length} player{team.length === 1 ? "" : "s"} · click any
            stat to re-sort
          </p>
        </div>
      </div>

      <div className="bip-table-shell overflow-hidden rounded-2xl">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bip-table-head border-b border-[var(--border)]">
                <th className="whitespace-nowrap px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">
                  Game
                </th>
                <SortableHeader label="MIN" sortKey="min" activeKey={sortKey} activeDir={sortDir} onSort={handleSort} />
                <SortableHeader label="PTS" sortKey="pts" activeKey={sortKey} activeDir={sortDir} onSort={handleSort} />
                <SortableHeader label="REB" sortKey="reb" activeKey={sortKey} activeDir={sortDir} onSort={handleSort} />
                <SortableHeader label="AST" sortKey="ast" activeKey={sortKey} activeDir={sortDir} onSort={handleSort} />
                <SortableHeader label="STL" sortKey="stl" activeKey={sortKey} activeDir={sortDir} onSort={handleSort} className="hidden sm:table-cell" />
                <SortableHeader label="BLK" sortKey="blk" activeKey={sortKey} activeDir={sortDir} onSort={handleSort} className="hidden sm:table-cell" />
                <SortableHeader label="TO" sortKey="tov" activeKey={sortKey} activeDir={sortDir} onSort={handleSort} className="hidden sm:table-cell" />
                <th className="hidden px-3 py-3 text-right text-xs font-semibold uppercase tracking-wider text-[var(--muted)] md:table-cell">
                  FG
                </th>
                <th className="hidden px-3 py-3 text-right text-xs font-semibold uppercase tracking-wider text-[var(--muted)] md:table-cell">
                  3P
                </th>
                <th className="hidden px-3 py-3 text-right text-xs font-semibold uppercase tracking-wider text-[var(--muted)] md:table-cell">
                  FT
                </th>
                <SortableHeader label="+/-" sortKey="plus_minus" activeKey={sortKey} activeDir={sortDir} onSort={handleSort} />
              </tr>
            </thead>
            <tbody>
              {sortedTeam.map((player, idx) => (
                <PlayerBlock key={player.player_id} player={player} isFirst={idx === 0} />
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

function PlayerBlock({
  player,
}: {
  player: SeriesPlayerLogs;
  /** Reserved for future styling (e.g. omit top border on the first block). */
  isFirst?: boolean;
}) {
  return (
    <>
      <PlayerHeaderRow player={player} />
      {player.games.map((line) => (
        <GameRow key={line.game_id} line={line} />
      ))}
      <GameRow line={player.series_totals} isTotals />
    </>
  );
}
