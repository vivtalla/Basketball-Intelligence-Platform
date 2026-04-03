"use client";

import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { TrajectoryTracker } from "@/components/TrajectoryTracker";
import UsageEfficiencyDashboard from "@/components/UsageEfficiencyDashboard";
import TrendCardsPanel from "@/components/TrendCardsPanel";
import WhatIfPanel from "@/components/WhatIfPanel";
import { useTeamAnalytics, useTeamIntelligence, useTeams } from "@/hooks/usePlayerStats";

type Mode = "trajectory" | "usage" | "trends" | "whatif";

const SEASONS = ["2025-26", "2024-25", "2023-24", "2022-23"];

function InsightsPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { data: teams } = useTeams();
  const modeParam = searchParams.get("tab");
  const mode =
    modeParam === "usage" || modeParam === "trends" || modeParam === "whatif"
      ? (modeParam as Mode)
      : "trajectory";
  const team = searchParams.get("team") ?? "OKC";
  const opponent = searchParams.get("opponent") ?? "";
  const season = searchParams.get("season") ?? "2024-25";
  const priorSeasonIndex = SEASONS.indexOf(season);
  const priorSeason =
    priorSeasonIndex >= 0 && priorSeasonIndex < SEASONS.length - 1
      ? SEASONS[priorSeasonIndex + 1]
      : null;
  const { data: currentAnalytics } = useTeamAnalytics(team, season);
  const { data: priorAnalytics } = useTeamAnalytics(team, priorSeason);
  const { data: intelligence } = useTeamIntelligence(team, season);

  function updateParams(mutator: (params: URLSearchParams) => void) {
    const params = new URLSearchParams(searchParams.toString());
    mutator(params);
    router.replace(`/insights?${params.toString()}`);
  }

  return (
    <div className="space-y-8">
      <section className="bip-panel-strong rounded-[2rem] p-6">
        <div className="flex flex-wrap items-end justify-between gap-5">
          <div className="max-w-3xl">
            <p className="bip-kicker mb-2">Coach Workflow</p>
            <h1 className="bip-display text-4xl font-semibold text-[var(--foreground)]">
              Platform intelligence, not just reporting
            </h1>
            <p className="mt-3 text-sm leading-6 text-[var(--muted-strong)]">
              Switch between trajectory, usage, weekly trend cards, and what-if prompts for {team}. Each tab is designed to preserve the investigation context and point toward the next drill-down.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Team</span>
              <select
                value={team}
                onChange={(event) => updateParams((params) => params.set("team", event.target.value))}
                className="bip-input w-full rounded-2xl px-4 py-3 text-sm"
              >
                {(teams ?? []).map((entry) => (
                  <option key={entry.abbreviation} value={entry.abbreviation}>
                    {entry.abbreviation} · {entry.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Season</span>
              <select
                value={season}
                onChange={(event) => updateParams((params) => params.set("season", event.target.value))}
                className="bip-input w-full rounded-2xl px-4 py-3 text-sm"
              >
                {SEASONS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Opponent</span>
              <select
                value={opponent}
                onChange={(event) => updateParams((params) => {
                  if (event.target.value) params.set("opponent", event.target.value);
                  else params.delete("opponent");
                })}
                className="bip-input w-full rounded-2xl px-4 py-3 text-sm"
              >
                <option value="">Optional matchup context</option>
                {(teams ?? [])
                  .filter((entry) => entry.abbreviation !== team)
                  .map((entry) => (
                    <option key={entry.abbreviation} value={entry.abbreviation}>
                      {entry.abbreviation} · {entry.name}
                    </option>
                  ))}
              </select>
            </label>
            <div className="rounded-2xl border border-[var(--border)] bg-[rgba(255,255,255,0.72)] px-4 py-3 text-sm text-[var(--muted-strong)]">
              Current context: {team} · {season}{opponent ? ` · vs ${opponent}` : ""}
            </div>
          </div>
        </div>
      </section>

      <section className="flex rounded-xl overflow-hidden border border-[var(--border)] w-fit text-sm">
        <button
          onClick={() => updateParams((params) => params.set("tab", "trajectory"))}
          className={`px-5 py-2 transition-colors ${
            mode === "trajectory"
              ? "bip-toggle-active"
              : "bip-toggle"
          }`}
          >
          Trajectory Tracker
        </button>
        <button
          onClick={() => updateParams((params) => params.set("tab", "usage"))}
          className={`px-5 py-2 transition-colors ${
            mode === "usage"
              ? "bip-toggle-active"
              : "bip-toggle"
          }`}
          >
          Usage vs Efficiency
        </button>
        <button
          onClick={() => updateParams((params) => params.set("tab", "trends"))}
          className={`px-5 py-2 transition-colors ${
            mode === "trends"
              ? "bip-toggle-active"
              : "bip-toggle"
          }`}
        >
          Trend Cards
        </button>
        <button
          onClick={() => updateParams((params) => params.set("tab", "whatif"))}
          className={`px-5 py-2 transition-colors ${
            mode === "whatif"
              ? "bip-toggle-active"
              : "bip-toggle"
          }`}
        >
          What-If
        </button>
      </section>

      {mode === "trajectory" ? (
        <TrajectoryTracker />
      ) : mode === "usage" ? (
        <UsageEfficiencyDashboard />
      ) : mode === "trends" ? (
        <TrendCardsPanel
          teamAbbreviation={team}
          season={season}
          currentAnalytics={currentAnalytics ?? null}
          priorAnalytics={priorAnalytics ?? null}
          intelligence={intelligence ?? null}
        />
      ) : (
        <WhatIfPanel
          teamAbbreviation={team}
          season={season}
          opponentAbbreviation={opponent || null}
          currentAnalytics={currentAnalytics ?? null}
          priorAnalytics={priorAnalytics ?? null}
        />
      )}
    </div>
  );
}

export default function InsightsPage() {
  return (
    <Suspense
      fallback={
        <div className="space-y-6">
          <div className="h-32 animate-pulse rounded-[2rem] bg-[var(--surface-alt)]" />
          <div className="h-12 w-96 animate-pulse rounded-xl bg-[var(--surface-alt)]" />
          <div className="h-[28rem] animate-pulse rounded-[2rem] bg-[var(--surface-alt)]" />
        </div>
      }
    >
      <InsightsPageInner />
    </Suspense>
  );
}
