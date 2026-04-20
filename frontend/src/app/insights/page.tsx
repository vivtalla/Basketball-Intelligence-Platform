"use client";

import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { TrajectoryTracker } from "@/components/TrajectoryTracker";
import UsageEfficiencyDashboard from "@/components/UsageEfficiencyDashboard";
import TrendCardsPanel from "@/components/TrendCardsPanel";
import WhatIfPanel from "@/components/WhatIfPanel";
import { InsightsHeader } from "@/components/InsightsHeader";
import { useTeamAnalytics, useTeams } from "@/hooks/usePlayerStats";

type Mode = "trajectory" | "usage" | "trends" | "whatif";

const SEASONS = ["2025-26", "2024-25", "2023-24", "2022-23"];

function InsightsPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { data: teams } = useTeams();
  const modeParam = searchParams.get("tab");
  const mode: Mode =
    modeParam === "usage" || modeParam === "trends" || modeParam === "whatif"
      ? (modeParam as Mode)
      : "trajectory";
  const team = searchParams.get("team") ?? "OKC";
  const opponent = searchParams.get("opponent") ?? "";
  const season = searchParams.get("season") ?? "2025-26";
  const playerIdParam = searchParams.get("player_id");
  const playerId = playerIdParam ? Number(playerIdParam) : null;
  const selectedPlayerId = Number.isFinite(playerId) ? playerId : null;
  const signal = searchParams.get("signal") ?? "";
  const priorSeasonIndex = SEASONS.indexOf(season);
  const priorSeason =
    priorSeasonIndex >= 0 && priorSeasonIndex < SEASONS.length - 1
      ? SEASONS[priorSeasonIndex + 1]
      : null;
  const { data: currentAnalytics } = useTeamAnalytics(team, season);
  const { data: priorAnalytics } = useTeamAnalytics(team, priorSeason);

  function updateParams(mutator: (params: URLSearchParams) => void) {
    const params = new URLSearchParams(searchParams.toString());
    mutator(params);
    router.replace(`/insights?${params.toString()}`);
  }

  function handleModeChange(newMode: Mode) {
    updateParams((params) => params.set("tab", newMode));
  }

  function handleParamChange(key: string, value: string | null) {
    updateParams((params) => {
      if (value !== null) params.set(key, value);
      else params.delete(key);
    });
  }

  return (
    <div className="space-y-8">
      <InsightsHeader
        mode={mode}
        team={team}
        season={season}
        opponent={opponent}
        playerId={selectedPlayerId}
        signal={signal}
        teams={teams ?? []}
        onModeChange={handleModeChange}
        onParamChange={handleParamChange}
      />

      {mode === "trajectory" ? (
        <TrajectoryTracker
          initialTeam={team}
          pinnedPlayerId={selectedPlayerId}
          onPlayerPin={(id) => handleParamChange("player_id", id == null ? null : String(id))}
        />
      ) : mode === "usage" ? (
        <UsageEfficiencyDashboard
          season={season}
          team={team}
          pinnedPlayerId={selectedPlayerId}
          signal={signal}
          onPlayerPin={(id) => handleParamChange("player_id", id == null ? null : String(id))}
          onSignalChange={(value) => handleParamChange("signal", value || null)}
        />
      ) : mode === "trends" ? (
        <TrendCardsPanel
          teamAbbreviation={team}
          season={season}
          pinnedPlayerId={selectedPlayerId}
          signal={signal}
          onPlayerPin={(id) => handleParamChange("player_id", id == null ? null : String(id))}
          onSignalChange={(value) => handleParamChange("signal", value || null)}
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
          <div className="h-48 animate-pulse rounded-[2rem] bg-[var(--surface-alt)]" />
          <div className="h-[28rem] animate-pulse rounded-[2rem] bg-[var(--surface-alt)]" />
        </div>
      }
    >
      <InsightsPageInner />
    </Suspense>
  );
}
