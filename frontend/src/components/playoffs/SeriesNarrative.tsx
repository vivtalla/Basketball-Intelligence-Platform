"use client";

import Link from "next/link";
import useSWR from "swr";
import { useEffect, useMemo, useState } from "react";
import { getBracket } from "@/lib/api";
import { useSeasonPhase } from "@/hooks/useSeasonPhase";
import type {
  PlayoffBracketResponse,
  PlayoffSeriesResponse,
} from "@/lib/types";

const ROTATION_MS = 3000;

function roundLabel(round: number): string {
  switch (round) {
    case 1:
      return "First Round";
    case 2:
      return "Conference Semifinals";
    case 3:
      return "Conference Finals";
    case 4:
      return "Finals";
    default:
      return `Round ${round}`;
  }
}

function seriesState(series: PlayoffSeriesResponse): string {
  const top = series.top_seed_team_abbr ?? "TBD";
  const bottom = series.bottom_seed_team_abbr ?? "TBD";
  if (series.status === "scheduled") {
    return `${top} vs ${bottom} · Tipoff TBD`;
  }
  if (series.status === "closed") {
    if (series.top_wins > series.bottom_wins) {
      return `${top} won ${series.top_wins}-${series.bottom_wins}`;
    }
    if (series.bottom_wins > series.top_wins) {
      return `${bottom} won ${series.bottom_wins}-${series.top_wins}`;
    }
    return `${top} vs ${bottom} · Series closed`;
  }
  if (series.top_wins === series.bottom_wins) {
    return `${top} ${series.top_wins} - ${series.bottom_wins} ${bottom}`;
  }
  if (series.top_wins > series.bottom_wins) {
    return `${top} leads ${bottom} ${series.top_wins}-${series.bottom_wins}`;
  }
  return `${bottom} leads ${top} ${series.bottom_wins}-${series.top_wins}`;
}

function whatsNext(series: PlayoffSeriesResponse): string {
  if (series.status === "closed") {
    return "Series complete — advance to next round.";
  }
  if (series.status === "scheduled") {
    return "Series tipoff to be announced.";
  }
  const played = series.games.filter(
    (g) => g.home_pts != null && g.away_pts != null
  ).length;
  const next = played + 1;
  const lead = Math.max(series.top_wins, series.bottom_wins);
  const trail = Math.min(series.top_wins, series.bottom_wins);
  if (lead === 3) {
    const leader =
      series.top_wins > series.bottom_wins
        ? series.top_seed_team_abbr
        : series.bottom_seed_team_abbr;
    return `${leader ?? "Leader"} can clinch in Game ${next}.`;
  }
  if (lead === trail) {
    return `Game ${next} is a swing game with the series even.`;
  }
  return `Game ${next} is must-win for the trailing side.`;
}

function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const mql = window.matchMedia("(prefers-reduced-motion: reduce)");
    // Initial sync from the platform — subscribing to an external value, which
    // is the documented escape from react-hooks/set-state-in-effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setReduced(mql.matches);
    const listener = (e: MediaQueryListEvent) => setReduced(e.matches);
    mql.addEventListener("change", listener);
    return () => mql.removeEventListener("change", listener);
  }, []);
  return reduced;
}

function SeriesSummaryCard({ series }: { series: PlayoffSeriesResponse }) {
  return (
    <Link
      href={`/beta/pre-read?series_id=${encodeURIComponent(series.series_id)}`}
      className="block bip-panel rounded-[1.4rem] px-5 py-4 hover:-translate-y-0.5 hover:border-[var(--accent)] transition-all"
    >
      <p className="bip-kicker mb-1.5 text-[var(--accent)]">
        {roundLabel(series.round)}
      </p>
      <p
        className="bip-display text-lg font-semibold text-[var(--foreground)]"
        style={{ letterSpacing: "-0.01em" }}
      >
        {seriesState(series)}
      </p>
      <p className="mt-1.5 text-sm leading-5 text-[var(--muted)]">
        {whatsNext(series)}
      </p>
    </Link>
  );
}

export default function SeriesNarrative() {
  const { season, isPlayoffs } = useSeasonPhase();
  const reducedMotion = usePrefersReducedMotion();

  const { data, isLoading } = useSWR<PlayoffBracketResponse>(
    isPlayoffs && season ? ["bracket-narrative", season] : null,
    () => getBracket(season as string)
  );

  const activeSeries: PlayoffSeriesResponse[] = useMemo(() => {
    if (!data) return [];
    const all: PlayoffSeriesResponse[] = [
      ...data.east,
      ...data.west,
      ...(data.finals ? [data.finals] : []),
    ];
    // Active first, then scheduled, then closed — surface live drama up front.
    const order: Record<PlayoffSeriesResponse["status"], number> = {
      active: 0,
      scheduled: 1,
      closed: 2,
    };
    return all
      .filter((s) => s.top_seed_team_abbr || s.bottom_seed_team_abbr)
      .sort((a, b) => order[a.status] - order[b.status]);
  }, [data]);

  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    if (reducedMotion) return;
    if (paused) return;
    if (activeSeries.length <= 1) return;
    const id = window.setInterval(() => {
      setIndex((i) => (i + 1) % activeSeries.length);
    }, ROTATION_MS);
    return () => window.clearInterval(id);
  }, [reducedMotion, paused, activeSeries.length]);

  // Keep index in range if the underlying list shrinks. Derive instead of
  // setting in an effect so we don't trip react-hooks/set-state-in-effect.
  const safeIndex = activeSeries.length > 0 ? index % activeSeries.length : 0;

  if (!isPlayoffs) return null;

  if (isLoading) {
    return (
      <section className="bip-panel rounded-[1.85rem] p-5 animate-pulse">
        <div className="h-3 w-24 rounded bg-[var(--surface-alt)] mb-3" />
        <div className="h-5 w-64 rounded bg-[var(--surface-alt)] mb-2" />
        <div className="h-3 w-72 rounded bg-[var(--surface-alt)]" />
      </section>
    );
  }

  if (!activeSeries.length) {
    return null;
  }

  if (reducedMotion) {
    // Show all stacked when motion is disabled — keeps content accessible.
    return (
      <section
        aria-label="Series narrative"
        className="space-y-3"
      >
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="bip-kicker mb-1.5">Playoff Storylines</p>
            <h2 className="bip-display text-3xl font-semibold text-[var(--foreground)]">
              Every active <span className="text-[var(--accent)]">series.</span>
            </h2>
          </div>
          <Link href="/bracket" className="text-sm bip-link shrink-0 font-medium">
            Full bracket →
          </Link>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {activeSeries.map((s) => (
            <SeriesSummaryCard key={s.series_id} series={s} />
          ))}
        </div>
      </section>
    );
  }

  const current = activeSeries[safeIndex] ?? activeSeries[0];

  return (
    <section
      aria-label="Series narrative"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      <div className="mb-4 flex items-end justify-between gap-4">
        <div>
          <p className="bip-kicker mb-1.5">Playoff Storylines</p>
          <h2 className="bip-display text-3xl font-semibold text-[var(--foreground)]">
            Right now in the <span className="text-[var(--accent)]">postseason.</span>
          </h2>
        </div>
        <Link href="/bracket" className="text-sm bip-link shrink-0 font-medium">
          Full bracket →
        </Link>
      </div>

      <SeriesSummaryCard series={current} />

      {activeSeries.length > 1 && (
        <div
          className="mt-3 flex items-center justify-center gap-1.5"
          role="tablist"
          aria-label="Active playoff series"
        >
          {activeSeries.map((s, i) => (
            <button
              key={s.series_id}
              type="button"
              role="tab"
              aria-selected={i === safeIndex}
              aria-label={`Show ${s.series_id}`}
              onClick={() => setIndex(i)}
              className="transition-all"
              style={{
                width: i === safeIndex ? 18 : 6,
                height: 6,
                borderRadius: 3,
                background:
                  i === safeIndex ? "var(--accent)" : "var(--surface-alt)",
                border: "1px solid var(--border)",
                cursor: "pointer",
              }}
            />
          ))}
        </div>
      )}
    </section>
  );
}
