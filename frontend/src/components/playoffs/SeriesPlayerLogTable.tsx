"use client";

/**
 * Sprint 85 — per-team player game-by-game log table.
 *
 * Renders one section per team for a single playoff series:
 *  - Team header strip (abbreviation + total players logged).
 *  - For each player (sorted by total minutes in the series), a stacked
 *    block of one row per game plus a "Totals" row at the bottom.
 *  - Game# column deep-links to /games/{game_id} for full game detail.
 */

import Link from "next/link";
import type {
  SeriesPlayerGameLine,
  SeriesPlayerLogs,
} from "@/lib/types";

interface SeriesPlayerLogTableProps {
  team: SeriesPlayerLogs[];
  teamAbbr: string;
  teamId: number | null;
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
              href={`/players/${player.player_id}`}
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
            href={`/games/${line.game_id}`}
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
            {team.length} player{team.length === 1 ? "" : "s"} · sorted by total
            minutes
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
                <th className="px-3 py-3 text-right text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">
                  MIN
                </th>
                <th className="px-3 py-3 text-right text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">
                  PTS
                </th>
                <th className="px-3 py-3 text-right text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">
                  REB
                </th>
                <th className="px-3 py-3 text-right text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">
                  AST
                </th>
                <th className="hidden px-3 py-3 text-right text-xs font-semibold uppercase tracking-wider text-[var(--muted)] sm:table-cell">
                  STL
                </th>
                <th className="hidden px-3 py-3 text-right text-xs font-semibold uppercase tracking-wider text-[var(--muted)] sm:table-cell">
                  BLK
                </th>
                <th className="hidden px-3 py-3 text-right text-xs font-semibold uppercase tracking-wider text-[var(--muted)] sm:table-cell">
                  TO
                </th>
                <th className="hidden px-3 py-3 text-right text-xs font-semibold uppercase tracking-wider text-[var(--muted)] md:table-cell">
                  FG
                </th>
                <th className="hidden px-3 py-3 text-right text-xs font-semibold uppercase tracking-wider text-[var(--muted)] md:table-cell">
                  3P
                </th>
                <th className="hidden px-3 py-3 text-right text-xs font-semibold uppercase tracking-wider text-[var(--muted)] md:table-cell">
                  FT
                </th>
                <th className="px-3 py-3 text-right text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">
                  +/-
                </th>
              </tr>
            </thead>
            <tbody>
              {team.map((player, idx) => (
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
