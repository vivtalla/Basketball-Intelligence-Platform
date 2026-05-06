"use client";

import { useMemo, useState } from "react";
import useSWR from "swr";
import { getBracket, getSeriesSimulationWithOverrides } from "@/lib/api";
import { useSeasonPhase } from "@/hooks/useSeasonPhase";
import type {
  PlayoffBracketResponse,
  PlayoffSeriesResponse,
  SeriesProjectionEntry,
  SeriesSimulationResponse,
} from "@/lib/types";

interface Props {
  defaultSeriesId?: string;
}

interface SeriesOption {
  series_id: string;
  label: string;
}

function flattenSeries(
  bracket: PlayoffBracketResponse | undefined
): PlayoffSeriesResponse[] {
  if (!bracket) return [];
  const list: PlayoffSeriesResponse[] = [];
  list.push(...bracket.east);
  list.push(...bracket.west);
  if (bracket.finals) list.push(bracket.finals);
  return list;
}

function seriesLabel(series: PlayoffSeriesResponse): string {
  const top =
    series.top_seed_team_abbr ??
    (series.top_seed != null ? `#${series.top_seed}` : "TBD");
  const bottom =
    series.bottom_seed_team_abbr ??
    (series.bottom_seed != null ? `#${series.bottom_seed}` : "TBD");
  const round =
    series.round === 1
      ? "R1"
      : series.round === 2
      ? "R2"
      : series.round === 3
      ? "CF"
      : series.round === 4
      ? "Finals"
      : `R${series.round}`;
  return `${round} · ${top} vs ${bottom} (${series.top_wins}-${series.bottom_wins})`;
}

const PAD = { l: 32, r: 16, t: 18, b: 28 };
const W = 720;
const H = 220;

function ProjectionChart({ projection }: { projection: SeriesProjectionEntry[] }) {
  // Memoize the chart geometry so the SVG path + per-point coords don't get
  // recomputed every time a parent (the SWR-driven simulator section) re-renders.
  const geom = useMemo(() => {
    const x = (i: number) =>
      PAD.l + (projection.length === 1 ? 0 : (i / (projection.length - 1)) * (W - PAD.l - PAD.r));
    const y = (p: number) => PAD.t + (1 - p) * (H - PAD.t - PAD.b);
    const path = projection
      .map((entry, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(entry.home_win_prob).toFixed(1)}`)
      .join(" ");
    return { x, y, path };
  }, [projection]);

  if (projection.length === 0) {
    return (
      <div className="flex h-[180px] items-center justify-center text-xs text-[var(--muted)]">
        Series is decided — no remaining projection.
      </div>
    );
  }
  const { x, y, path } = geom;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: "block" }}>
      <defs>
        <linearGradient id="cv-series-wp" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="#21483b" stopOpacity="0.28" />
          <stop offset="100%" stopColor="#21483b" stopOpacity="0" />
        </linearGradient>
      </defs>
      {/* baseline 50% */}
      <line
        x1={PAD.l}
        x2={W - PAD.r}
        y1={y(0.5)}
        y2={y(0.5)}
        stroke="rgba(53,41,33,0.18)"
        strokeWidth="0.8"
      />
      <text
        x={PAD.l - 6}
        y={y(0.5) + 4}
        fontFamily="var(--font-geist-mono)"
        fontSize="9"
        fill="var(--muted)"
        textAnchor="end"
      >
        50
      </text>
      {/* area under the line */}
      <path
        d={`${path} L ${x(projection.length - 1).toFixed(1)} ${y(0)} L ${x(0).toFixed(1)} ${y(0)} Z`}
        fill="url(#cv-series-wp)"
      />
      {/* line */}
      <path
        d={path}
        fill="none"
        stroke="var(--accent)"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* dots + game labels */}
      {projection.map((entry, i) => (
        <g key={entry.game_num}>
          <circle
            cx={x(i)}
            cy={y(entry.home_win_prob)}
            r="4"
            fill="var(--signal)"
            stroke="#fcfffd"
            strokeWidth="1.5"
          />
          <text
            x={x(i)}
            y={H - 8}
            fontFamily="var(--font-geist-mono)"
            fontSize="10"
            fill="var(--muted)"
            textAnchor="middle"
          >
            G{entry.game_num}
          </text>
          <text
            x={x(i)}
            y={y(entry.home_win_prob) - 10}
            fontFamily="var(--font-geist-mono)"
            fontSize="9"
            fill="var(--foreground)"
            textAnchor="middle"
            fontWeight="700"
          >
            {Math.round(entry.home_win_prob * 100)}%
          </text>
        </g>
      ))}
    </svg>
  );
}

export default function SeriesWPSimulator({ defaultSeriesId }: Props) {
  const { season, isPlayoffs } = useSeasonPhase();

  const { data: bracket } = useSWR<PlayoffBracketResponse>(
    isPlayoffs && season ? ["bracket", season] : null,
    () => getBracket(season as string)
  );

  const options = useMemo<SeriesOption[]>(() => {
    return flattenSeries(bracket).map((s) => ({
      series_id: s.series_id,
      label: seriesLabel(s),
    }));
  }, [bracket]);

  // Initialize with default or first available active/scheduled series.
  const initialSeriesId = useMemo(() => {
    if (defaultSeriesId) return defaultSeriesId;
    if (!bracket) return null;
    const all = flattenSeries(bracket);
    const active = all.find((s) => s.status === "active");
    if (active) return active.series_id;
    return all[0]?.series_id ?? null;
  }, [defaultSeriesId, bracket]);

  const [selectedSeriesId, setSelectedSeriesId] = useState<string | null>(null);
  const [overrideState, setOverrideState] = useState<{
    topWins: number;
    bottomWins: number;
  } | null>(null);

  const effectiveSeriesId = selectedSeriesId ?? initialSeriesId;

  const { data: simulation, error: simError } = useSWR<SeriesSimulationResponse>(
    effectiveSeriesId
      ? [
          "series-sim",
          effectiveSeriesId,
          overrideState?.topWins ?? null,
          overrideState?.bottomWins ?? null,
        ]
      : null,
    () =>
      getSeriesSimulationWithOverrides(effectiveSeriesId as string, {
        overrideTopWins: overrideState?.topWins ?? null,
        overrideBottomWins: overrideState?.bottomWins ?? null,
      })
  );

  const handleHypothetical = (winner: "top" | "bottom") => {
    if (!effectiveSeriesId || !simulation) return;
    const current = simulation.current_state;
    setOverrideState({
      topWins: Math.min(4, current.top_wins + (winner === "top" ? 1 : 0)),
      bottomWins: Math.min(4, current.bottom_wins + (winner === "bottom" ? 1 : 0)),
    });
    setSelectedSeriesId(effectiveSeriesId);
  };

  if (!isPlayoffs) return null;

  const currentState = simulation?.current_state;
  const topAbbr = currentState?.top_seed_team_abbr ?? "Top";
  const bottomAbbr = currentState?.bottom_seed_team_abbr ?? "Bottom";
  const seriesDecided = currentState?.status === "closed";

  return (
    <section className="bip-panel rounded-[1.8rem] p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <p className="bip-kicker">Series WP Simulator</p>
          <h2 className="bip-display mt-1 text-2xl font-semibold text-[var(--foreground)]">
            What&apos;s left to play.
          </h2>
        </div>
        <label className="text-xs text-[var(--muted)]">
          Series
          <select
            value={effectiveSeriesId ?? ""}
            onChange={(event) => {
              setSelectedSeriesId(event.target.value || null);
              setOverrideState(null);
            }}
            className="ml-2 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--foreground)]"
          >
            {options.length === 0 && <option value="">No series available</option>}
            {options.map((option) => (
              <option key={option.series_id} value={option.series_id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {simError ? (
        <div className="mt-4 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-4 text-sm text-[var(--muted-strong)]">
          Could not load series simulation.
        </div>
      ) : !simulation ? (
        <div className="mt-4 h-[180px] animate-pulse rounded-lg bg-[var(--surface-alt)]" />
      ) : (
        <>
          <div className="mt-3 flex flex-wrap gap-3 text-sm">
            <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-2">
              <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
                Series
              </span>
              <div className="font-semibold tabular-nums text-[var(--foreground)]">
                {topAbbr} {currentState?.top_wins ?? 0} – {currentState?.bottom_wins ?? 0} {bottomAbbr}
              </div>
              {overrideState && (
                <div className="mt-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--signal)]">
                  Hypothetical
                </div>
              )}
            </div>
            <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-2">
              <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
                {topAbbr} series WP
              </span>
              <div className="font-semibold tabular-nums text-[var(--foreground)]">
                {Math.round((simulation.top_seed_series_win_prob ?? 0) * 100)}%
              </div>
            </div>
            <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-2">
              <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
                {bottomAbbr} series WP
              </span>
              <div className="font-semibold tabular-nums text-[var(--foreground)]">
                {Math.round((simulation.bottom_seed_series_win_prob ?? 0) * 100)}%
              </div>
            </div>
            <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-2">
              <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
                Trials
              </span>
              <div className="font-semibold tabular-nums text-[var(--foreground)]">
                {simulation.trials.toLocaleString()}
              </div>
            </div>
          </div>

          <div className="mt-4">
            <ProjectionChart projection={simulation.projection} />
          </div>
          <p className="mt-2 text-[11px] leading-5 text-[var(--muted)]">
            Per-game home WP for the projected remaining games (Monte-Carlo · {simulation.trials.toLocaleString()} trials).
          </p>

          {!seriesDecided && simulation.projection.length > 0 ? (
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
                What if
              </span>
              <button
                type="button"
                onClick={() => handleHypothetical("top")}
                className="rounded-full border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-1 text-xs font-semibold text-[var(--foreground)] hover:bg-[var(--surface)]"
                title="Re-simulate the series as if the top seed wins the next game."
              >
                {topAbbr} wins next
              </button>
              <button
                type="button"
                onClick={() => handleHypothetical("bottom")}
                className="rounded-full border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-1 text-xs font-semibold text-[var(--foreground)] hover:bg-[var(--surface)]"
                title="Re-simulate the series as if the bottom seed wins the next game."
              >
                {bottomAbbr} wins next
              </button>
              {overrideState ? (
                <button
                  type="button"
                  onClick={() => setOverrideState(null)}
                  className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1 text-xs font-semibold text-[var(--muted)] hover:text-[var(--foreground)]"
                >
                  Reset
                </button>
              ) : null}
            </div>
          ) : null}
        </>
      )}
    </section>
  );
}
