"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useSeasonPhase } from "@/hooks/useSeasonPhase";
import PostseasonHeatmap from "@/components/playoffs/PostseasonHeatmap";
import TopLeadersTable from "@/components/leaderboards/TopLeadersTable";

type SeasonType = "Regular Season" | "Playoffs";

function buildPlayerStatsHref(
  searchParams: URLSearchParams,
  override?: SeasonType
): string {
  const params = new URLSearchParams(searchParams);
  if (override) params.set("seasonType", override);
  const query = params.toString();
  return query ? `/player-stats?${query}` : "/player-stats";
}

function SeasonTypeToggle({
  value,
  onChange,
}: {
  value: SeasonType;
  onChange: (next: SeasonType) => void;
}) {
  const options: SeasonType[] = ["Regular Season", "Playoffs"];
  return (
    <div
      role="group"
      aria-label="Season type"
      className="inline-flex items-center rounded-full border border-[var(--border)] bg-[var(--surface-alt)] p-0.5"
    >
      {options.map((opt) => {
        const active = opt === value;
        return (
          <button
            key={opt}
            type="button"
            onClick={() => onChange(opt)}
            className="rounded-full px-3 py-1 text-xs font-medium transition-colors"
            style={{
              background: active ? "var(--surface)" : "transparent",
              color: active ? "var(--foreground)" : "var(--muted)",
              boxShadow: active ? "0 1px 2px rgba(33,72,59,0.12)" : "none",
            }}
          >
            {opt}
          </button>
        );
      })}
    </div>
  );
}

function LeaderboardsPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isPlayoffs, isLoading, season } = useSeasonPhase();

  const initialSeasonType: SeasonType =
    searchParams.get("seasonType") === "Playoffs" ? "Playoffs" : "Regular Season";
  const [seasonType, setSeasonType] = useState<SeasonType>(initialSeasonType);

  // Sprint 73 (EB3): in regular season, this page reverts to its legacy
  // behavior of redirecting to `/player-stats` so the toggle-back guarantee
  // holds. In playoffs, render the toggle at the top and let EB4 mount their
  // postseason heatmap section below.
  useEffect(() => {
    if (isLoading) return;
    if (!isPlayoffs) {
      router.replace(buildPlayerStatsHref(searchParams));
    }
  }, [isLoading, isPlayoffs, router, searchParams]);

  // Push the toggle state into the URL so deep links (and EB4's heatmap below)
  // can read it as a single source of truth.
  useEffect(() => {
    if (!isPlayoffs) return;
    const current = searchParams.get("seasonType");
    if (current === seasonType) return;
    const next = new URLSearchParams(searchParams);
    next.set("seasonType", seasonType);
    router.replace(`/leaderboards?${next.toString()}`, { scroll: false });
  }, [seasonType, isPlayoffs, router, searchParams]);

  const fullPlayerStatsHref = useMemo(
    () => buildPlayerStatsHref(searchParams, seasonType),
    [searchParams, seasonType]
  );

  if (isLoading || !isPlayoffs) {
    // Spinner-free placeholder while we resolve season phase or redirect.
    return null;
  }

  return (
    <div className="space-y-10">
      {/* ── TOP: Regular/Playoffs toggle (EB3) ───────────────────── */}
      <section>
        <div className="mb-4 flex items-end justify-between gap-4">
          <div>
            <p className="bip-kicker mb-1.5">Leaderboards</p>
            <h1 className="bip-display text-3xl font-semibold text-[var(--foreground)]">
              The composite <span className="text-[var(--accent)]">top tier.</span>
            </h1>
            <p className="mt-2 text-sm text-[var(--muted)]">
              Switch between regular-season form and live playoff impact.
            </p>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <SeasonTypeToggle value={seasonType} onChange={setSeasonType} />
            <Link
              href={fullPlayerStatsHref}
              className="text-sm bip-link font-medium"
            >
              Full player stats →
            </Link>
          </div>
        </div>
        <div className="bip-panel rounded-[1.4rem] px-5 py-4 text-sm text-[var(--muted)]">
          Showing <span className="font-medium text-[var(--foreground)]">{seasonType}</span> leaderboards.{" "}
          <Link href={fullPlayerStatsHref} className="bip-link">
            Open the full Player Stats workspace →
          </Link>
        </div>
      </section>

      {/* Top leaders table — switches data source based on the toggle. */}
      <TopLeadersTable
        season={season ?? "2025-26"}
        seasonType={seasonType}
      />

      {/* Postseason Performer Heatmap — playoff-specific (compares playoff
          USG/TS to regular-season baseline). Hide when toggle is on Regular
          Season since the comparison is degenerate there. */}
      {seasonType === "Playoffs" && <PostseasonHeatmap />}
    </div>
  );
}

export default function LeaderboardsPage() {
  return (
    <Suspense fallback={null}>
      <LeaderboardsPageInner />
    </Suspense>
  );
}
