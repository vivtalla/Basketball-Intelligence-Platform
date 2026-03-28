"use client";

import { useState } from "react";
import { usePlayerProfile, usePlayerCareerStats } from "@/hooks/usePlayerStats";
import PlayerHeader from "./PlayerHeader";
import StatTable from "./StatTable";
import RadarChart from "./RadarChart";
import CareerArcChart from "./CareerArcChart";
import ShotChart from "./ShotChart";
import PlayerPbpInsights from "./PlayerPbpInsights";
import GameLogTable from "./GameLogTable";
import PlayerSimilarity from "./PlayerSimilarity";
import SeasonSplits from "./SeasonSplits";

interface PlayerDashboardProps {
  playerId: number;
}

type Mode = "regular" | "playoffs";

export default function PlayerDashboard({ playerId }: PlayerDashboardProps) {
  const [mode, setMode] = useState<Mode>("regular");

  const { data: profile, error: profileError } = usePlayerProfile(playerId);
  const { data: careerStats, error: statsError } = usePlayerCareerStats(playerId);

  if (profileError || statsError) {
    return (
      <div className="text-center py-20">
        <h2 className="text-2xl font-bold text-red-500 mb-2">Error Loading Player</h2>
        <p className="text-gray-500">
          Could not fetch player data. Make sure the backend is running.
        </p>
      </div>
    );
  }

  if (!profile || !careerStats) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-48 bg-gray-200 dark:bg-gray-700 rounded-2xl" />
        <div className="h-96 bg-gray-200 dark:bg-gray-700 rounded-2xl" />
      </div>
    );
  }

  const isPlayoffs = mode === "playoffs";
  const hasPlayoffs = careerStats.playoff_seasons.length > 0;
  const activeSeasonsArr = isPlayoffs ? careerStats.playoff_seasons : careerStats.seasons;

  const currentSeason = activeSeasonsArr.length > 0
    ? activeSeasonsArr[activeSeasonsArr.length - 1]
    : null;

  return (
    <div className="space-y-6">
      <PlayerHeader profile={profile} currentSeason={currentSeason} />

      {/* RS / Playoffs toggle — only shown when player has playoff data */}
      {hasPlayoffs && (
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500 dark:text-gray-400 mr-1">View:</span>
          <div className="flex rounded-xl overflow-hidden border border-gray-200 dark:border-gray-700 text-sm w-fit">
            <button
              onClick={() => setMode("regular")}
              className={`px-4 py-1.5 transition-colors ${
                !isPlayoffs
                  ? "bg-blue-500 text-white"
                  : "bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700"
              }`}
            >
              Regular Season
            </button>
            <button
              onClick={() => setMode("playoffs")}
              className={`px-4 py-1.5 transition-colors ${
                isPlayoffs
                  ? "bg-amber-500 text-white"
                  : "bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700"
              }`}
            >
              Playoffs
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {currentSeason && (
          <div className="lg:col-span-1">
            <RadarChart stats={currentSeason} />
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

      {/* PBP insights are regular-season only */}
      {isPlayoffs ? (
        <div className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 text-sm text-gray-400 dark:text-gray-500 text-center">
          Play-by-play insights (on/off splits, clutch) are available for regular season only.
        </div>
      ) : (
        <PlayerPbpInsights playerId={playerId} season={currentSeason?.season ?? null} />
      )}

      <PlayerSimilarity playerId={playerId} season={currentSeason?.season ?? null} />

      {/* Season splits — regular season only, needs game log data */}
      {!isPlayoffs && (
        <SeasonSplits playerId={playerId} season={currentSeason?.season ?? null} />
      )}

      {/* Game Log has its own internal RS/Playoffs toggle */}
      <GameLogTable playerId={playerId} season={currentSeason?.season ?? null} />

      <StatTable
        seasons={careerStats.seasons}
        careerTotals={careerStats.career_totals}
        playoffSeasons={careerStats.playoff_seasons}
      />
    </div>
  );
}
