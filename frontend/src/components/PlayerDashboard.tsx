"use client";

import { useState } from "react";
import { usePlayerProfile, usePlayerCareerStats, usePlayerGravity, usePlayerPercentiles } from "@/hooks/usePlayerStats";
import PlayerHeader from "./PlayerHeader";
import StatTable from "./StatTable";
import RadarChart from "./RadarChart";
import CareerArcChart from "./CareerArcChart";
import ShotChart from "./ShotChart";
import PlayerPbpInsights from "./PlayerPbpInsights";
import PlayerTrendIntelligencePanel from "./PlayerTrendIntelligencePanel";
import GameLogTable from "./GameLogTable";
import PlayerSimilarity from "./PlayerSimilarity";
import { PlayerArchetypeProfile } from "./archetype/PlayerArchetypeProfile";
import { ArchetypeEvolutionTimeline } from "./archetype/ArchetypeEvolutionTimeline";
import { ScoutingBrief } from "./scouting-brief/ScoutingBrief";
import { BriefSourceBanner } from "./scouting-brief/BriefSourceBanner";
import { TeamFitPanel } from "./team-fit/TeamFitPanel";
import { PlayerSettingsDrawer } from "./player-settings/PlayerSettingsDrawer";
import SeasonSplits from "./SeasonSplits";
import ExternalMetricsPanel from "./ExternalMetricsPanel";
import ChartStatusBadge from "./ChartStatusBadge";
import PerformanceCalendar from "./PerformanceCalendar";
import PlayerGravityPanel from "./PlayerGravityPanel";
import MvpPlayerCaseEmbed from "./MvpPlayerCaseEmbed";
import LegacyTab from "./career/LegacyTab";

interface PlayerDashboardProps {
  playerId: number;
}

type Mode = "regular" | "playoffs";
type Tab = "profile" | "legacy";

export default function PlayerDashboard({ playerId }: PlayerDashboardProps) {
  const [mode, setMode] = useState<Mode>("regular");
  const [tab, setTab] = useState<Tab>("profile");
  const [selectedSeasonStr, setSelectedSeasonStr] = useState<string>("");

  const { data: profile, error: profileError } = usePlayerProfile(playerId);
  const { data: careerStats, error: statsError } = usePlayerCareerStats(playerId);

  const latestRegularSeason =
    careerStats && careerStats.seasons.length > 0
      ? careerStats.seasons[careerStats.seasons.length - 1].season
      : null;
  const percentileSeason =
    mode === "regular"
      ? selectedSeasonStr || latestRegularSeason
      : null;
  const { data: radarPercentiles, isLoading: radarPercentilesLoading } = usePlayerPercentiles(
    playerId,
    percentileSeason
  );
  const latestPlayoffSeason =
    careerStats && careerStats.playoff_seasons.length > 0
      ? careerStats.playoff_seasons[careerStats.playoff_seasons.length - 1].season
      : null;
  const gravitySeason =
    mode === "regular"
      ? selectedSeasonStr || latestRegularSeason
      : selectedSeasonStr || latestPlayoffSeason;
  const gravitySeasonType = mode === "playoffs" ? "Playoffs" : "Regular Season";
  const { data: gravityProfile, isLoading: gravityLoading } = usePlayerGravity(
    playerId,
    gravitySeason,
    gravitySeasonType
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
  const shotLabSeasons = Array.from(
    new Set([
      ...careerStats.seasons.map((season) => season.season).filter(Boolean),
      ...careerStats.playoff_seasons.map((season) => season.season).filter(Boolean),
    ])
  ).sort((left, right) => left.localeCompare(right));
  const effectiveSeasonStr = selectedSeasonStr || latestSeason?.season || null;
  const selectedSeasonData = activeSeasonsArr.find((s) => s.season === effectiveSeasonStr) ?? latestSeason;
  const missingCoreData =
    profile.data_status === "missing" || careerStats.data_status === "missing";
  const staleCoreData =
    profile.data_status === "stale" || careerStats.data_status === "stale";

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

      {/* Sprint 78 / CF3 — Profile / Legacy tabs */}
      <div className="flex items-center gap-2">
        <span className="mr-1 text-sm text-[var(--muted)]">Tab:</span>
        <div className="flex w-fit overflow-hidden rounded-xl border border-[var(--border)] text-sm">
          <button
            onClick={() => setTab("profile")}
            className={`px-4 py-1.5 transition-colors ${
              tab === "profile" ? "bip-toggle-active" : "bip-toggle"
            }`}
          >
            Profile
          </button>
          <button
            onClick={() => setTab("legacy")}
            className={`px-4 py-1.5 transition-colors ${
              tab === "legacy" ? "bip-toggle-signal" : "bip-toggle"
            }`}
          >
            Legacy
          </button>
        </div>
      </div>

      {tab === "legacy" ? (
        <LegacyTab
          playerId={playerId}
          seasons={careerStats.seasons}
          birthDate={profile.birth_date}
        />
      ) : null}

      {tab === "profile" ? (
        <>
      <PlayerSettingsDrawer playerId={playerId} season={effectiveSeasonStr} />

      <ScoutingBrief playerId={playerId} season={effectiveSeasonStr} />

      {(missingCoreData || staleCoreData) && (
        <div className="rounded-[1.5rem] border border-[rgba(25,52,42,0.12)] bg-[rgba(255,255,255,0.74)] px-5 py-4">
          <div className="flex flex-wrap items-center gap-2">
            <ChartStatusBadge status={missingCoreData ? "missing" : "stale"} compact />
            <span className="text-sm font-medium text-[var(--foreground)]">
              {missingCoreData
                ? "This player page is reading only from persisted data, and part of the player record has not been synced yet."
                : "Some player data is currently cached from the last successful sync."}
            </span>
          </div>
          <p className="mt-2 text-sm text-[var(--muted)]">
            {missingCoreData
              ? "Profile, career, game-log, and shot-chart sections will stay stable, but some panels may remain empty until queued enrichment finishes."
              : "The page remains usable while background refresh jobs catch up."}
          </p>
        </div>
      )}

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

      {effectiveSeasonStr && (
        <PlayerTrendIntelligencePanel
          playerId={playerId}
          season={effectiveSeasonStr}
          isPlayoffs={isPlayoffs}
        />
      )}

      {!isPlayoffs && effectiveSeasonStr && (
        <MvpPlayerCaseEmbed playerId={playerId} season={effectiveSeasonStr} />
      )}

      {effectiveSeasonStr && (
        <PlayerGravityPanel
          profile={gravityProfile}
          isLoading={gravityLoading}
          season={effectiveSeasonStr}
        />
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {selectedSeasonData && (
          <div className="lg:col-span-1">
            <RadarChart
              stats={selectedSeasonData}
              percentiles={radarPercentiles}
              isPercentileLoading={radarPercentilesLoading}
            />
          </div>
        )}
        <div className="lg:col-span-2">
          <CareerArcChart seasons={activeSeasonsArr} birthDate={profile.birth_date} />
        </div>
      </div>

      {/* Shot Chart has its own internal RS/Playoffs toggle */}
      {careerStats.seasons.length > 0 && (
        <div id="shot-lab" className="space-y-3 scroll-mt-6">
          <BriefSourceBanner anchor="shot-lab" />
          <ShotChart
            playerId={playerId}
            seasons={shotLabSeasons}
            defaultSeason={shotLabSeasons[shotLabSeasons.length - 1]}
          />
        </div>
      )}

      {/* Team Impact & Clutch are regular-season only */}
      {isPlayoffs ? (
        <div className="bip-empty rounded-2xl p-5 text-center text-sm">
          Team Impact & Clutch metrics are available for regular season only.
        </div>
      ) : (
        <PlayerPbpInsights playerId={playerId} season={effectiveSeasonStr} />
      )}

      {/* Season splits — regular season only, needs game log data */}
      {!isPlayoffs && effectiveSeasonStr && (
        <SeasonSplits playerId={playerId} season={effectiveSeasonStr} />
      )}

      {/* Performance Calendar — game-by-game heatmap for current season */}
      {effectiveSeasonStr && (
        <PerformanceCalendar playerId={playerId} season={effectiveSeasonStr} />
      )}

      {/* Game Log has its own internal RS/Playoffs toggle */}
      <GameLogTable playerId={playerId} season={effectiveSeasonStr} />

      <div id="archetype" className="space-y-3 scroll-mt-6">
        <BriefSourceBanner anchor="archetype" />
        <PlayerArchetypeProfile playerId={playerId} season={effectiveSeasonStr} />
        <ArchetypeEvolutionTimeline playerId={playerId} />
      </div>

      <TeamFitPanel playerId={playerId} season={effectiveSeasonStr} />

      <PlayerSimilarity playerId={playerId} season={effectiveSeasonStr} />

      <StatTable
        seasons={careerStats.seasons}
        careerTotals={careerStats.career_totals}
        playoffSeasons={careerStats.playoff_seasons}
      />

      <ExternalMetricsPanel seasons={activeSeasonsArr} />
        </>
      ) : null}
    </div>
  );
}
