"use client";

import { usePlayerProfile, usePlayerCareerStats } from "@/hooks/usePlayerStats";
import PlayerHeader from "./PlayerHeader";
import StatTable from "./StatTable";
import RadarChart from "./RadarChart";
import CareerArcChart from "./CareerArcChart";
import ShotChart from "./ShotChart";
import PlayerPbpInsights from "./PlayerPbpInsights";
import GameLogTable from "./GameLogTable";
import PlayerSimilarity from "./PlayerSimilarity";

interface PlayerDashboardProps {
  playerId: number;
}

export default function PlayerDashboard({ playerId }: PlayerDashboardProps) {
  const { data: profile, error: profileError } = usePlayerProfile(playerId);
  const { data: careerStats, error: statsError } =
    usePlayerCareerStats(playerId);

  if (profileError || statsError) {
    return (
      <div className="text-center py-20">
        <h2 className="text-2xl font-bold text-red-500 mb-2">
          Error Loading Player
        </h2>
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

  const currentSeason =
    careerStats.seasons.length > 0
      ? careerStats.seasons[careerStats.seasons.length - 1]
      : null;

  return (
    <div className="space-y-6">
      <PlayerHeader profile={profile} currentSeason={currentSeason} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Radar Chart */}
        {currentSeason && (
          <div className="lg:col-span-1">
            <RadarChart stats={currentSeason} />
          </div>
        )}

        {/* Career Arc */}
        <div className="lg:col-span-2">
          <CareerArcChart seasons={careerStats.seasons} birthDate={profile.birth_date} />
        </div>
      </div>

      {/* Shot Chart */}
      {careerStats.seasons.length > 0 && (
        <ShotChart
          playerId={playerId}
          seasons={careerStats.seasons.map((s) => s.season).filter(Boolean)}
          defaultSeason={currentSeason?.season ?? careerStats.seasons[careerStats.seasons.length - 1].season}
        />
      )}

      <PlayerPbpInsights playerId={playerId} season={currentSeason?.season ?? null} />

      <PlayerSimilarity playerId={playerId} season={currentSeason?.season ?? null} />

      <GameLogTable playerId={playerId} season={currentSeason?.season ?? null} />

      <StatTable
        seasons={careerStats.seasons}
        careerTotals={careerStats.career_totals}
        playoffSeasons={careerStats.playoff_seasons}
      />
    </div>
  );
}
