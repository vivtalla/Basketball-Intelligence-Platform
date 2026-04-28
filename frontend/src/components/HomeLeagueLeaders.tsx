"use client";

import Image from "next/image";
import Link from "next/link";
import { useMemo, useState } from "react";
import {
  useLeaderboard,
  useLeaderboardTrends,
} from "@/hooks/usePlayerStats";
import { useSeasonPhase } from "@/hooks/useSeasonPhase";
import Sparkline from "@/components/Sparkline";

const SEASON = "2025-26";
const LIMIT = 5;
const TREND_WINDOW = 10;

type LeaderboardSeasonType = "Regular Season" | "Playoffs";

interface LeaderColumnProps {
  stat: string;
  label: string;
  seasonType: LeaderboardSeasonType;
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

function LeaderColumn({ stat, label, seasonType, unit, isPercent }: LeaderColumnProps) {
  const { data, isLoading } = useLeaderboard(stat, SEASON, seasonType);

  const top = useMemo(
    () => data?.entries.slice(0, LIMIT) ?? [],
    [data]
  );
  const playerIds = useMemo(() => top.map((e) => e.player_id), [top]);

  // Trends fetch depends on the leader IDs — guard prevents waterfall side
  // effects: only fires when leaderboard entries are loaded. Trends are
  // regular-season only today; suppress the call entirely under Playoffs.
  const { data: trendData } = useLeaderboardTrends(
    playerIds.length > 0 && seasonType === "Regular Season" ? stat : null,
    playerIds,
    playerIds.length > 0 && seasonType === "Regular Season" ? SEASON : null,
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
        {seasonType === "Regular Season" && (
          <span className="bip-kicker text-[var(--muted)] text-[0.6rem] tracking-[0.16em]">
            Trend · L{TREND_WINDOW}
          </span>
        )}
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
                {seasonType === "Regular Season" && (
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
                )}
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

function SeasonTypeToggle({
  value,
  onChange,
}: {
  value: LeaderboardSeasonType;
  onChange: (next: LeaderboardSeasonType) => void;
}) {
  const options: LeaderboardSeasonType[] = ["Regular Season", "Playoffs"];
  return (
    <div
      role="group"
      aria-label="Season type"
      className="inline-flex items-center rounded-full border border-[var(--border)] bg-[var(--surface-alt)] p-0.5"
    >
      {options.map((opt) => {
        const active = opt === value;
        return (
          <button
            key={opt}
            type="button"
            onClick={() => onChange(opt)}
            className="rounded-full px-3 py-1 text-xs font-medium transition-colors"
            style={{
              background: active ? "var(--surface)" : "transparent",
              color: active ? "var(--foreground)" : "var(--muted)",
              boxShadow: active
                ? "0 1px 2px rgba(33,72,59,0.12)"
                : "none",
            }}
          >
            {opt}
          </button>
        );
      })}
    </div>
  );
}

export default function HomeLeagueLeaders() {
  // Sprint 73: surface a Regular/Playoffs toggle on the home leaders block, but
  // only during the playoffs phase. Default to Regular Season so users aren't
  // surprised by a smaller-sample postseason board.
  const { isPlayoffs } = useSeasonPhase();
  const [seasonType, setSeasonType] = useState<LeaderboardSeasonType>(
    "Regular Season"
  );

  // Sample-size caveat: read the scoring leaderboard's first-place gp under the
  // current toggle. Empty/loading → no caveat. The hook is allocated
  // unconditionally to keep hook order stable.
  const { data: caveatData } = useLeaderboard("pts_pg", SEASON, seasonType);
  const showLimitedSampleCaveat =
    seasonType === "Playoffs" &&
    caveatData != null &&
    caveatData.entries.length > 0 &&
    (caveatData.entries[0]?.gp ?? 0) < 3;

  return (
    <div>
      <div className="mb-4 flex items-end justify-between gap-4">
        <div>
          <p className="bip-kicker mb-1.5">League Leaders · {SEASON}</p>
          <h2 className="bip-display text-3xl font-semibold text-[var(--foreground)]">
            The composite <span className="text-[var(--accent)]">top five.</span>
          </h2>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          {isPlayoffs && (
            <SeasonTypeToggle value={seasonType} onChange={setSeasonType} />
          )}
          <Link
            href="/player-stats"
            className="text-sm bip-link font-medium"
          >
            All player stats →
          </Link>
        </div>
      </div>
      {showLimitedSampleCaveat && (
        <p className="mb-3 text-xs text-[var(--muted)]">
          Limited playoff sample — leaders shown reflect very few games played.
        </p>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <LeaderColumn stat="pts_pg" label="Scoring" seasonType={seasonType} />
        <LeaderColumn stat="ast_pg" label="Assists" seasonType={seasonType} />
        <LeaderColumn stat="reb_pg" label="Rebounds" seasonType={seasonType} />
        <LeaderColumn stat="per" label="PER" seasonType={seasonType} />
      </div>
    </div>
  );
}
