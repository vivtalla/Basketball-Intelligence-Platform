"use client";

import useSWR from "swr";
import Link from "next/link";
import { getPlayoffLeaders } from "@/lib/api";
import { useSeasonPhase } from "@/hooks/useSeasonPhase";
import type {
  PlayoffLeaderEntry,
  PlayoffLeadersResponse,
} from "@/lib/types";

/**
 * Sprint 77 (Stream B / EB1): Narrative Leaders.
 *
 * Renders 5 rows fed by `GET /api/playoffs/leaders?season=...&limit=5`:
 *   - Rank circle (gold for top 3, cream for the rest),
 *   - Player + team line,
 *   - One-line stat line ("32.4 PPS · 7.1 RPG"),
 *   - Trend glyph (▲ green, → muted, ▼ danger),
 *   - 5-bar mini chart driven by `recent_games_grade` (0..1).
 */

const ACTIVE_SEASON_FALLBACK = "2025-26";

function trendColor(trend: PlayoffLeaderEntry["trend"]): string {
  switch (trend) {
    case "▲":
      return "var(--success-ink)";
    case "▼":
      return "var(--danger-ink)";
    default:
      return "var(--muted)";
  }
}

function rankBadge(rank: number) {
  const isTop3 = rank <= 3;
  return (
    <div
      className="shrink-0 rounded-full flex items-center justify-center font-bold"
      style={{
        width: 32,
        height: 32,
        fontFamily: "var(--font-display)",
        fontSize: 14,
        background: isTop3 ? "var(--signal)" : "var(--surface-alt)",
        color: isTop3 ? "var(--signal-ink)" : "var(--muted)",
        border: `1px solid ${isTop3 ? "rgba(180,137,61,0.32)" : "var(--border)"}`,
      }}
      aria-label={`Rank ${rank}`}
    >
      {rank}
    </div>
  );
}

function MiniBarChart({ values }: { values: number[] }) {
  // Render up to 5 bars. Inputs are expected in 0..1 (grade-like). Clamp
  // defensively. If fewer than 5 values arrive, pad with empties so the
  // chart stays the same width.
  const clamped = values.slice(0, 5).map((v) => {
    if (typeof v !== "number" || Number.isNaN(v)) return 0;
    return Math.max(0, Math.min(1, v));
  });
  while (clamped.length < 5) clamped.push(0);

  return (
    <div
      className="flex items-end gap-1"
      style={{ width: 60, height: 24 }}
      role="img"
      aria-label="Recent games grade"
    >
      {clamped.map((value, i) => {
        const heightPct = Math.max(8, value * 100);
        // Color the highest bar gold, the rest forest, washed out for
        // sub-0.5 grades.
        const isWeak = value < 0.5;
        return (
          <div
            key={i}
            className="flex-1 rounded-sm"
            style={{
              height: `${heightPct}%`,
              background: isWeak ? "var(--surface-alt)" : "var(--accent)",
              opacity: isWeak ? 0.7 : 1,
            }}
          />
        );
      })}
    </div>
  );
}

function LeaderRow({ entry }: { entry: PlayoffLeaderEntry }) {
  return (
    <Link
      href={`/players/${entry.player_id}`}
      className="flex items-center gap-3 px-4 py-3 hover:bg-[rgba(33,72,59,0.06)] transition-colors"
    >
      {rankBadge(entry.rank)}
      <div className="flex-1 min-w-0">
        <p
          className="font-semibold text-[var(--foreground)] truncate"
          style={{
            fontFamily: "var(--font-display)",
            fontSize: 14,
            letterSpacing: "-0.01em",
          }}
        >
          {entry.player_name}{" "}
          <span
            className="font-normal text-[var(--muted)]"
            style={{ fontSize: 12 }}
          >
            · {entry.team_abbreviation}
          </span>
        </p>
        <p
          className="text-[12px] text-[var(--muted)] truncate"
          style={{
            fontFamily: "var(--font-geist-mono)",
            letterSpacing: "0.04em",
          }}
        >
          {entry.line}
        </p>
      </div>
      <span
        className="shrink-0 tabular-nums"
        style={{
          fontFamily: "var(--font-display)",
          fontSize: 18,
          color: trendColor(entry.trend),
          width: 18,
          textAlign: "center",
        }}
        aria-label={`Trend ${entry.trend}`}
      >
        {entry.trend}
      </span>
      <div className="shrink-0">
        <MiniBarChart values={entry.recent_games_grade ?? []} />
      </div>
    </Link>
  );
}

export default function NarrativeLeaders() {
  const { season } = useSeasonPhase();
  const seasonKey = season ?? ACTIVE_SEASON_FALLBACK;

  const { data, isLoading, error } = useSWR<PlayoffLeadersResponse>(
    ["broadsheet-narrative-leaders", seasonKey],
    () => getPlayoffLeaders(seasonKey, 5),
    {
      refreshInterval: 5 * 60_000,
      revalidateOnFocus: false,
    }
  );

  const leaders = data?.leaders ?? [];

  return (
    <section className="bip-panel rounded-[1.85rem] overflow-hidden">
      <header className="px-6 py-4 border-b border-[var(--border)] flex items-end justify-between gap-4">
        <div>
          <p className="bip-kicker mb-1">Narrative Leaders</p>
          <h3
            className="bip-display font-bold text-[var(--foreground)]"
            style={{
              fontSize: "1.6rem",
              letterSpacing: "-0.015em",
            }}
          >
            Who&rsquo;s writing the headlines.
          </h3>
        </div>
        <Link
          href="/leaderboards"
          className="text-xs bip-link shrink-0 font-medium"
        >
          All leaders →
        </Link>
      </header>

      {isLoading && (
        <div className="divide-y divide-[var(--border)] animate-pulse">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3 px-4 py-3">
              <div className="h-8 w-8 rounded-full bg-[var(--surface-alt)] shrink-0" />
              <div className="flex-1 space-y-1.5">
                <div className="h-3 w-2/3 rounded bg-[var(--surface-alt)]" />
                <div className="h-3 w-1/2 rounded bg-[var(--surface-alt)]" />
              </div>
              <div className="h-6 w-14 rounded bg-[var(--surface-alt)] shrink-0" />
            </div>
          ))}
        </div>
      )}

      {!isLoading && error && (
        <p
          className="px-6 py-6 text-sm italic text-[var(--muted)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Leaders are between editions.
        </p>
      )}

      {!isLoading && !error && leaders.length === 0 && (
        <p
          className="px-6 py-6 text-sm italic text-[var(--muted)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          No narrative leaders yet for this round.
        </p>
      )}

      {!isLoading && !error && leaders.length > 0 && (
        <ul className="divide-y divide-[var(--border)]">
          {leaders.map((entry) => (
            <li key={entry.player_id}>
              <LeaderRow entry={entry} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
