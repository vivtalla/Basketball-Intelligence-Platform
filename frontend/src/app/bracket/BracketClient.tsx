"use client";

import { Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import useSWR from "swr";
import HeroHardwood from "@/components/HeroHardwood";
import Reveal from "@/components/Reveal";
import PlayoffCommandCenter from "@/components/playoffs/PlayoffCommandCenter";
import { useSeasonPhase } from "@/hooks/useSeasonPhase";
import { getBracket } from "@/lib/api";
import type { PlayoffBracketResponse } from "@/lib/types";

const FALLBACK_SEASON = "2025-26";

function BracketSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {[0, 1].map((col) => (
        <div key={col} className="space-y-4">
          <div className="h-3 w-32 rounded bg-[rgba(33,72,59,0.08)] animate-pulse" />
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="h-24 rounded-2xl bg-[rgba(33,72,59,0.05)] border border-[var(--border)] animate-pulse"
            />
          ))}
        </div>
      ))}
    </div>
  );
}

function BracketPageInner() {
  const phase = useSeasonPhase();
  const season = phase.season ?? FALLBACK_SEASON;
  // Sprint 83c — deep-link support: /bracket?series_id=X selects that series
  // in the command center on first render.
  const searchParams = useSearchParams();
  const initialSeriesId = searchParams?.get("series_id") ?? null;

  // Fetch the bracket as soon as we know the season. Don't gate on
  // `phase.isPlayoffs` — if `/api/season-phase` hiccups, we still want the
  // bracket to load so the page doesn't fall back to the "Playoffs aren't
  // active" empty state while the postseason is live.
  const swrKey = !phase.isLoading ? `bracket-${season}` : null;
  const { data, error, isLoading, mutate } = useSWR<PlayoffBracketResponse>(
    swrKey,
    () => getBracket(season)
  );
  const hasBracketData = Boolean(
    data && (data.east.length || data.west.length || data.finals)
  );

  return (
    <div className="relative">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 rounded-[2.4rem] overflow-hidden"
      >
        <HeroHardwood opacity={0.07} />
      </div>

      <div className="space-y-8">
        {/* Header */}
        <div className="space-y-2">
          <Link href="/" className="bip-link inline-flex items-center gap-1 text-sm">
            ← Back to Home
          </Link>
          <div>
            <p className="bip-kicker">Postseason</p>
            <h1 className="bip-display text-4xl font-semibold text-[var(--foreground)]">
              Playoff Command Center
            </h1>
            <p className="mt-2 max-w-2xl text-[var(--muted)]">
              {phase.roundLabel
                ? `${phase.roundLabel} · ${season} · series intelligence, tactical edges, and reliability.`
                : phase.isPlayoffs
                ? `Live command center for the ${season} postseason.`
                : "The bracket lights up when the playoffs tip off."}
            </p>
          </div>
        </div>

        {/* Phase still loading — show skeleton until we know the phase */}
        {phase.isLoading && <BracketSkeleton />}

        {/* Bracket loading (data still in flight) */}
        {!phase.isLoading && !hasBracketData && (isLoading || (!data && !error)) && (
          <BracketSkeleton />
        )}

        {/* Error fetching the bracket — only when we have no data to show */}
        {!phase.isLoading && error && !hasBracketData && (
          <div className="bip-panel rounded-2xl p-6 text-center space-y-3">
            <p className="text-[var(--foreground)] font-medium">
              Could not load the playoff bracket.
            </p>
            <p className="text-sm text-[var(--muted)]">
              {error instanceof Error ? error.message : "Unknown error"}
            </p>
            <button
              onClick={() => mutate()}
              className="inline-flex items-center px-4 py-2 rounded-xl bg-[var(--accent)] text-white text-sm font-semibold"
            >
              Retry
            </button>
          </div>
        )}

        {/* Off-season / regular-season empty state — only when there is
            genuinely no bracket data to show. */}
        {!phase.isLoading && !isLoading && !error && !hasBracketData && (
          <div className="bip-empty rounded-3xl p-10 text-center">
            <h2 className="text-xl font-semibold text-[var(--foreground)]">
              Playoffs aren&apos;t active right now.
            </h2>
            <p className="mt-2 text-[var(--muted)]">Check back in April.</p>
            <Link
              href="/"
              className="mt-6 inline-flex items-center px-4 py-2 rounded-xl bg-[var(--accent)] text-white text-sm font-semibold"
            >
              Back to Home
            </Link>
          </div>
        )}

        {/* Live bracket */}
        {hasBracketData && data && (
          <Reveal>
            <PlayoffCommandCenter bracket={data} initialSeriesId={initialSeriesId} />
          </Reveal>
        )}
      </div>
    </div>
  );
}

export default function BracketClient() {
  return (
    <Suspense fallback={<BracketSkeleton />}>
      <BracketPageInner />
    </Suspense>
  );
}
