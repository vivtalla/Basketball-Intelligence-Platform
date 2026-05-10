"use client";

import Link from "next/link";
import type { LineupLeaderboardEntry } from "@/lib/types";
import LineupArchetypePill from "./LineupArchetypePill";
import LineupConfidenceBadge from "./LineupConfidenceBadge";

type SortKey = "net_rating" | "ortg" | "drtg" | "plus_minus" | "possessions" | "minutes" | "shrunk_net_rating" | "net_vs_baseline";

interface Props {
  lineups: LineupLeaderboardEntry[];
  sortBy: SortKey;
  sortDir: "asc" | "desc";
  onSort: (key: SortKey) => void;
  compact?: boolean;
}

function fmt(v: number | null | undefined, digits = 1): string {
  if (v == null) return "—";
  return v.toFixed(digits);
}

function fmtSigned(v: number | null | undefined, digits = 1): string {
  if (v == null) return "—";
  return `${v >= 0 ? "+" : ""}${v.toFixed(digits)}`;
}

function signColor(v: number | null | undefined): string {
  if (v == null) return "";
  return v >= 0 ? "text-green-600 dark:text-green-400" : "text-red-500 dark:text-red-400";
}

function SortHeader({ label, col, sortBy, sortDir, onSort }: {
  label: string; col: SortKey; sortBy: SortKey; sortDir: "asc" | "desc"; onSort: (k: SortKey) => void;
}) {
  const active = sortBy === col;
  return (
    <th
      className="px-2 py-2 text-left text-[10px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 cursor-pointer select-none hover:text-gray-700 dark:hover:text-gray-200 whitespace-nowrap"
      onClick={() => onSort(col)}
    >
      {label}
      {active && <span className="ml-0.5">{sortDir === "desc" ? " ↓" : " ↑"}</span>}
    </th>
  );
}

function PlayerChips({ names }: { names: string[] }) {
  return (
    <div className="flex flex-wrap gap-0.5">
      {names.map((n, i) => (
        <span key={i} className="rounded bg-gray-100 dark:bg-gray-700 px-1 py-0.5 text-[9px] text-gray-700 dark:text-gray-300 whitespace-nowrap">
          {n}
        </span>
      ))}
    </div>
  );
}

export default function LineupLeaderboardTable({ lineups, sortBy, sortDir, onSort, compact = false }: Props) {
  if (lineups.length === 0) {
    return (
      <p className="text-sm text-gray-400 dark:text-gray-500 italic py-6 text-center">
        No lineups match the current filters.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-700">
      <table className="w-full text-xs">
        <thead className="bg-gray-50 dark:bg-gray-800/60 border-b border-gray-200 dark:border-gray-700">
          <tr>
            <th className="px-2 py-2 text-left text-[10px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 w-8">#</th>
            <th className="px-2 py-2 text-left text-[10px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Players</th>
            {!compact && <th className="px-2 py-2 text-left text-[10px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 hidden sm:table-cell">Team</th>}
            <SortHeader label="MIN" col="minutes" sortBy={sortBy} sortDir={sortDir} onSort={onSort} />
            <SortHeader label="POSS" col="possessions" sortBy={sortBy} sortDir={sortDir} onSort={onSort} />
            {!compact && <SortHeader label="ORTG" col="ortg" sortBy={sortBy} sortDir={sortDir} onSort={onSort} />}
            {!compact && <SortHeader label="DRTG" col="drtg" sortBy={sortBy} sortDir={sortDir} onSort={onSort} />}
            <SortHeader label="Net Rtg" col="net_rating" sortBy={sortBy} sortDir={sortDir} onSort={onSort} />
            <SortHeader label="Shrunk" col="shrunk_net_rating" sortBy={sortBy} sortDir={sortDir} onSort={onSort} />
            {!compact && <SortHeader label="vs Team" col="net_vs_baseline" sortBy={sortBy} sortDir={sortDir} onSort={onSort} />}
            {!compact && <th className="px-2 py-2 text-left text-[10px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Archetype</th>}
            <th className="px-2 py-2 text-left text-[10px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Conf</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
          {lineups.map((row, i) => (
            <tr key={row.lineup_key} className="hover:bg-gray-50 dark:hover:bg-gray-800/40 transition-colors">
              <td className="px-2 py-2 text-gray-400 dark:text-gray-500">{i + 1}</td>
              <td className="px-2 py-2 max-w-[220px]">
                <PlayerChips names={row.player_names} />
              </td>
              {!compact && (
                <td className="px-2 py-2 hidden sm:table-cell">
                  {row.team_abbreviation ? (
                    <Link href={`/beta/teams/${row.team_abbreviation}`} className="text-teal-600 dark:text-teal-400 hover:underline font-medium">
                      {row.team_abbreviation}
                    </Link>
                  ) : "—"}
                </td>
              )}
              <td className="px-2 py-2 tabular-nums text-gray-600 dark:text-gray-300">{fmt(row.minutes, 0)}</td>
              <td className="px-2 py-2 tabular-nums text-gray-600 dark:text-gray-300">{row.possessions?.toLocaleString() ?? "—"}</td>
              {!compact && <td className="px-2 py-2 tabular-nums text-gray-700 dark:text-gray-200">{fmt(row.ortg)}</td>}
              {!compact && <td className="px-2 py-2 tabular-nums text-gray-700 dark:text-gray-200">{fmt(row.drtg)}</td>}
              <td className={`px-2 py-2 tabular-nums font-semibold ${signColor(row.net_rating)}`}>{fmtSigned(row.net_rating)}</td>
              <td className={`px-2 py-2 tabular-nums ${signColor(row.shrunk_net_rating)}`}>{fmtSigned(row.shrunk_net_rating)}</td>
              {!compact && <td className={`px-2 py-2 tabular-nums ${signColor(row.net_vs_baseline)}`}>{fmtSigned(row.net_vs_baseline)}</td>}
              {!compact && <td className="px-2 py-2"><LineupArchetypePill archetype={row.archetype} /></td>}
              <td className="px-2 py-2"><LineupConfidenceBadge confidence={row.confidence} possessions={row.possessions} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
