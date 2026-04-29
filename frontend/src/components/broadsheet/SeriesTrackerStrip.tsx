"use client";

import useSWR from "swr";
import Link from "next/link";
import { getBracket } from "@/lib/api";
import { useSeasonPhase } from "@/hooks/useSeasonPhase";
import type {
  PlayoffBracketResponse,
  PlayoffSeriesResponse,
} from "@/lib/types";

/**
 * Sprint 77 (Stream B / EB1): Series Tracker Strip.
 *
 * 4-up tracker (2×2 grid) showing the most-active playoff series. Each card
 * carries:
 *   - 7-cell win bar (forest=top wins, danger=bottom wins, muted=unplayed),
 *   - record line ("OKC leads 2-1"),
 *   - P(series win) percent (computed from current state),
 *   - "Next game" cue ("Game 4 tonight"). Closed series render muted.
 */

const ACTIVE_SEASON_FALLBACK = "2024-25";

interface TrackerSeries {
  series: PlayoffSeriesResponse;
  topWP: number; // 0-1 — naive estimate from current state.
}

/**
 * Closed-form P(series win | current state). Treats each remaining game as a
 * fair 50/50 coin flip — sufficient for the broadsheet teaser. The full
 * Monte-Carlo simulator lives in the Series Command Center.
 */
function seriesWinProbability(
  topWins: number,
  bottomWins: number
): { top: number; bottom: number } {
  const target = 4;
  if (topWins >= target) return { top: 1, bottom: 0 };
  if (bottomWins >= target) return { top: 0, bottom: 1 };

  const winsNeededTop = target - topWins;
  const winsNeededBottom = target - bottomWins;
  // Prob(top wins exactly k of next n games) — but we just need the prob
  // top reaches `winsNeededTop` before bottom reaches `winsNeededBottom`.
  // Use the recursive solution: P(top) = 0.5 * P(after top wins) + 0.5 *
  // P(after bottom wins).
  const memo = new Map<string, number>();
  function probTopWins(t: number, b: number): number {
    if (t === 0) return 1;
    if (b === 0) return 0;
    const key = `${t}-${b}`;
    const cached = memo.get(key);
    if (cached !== undefined) return cached;
    const value = 0.5 * probTopWins(t - 1, b) + 0.5 * probTopWins(t, b - 1);
    memo.set(key, value);
    return value;
  }
  const top = probTopWins(winsNeededTop, winsNeededBottom);
  return { top, bottom: 1 - top };
}

function pickTrackedSeries(
  bracket: PlayoffBracketResponse | undefined
): TrackerSeries[] {
  if (!bracket) return [];
  const all: PlayoffSeriesResponse[] = [
    ...(bracket.east ?? []),
    ...(bracket.west ?? []),
    ...(bracket.finals ? [bracket.finals] : []),
  ];

  // Sort: active first, then closed, then scheduled. Within each, prefer
  // the highest combined wins (most narrative weight).
  const order: Record<PlayoffSeriesResponse["status"], number> = {
    active: 0,
    closed: 1,
    scheduled: 2,
  };
  const sorted = [...all].sort((a, b) => {
    const byStatus = order[a.status] - order[b.status];
    if (byStatus !== 0) return byStatus;
    const aPlayed = a.top_wins + a.bottom_wins;
    const bPlayed = b.top_wins + b.bottom_wins;
    return bPlayed - aPlayed;
  });

  return sorted.slice(0, 4).map((series) => {
    const { top } = seriesWinProbability(series.top_wins, series.bottom_wins);
    return { series, topWP: top };
  });
}

function recordSummary(series: PlayoffSeriesResponse): string {
  const top = series.top_seed_team_abbr ?? "TBD";
  const bot = series.bottom_seed_team_abbr ?? "TBD";
  if (series.top_wins === 0 && series.bottom_wins === 0) {
    return `Series tied 0-0`;
  }
  if (series.top_wins === series.bottom_wins) {
    return `Tied ${series.top_wins}-${series.bottom_wins}`;
  }
  if (series.top_wins > series.bottom_wins) {
    return `${top} leads ${series.top_wins}-${series.bottom_wins}`;
  }
  return `${bot} leads ${series.bottom_wins}-${series.top_wins}`;
}

function nextGameLabel(series: PlayoffSeriesResponse): string {
  if (series.status === "closed") {
    const win = Math.max(series.top_wins, series.bottom_wins);
    const loss = Math.min(series.top_wins, series.bottom_wins);
    return `Series closed · ${win}-${loss}`;
  }
  if (series.status === "scheduled") {
    return "Game 1 — tipoff TBD";
  }
  // active.
  const played = series.games.filter(
    (g) => g.home_pts != null && g.away_pts != null
  ).length;
  const next = played + 1;
  return `Game ${next} next`;
}

function WinBar({ series }: { series: PlayoffSeriesResponse }) {
  // 7 cells. The first `top_wins` are forest, the next `bottom_wins` are
  // danger, the remainder are muted/unplayed. Closed series render
  // slightly desaturated.
  const cells = Array.from({ length: 7 }, (_, i) => {
    if (i < series.top_wins) return "top" as const;
    if (i < series.top_wins + series.bottom_wins) return "bottom" as const;
    return "empty" as const;
  });
  const muted = series.status === "closed" ? 0.55 : 1;
  return (
    <div
      className="flex gap-1"
      role="img"
      aria-label={`Series progress: ${series.top_wins}-${series.bottom_wins}`}
      style={{ opacity: muted }}
    >
      {cells.map((cell, i) => (
        <div
          key={i}
          className="h-2 flex-1 rounded-sm"
          style={{
            background:
              cell === "top"
                ? "var(--accent)"
                : cell === "bottom"
                  ? "var(--danger-ink)"
                  : "var(--surface-alt)",
          }}
        />
      ))}
    </div>
  );
}

function TrackerCard({ entry }: { entry: TrackerSeries }) {
  const { series, topWP } = entry;
  const top = series.top_seed_team_abbr ?? "TBD";
  const bot = series.bottom_seed_team_abbr ?? "TBD";
  const closed = series.status === "closed";
  return (
    <Link
      href={`/pre-read?series_id=${encodeURIComponent(series.series_id)}`}
      className="block bip-panel rounded-2xl px-4 py-3 hover:-translate-y-0.5 transition-transform focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
      style={{
        background: closed ? "rgba(255,249,241,0.42)" : "rgba(255,249,241,0.7)",
        opacity: closed ? 0.78 : 1,
      }}
    >
      <div className="flex items-baseline justify-between gap-2 mb-2">
        <p
          className="font-semibold text-[var(--foreground)]"
          style={{
            fontFamily: "var(--font-display)",
            fontSize: 14,
            letterSpacing: "-0.01em",
          }}
        >
          #{series.top_seed} {top}{" "}
          <span className="text-[var(--muted)] font-normal">vs</span>{" "}
          #{series.bottom_seed} {bot}
        </p>
        <span
          className="tabular-nums font-bold"
          style={{
            fontFamily: "var(--font-geist-mono)",
            fontSize: 11,
            color: closed ? "var(--muted)" : "var(--accent)",
          }}
        >
          {Math.round(topWP * 100)}%
        </span>
      </div>
      <WinBar series={series} />
      <div
        className="mt-2 flex items-baseline justify-between gap-2"
        style={{
          fontFamily: "var(--font-geist-mono)",
          fontSize: 11,
          letterSpacing: "0.04em",
          color: "var(--muted)",
        }}
      >
        <span>{recordSummary(series)}</span>
        <span>{nextGameLabel(series)}</span>
      </div>
    </Link>
  );
}

export default function SeriesTrackerStrip() {
  const { season } = useSeasonPhase();
  const seasonKey = season ?? ACTIVE_SEASON_FALLBACK;

  const { data, isLoading, error } = useSWR<PlayoffBracketResponse>(
    ["broadsheet-tracker-strip", seasonKey],
    () => getBracket(seasonKey),
    {
      refreshInterval: 5 * 60_000,
      revalidateOnFocus: false,
    }
  );

  const tracked = pickTrackedSeries(data);

  return (
    <section className="bip-panel rounded-[1.85rem] overflow-hidden">
      <header className="px-5 py-4 border-b border-[var(--border)] flex items-end justify-between gap-4">
        <div>
          <p className="bip-kicker mb-1">Series Tracker</p>
          <h3
            className="bip-display font-bold text-[var(--foreground)]"
            style={{
              fontSize: "1.4rem",
              letterSpacing: "-0.015em",
            }}
          >
            Where the math sits.
          </h3>
        </div>
        <Link
          href="/bracket"
          className="text-xs bip-link shrink-0 font-medium"
        >
          All series →
        </Link>
      </header>
      <div className="p-4">
        {isLoading && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 animate-pulse">
            {Array.from({ length: 4 }).map((_, i) => (
              <div
                key={i}
                className="rounded-2xl border border-[var(--border)]"
                style={{
                  height: 96,
                  background: "rgba(255,249,241,0.5)",
                }}
              />
            ))}
          </div>
        )}
        {!isLoading && error && (
          <p
            className="px-1 py-4 text-sm italic text-[var(--muted)]"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Tracker is between editions.
          </p>
        )}
        {!isLoading && !error && tracked.length === 0 && (
          <p
            className="px-1 py-4 text-sm italic text-[var(--muted)]"
            style={{ fontFamily: "var(--font-display)" }}
          >
            No playoff series active yet.
          </p>
        )}
        {!isLoading && !error && tracked.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {tracked.map((entry) => (
              <TrackerCard key={entry.series.series_id} entry={entry} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
