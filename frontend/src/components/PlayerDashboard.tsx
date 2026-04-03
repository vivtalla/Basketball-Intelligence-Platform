"use client";

import { useState } from "react";
import { usePlayerProfile, usePlayerCareerStats, usePlayerZoneProfile } from "@/hooks/usePlayerStats";
import PlayerHeader from "./PlayerHeader";
import StatTable from "./StatTable";
import RadarChart from "./RadarChart";
import CareerArcChart from "./CareerArcChart";
import ShotChart from "./ShotChart";
import ZoneProfilePanel from "./ZoneProfilePanel";
import PlayerPbpInsights from "./PlayerPbpInsights";
import PlayerTrendIntelligencePanel from "./PlayerTrendIntelligencePanel";
import GameLogTable from "./GameLogTable";
import PlayerSimilarity from "./PlayerSimilarity";
import SeasonSplits from "./SeasonSplits";
import ExternalMetricsPanel from "./ExternalMetricsPanel";

interface PlayerDashboardProps {
  playerId: number;
}

type Mode = "regular" | "playoffs";

export default function PlayerDashboard({ playerId }: PlayerDashboardProps) {
  const [mode, setMode] = useState<Mode>("regular");
  const [selectedSeasonStr, setSelectedSeasonStr] = useState<string>("");

  const { data: profile, error: profileError } = usePlayerProfile(playerId);
  const { data: careerStats, error: statsError } = usePlayerCareerStats(playerId);

  // Sprint 29 — zone profile (Regular Season, latest season resolved after careerStats loads)
  // Must be declared unconditionally here; SWR key is null-guarded inside the hook.
  const latestRegularSeason =
    careerStats && careerStats.seasons.length > 0
      ? careerStats.seasons[careerStats.seasons.length - 1].season
      : null;
  const { data: zoneData, isLoading: zoneLoading } = usePlayerZoneProfile(
    playerId,
    latestRegularSeason
  );

  if (profileError || statsError) {
    return (
      <div className="text-center py-20">
        <h2 className="mb-2 text-2xl font-bold text-[var(--danger-ink)]">Error Loading Player</h2>
        <p className="text-[var(--muted)]">
          Could not fetch player data. Make sure the backend is running.
        </p>
      </div>
    );
  }

  if (!profile || !careerStats) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-48 rounded-2xl bg-[var(--surface-alt)]" />
        <div className="h-96 rounded-2xl bg-[var(--surface-alt)]" />
      </div>
    );
  }

  const isPlayoffs = mode === "playoffs";
  const hasPlayoffs = careerStats.playoff_seasons.length > 0;
  const activeSeasonsArr = isPlayoffs ? careerStats.playoff_seasons : careerStats.seasons;

  const latestSeason = activeSeasonsArr.length > 0
    ? activeSeasonsArr[activeSeasonsArr.length - 1]
    : null;
  const effectiveSeasonStr = selectedSeasonStr || latestSeason?.season || null;
  const selectedSeasonData = activeSeasonsArr.find((s) => s.season === effectiveSeasonStr) ?? latestSeason;

  // currentSeason used only for PlayerHeader (always latest)
  const currentSeason = latestSeason;
  const priorSeason =
    latestSeason && activeSeasonsArr.length > 1
      ? activeSeasonsArr[activeSeasonsArr.length - 2]
      : null;

  function handleModeChange(next: Mode) {
    setMode(next);
    setSelectedSeasonStr("");
  }

  return (
    <div className="space-y-6">
      <PlayerHeader profile={profile} currentSeason={currentSeason} priorSeason={priorSeason} />

      {/* RS / Playoffs toggle — only shown when player has playoff data */}
      {hasPlayoffs && (
        <div className="flex items-center gap-2">
          <span className="mr-1 text-sm text-[var(--muted)]">View:</span>
          <div className="flex w-fit overflow-hidden rounded-xl border border-[var(--border)] text-sm">
            <button
              onClick={() => handleModeChange("regular")}
              className={`px-4 py-1.5 transition-colors ${
                !isPlayoffs
                  ? "bip-toggle-active"
                  : "bip-toggle"
              }`}
            >
              Regular Season
            </button>
            <button
              onClick={() => handleModeChange("playoffs")}
              className={`px-4 py-1.5 transition-colors ${
                isPlayoffs
                  ? "bip-toggle-signal"
                  : "bip-toggle"
              }`}
            >
              Playoffs
            </button>
          </div>
        </div>
      )}

      {/* Season selector — shown when there are multiple seasons */}
      {activeSeasonsArr.length > 1 && (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="shrink-0 text-xs text-[var(--muted)]">Season:</span>
          <div className="flex gap-1.5 flex-wrap">
            {[...activeSeasonsArr].reverse().map((s) => (
              <button
                key={s.season}
                onClick={() => setSelectedSeasonStr(s.season === latestSeason?.season ? "" : s.season)}
                className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
                  s.season === effectiveSeasonStr
                    ? isPlayoffs
                      ? "bip-toggle-signal"
                      : "bip-toggle-active"
                    : "bip-toggle"
                }`}
              >
                {s.season}
              </button>
            ))}
          </div>
        </div>
      )}

      <PlayerTrendIntelligencePanel
        playerId={playerId}
        season={effectiveSeasonStr}
        isPlayoffs={isPlayoffs}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {selectedSeasonData && (
          <div className="lg:col-span-1">
            <RadarChart stats={selectedSeasonData} />
          </div>
        )}
        <div className="lg:col-span-2">
          <CareerArcChart seasons={activeSeasonsArr} birthDate={profile.birth_date} />
        </div>
      </div>

      {/* Shot Chart has its own internal RS/Playoffs toggle */}
      {careerStats.seasons.length > 0 && (
        <ShotChart
          playerId={playerId}
          seasons={careerStats.seasons.map((s) => s.season).filter(Boolean)}
          defaultSeason={
            careerStats.seasons[careerStats.seasons.length - 1].season
          }
        />
      )}

      {/* Zone efficiency panel — Regular Season, latest season */}
      {careerStats.seasons.length > 0 && (
        <ZoneProfilePanel data={zoneData} isLoading={zoneLoading} />
      )}

      {/* PBP insights are regular-season only */}
      {isPlayoffs ? (
        <div className="bip-empty rounded-2xl p-5 text-center text-sm">
          Play-by-play insights (on/off splits, clutch) are available for regular season only.
        </div>
      ) : (
        <PlayerPbpInsights playerId={playerId} season={effectiveSeasonStr} />
      )}

      <PlayerSimilarity playerId={playerId} season={effectiveSeasonStr} />

      {/* Season splits — regular season only, needs game log data */}
      {!isPlayoffs && (
        <SeasonSplits playerId={playerId} season={effectiveSeasonStr} />
      )}

      {/* Game Log has its own internal RS/Playoffs toggle */}
      <GameLogTable playerId={playerId} season={effectiveSeasonStr} />

      <StatTable
        seasons={careerStats.seasons}
        careerTotals={careerStats.career_totals}
        playoffSeasons={careerStats.playoff_seasons}
      />

      <ExternalMetricsPanel seasons={activeSeasonsArr} />
    </div>
  );
}
