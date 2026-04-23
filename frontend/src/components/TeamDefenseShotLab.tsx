"use client";

import { useSearchParams } from "next/navigation";
import { startTransition, useEffect, useMemo, useState } from "react";
import {
  useShotLabSnapshot,
  useTeamDefenseShotChart,
  useTeamDefenseShotCreation,
  useTeamDefenseShotIdentity,
  useTeamDefenseShotQuality,
  useTeamDefenseShotChartRefresh,
  useTeamShootingSplits,
  useTeamDefenseZoneProfile,
} from "@/hooks/usePlayerStats";
import type { ShotChartShot, ShotLabDateRange, ShotLabSituationalFilters, ShotLabWindowPreset } from "@/lib/types";
import { clampShotLabCustomRange, resolveShotLabRange } from "@/lib/shotlab";
import ChartStatusBadge from "./ChartStatusBadge";
import ShotLabControls from "./ShotLabControls";
import ShotSnapshotButton from "./ShotSnapshotButton";
import ShotSprawlMap from "./ShotSprawlMap";
import ShotValueMap from "./ShotValueMap";
import ZoneProfilePanel from "./ZoneProfilePanel";
import ShotIntelligencePanel from "./ShotIntelligencePanel";

interface TeamDefenseShotLabProps {
  teamId: number;
  teamAbbreviation: string;
  seasons: string[];
  defaultSeason: string;
}

type TeamDefenseView = "quality" | "making" | "creation" | "summary" | "value" | "sprawl" | "zone";

const DEFAULT_SITUATIONAL_FILTERS: ShotLabSituationalFilters = {
  periodBucket: "all",
  result: "all",
  shotValue: "all",
};

function windowLabel(preset: ShotLabWindowPreset, range: ShotLabDateRange): string {
  if (!range.startDate && !range.endDate) return "Full season window";
  if (preset === "last-5-games") return "Last 5 game dates";
  if (preset === "last-10-games") return "Last 10 game dates";
  if (preset === "last-30-days") return "Last 30 days";
  if (range.startDate && range.endDate) return `${range.startDate} to ${range.endDate}`;
  return "Custom window";
}

function isLegacyPeriodContext(shots: ShotChartShot[] | undefined): boolean {
  if (!shots || shots.length === 0) return false;
  return !shots.some((shot) => typeof shot.period === "number" && Number.isFinite(shot.period));
}

export default function TeamDefenseShotLab({
  teamId,
  teamAbbreviation,
  seasons,
  defaultSeason,
}: TeamDefenseShotLabProps) {
  const searchParams = useSearchParams();
  const snapshotId = searchParams.get("shot_snapshot_id");
  const { data: snapshot } = useShotLabSnapshot(snapshotId);
  const [selectedSeason, setSelectedSeason] = useState(defaultSeason);
  const [seasonType, setSeasonType] = useState<"Regular Season" | "Playoffs">("Regular Season");
  const [preset, setPreset] = useState<ShotLabWindowPreset>("full");
  const [customRange, setCustomRange] = useState<ShotLabDateRange>({ startDate: null, endDate: null });
  const [situationalFilters, setSituationalFilters] = useState<ShotLabSituationalFilters>(DEFAULT_SITUATIONAL_FILTERS);
  const [view, setView] = useState<TeamDefenseView>("quality");
  const [appliedSnapshotId, setAppliedSnapshotId] = useState<string | null>(null);

  const { data: baseShot } = useTeamDefenseShotChart(teamId, selectedSeason, seasonType);
  const availableDates = useMemo(() => baseShot?.available_game_dates ?? [], [baseShot?.available_game_dates]);
  const availableStartDate = baseShot?.available_start_date ?? null;
  const availableEndDate = baseShot?.available_end_date ?? null;

  const filters = useMemo(
    () =>
      resolveShotLabRange(
        preset,
        availableDates,
        clampShotLabCustomRange(customRange, availableStartDate, availableEndDate)
      ),
    [availableDates, availableEndDate, availableStartDate, customRange, preset]
  );
  const activeFilters = useMemo(
    () => ({ ...filters, ...situationalFilters }),
    [filters, situationalFilters]
  );
  const { data: shotChart, isLoading: shotLoading } = useTeamDefenseShotChart(
    teamId,
    selectedSeason,
    seasonType,
    activeFilters
  );
  const { data: zoneProfile, isLoading: zoneLoading } = useTeamDefenseZoneProfile(
    teamId,
    selectedSeason,
    seasonType,
    activeFilters
  );
  const { data: shotQuality, isLoading: qualityLoading } = useTeamDefenseShotQuality(
    teamId,
    selectedSeason,
    seasonType,
    activeFilters
  );
  const { data: shotCreation, isLoading: creationLoading } = useTeamDefenseShotCreation(
    teamId,
    selectedSeason,
    seasonType,
    activeFilters
  );
  const { data: shotIdentity, isLoading: identityLoading } = useTeamDefenseShotIdentity(
    teamId,
    selectedSeason,
    seasonType,
    activeFilters
  );
  const { data: shootingSplits } = useTeamShootingSplits(teamAbbreviation, selectedSeason);
  const { refresh, isRefreshing } = useTeamDefenseShotChartRefresh(
    teamId,
    selectedSeason,
    seasonType,
    activeFilters
  );

  useEffect(() => {
    if (!snapshotId || !snapshot || appliedSnapshotId === snapshotId) return;
    if (snapshot.payload.subject_type !== "team-defense" || snapshot.payload.team_id !== teamId) return;
    startTransition(() => {
      setSelectedSeason(snapshot.payload.season);
      setSeasonType(snapshot.payload.season_type === "Playoffs" ? "Playoffs" : "Regular Season");
      setView((snapshot.payload.active_view as TeamDefenseView) ?? "value");
      setCustomRange({
        startDate: snapshot.payload.filters.start_date ?? null,
        endDate: snapshot.payload.filters.end_date ?? null,
      });
      setSituationalFilters({
        periodBucket: snapshot.payload.filters.period_bucket ?? "all",
        result: snapshot.payload.filters.result ?? "all",
        shotValue: snapshot.payload.filters.shot_value ?? "all",
      });
      setAppliedSnapshotId(snapshotId);
    });
  }, [appliedSnapshotId, snapshot, snapshotId, teamId]);

  const activeShotChart = shotChart ?? baseShot;
  const hasNoAttempts = Boolean(activeShotChart && activeShotChart.attempted === 0 && activeShotChart.data_status !== "missing");
  const needsPeriodRefresh = Boolean(
    situationalFilters.periodBucket !== "all" &&
      baseShot &&
      baseShot.attempted > 0 &&
      isLegacyPeriodContext(baseShot.shots) &&
      activeShotChart &&
      activeShotChart.attempted === 0
  );
  const isIntelligenceView = view === "quality" || view === "making" || view === "creation" || view === "summary";

  return (
    <section className="bip-shot-shell bip-shot-shell-neutral space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="bip-shot-kicker">Team Defense Surface</p>
          <h3 className="bip-display mt-2 text-[1.7rem] font-semibold text-[var(--foreground)]">
            Opponent Shot Lab
          </h3>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted-strong)]">
            See opponent shot quality, making, creation profile, and classic shot maps against {teamAbbreviation}. Team-defense intelligence depends on opponent shot-chart and warehouse coverage.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <ChartStatusBadge status={activeShotChart?.data_status ?? "missing"} compact />
          {(activeShotChart?.data_status === "missing" || activeShotChart?.data_status === "stale") ? (
            <button
              onClick={() => void refresh(true)}
              disabled={isRefreshing}
              className="rounded-full border border-[rgba(25,52,42,0.12)] bg-white px-3 py-1.5 text-xs font-medium text-[var(--foreground)] transition-colors hover:border-[rgba(25,52,42,0.24)] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isRefreshing ? "Refreshing..." : "Refresh opponent shots"}
            </button>
          ) : null}
          <ShotSnapshotButton
            payload={{
              subject_type: "team-defense",
              team_id: teamId,
              season: selectedSeason,
              season_type: seasonType,
              active_view: view,
              route_path: `/teams/${teamAbbreviation}?tab=analytics`,
              filters: {
                start_date: activeFilters.startDate,
                end_date: activeFilters.endDate,
                period_bucket: activeFilters.periodBucket,
                result: activeFilters.result,
                shot_value: activeFilters.shotValue,
              },
              metadata: {
                team_abbreviation: teamAbbreviation,
                intelligence_view: view,
                coverage_state: shotQuality?.coverage_state ?? activeShotChart?.completeness_status ?? activeShotChart?.data_status ?? "missing",
                methodology_version: shotQuality?.methodology_version ?? "shot_quality_v1",
                advanced_split_mode: view === "creation" ? "proxy-labeled" : "default",
              },
            }}
          />
        </div>
      </div>

      <ShotLabControls
        seasons={seasons}
        selectedSeason={selectedSeason}
        onSeasonChange={setSelectedSeason}
        seasonType={seasonType}
        onSeasonTypeChange={setSeasonType}
        preset={preset}
        onPresetChange={setPreset}
        customRange={customRange}
        onCustomRangeChange={setCustomRange}
        situationalFilters={situationalFilters}
        onSituationalFiltersChange={setSituationalFilters}
        availableStartDate={availableStartDate}
        availableEndDate={availableEndDate}
      />

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-[1.35rem] border border-[rgba(25,52,42,0.12)] bg-[rgba(255,255,255,0.62)] px-4 py-3 text-sm text-[var(--muted-strong)]">
        <div className="flex flex-wrap gap-2">
          {(["quality", "making", "creation", "summary", "value", "sprawl", "zone"] as TeamDefenseView[]).map((option) => (
            <button
              key={option}
              onClick={() => setView(option)}
              className={`rounded-full px-3 py-1.5 text-xs ${view === option ? "bip-toggle-active" : "bip-toggle"}`}
            >
              {option === "quality"
                ? "Quality"
                : option === "making"
                  ? "Making"
                  : option === "creation"
                    ? "Creation"
                    : option === "summary"
                      ? "Scout Summary"
                      : option === "value"
                        ? "Value map"
                        : option === "sprawl"
                          ? "Sprawl map"
                          : "Zone view"}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-2 text-[11px]">
          <span>{windowLabel(preset, filters)}</span>
          <span>{activeShotChart?.attempted ?? 0} opponent attempts</span>
          {activeShotChart?.completeness_status ? (
            <span className="rounded-full border border-[rgba(25,52,42,0.1)] bg-[rgba(255,255,255,0.78)] px-3 py-1.5">
              Completeness {activeShotChart.completeness_status}
            </span>
          ) : null}
        </div>
      </div>

      {activeShotChart?.data_status === "missing" ? (
        <div className="bip-empty flex flex-wrap items-center justify-between gap-3 rounded-[1.25rem] px-4 py-3 text-sm text-[var(--muted-strong)]">
          <span>Opponent shot context has not been prepared for this team and season yet.</span>
          <button
            onClick={() => void refresh(true)}
            disabled={isRefreshing}
            className="rounded-full border border-[rgba(25,52,42,0.12)] bg-white px-3 py-1.5 text-xs font-medium text-[var(--foreground)] transition-colors hover:border-[rgba(25,52,42,0.24)] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isRefreshing ? "Refreshing..." : "Refresh opponent shots"}
          </button>
        </div>
      ) : null}

      {needsPeriodRefresh ? (
        <div className="bip-empty flex flex-wrap items-center justify-between gap-3 rounded-[1.25rem] px-4 py-3 text-sm text-[var(--muted-strong)]">
          <span>
            Period filters need refreshed opponent shot-context data for this selection. Refresh now to pull the richer shot payload.
          </span>
          <button
            onClick={() => void refresh(true)}
            disabled={isRefreshing}
            className="rounded-full border border-[rgba(25,52,42,0.12)] bg-white px-3 py-1.5 text-xs font-medium text-[var(--foreground)] transition-colors hover:border-[rgba(25,52,42,0.24)] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isRefreshing ? "Refreshing..." : "Refresh opponent shots"}
          </button>
        </div>
      ) : null}

      {hasNoAttempts && !needsPeriodRefresh ? (
        <div className="bip-empty rounded-[1.25rem] px-4 py-3 text-sm text-[var(--muted-strong)]">
          No opponent attempts fall inside this selected window.
        </div>
      ) : null}

      {isIntelligenceView ? (
        <div className="space-y-4">
          {shootingSplits?.splits?.length ? (
            <section className="rounded-[1.25rem] border border-[rgba(25,52,42,0.12)] bg-[rgba(255,255,255,0.62)] p-4 text-sm text-[var(--muted-strong)]">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                    Canonical shot-profile context
                  </div>
                  <p className="mt-2 max-w-3xl leading-6">
                    Keep the defensive shot-lab read tied to the same persisted shooting-split families used by Style X-Ray and team compare.
                  </p>
                </div>
                <a
                  href={`/teams/${teamAbbreviation}?tab=splits&season=${selectedSeason}`}
                  className="rounded-full border border-[rgba(25,52,42,0.18)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]"
                >
                  Open shooting splits
                </a>
              </div>
            </section>
          ) : null}
          <ShotIntelligencePanel
            mode={view === "quality" ? "quality" : view === "making" ? "making" : view === "creation" ? "creation" : "summary"}
            quality={shotQuality}
            creation={shotCreation}
            identity={shotIdentity}
            label={
              view === "quality"
                ? "Opponent shot quality allowed"
                : view === "making"
                  ? "Opponent shot making allowed"
                  : view === "creation"
                    ? "Allowed creation profile"
                    : "Defensive shot profile identity"
            }
            contextLabel={`${teamAbbreviation} defense · depends on opponent shot-chart coverage`}
            isLoading={
              view === "quality" || view === "making"
                ? qualityLoading
                : view === "creation"
                  ? creationLoading
                  : identityLoading
            }
          />
        </div>
      ) : null}

      {!isIntelligenceView && !shotLoading && activeShotChart && activeShotChart.shots.length > 0 ? (
        view === "value" ? (
          <ShotValueMap shots={activeShotChart.shots} playerLabel="Opponent shot value" />
        ) : view === "sprawl" ? (
          <ShotSprawlMap shots={activeShotChart.shots} playerLabel="Opponent shot sprawl" />
        ) : (
          null
        )
      ) : null}

      {view === "zone" ? (
        <ZoneProfilePanel
          data={zoneProfile}
          isLoading={zoneLoading}
          playerLabel={`${teamAbbreviation} defensive profile`}
        />
      ) : null}
    </section>
  );
}
