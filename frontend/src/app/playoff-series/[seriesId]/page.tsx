"use client";

/**
 * Sprint 85 — per-series detail page.
 *
 * URL: /playoff-series/{seriesId}
 *
 * Vivek brief: "fully fleshed out tracker with stats of matchup so far,
 * with options to click through the different games and their stats."
 *
 * The bracket command center (/bracket?series_id=X) covers series-level
 * intelligence (four factors, star burden, lineup chess). This page
 * complements it by showing every player's per-game stat line, with each
 * game-row deep-linking to /games/{game_id} for the full game detail.
 *
 * Uses useParams (not useSearchParams), so no Suspense wrapper is needed
 * — see Sprint 84 lesson on Suspense gymnastics.
 */

import Link from "next/link";
import { useParams } from "next/navigation";
import useSWR from "swr";

import SeriesPlayerLogTable from "@/components/playoffs/SeriesPlayerLogTable";
import { getSeries, getSeriesPlayerLogs } from "@/lib/api";
import type {
  PlayoffSeriesPlayerLogsResponse,
  PlayoffSeriesResponse,
} from "@/lib/types";

const ROUND_LABELS: Record<number, string> = {
  1: "First Round",
  2: "Conference Semifinals",
  3: "Conference Finals",
  4: "NBA Finals",
};

function seriesStateLabel(series: PlayoffSeriesResponse): string {
  const top = series.top_seed_team_abbr ?? "Top";
  const bottom = series.bottom_seed_team_abbr ?? "Bottom";
  if (series.status === "closed") {
    const winner =
      series.top_wins > series.bottom_wins ? top : bottom;
    return `${winner} won ${Math.max(series.top_wins, series.bottom_wins)}-${Math.min(
      series.top_wins,
      series.bottom_wins
    )}`;
  }
  if (series.status === "scheduled") return "Tipoff TBD";
  if (series.top_wins === series.bottom_wins) {
    return `Tied ${series.top_wins}-${series.bottom_wins}`;
  }
  const leader = series.top_wins > series.bottom_wins ? top : bottom;
  return `${leader} leads ${Math.max(series.top_wins, series.bottom_wins)}-${Math.min(
    series.top_wins,
    series.bottom_wins
  )}`;
}

function HeaderSkeleton() {
  return (
    <div className="bip-panel rounded-[1.4rem] p-6">
      <div className="h-4 w-32 animate-pulse rounded bg-[var(--surface-alt)]" />
      <div className="mt-3 h-8 w-72 animate-pulse rounded bg-[var(--surface-alt)]" />
      <div className="mt-2 h-4 w-48 animate-pulse rounded bg-[var(--surface-alt)]" />
    </div>
  );
}

function TableSkeleton() {
  return (
    <div className="bip-panel rounded-[1.4rem] p-6">
      <div className="h-6 w-40 animate-pulse rounded bg-[var(--surface-alt)]" />
      <div className="mt-4 space-y-2">
        {Array.from({ length: 6 }).map((_, idx) => (
          <div
            key={idx}
            className="h-8 w-full animate-pulse rounded bg-[var(--surface-alt)]"
          />
        ))}
      </div>
    </div>
  );
}

function SeriesHeader({
  series,
  seriesId,
}: {
  series: PlayoffSeriesResponse | undefined;
  seriesId: string;
}) {
  if (!series) {
    return (
      <div className="bip-panel rounded-[1.4rem] p-6">
        <p className="bip-kicker">Per-series tracker</p>
        <h1 className="bip-display mt-1 text-2xl font-semibold text-[var(--foreground)]">
          {seriesId}
        </h1>
      </div>
    );
  }

  const topAbbr = series.top_seed_team_abbr ?? `#${series.top_seed}`;
  const bottomAbbr = series.bottom_seed_team_abbr ?? `#${series.bottom_seed}`;
  const roundLabel = ROUND_LABELS[series.round] ?? `Round ${series.round}`;

  return (
    <div className="bip-panel rounded-[1.4rem] p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-3 text-[11px] uppercase tracking-[0.14em] text-[var(--muted)]">
            <span>{roundLabel}</span>
            <span className="text-[var(--border)]">·</span>
            <span>{series.season}</span>
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              {series.top_seed_team_id != null ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={`https://cdn.nba.com/logos/nba/${series.top_seed_team_id}/global/L/logo.svg`}
                  alt={topAbbr}
                  className="h-12 w-12 object-contain"
                />
              ) : null}
              <span className="bip-display text-3xl font-semibold text-[var(--foreground)]">
                {topAbbr}
              </span>
            </div>
            <span className="bip-display text-2xl font-semibold text-[var(--muted)]">
              {series.top_wins} - {series.bottom_wins}
            </span>
            <div className="flex items-center gap-2">
              {series.bottom_seed_team_id != null ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={`https://cdn.nba.com/logos/nba/${series.bottom_seed_team_id}/global/L/logo.svg`}
                  alt={bottomAbbr}
                  className="h-12 w-12 object-contain"
                />
              ) : null}
              <span className="bip-display text-3xl font-semibold text-[var(--foreground)]">
                {bottomAbbr}
              </span>
            </div>
          </div>
          <p className="mt-3 text-sm text-[var(--muted-strong)]">
            {seriesStateLabel(series)} · {series.games.length} game
            {series.games.length === 1 ? "" : "s"} played
          </p>
        </div>
        <div className="flex flex-col gap-2 lg:items-end">
          <Link
            href={`/bracket?series_id=${encodeURIComponent(seriesId)}`}
            className="inline-flex items-center gap-1 rounded-full border border-[var(--border)] bg-[var(--surface)] px-4 py-2 text-xs font-semibold text-[var(--accent)] transition-colors hover:border-[var(--accent)]"
          >
            ← Back to series intelligence
          </Link>
          <p className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">
            Click a Game# to open full play-by-play
          </p>
        </div>
      </div>
    </div>
  );
}

export default function PerSeriesDetailPage() {
  const params = useParams<{ seriesId: string }>();
  const seriesId = params?.seriesId ?? "";

  const seriesQuery = useSWR<PlayoffSeriesResponse>(
    seriesId ? ["playoff-series-summary", seriesId] : null,
    () => getSeries(seriesId)
  );

  const logsQuery = useSWR<PlayoffSeriesPlayerLogsResponse>(
    seriesId ? ["playoff-series-player-logs", seriesId] : null,
    () => getSeriesPlayerLogs(seriesId)
  );

  if (!seriesId) {
    return (
      <div className="bip-empty rounded-[1.4rem] p-12 text-center text-sm text-[var(--muted)]">
        Missing series identifier in the URL.
      </div>
    );
  }

  const isLoading = seriesQuery.isLoading || logsQuery.isLoading;
  const error = seriesQuery.error || logsQuery.error;

  if (error) {
    return (
      <div className="space-y-4">
        <SeriesHeader series={seriesQuery.data} seriesId={seriesId} />
        <div className="bip-panel rounded-[1.4rem] p-6 text-sm text-[var(--muted)]">
          <p className="font-semibold text-[var(--foreground)]">
            Could not load per-game player logs for this series.
          </p>
          <p className="mt-2">
            This usually means the series id doesn&apos;t exist yet, or the
            playoff sync hasn&apos;t ingested any games for it. Try again or
            return to the bracket.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => {
                seriesQuery.mutate();
                logsQuery.mutate();
              }}
              className="rounded-full border border-[var(--accent)] bg-[var(--surface)] px-4 py-2 text-xs font-semibold text-[var(--accent)] transition-colors hover:bg-[var(--accent)] hover:text-[var(--surface)]"
            >
              Retry
            </button>
            <Link
              href="/bracket"
              className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-4 py-2 text-xs font-semibold text-[var(--foreground)] transition-colors hover:border-[var(--accent)]"
            >
              ← Back to bracket
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (isLoading || !logsQuery.data) {
    return (
      <div className="space-y-4">
        <HeaderSkeleton />
        <TableSkeleton />
        <TableSkeleton />
      </div>
    );
  }

  const series = seriesQuery.data;
  const logs = logsQuery.data;
  const topAbbr = series?.top_seed_team_abbr ?? "Top seed";
  const bottomAbbr = series?.bottom_seed_team_abbr ?? "Bottom seed";
  const topTeamId = series?.top_seed_team_id ?? null;
  const bottomTeamId = series?.bottom_seed_team_id ?? null;

  const noLogs =
    logs.top_seed.length === 0 && logs.bottom_seed.length === 0;

  return (
    <div className="space-y-6">
      <SeriesHeader series={series} seriesId={seriesId} />

      {noLogs ? (
        <div className="bip-empty rounded-[1.4rem] p-12 text-center text-sm text-[var(--muted)]">
          <p className="font-semibold text-[var(--foreground)]">
            No per-game player logs synced yet.
          </p>
          <p className="mt-2">
            Logs populate after each game completes and the daily sync
            ingests box scores. If the series has just tipped off, check back
            in a few minutes.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          <SeriesPlayerLogTable
            team={logs.top_seed}
            teamAbbr={topAbbr}
            teamId={topTeamId}
          />
          <SeriesPlayerLogTable
            team={logs.bottom_seed}
            teamAbbr={bottomAbbr}
            teamId={bottomTeamId}
          />
        </div>
      )}
    </div>
  );
}
