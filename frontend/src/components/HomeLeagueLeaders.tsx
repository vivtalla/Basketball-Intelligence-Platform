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
    <div className="bip-panel overflow-hidden rounded-[1.7rem]">
      <div className="px-4 py-3 border-b border-[var(--border)]">
        <h3 className="bip-kicker">
          {label}
        </h3>
      </div>

      {isLoading && (
        <div className="divide-y divide-[var(--border)] animate-pulse">
          {Array.from({ length: LIMIT }).map((_, i) => (
            <div key={i} className="flex items-center gap-3 px-4 py-3">
              <div className="w-8 h-8 rounded-full bg-[var(--surface-alt)] shrink-0" />
              <div className="flex-1 space-y-1.5">
                <div className="h-3 w-28 rounded bg-[var(--surface-alt)]" />
                <div className="h-2.5 w-16 rounded bg-[var(--surface-alt)]" />
              </div>
              <div className="h-4 w-10 rounded bg-[var(--surface-alt)]" />
            </div>
          ))}
        </div>
      )}

      {!isLoading && (
        <div className="divide-y divide-[var(--border)]">
          {top.map((entry, i) => {
            const value = isPercent
              ? `${(entry.stat_value * 100).toFixed(1)}%`
              : `${entry.stat_value.toFixed(1)}${unit ?? ""}`;
            return (
              <Link
                key={entry.player_id}
                href={`/players/${entry.player_id}`}
                className="flex items-center gap-3 px-4 py-3 hover:bg-[rgba(33,72,59,0.08)] group"
              >
                <span className="text-xs text-[var(--muted)] w-4 shrink-0 tabular-nums text-right">
                  {i + 1}
                </span>
                <div className="relative w-8 h-8 rounded-full overflow-hidden bg-[var(--surface-alt)] shrink-0">
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
                  <div className="text-sm font-medium text-[var(--foreground)] group-hover:text-[var(--accent)] truncate">
                    {entry.player_name}
                  </div>
                  <div className="text-xs text-[var(--muted)]">
                    {entry.team_abbreviation}
                  </div>
                </div>
                <span className="text-sm font-bold tabular-nums text-[var(--foreground)] shrink-0">
                  {value}
                </span>
              </Link>
            );
          })}
        </div>
      )}

      <div className="px-4 py-2.5 border-t border-[var(--border)]">
        <Link
          href="/player-stats"
          className="text-xs bip-link"
        >
          Full player stats →
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
          <h2 className="bip-display text-2xl font-semibold text-[var(--foreground)]">League Leaders</h2>
          <p className="text-sm text-[var(--muted)]">
            {SEASON} regular season — top 5 per category.
          </p>
        </div>
        <Link
          href="/player-stats"
          className="text-sm bip-link"
        >
          All player stats →
        </Link>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <LeaderColumn stat="pts_pg" label="Scoring" />
        <LeaderColumn stat="ast_pg" label="Assists" />
        <LeaderColumn stat="reb_pg" label="Rebounds" />
        <LeaderColumn stat="per" label="PER" />
      </div>
    </div>
  );
}
