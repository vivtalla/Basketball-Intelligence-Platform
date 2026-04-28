"use client";

import { useMemo } from "react";
import WinProbabilityChart, {
  type WinProbPoint,
} from "@/components/WinProbabilityChart";
import type { PlayoffSeriesResponse } from "@/lib/types";

interface SeriesWPChartProps {
  series: PlayoffSeriesResponse;
}

const SERIES_GAMES = 7;

/**
 * Sprint 73B — Series-level win-probability wrapper around the existing
 * `<WinProbabilityChart>` (Sprint 70). Converts the per-game outcomes of
 * a `PlayoffSeriesResponse` into a cumulative WP curve for the top seed
 * across games 1..7.
 *
 * Cumulative WP for game N (completed games):
 *   wp_n = clamp(top_wins_after_game_n / 4, 0, 1)
 *
 * For unplayed games we extend a flat 0.5 forecast (sufficient for v1 —
 * the spec accepts a flat 0.5 baseline). The cumulative WP at game 0 is
 * seeded at 0.5 so the curve has a TIP point.
 *
 * The underlying chart's x-axis is hard-coded to a 0..48 minute scale, so
 * we map game numbers (0..7) into that range. The wrapper adds its own
 * labelled game-tick strip + a "current state" vertical marker beneath
 * the chart so the basketball-quarter labels of the inner chart are
 * visually scoped to series progress.
 */
export default function SeriesWPChart({ series }: SeriesWPChartProps) {
  const gamesPlayed = useMemo(
    () =>
      series.games.filter(
        (g) => g.home_pts != null && g.away_pts != null && g.winner_team_id != null
      ).length,
    [series.games]
  );

  const data = useMemo<WinProbPoint[]>(() => {
    const points: WinProbPoint[] = [];
    // Seed at TIP (game 0) so the line starts at coin-flip baseline.
    points.push({ t: 0, prob: 0.5 });

    let topWinsRunning = 0;
    let bottomWinsRunning = 0;
    const sortedGames = [...series.games].sort(
      (a, b) => (a.series_game_num ?? 0) - (b.series_game_num ?? 0)
    );

    for (let gameNum = 1; gameNum <= SERIES_GAMES; gameNum++) {
      const game = sortedGames.find((g) => g.series_game_num === gameNum);
      const isComplete =
        game != null &&
        game.winner_team_id != null &&
        game.home_pts != null &&
        game.away_pts != null;
      if (isComplete) {
        if (game.winner_team_id === series.top_seed_team_id) {
          topWinsRunning += 1;
        } else if (game.winner_team_id === series.bottom_seed_team_id) {
          bottomWinsRunning += 1;
        }
      }

      const t = (gameNum / SERIES_GAMES) * 48;
      let prob: number;
      if (isComplete) {
        prob = clamp01(topWinsRunning / 4);
      } else {
        // Flat 0.5 forecast for v1.
        prob = 0.5;
      }
      const point: WinProbPoint = { t, prob };
      if (isComplete) {
        point.event = `G${gameNum}`;
      }
      points.push(point);

      // Stop early once series is decided (one side has 4 wins).
      if (topWinsRunning >= 4 || bottomWinsRunning >= 4) {
        break;
      }
    }
    return points;
  }, [series.games, series.top_seed_team_id, series.bottom_seed_team_id]);

  const topAbbr = series.top_seed_team_abbr ?? "Top seed";

  // Tick strip mapping game number -> percentage along x-axis. Mirrors the
  // inner chart's PAD.l = 28 / PAD.r = 16 / W = 720 layout so our overlay
  // ticks line up with the underlying SVG.
  const xPctForGame = (gameNum: number): number => {
    const PAD_L = 28;
    const PAD_R = 16;
    const W = 720;
    const xPx = PAD_L + (gameNum / SERIES_GAMES) * (W - PAD_L - PAD_R);
    return (xPx / W) * 100;
  };

  return (
    <section className="bip-panel rounded-[1.8rem] p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <p className="bip-kicker">Series win probability</p>
          <h2 className="bip-display mt-1 text-2xl font-semibold text-[var(--foreground)]">
            Cumulative WP · {topAbbr}
          </h2>
        </div>
        <div className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
          {series.top_wins}-{series.bottom_wins} · {gamesPlayed}/{SERIES_GAMES} games
        </div>
      </div>

      <div className="mt-4 relative">
        <WinProbabilityChart data={data} />

        {/* Current-state vertical marker overlay. Positioned absolutely on
            top of the chart's SVG so it tracks the same x-axis. */}
        {gamesPlayed > 0 && gamesPlayed < SERIES_GAMES ? (
          <div
            aria-hidden
            className="pointer-events-none absolute inset-y-0"
            style={{
              left: `${xPctForGame(gamesPlayed)}%`,
              top: 0,
              bottom: 0,
              width: 0,
              borderLeft: "1.5px dashed rgba(180,137,61,0.6)",
            }}
          />
        ) : null}
      </div>

      {/* Game-number tick strip — overlays the inner chart's quarter labels
          with series-aware game labels. */}
      <div className="mt-2 flex justify-between text-[10px] font-semibold tracking-[0.12em] text-[var(--muted)]">
        {Array.from({ length: SERIES_GAMES }, (_, i) => {
          const gameNum = i + 1;
          const isPlayed = gameNum <= gamesPlayed;
          const isCurrent = gameNum === gamesPlayed + 1 && gamesPlayed < SERIES_GAMES;
          return (
            <span
              key={gameNum}
              style={{
                color: isCurrent
                  ? "var(--signal)"
                  : isPlayed
                  ? "var(--accent)"
                  : "var(--muted)",
                fontFamily: "var(--font-geist-mono)",
              }}
            >
              G{gameNum}
            </span>
          );
        })}
      </div>

      <p className="mt-4 text-xs leading-5 text-[var(--muted)]">
        Series WP for {topAbbr} · cumulative based on completed games. Unplayed
        games carry a flat 0.5 baseline; the dashed gold marker denotes current
        series progress.
      </p>
    </section>
  );
}

function clamp01(value: number): number {
  if (Number.isNaN(value)) return 0.5;
  if (value < 0) return 0;
  if (value > 1) return 1;
  return value;
}
