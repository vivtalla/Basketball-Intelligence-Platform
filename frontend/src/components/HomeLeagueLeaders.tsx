"use client";

import Image from "next/image";
import Link from "next/link";
import { useLeaderboard } from "@/hooks/usePlayerStats";

const SEASON = "2024-25";
const LIMIT = 5;

interface LeaderColumnProps {
  stat: string;
  label: string;
  unit?: string;
  isPercent?: boolean;
}

function LeaderColumn({ stat, label, unit, isPercent }: LeaderColumnProps) {
  const { data, isLoading } = useLeaderboard(stat, SEASON);

  const top = data?.entries.slice(0, LIMIT) ?? [];

  return (
    <div className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700/60">
        <h3 className="text-xs font-semibold uppercase tracking-[0.2em] text-blue-500">
          {label}
        </h3>
      </div>

      {isLoading && (
        <div className="divide-y divide-gray-100 dark:divide-gray-700/60 animate-pulse">
          {Array.from({ length: LIMIT }).map((_, i) => (
            <div key={i} className="flex items-center gap-3 px-4 py-3">
              <div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 shrink-0" />
              <div className="flex-1 space-y-1.5">
                <div className="h-3 w-28 rounded bg-gray-200 dark:bg-gray-700" />
                <div className="h-2.5 w-16 rounded bg-gray-200 dark:bg-gray-700" />
              </div>
              <div className="h-4 w-10 rounded bg-gray-200 dark:bg-gray-700" />
            </div>
          ))}
        </div>
      )}

      {!isLoading && (
        <div className="divide-y divide-gray-100 dark:divide-gray-700/60">
          {top.map((entry, i) => {
            const value = isPercent
              ? `${(entry.stat_value * 100).toFixed(1)}%`
              : `${entry.stat_value.toFixed(1)}${unit ?? ""}`;
            return (
              <Link
                key={entry.player_id}
                href={`/players/${entry.player_id}`}
                className="flex items-center gap-3 px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-700/40 transition-colors group"
              >
                <span className="text-xs text-gray-400 dark:text-gray-500 w-4 shrink-0 tabular-nums text-right">
                  {i + 1}
                </span>
                <div className="relative w-8 h-8 rounded-full overflow-hidden bg-gray-100 dark:bg-gray-700 shrink-0">
                  {entry.headshot_url && (
                    <Image
                      src={entry.headshot_url}
                      alt={entry.player_name}
                      fill
                      className="object-cover object-top"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = "none";
                      }}
                    />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-gray-900 dark:text-gray-100 group-hover:text-blue-500 dark:group-hover:text-blue-400 transition-colors truncate">
                    {entry.player_name}
                  </div>
                  <div className="text-xs text-gray-400 dark:text-gray-500">
                    {entry.team_abbreviation}
                  </div>
                </div>
                <span className="text-sm font-bold tabular-nums text-gray-900 dark:text-gray-100 shrink-0">
                  {value}
                </span>
              </Link>
            );
          })}
        </div>
      )}

      <div className="px-4 py-2.5 border-t border-gray-100 dark:border-gray-700/60">
        <Link
          href={`/leaderboards`}
          className="text-xs text-blue-500 hover:text-blue-600 transition-colors"
        >
          Full leaderboard →
        </Link>
      </div>
    </div>
  );
}

export default function HomeLeagueLeaders() {
  return (
    <div>
      <div className="mb-4 flex items-end justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold">League Leaders</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {SEASON} regular season — top 5 per category.
          </p>
        </div>
        <Link
          href="/leaderboards"
          className="text-sm text-blue-500 hover:text-blue-600 transition-colors"
        >
          All leaderboards →
        </Link>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <LeaderColumn stat="pts" label="Scoring" />
        <LeaderColumn stat="ast" label="Assists" />
        <LeaderColumn stat="reb" label="Rebounds" />
        <LeaderColumn stat="per" label="PER" />
      </div>
    </div>
  );
}
