"use client";

import Image from "next/image";
import Link from "next/link";
import { useMemo } from "react";
import {
  useLeaderboard,
  useLeaderboardTrends,
} from "@/hooks/usePlayerStats";
import Sparkline from "@/components/Sparkline";

const SEASON = "2025-26";
const LIMIT = 5;
const TREND_WINDOW = 10;

interface LeaderColumnProps {
  stat: string;
  label: string;
  unit?: string;
  isPercent?: boolean;
}

function formatTooltip(
  isPercent: boolean | undefined,
  unit: string | undefined,
  latest: number | null,
  delta: number | null
): string {
  if (latest === null) return "No trend data";
  const fmt = (v: number) =>
    isPercent ? `${(v * 100).toFixed(1)}%` : `${v.toFixed(1)}${unit ?? ""}`;
  const parts = [`Latest: ${fmt(latest)}`];
  if (delta !== null) {
    const sign = delta > 0 ? "+" : "";
    const deltaStr = isPercent
      ? `${sign}${(delta * 100).toFixed(1)}pp`
      : `${sign}${delta.toFixed(1)}`;
    parts.push(`vs season avg: ${deltaStr}`);
  }
  return parts.join(" · ");
}

function LeaderColumn({ stat, label, unit, isPercent }: LeaderColumnProps) {
  const { data, isLoading } = useLeaderboard(stat, SEASON);

  const top = useMemo(
    () => data?.entries.slice(0, LIMIT) ?? [],
    [data]
  );
  const playerIds = useMemo(() => top.map((e) => e.player_id), [top]);

  // Trends fetch depends on the leader IDs — guard prevents waterfall side
  // effects: only fires when leaderboard entries are loaded.
  const { data: trendData } = useLeaderboardTrends(
    playerIds.length > 0 ? stat : null,
    playerIds,
    playerIds.length > 0 ? SEASON : null,
    TREND_WINDOW
  );

  const trendByPlayerId = useMemo(() => {
    const map = new Map<
      number,
      { rolling: number[]; latest: number | null; delta: number | null }
    >();
    if (trendData?.entries) {
      for (const entry of trendData.entries) {
        map.set(entry.player_id, {
          rolling: entry.rolling_values,
          latest: entry.latest_value,
          delta: entry.delta_vs_baseline,
        });
      }
    }
    return map;
  }, [trendData]);

  return (
    <div className="bip-panel overflow-hidden rounded-[1.7rem]">
      <div className="px-4 py-3 border-b border-[var(--border)] flex items-center justify-between">
        <h3 className="bip-kicker">
          {label}
        </h3>
        <span className="bip-kicker text-[var(--muted)] text-[0.6rem] tracking-[0.16em]">
          Trend · L{TREND_WINDOW}
        </span>
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
            const trend = trendByPlayerId.get(entry.player_id);
            const tooltip = formatTooltip(
              isPercent,
              unit,
              trend?.latest ?? null,
              trend?.delta ?? null
            );
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
                <div
                  className="shrink-0 flex items-center"
                  title={tooltip}
                  aria-label={tooltip}
                >
                  <Sparkline
                    values={trend?.rolling ?? []}
                    delta={trend?.delta ?? undefined}
                    width={56}
                    height={18}
                  />
                </div>
                <span className="text-sm font-bold tabular-nums text-[var(--foreground)] shrink-0 w-12 text-right">
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
          <p className="bip-kicker mb-1.5">League Leaders · {SEASON}</p>
          <h2 className="bip-display text-3xl font-semibold text-[var(--foreground)]">
            The composite <span className="text-[var(--accent)]">top five.</span>
          </h2>
        </div>
        <Link
          href="/player-stats"
          className="text-sm bip-link shrink-0 font-medium"
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
