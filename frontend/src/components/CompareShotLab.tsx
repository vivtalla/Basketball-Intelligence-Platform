"use client";

import { useMemo, useState, type ReactNode } from "react";
import { usePlayerShotChart, usePlayerZoneProfile } from "@/hooks/usePlayerStats";
import type { ShotChartShot, ShotLabDateRange, ShotLabWindowPreset } from "@/lib/types";
import { clampShotLabCustomRange, mergeAvailableShotDates, resolveShotLabRange } from "@/lib/shotlab";
import ChartStatusBadge from "./ChartStatusBadge";
import ShotDistanceProfile from "./ShotDistanceProfile";
import ShotLabControls from "./ShotLabControls";
import ShotProfileDuel from "./ShotProfileDuel";
import ShotSprawlMap from "./ShotSprawlMap";
import ShotValueMap from "./ShotValueMap";
import ZoneProfilePanel from "./ZoneProfilePanel";

type CompareShotView = "value" | "sprawl" | "distance";

interface CompareShotLabProps {
  playerAId: number;
  playerBId: number;
  playerALabel: string;
  playerBLabel: string;
  season: string;
  seasons: string[];
  onSeasonChange: (season: string) => void;
}

const VIEW_OPTIONS: Array<{ id: CompareShotView; label: string }> = [
  { id: "value", label: "Value map" },
  { id: "sprawl", label: "Sprawl map" },
  { id: "distance", label: "Distance profile" },
];

function buildZoneMaxFrequency(shots: ShotChartShot[]): number {
  if (shots.length === 0) return 0;
  const counts = new Map<string, number>();
  for (const shot of shots) {
    const zone = shot.zone_basic || "Unknown";
    counts.set(zone, (counts.get(zone) ?? 0) + 1);
  }
  return Math.max(...Array.from(counts.values()).map((value) => value / shots.length), 0);
}

function buildDistanceMaxFrequency(shots: ShotChartShot[]): number {
  if (shots.length === 0) return 0;
  const counts = new Map<number, number>();
  for (const shot of shots) {
    const distance = Math.floor(Math.max(0, shot.distance));
    counts.set(distance, (counts.get(distance) ?? 0) + 1);
  }
  return Math.max(...Array.from(counts.values()).map((value) => value / shots.length), 0);
}

function formatWindowLabel(preset: ShotLabWindowPreset, range: ShotLabDateRange): string {
  if (!range.startDate && !range.endDate) return "Full season window";
  if (preset === "last-5-games") return "Last 5 game dates";
  if (preset === "last-10-games") return "Last 10 game dates";
  if (preset === "last-30-days") return "Last 30 days";
  if (range.startDate && range.endDate) return `${range.startDate} to ${range.endDate}`;
  return "Custom window";
}

function ShotLabColumn({
  label,
  status,
  attempts,
  side,
  children,
}: {
  label: string;
  status: "ready" | "stale" | "missing";
  attempts: number;
  side: "left" | "right";
  children: ReactNode;
}) {
  return (
    <div
      className={`space-y-3 rounded-[1.9rem] border p-4 shadow-[0_16px_40px_rgba(47,43,36,0.06)] ${
        side === "left"
          ? "border-[rgba(33,72,59,0.16)] bg-[linear-gradient(180deg,rgba(255,252,247,0.88),rgba(228,236,232,0.72))]"
          : "border-[rgba(181,145,78,0.18)] bg-[linear-gradient(180deg,rgba(255,250,244,0.88),rgba(239,231,212,0.74))]"
      }`}
    >
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            {side === "left" ? "Left Surface" : "Right Surface"}
          </p>
          <p className="mt-1 text-sm font-semibold text-[var(--foreground)]">{label}</p>
          <p className="text-xs text-[var(--muted)]">{attempts} attempts in window</p>
        </div>
        <ChartStatusBadge status={status} compact />
      </div>
      {children}
    </div>
  );
}

export default function CompareShotLab({
  playerAId,
  playerBId,
  playerALabel,
  playerBLabel,
  season,
  seasons,
  onSeasonChange,
}: CompareShotLabProps) {
  const [seasonType, setSeasonType] = useState<"Regular Season" | "Playoffs">("Regular Season");
  const [preset, setPreset] = useState<ShotLabWindowPreset>("full");
  const [customRange, setCustomRange] = useState<ShotLabDateRange>({ startDate: null, endDate: null });
  const [view, setView] = useState<CompareShotView>("value");

  const { data: baseA } = usePlayerShotChart(playerAId, season, seasonType);
  const { data: baseB } = usePlayerShotChart(playerBId, season, seasonType);

  const availableDates = useMemo(
    () => mergeAvailableShotDates([baseA?.available_game_dates, baseB?.available_game_dates]),
    [baseA?.available_game_dates, baseB?.available_game_dates]
  );
  const availableStartDate = availableDates[0] ?? baseA?.available_start_date ?? baseB?.available_start_date ?? null;
  const availableEndDate = availableDates[availableDates.length - 1] ?? baseA?.available_end_date ?? baseB?.available_end_date ?? null;

  const filters = useMemo(
    () =>
      resolveShotLabRange(
        preset,
        availableDates,
        clampShotLabCustomRange(customRange, availableStartDate, availableEndDate)
      ),
    [availableDates, availableEndDate, availableStartDate, customRange, preset]
  );

  const { data: shotA, isLoading: shotALoading } = usePlayerShotChart(playerAId, season, seasonType, filters);
  const { data: shotB, isLoading: shotBLoading } = usePlayerShotChart(playerBId, season, seasonType, filters);
  const { data: zoneA, isLoading: zoneALoading } = usePlayerZoneProfile(playerAId, season, seasonType, filters);
  const { data: zoneB, isLoading: zoneBLoading } = usePlayerZoneProfile(playerBId, season, seasonType, filters);

  const sharedZoneFreq = useMemo(
    () => Math.max(buildZoneMaxFrequency(shotA?.shots ?? []), buildZoneMaxFrequency(shotB?.shots ?? []), 0.01),
    [shotA?.shots, shotB?.shots]
  );
  const sharedDistanceFreq = useMemo(
    () => Math.max(buildDistanceMaxFrequency(shotA?.shots ?? []), buildDistanceMaxFrequency(shotB?.shots ?? []), 0.001),
    [shotA?.shots, shotB?.shots]
  );

  const windowLabel = formatWindowLabel(preset, filters);
  const bothMissing = (shotA?.data_status ?? "missing") === "missing" && (shotB?.data_status ?? "missing") === "missing";
  const noAttemptsInWindow = Boolean(
    ((shotA?.attempted ?? 0) === 0 || !shotA) &&
      ((shotB?.attempted ?? 0) === 0 || !shotB) &&
      (filters.startDate || filters.endDate)
  );

  function handleSeasonChange(nextSeason: string) {
    onSeasonChange(nextSeason);
    setPreset("full");
    setCustomRange({ startDate: null, endDate: null });
  }

  function handleSeasonTypeChange(nextSeasonType: "Regular Season" | "Playoffs") {
    setSeasonType(nextSeasonType);
    setPreset("full");
    setCustomRange({ startDate: null, endDate: null });
  }

  function handleCustomRangeChange(nextRange: ShotLabDateRange) {
    setCustomRange(
      clampShotLabCustomRange(nextRange, availableStartDate, availableEndDate)
    );
  }

  return (
    <section className="bip-shot-shell bip-shot-shell-neutral space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="bip-shot-kicker">
            Compare Surface
          </p>
          <h3 className="bip-display mt-2 text-[1.7rem] font-semibold text-[var(--foreground)]">
            Shot Lab
          </h3>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted-strong)]">
            A premium duel surface with shared season and date window across value, sprawl, and distance views.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 rounded-full border border-[rgba(25,52,42,0.08)] bg-[rgba(255,255,255,0.46)] p-1">
          {VIEW_OPTIONS.map((option) => (
            <button
              key={option.id}
              onClick={() => setView(option.id)}
              className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                view === option.id ? "bip-toggle-active" : "bip-toggle"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      <ShotLabControls
        seasons={seasons}
        selectedSeason={season}
        onSeasonChange={handleSeasonChange}
        seasonType={seasonType}
        onSeasonTypeChange={handleSeasonTypeChange}
        preset={preset}
        onPresetChange={setPreset}
        customRange={customRange}
        onCustomRangeChange={handleCustomRangeChange}
        availableStartDate={availableStartDate}
        availableEndDate={availableEndDate}
      />

      <div className="grid gap-3 rounded-[1.4rem] border border-[rgba(25,52,42,0.12)] bg-[rgba(255,255,255,0.62)] px-4 py-3 text-sm text-[var(--muted-strong)] md:grid-cols-[1fr_auto_1fr] md:items-center">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">{playerALabel}</p>
          <p className="mt-1 text-sm text-[var(--foreground)]">{shotA?.attempted ?? 0} attempts</p>
        </div>
        <span>{windowLabel}</span>
        <div className="text-right">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">{playerBLabel}</p>
          <p className="mt-1 text-sm text-[var(--foreground)]">{shotB?.attempted ?? 0} attempts</p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3 text-xs text-[var(--muted)]">
        <span className="rounded-full border border-[rgba(25,52,42,0.1)] bg-[rgba(255,255,255,0.72)] px-3 py-1.5">{season}</span>
        <span className="rounded-full border border-[rgba(25,52,42,0.1)] bg-[rgba(255,255,255,0.72)] px-3 py-1.5">{seasonType}</span>
        <span className="rounded-full border border-[rgba(25,52,42,0.1)] bg-[rgba(255,255,255,0.72)] px-3 py-1.5">{VIEW_OPTIONS.find((option) => option.id === view)?.label}</span>
      </div>

      {bothMissing ? (
        <div className="rounded-[1.5rem] border border-dashed border-[rgba(25,52,42,0.16)] bg-[rgba(255,255,255,0.62)] px-4 py-4 text-sm text-[var(--muted-strong)]">
          Persisted shot charts are still missing for both players in this season/type.
        </div>
      ) : null}

      {noAttemptsInWindow ? (
        <div className="rounded-[1.5rem] border border-dashed border-[rgba(25,52,42,0.16)] bg-[rgba(255,255,255,0.62)] px-4 py-4 text-sm text-[var(--muted-strong)]">
          Neither player has shot attempts inside this selected window.
        </div>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-2">
        <ShotLabColumn
          label={playerALabel}
          status={shotA?.data_status ?? "missing"}
          attempts={shotA?.attempted ?? 0}
          side="left"
        >
          {view === "value" ? (
            <ShotValueMap shots={shotA?.shots ?? []} playerLabel={windowLabel} scaleMaxFreq={sharedZoneFreq} idPrefix="compare-left-value" />
          ) : view === "sprawl" ? (
            <ShotSprawlMap shots={shotA?.shots ?? []} playerLabel={windowLabel} idPrefix="compare-left-sprawl" />
          ) : (
            <ShotDistanceProfile shots={shotA?.shots ?? []} playerLabel={windowLabel} scaleMaxFrequency={sharedDistanceFreq} idPrefix="compare-left-distance" />
          )}
        </ShotLabColumn>

        <ShotLabColumn
          label={playerBLabel}
          status={shotB?.data_status ?? "missing"}
          attempts={shotB?.attempted ?? 0}
          side="right"
        >
          {view === "value" ? (
            <ShotValueMap shots={shotB?.shots ?? []} playerLabel={windowLabel} scaleMaxFreq={sharedZoneFreq} idPrefix="compare-right-value" />
          ) : view === "sprawl" ? (
            <ShotSprawlMap shots={shotB?.shots ?? []} playerLabel={windowLabel} idPrefix="compare-right-sprawl" />
          ) : (
            <ShotDistanceProfile shots={shotB?.shots ?? []} playerLabel={windowLabel} scaleMaxFrequency={sharedDistanceFreq} idPrefix="compare-right-distance" />
          )}
        </ShotLabColumn>
      </div>

      <ShotProfileDuel
        left={zoneA}
        right={zoneB}
        leftLabel={playerALabel}
        rightLabel={playerBLabel}
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <ZoneProfilePanel
          data={zoneA}
          isLoading={zoneALoading || shotALoading}
          playerLabel={playerALabel}
        />
        <ZoneProfilePanel
          data={zoneB}
          isLoading={zoneBLoading || shotBLoading}
          playerLabel={playerBLabel}
        />
      </div>
    </section>
  );
}
