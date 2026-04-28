"use client";

import { useMemo } from "react";
import useSWR from "swr";
import { getLeaderboard } from "@/lib/api";
import { useSeasonPhase } from "@/hooks/useSeasonPhase";
import type { LeaderboardEntry, LeaderboardResponse } from "@/lib/types";

/**
 * Sprint 73B — Postseason Performer Heatmap.
 *
 * USG% × TS%-delta scatter that surfaces playoff-vs-regular-season divergence
 * for rotation players. The plotting math is borrowed from the Sprint 58
 * `<EfficiencyLoadCard>` (USG axis 10–40, TS axis 45–65). For v1 we fetch
 * the leaderboard sorted by `usg_pct` for both `season_type=Regular Season`
 * and `season_type=Playoffs`, then compute the TS% delta client-side.
 *
 * Player position is not exposed on `LeaderboardEntry`, so v1 colors dots by
 * the sign of the TS% delta (gainer vs slipper) instead of by G/F/C bucket.
 * A small follow-on Stream A endpoint that returns position alongside the
 * leaderboard rows would let us swap to the spec'd G/F/C palette — see the
 * comment at the bottom of this file.
 */

interface RotationPoint {
  player_id: number;
  player_name: string;
  team_abbreviation: string;
  usg_pct_playoff: number;
  ts_pct_playoff: number;
  ts_pct_regular: number;
  ts_delta: number;
  gp_playoff: number;
  min_pg_playoff: number;
}

const PLOT_W = 520;
const PLOT_H = 320;
const PAD_L = 44;
const PAD_R = 24;
const PAD_T = 28;
const PAD_B = 36;

// USG axis bounds. Playoff usage tends to compress slightly compared to
// regular-season usage so we keep the same 10–40 box from EfficiencyLoadCard.
const USG_MIN = 10;
const USG_MAX = 40;
// TS%-delta bounds: most playoff-vs-regular swings sit within ±10 TS%.
const TS_DELTA_MIN = -0.1;
const TS_DELTA_MAX = 0.1;

function clamp(value: number, lo: number, hi: number): number {
  if (Number.isNaN(value)) return lo;
  if (value < lo) return lo;
  if (value > hi) return hi;
  return value;
}

function colorForDelta(delta: number): string {
  if (delta > 0.005) return "#21483b"; // forest-green gainer
  if (delta < -0.005) return "#a7484a"; // terracotta slipper
  return "#7e7468"; // neutral
}

function buildPoints(
  regular: LeaderboardEntry[] | undefined,
  playoff: LeaderboardEntry[] | undefined
): RotationPoint[] {
  if (!regular || !playoff) return [];
  const regularByPlayer = new Map<number, LeaderboardEntry>();
  for (const entry of regular) regularByPlayer.set(entry.player_id, entry);

  const points: RotationPoint[] = [];
  for (const playoffEntry of playoff) {
    const usg = playoffEntry.metric_values.usg_pct ?? null;
    const tsPlayoff = playoffEntry.ts_pct ?? playoffEntry.metric_values.ts_pct ?? null;
    const minPg = playoffEntry.metric_values.min_pg ?? null;
    if (usg == null || tsPlayoff == null) continue;
    if (minPg != null && minPg < 8) continue;
    if (playoffEntry.gp < 2) continue;

    const regularEntry = regularByPlayer.get(playoffEntry.player_id);
    const tsRegular = regularEntry?.ts_pct ?? regularEntry?.metric_values?.ts_pct ?? null;
    if (tsRegular == null) continue;

    points.push({
      player_id: playoffEntry.player_id,
      player_name: playoffEntry.player_name,
      team_abbreviation: playoffEntry.team_abbreviation,
      usg_pct_playoff: usg,
      ts_pct_playoff: tsPlayoff,
      ts_pct_regular: tsRegular,
      ts_delta: tsPlayoff - tsRegular,
      gp_playoff: playoffEntry.gp,
      min_pg_playoff: minPg ?? 0,
    });
  }
  return points;
}

interface ScatterProps {
  points: RotationPoint[];
}

function Scatter({ points }: ScatterProps) {
  const xFor = (usg: number) =>
    PAD_L + ((clamp(usg, USG_MIN, USG_MAX) - USG_MIN) / (USG_MAX - USG_MIN)) * (PLOT_W - PAD_L - PAD_R);
  const yFor = (delta: number) =>
    PAD_T + (1 - (clamp(delta, TS_DELTA_MIN, TS_DELTA_MAX) - TS_DELTA_MIN) / (TS_DELTA_MAX - TS_DELTA_MIN)) *
      (PLOT_H - PAD_T - PAD_B);

  const x0 = xFor((USG_MIN + USG_MAX) / 2);
  const y0 = yFor(0);

  return (
    <svg viewBox={`0 0 ${PLOT_W} ${PLOT_H}`} width="100%" style={{ display: "block" }}>
      {/* axis box */}
      <rect
        x={PAD_L}
        y={PAD_T}
        width={PLOT_W - PAD_L - PAD_R}
        height={PLOT_H - PAD_T - PAD_B}
        fill="rgba(248,244,232,0.6)"
        stroke="var(--border)"
        strokeWidth="0.8"
      />
      {/* quadrant cross-hairs */}
      <line
        x1={x0}
        x2={x0}
        y1={PAD_T}
        y2={PLOT_H - PAD_B}
        stroke="rgba(47,43,36,0.18)"
        strokeDasharray="3 4"
      />
      <line
        x1={PAD_L}
        x2={PLOT_W - PAD_R}
        y1={y0}
        y2={y0}
        stroke="rgba(47,43,36,0.18)"
        strokeDasharray="3 4"
      />
      {/* quadrant labels — full var(--foreground) for WCAG AA contrast on
          small text rather than the muted token. */}
      <text
        x={PLOT_W - PAD_R - 6}
        y={PAD_T + 14}
        fontFamily="var(--font-geist-mono)"
        fontSize="10"
        fill="var(--foreground)"
        textAnchor="end"
        fontWeight="700"
      >
        Volume + efficient gainers
      </text>
      <text
        x={PAD_L + 6}
        y={PAD_T + 14}
        fontFamily="var(--font-geist-mono)"
        fontSize="10"
        fill="var(--foreground)"
        fontWeight="700"
      >
        Lower volume, more efficient
      </text>
      <text
        x={PLOT_W - PAD_R - 6}
        y={PLOT_H - PAD_B - 6}
        fontFamily="var(--font-geist-mono)"
        fontSize="10"
        fill="var(--foreground)"
        textAnchor="end"
        fontWeight="700"
      >
        More volume, less efficient
      </text>
      <text
        x={PAD_L + 6}
        y={PLOT_H - PAD_B - 6}
        fontFamily="var(--font-geist-mono)"
        fontSize="10"
        fill="var(--foreground)"
        fontWeight="700"
      >
        Lower volume + slipping
      </text>
      {/* axis ticks */}
      {[USG_MIN, (USG_MIN + USG_MAX) / 2, USG_MAX].map((tick) => (
        <text
          key={`x-${tick}`}
          x={xFor(tick)}
          y={PLOT_H - PAD_B + 14}
          fontFamily="var(--font-geist-mono)"
          fontSize="9"
          fill="var(--muted)"
          textAnchor="middle"
        >
          {tick.toFixed(0)}%
        </text>
      ))}
      {[TS_DELTA_MAX, 0, TS_DELTA_MIN].map((tick) => (
        <text
          key={`y-${tick}`}
          x={PAD_L - 6}
          y={yFor(tick) + 3}
          fontFamily="var(--font-geist-mono)"
          fontSize="9"
          fill="var(--muted)"
          textAnchor="end"
        >
          {(tick > 0 ? "+" : "") + (tick * 100).toFixed(0)}
        </text>
      ))}
      {/* axis labels */}
      <text
        x={(PLOT_W + PAD_L - PAD_R) / 2}
        y={PLOT_H - 6}
        fontFamily="var(--font-geist-mono)"
        fontSize="10"
        fill="var(--muted-strong)"
        textAnchor="middle"
      >
        Playoff USG%
      </text>
      <text
        x={12}
        y={(PLOT_H + PAD_T - PAD_B) / 2}
        fontFamily="var(--font-geist-mono)"
        fontSize="10"
        fill="var(--muted-strong)"
        textAnchor="middle"
        transform={`rotate(-90 12 ${(PLOT_H + PAD_T - PAD_B) / 2})`}
      >
        TS% Δ vs reg. season
      </text>
      {/* points */}
      {points.map((point) => (
        <g key={point.player_id}>
          <title>
            {point.player_name} ({point.team_abbreviation}) · USG {point.usg_pct_playoff.toFixed(1)}% · playoff TS {(
              point.ts_pct_playoff * 100
            ).toFixed(1)}% · Δ {(point.ts_delta * 100 > 0 ? "+" : "") + (point.ts_delta * 100).toFixed(1)}
          </title>
          <circle
            cx={xFor(point.usg_pct_playoff)}
            cy={yFor(point.ts_delta)}
            r={4}
            fill={colorForDelta(point.ts_delta)}
            stroke="#fcfffd"
            strokeWidth="1.2"
            opacity="0.92"
          />
        </g>
      ))}
    </svg>
  );
}

interface PostseasonHeatmapProps {
  /** Optional season override; otherwise uses `useSeasonPhase().season`. */
  season?: string;
}

export default function PostseasonHeatmap({ season: seasonProp }: PostseasonHeatmapProps = {}) {
  const { season: phaseSeason, isPlayoffs } = useSeasonPhase();
  const season = seasonProp ?? phaseSeason ?? null;

  const { data: regular } = useSWR<LeaderboardResponse>(
    season ? ["lb-usg-regular", season] : null,
    () => getLeaderboard("usg_pct", season as string, "Regular Season", 100)
  );
  const { data: playoff, error: playoffError } = useSWR<LeaderboardResponse>(
    season ? ["lb-usg-playoff", season] : null,
    () => getLeaderboard("usg_pct", season as string, "Playoffs", 100)
  );

  const points = useMemo(
    () => buildPoints(regular?.entries, playoff?.entries),
    [regular, playoff]
  );

  if (!isPlayoffs) return null;

  return (
    <section className="bip-panel rounded-[1.8rem] p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <p className="bip-kicker">Postseason Performer Heatmap</p>
          <h2 className="bip-display mt-1 text-2xl font-semibold text-[var(--foreground)]">
            Where playoff usage meets efficiency divergence.
          </h2>
        </div>
        <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
          ≥8 mpg · ≥2 playoff games
        </span>
      </div>

      {playoffError ? (
        <div className="mt-4 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-4 text-sm text-[var(--muted-strong)]">
          Could not load playoff leaderboard for {season ?? "this season"}.
        </div>
      ) : !regular || !playoff ? (
        <div className="mt-4 h-[320px] animate-pulse rounded-lg bg-[var(--surface-alt)]" />
      ) : points.length === 0 ? (
        <div className="mt-4 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-4 text-sm text-[var(--muted-strong)]">
          Not enough playoff sample yet — check back once rotations log ≥2 playoff games and ≥8 mpg.
        </div>
      ) : (
        <>
          <div className="mt-4">
            <Scatter points={points} />
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-4 text-[11px] text-[var(--muted-strong)]">
            <span className="inline-flex items-center gap-2">
              <span
                aria-hidden
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ background: "#21483b" }}
              />
              TS% gainer
            </span>
            <span className="inline-flex items-center gap-2">
              <span
                aria-hidden
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ background: "#a7484a" }}
              />
              TS% slipper
            </span>
            <span className="inline-flex items-center gap-2">
              <span
                aria-hidden
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ background: "#7e7468" }}
              />
              Held the line
            </span>
            <span>{points.length} rotation players plotted.</span>
          </div>
        </>
      )}
    </section>
  );
}

// Position-bucket coloring (G/F/C) is a Stream A follow-on: the leaderboard
// API does not expose `position` per row, and we don't want to fan out a
// per-player profile fetch from the leaderboards page. When a leaderboard
// payload that includes `position_bucket` ships, swap `colorForDelta(...)` for
// a position-bucket palette and update the legend.
