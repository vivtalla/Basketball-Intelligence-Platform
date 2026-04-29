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
 *   - Impact score (CourtVue composite — see hover explainer),
 *   - Trend glyph (▲ green, → muted, ▼ danger),
 *   - 5-bar mini chart driven by `recent_games_grade` (0..1).
 *
 * Header includes an info icon (ⓘ) that on hover reveals a popover
 * documenting the composite formula and qualifying thresholds — so
 * users understand how the ranking is derived without leaving the page.
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
      style={{ width: 48, height: 20 }}
      role="img"
      aria-label="Recent games grade"
    >
      {clamped.map((value, i) => {
        const heightPct = Math.max(8, value * 100);
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

function ImpactPill({ score }: { score: number }) {
  return (
    <div
      className="shrink-0 flex flex-col items-end"
      style={{ width: 56 }}
      aria-label={`Impact score ${score.toFixed(1)}`}
    >
      <span
        className="text-[9px] font-bold uppercase"
        style={{
          fontFamily: "var(--font-geist-mono)",
          letterSpacing: "0.14em",
          color: "var(--muted)",
        }}
      >
        Impact
      </span>
      <span
        className="tabular-nums font-bold text-[var(--accent)]"
        style={{
          fontFamily: "var(--font-display)",
          fontSize: 22,
          lineHeight: 1.05,
          letterSpacing: "-0.02em",
        }}
      >
        {score.toFixed(1)}
      </span>
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
      <ImpactPill score={entry.impact_score} />
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

/**
 * Hover/focus popover that explains the composite score. Pure CSS group
 * hover so there's no React state — the popover is positioned absolutely
 * relative to the trigger and uses `pointer-events-none` until shown so
 * it can't trap clicks.
 */
function MethodologyTooltip() {
  return (
    <span
      className="group relative inline-flex items-center"
      tabIndex={0}
      aria-label="How the impact score is calculated"
    >
      <span
        aria-hidden
        className="inline-flex items-center justify-center rounded-full border text-[11px] font-bold cursor-help transition-colors hover:bg-[var(--accent)] hover:text-[var(--accent-ink)] hover:border-[var(--accent)] group-focus:bg-[var(--accent)] group-focus:text-[var(--accent-ink)]"
        style={{
          width: 18,
          height: 18,
          borderColor: "var(--border-strong)",
          color: "var(--muted)",
          fontFamily: "var(--font-display)",
        }}
      >
        i
      </span>
      <span
        role="tooltip"
        className="absolute left-0 top-full mt-2 z-30 w-[300px] max-w-[calc(100vw-2rem)] p-4 rounded-xl border shadow-lg opacity-0 pointer-events-none translate-y-1 transition-all duration-150 group-hover:opacity-100 group-hover:pointer-events-auto group-hover:translate-y-0 group-focus:opacity-100 group-focus:pointer-events-auto group-focus:translate-y-0"
        style={{
          background: "var(--surface)",
          borderColor: "var(--border-strong)",
          boxShadow: "var(--shadow)",
        }}
      >
        <p
          className="bip-kicker mb-2"
          style={{ color: "var(--accent)" }}
        >
          Impact Score · Methodology
        </p>
        <p
          className="text-[12px] leading-5 mb-3 text-[var(--foreground)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          A weighted composite of scoring, playmaking, rebounding,
          shooting efficiency, and team net rating.
        </p>
        <pre
          className="text-[11px] leading-[1.55] mb-3 px-3 py-2 rounded-md whitespace-pre-wrap"
          style={{
            fontFamily: "var(--font-geist-mono)",
            background: "var(--surface-alt)",
            color: "var(--foreground)",
          }}
        >
{`Impact = PPG × 0.35
       + AST × 0.20
       + RPG × 0.10
       + TS% × 0.20
       + NET × 0.15`}
        </pre>
        <ul
          className="text-[11px] leading-[1.5] space-y-1.5 text-[var(--muted)]"
          style={{
            fontFamily: "var(--font-geist-mono)",
            letterSpacing: "0.02em",
          }}
        >
          <li>· TS% clamped at 65 to prevent small-sample distortion.</li>
          <li>· Filters: GP ≥ 4 · MIN ≥ 22 · PPG ≥ 12.</li>
          <li>
            · Trend (▲/→/▼) compares last 3 games vs. season pts_pg.
          </li>
          <li>· Bars grade each of the last 5 games 1–5 vs. distribution.</li>
        </ul>
      </span>
    </span>
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
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <p className="bip-kicker">Narrative Leaders</p>
            <MethodologyTooltip />
          </div>
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
          href="/leaderboards?seasonType=Playoffs"
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
