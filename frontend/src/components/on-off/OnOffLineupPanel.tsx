"use client";

import type { LineupSlot } from "@/lib/types";

interface Props {
  topLineups: LineupSlot[];
  worstLineups: LineupSlot[];
  playerName: string;
}

function LineupRow({ slot }: { slot: LineupSlot }) {
  const nr = slot.net_rating;
  const nrColor = nr == null ? "" : nr >= 0 ? "text-green-600 dark:text-green-400" : "text-red-500 dark:text-red-400";
  const names = slot.player_names.length > 0 ? slot.player_names : ["—"];
  return (
    <div className="rounded-lg border border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60 px-3 py-2 text-xs">
      <div className="flex flex-wrap gap-1 mb-1">
        {names.map((n, i) => (
          <span key={i} className="rounded bg-gray-200 dark:bg-gray-700 px-1.5 py-0.5 text-[10px] text-gray-700 dark:text-gray-300">
            {n}
          </span>
        ))}
      </div>
      <div className="flex items-center gap-3 text-gray-500 dark:text-gray-400">
        {nr != null && (
          <span className={`font-semibold ${nrColor}`}>
            {nr >= 0 ? "+" : ""}{nr.toFixed(1)} NR
          </span>
        )}
        {slot.possessions != null && (
          <span>{slot.possessions.toLocaleString()} poss</span>
        )}
        {slot.minutes != null && (
          <span>{slot.minutes.toFixed(0)} min</span>
        )}
      </div>
    </div>
  );
}

export default function OnOffLineupPanel({ topLineups, worstLineups, playerName }: Props) {
  const hasTop = topLineups.length > 0;
  const hasWorst = worstLineups.length > 0;

  if (!hasTop && !hasWorst) {
    return (
      <p className="text-xs text-gray-400 dark:text-gray-500 italic">
        No qualifying lineups found (min. 100 possessions).
      </p>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <div>
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-teal-600 dark:text-teal-400">
          Best lineups with {playerName}
        </p>
        {hasTop ? (
          <div className="space-y-2">
            {topLineups.map((s, i) => <LineupRow key={i} slot={s} />)}
          </div>
        ) : (
          <p className="text-xs text-gray-400 dark:text-gray-500 italic">None qualifying</p>
        )}
      </div>
      <div>
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-red-500 dark:text-red-400">
          Struggles with
        </p>
        {hasWorst ? (
          <div className="space-y-2">
            {worstLineups.map((s, i) => <LineupRow key={i} slot={s} />)}
          </div>
        ) : (
          <p className="text-xs text-gray-400 dark:text-gray-500 italic">None qualifying</p>
        )}
      </div>
    </div>
  );
}
