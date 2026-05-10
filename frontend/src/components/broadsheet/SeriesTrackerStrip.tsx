"use client";

import useSWR from "swr";
import Link from "next/link";
import { getBracket } from "@/lib/api";
import { useSeasonPhase } from "@/hooks/useSeasonPhase";
import ShareCardButton from "@/components/share/ShareCardButton";
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

  // Sprint 96 — Round-aware ordering. The "live round" is the highest round
  // number that has at least one started series (active or closed). Series
  // in the live round always outrank earlier rounds, so a fresh R2 G1 takes
  // priority over an R1 G7 even though R1 has more combined wins. When the
  // live round has fewer than 4 series, we backfill from the next-most-
  // recent round with the same internal sort.
  const startedRounds = all
    .filter((s) => s.status !== "scheduled")
    .map((s) => s.round);
  const liveRound = startedRounds.length > 0 ? Math.max(...startedRounds) : 0;

  const statusOrder: Record<PlayoffSeriesResponse["status"], number> = {
    active: 0,
    closed: 1,
    scheduled: 2,
  };
  const sorted = [...all].sort((a, b) => {
    // Live-round series first.
    const aLive = a.round === liveRound ? 0 : 1;
    const bLive = b.round === liveRound ? 0 : 1;
    if (aLive !== bLive) return aLive - bLive;
    // Active before closed before scheduled.
    const byStatus = statusOrder[a.status] - statusOrder[b.status];
    if (byStatus !== 0) return byStatus;
    // Within the same status, prefer the most recent round (descending).
    if (a.round !== b.round) return b.round - a.round;
    // Then prefer the most narrative-weighty (highest combined wins).
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
  // 7 cells. Played cells deep-link to /games/[game_id]; unplayed cells
  // fall through to the series pre-read. Cells are colored by which team
  // won that game (top=forest, bottom=danger). Hover lifts the cell so
  // the click target is discoverable.
  const muted = series.status === "closed" ? 0.55 : 1;

  // Map series_game_num (1-based) → game record so we can deep-link the
  // played cells. Some series have games in the array but with null
  // scores (e.g. live game in progress) — those still get a real
  // game_id, so they're linkable.
  const gameByNum = new Map<number, (typeof series.games)[number]>();
  for (const game of series.games ?? []) {
    if (game.series_game_num != null) {
      gameByNum.set(game.series_game_num, game);
    }
  }

  // Walk the games in order and decide colors based on cumulative top/bot
  // win count, which is consistent with the existing visual.
  let topSoFar = 0;
  let botSoFar = 0;
  const cells: Array<{
    color: string;
    href: string | null;
    label: string;
  }> = [];
  for (let i = 0; i < 7; i++) {
    const game = gameByNum.get(i + 1);
    let color = "var(--surface-alt)";
    let label = `Game ${i + 1} — upcoming`;
    if (game?.winner_team_id != null) {
      // We don't have top_seed_team_id here; use home/away + top_wins
      // ordering: alternate top/bot per the existing aggregate counters.
      // Since the API exposes top_wins/bottom_wins as aggregates, we
      // approximate by giving the next-in-order win to whichever side
      // still has slots remaining in those counters.
      if (topSoFar < series.top_wins) {
        color = "var(--accent)";
        topSoFar++;
        label = `Game ${i + 1} — ${series.top_seed_team_abbr ?? "top seed"} won`;
      } else if (botSoFar < series.bottom_wins) {
        color = "var(--danger-ink)";
        botSoFar++;
        label = `Game ${i + 1} — ${series.bottom_seed_team_abbr ?? "bottom seed"} won`;
      }
    } else if (game) {
      // Game scheduled or in progress (has game_id but no winner yet).
      label = `Game ${i + 1} — in progress / scheduled`;
    }
    const href = game ? `/games/${encodeURIComponent(game.game_id)}` : null;
    cells.push({ color, href, label });
  }

  // Suppress drag-to-select / accidental click targets — we want a
  // pointer cursor only on linkable cells.
  function Cell({ idx }: { idx: number }) {
    const cell = cells[idx];
    const inner = (
      <span
        className="block h-2 w-full rounded-sm transition-transform"
        style={{ background: cell.color }}
      />
    );
    if (cell.href == null) {
      return (
        <div
          className="flex-1"
          aria-label={cell.label}
          title={cell.label}
        >
          {inner}
        </div>
      );
    }
    return (
      <Link
        href={cell.href}
        aria-label={cell.label}
        title={cell.label}
        className="flex-1 group/cell rounded-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
        onClick={(e) => e.stopPropagation()}
      >
        <span
          className="block h-2 w-full rounded-sm transition-all group-hover/cell:h-3 group-hover/cell:-translate-y-0.5 group-hover/cell:shadow-sm"
          style={{ background: cell.color }}
        />
      </Link>
    );
  }

  return (
    <div
      className="flex gap-1 items-center"
      role="img"
      aria-label={`Series progress: ${series.top_wins}-${series.bottom_wins}`}
      style={{ opacity: muted }}
    >
      {cells.map((_, i) => (
        <Cell key={i} idx={i} />
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
    <div
      className="bip-panel rounded-2xl px-4 py-3"
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
        <div className="flex items-center gap-2">
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
          {/* Sprint 78 (CF1): compact share-card icon for this series. */}
          <ShareCardButton
            kind="series"
            id={series.series_id}
            compact
          />
        </div>
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
        <Link
          href={`/pre-read?series_id=${encodeURIComponent(series.series_id)}&team=${encodeURIComponent(top)}&opponent=${encodeURIComponent(bot)}`}
          className="bip-link"
        >
          {nextGameLabel(series)} →
        </Link>
      </div>
    </div>
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
