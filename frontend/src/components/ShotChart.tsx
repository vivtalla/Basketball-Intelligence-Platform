"use client";

import dynamic from "next/dynamic";
import { useSearchParams } from "next/navigation";
import { startTransition, useEffect, useMemo, useState } from "react";
import {
  usePlayerShotChart,
  usePlayerShotCreation,
  usePlayerShotIdentity,
  usePlayerShotQuality,
  useShotChartRefresh,
  useShotLabSnapshot,
} from "@/hooks/usePlayerStats";
import type {
  ShotChartShot,
  ShotLabDateRange,
  ShotLabSituationalFilters,
  ShotLabWindowPreset,
} from "@/lib/types";
import { LEAGUE_AVG_FG, heatColor } from "@/lib/shotchart-constants";
import { clampShotLabCustomRange, resolveShotLabRange } from "@/lib/shotlab";
import ChartStatusBadge from "./ChartStatusBadge";
import ShotCourt from "./ShotCourt";
import ShotValueMap from "./ShotValueMap";
import ShotSprawlMap from "./ShotSprawlMap";
import ShotActionSignature from "./ShotActionSignature";
import ShotDistanceProfile from "./ShotDistanceProfile";
import ShotContextPanel from "./ShotContextPanel";
import ShotLabControls from "./ShotLabControls";
import ShotSnapshotButton from "./ShotSnapshotButton";
import ShotIntelligencePanel from "./ShotIntelligencePanel";
import { ShotDiagnosisPanel } from "./ShotDiagnosisPanel";

const ShotLab3DScene = dynamic(() => import("./three/ShotLab3DScene"), {
  ssr: false,
  loading: () => (
    <div className="rounded-[1.25rem] border border-[rgba(25,52,42,0.12)] bg-[rgba(255,255,255,0.68)] p-6 text-sm text-[var(--muted)]">
      Loading 3D view...
    </div>
  ),
});

interface ShotChartProps {
  playerId: number;
  seasons: string[];
  defaultSeason: string;
}

// SVG viewport — NBA coordinates mapped to:
//   svgX = loc_x + 250   (LOC_X: -250→0, 250→500)
//   svgY = 430 - loc_y   (LOC_Y:  -50→480, 0→430, 420→10)
const W = 500;
const H = 480;

function toSvg(locX: number, locY: number): [number, number] {
  return [locX + 250, 430 - locY];
}

const LEAGUE_AVG = LEAGUE_AVG_FG;

const HEAT_COLS = 28;
const HEAT_ROWS = 26;
const HEAT_CELL_W = W / HEAT_COLS;
const HEAT_CELL_H = H / HEAT_ROWS;

const HEAT_KERNEL = [
  [1, 4, 7, 4, 1],
  [4, 16, 26, 16, 4],
  [7, 26, 41, 26, 7],
  [4, 16, 26, 16, 4],
  [1, 4, 7, 4, 1],
];
const HEAT_KERNEL_SUM = 273;

function gaussianBlurHeatGrid(grid: number[][]): number[][] {
  const out: number[][] = Array.from({ length: HEAT_COLS }, () => new Array(HEAT_ROWS).fill(0));
  for (let col = 0; col < HEAT_COLS; col++) {
    for (let row = 0; row < HEAT_ROWS; row++) {
      let value = 0;
      for (let ki = 0; ki < 5; ki++) {
        for (let kj = 0; kj < 5; kj++) {
          const nc = col + ki - 2;
          const nr = row + kj - 2;
          if (nc >= 0 && nc < HEAT_COLS && nr >= 0 && nr < HEAT_ROWS) {
            value += HEAT_KERNEL[ki][kj] * grid[nc][nr];
          }
        }
      }
      out[col][row] = value / HEAT_KERNEL_SUM;
    }
  }
  return out;
}

function heatmapColor(t: number): string {
  if (t >= 0.92) return "rgba(255,250,181,0.96)";
  if (t >= 0.76) return "rgba(255,201,103,0.82)";
  if (t >= 0.56) return "rgba(255,142,110,0.62)";
  if (t >= 0.34) return "rgba(198,116,241,0.46)";
  if (t >= 0.16) return "rgba(129,74,205,0.3)";
  return "rgba(92,56,164,0.14)";
}

function heatmapRadius(t: number): number {
  return 14 + t * 28;
}

// ─── Hexbin logic (flat-top hexagons, pure math — no library) ────────────────

interface HexBin {
  cx: number;
  cy: number;
  made: number;
  attempted: number;
  diff: number | null;
  zone: string;
}

function computeHexBins(shots: ShotChartShot[], R: number): HexBin[] {
  const colStep = (3 / 2) * R;
  const rowStep = Math.sqrt(3) * R;

  const binMap = new Map<string, HexBin>();

  for (const shot of shots) {
    const [svgX, svgY] = toSvg(shot.loc_x, shot.loc_y);
    const col = Math.round(svgX / colStep);
    const rowOffset = col % 2 === 0 ? 0 : rowStep / 2;
    const row = Math.round((svgY - rowOffset) / rowStep);
    const key = `${col},${row}`;
    const cx = col * colStep;
    const cy = row * rowStep + rowOffset;

    if (!binMap.has(key)) {
      binMap.set(key, { cx, cy, made: 0, attempted: 0, diff: null, zone: shot.zone_basic || "Unknown" });
    }
    const bin = binMap.get(key)!;
    bin.attempted++;
    if (shot.shot_made) bin.made++;
  }

  // Compute efficiency diff per bin
  for (const bin of binMap.values()) {
    const avg = LEAGUE_AVG[bin.zone] ?? null;
    const pct = bin.attempted >= 3 ? bin.made / bin.attempted : null;
    bin.diff = pct !== null && avg !== null ? pct - avg : null;
  }

  return Array.from(binMap.values());
}

// Generate SVG polygon points string for a flat-top hexagon centered at (cx, cy) with radius r
function hexPoints(cx: number, cy: number, r: number): string {
  const pts: string[] = [];
  for (let i = 0; i < 6; i++) {
    const angleDeg = 60 * i; // flat-top: start at 0°
    const angleRad = (Math.PI / 180) * angleDeg;
    pts.push(`${(cx + r * Math.cos(angleRad)).toFixed(2)},${(cy + r * Math.sin(angleRad)).toFixed(2)}`);
  }
  return pts.join(" ");
}

function HexLayer({ shots }: { shots: ShotChartShot[] }) {
  const R = 20;
  const bins = computeHexBins(shots, R);
  const maxAttempted = Math.max(...bins.map((b) => b.attempted), 1);

  return (
    <>
      {bins.map((bin, i) => {
        const scale = 0.4 + 0.6 * (bin.attempted / maxAttempted);
        const r = R * scale;
        const pts = hexPoints(bin.cx, bin.cy, r);
        const pct = bin.attempted > 0 ? bin.made / bin.attempted : null;
        return (
          <polygon
            key={i}
            points={pts}
            fill={heatColor(bin.diff, 0.82)}
            stroke="rgba(255,255,255,0.35)"
            strokeWidth="0.8"
          >
            <title>
              {bin.zone}
              {`\n${bin.made}/${bin.attempted} FGM/FGA`}
              {pct !== null ? `\n${(pct * 100).toFixed(1)}% FG` : ""}
              {bin.diff !== null
                ? ` (${bin.diff >= 0 ? "+" : ""}${(bin.diff * 100).toFixed(1)}% vs avg)`
                : ""}
            </title>
          </polygon>
        );
      })}
    </>
  );
}

// ─────────────────────────────────────────────────────────────────────────────

function HeatmapZones({ shots }: { shots: ShotChartShot[] }) {
  const nodes = useMemo(() => {
    if (shots.length === 0) return [];

    const rawGrid: number[][] = Array.from({ length: HEAT_COLS }, () =>
      new Array(HEAT_ROWS).fill(0)
    );

    for (const shot of shots) {
      const [svgX, svgY] = toSvg(shot.loc_x, shot.loc_y);
      const col = Math.min(HEAT_COLS - 1, Math.max(0, Math.floor(svgX / HEAT_CELL_W)));
      const row = Math.min(HEAT_ROWS - 1, Math.max(0, Math.floor(svgY / HEAT_CELL_H)));
      rawGrid[col][row]++;
    }

    const blurred = gaussianBlurHeatGrid(rawGrid);
    const positiveValues = blurred.flat().filter((value) => value > 0).sort((left, right) => left - right);
    const softPeak =
      positiveValues[Math.max(0, Math.floor(positiveValues.length * 0.94) - 1)] ??
      Math.max(...blurred.flat(), 0.0001);
    const values: Array<{ x: number; y: number; intensity: number; core: number }> = [];

    for (let col = 0; col < HEAT_COLS; col++) {
      for (let row = 0; row < HEAT_ROWS; row++) {
        const normalized = Math.min(1, blurred[col][row] / Math.max(softPeak, 0.0001));
        const intensity = Math.pow(normalized, 0.88);
        if (intensity < 0.06) continue;
        values.push({
          x: col * HEAT_CELL_W + HEAT_CELL_W / 2,
          y: row * HEAT_CELL_H + HEAT_CELL_H / 2,
          intensity,
          core: Math.max(0, (intensity - 0.58) / 0.42),
        });
      }
    }

    return values.sort((left, right) => left.intensity - right.intensity);
  }, [shots]);

  return (
    <>
      <rect x="0" y="0" width={W} height={H} rx="18" fill="rgba(248,243,235,0.98)" />
      <rect x="0" y="0" width={W} height={H} rx="18" fill="url(#heatmapAtmosphere)" />
      <rect x="0" y="0" width={W} height={H} rx="18" fill="url(#heatmapVignette)" />
      <g filter="url(#heatmapGlow)">
        {nodes.map((node, index) => (
          <circle
            key={`${node.x}-${node.y}-${index}`}
            cx={node.x}
            cy={node.y}
            r={heatmapRadius(node.intensity)}
            fill={heatmapColor(node.intensity)}
          />
        ))}
      </g>
      <g filter="url(#heatmapCoreGlow)">
        {nodes
          .filter((node) => node.core > 0)
          .map((node, index) => (
            <circle
              key={`core-${node.x}-${node.y}-${index}`}
              cx={node.x}
              cy={node.y}
              r={8 + node.core * 18}
              fill={`rgba(255,248,182,${0.2 + node.core * 0.72})`}
            />
          ))}
      </g>
    </>
  );
}

type ChartView = "diet" | "quality" | "making" | "creation" | "summary" | "scatter" | "heatmap" | "hex" | "value" | "sprawl" | "three";

const VIEW_LABELS: Record<ChartView, string> = {
  diet: "Diet",
  quality: "Quality",
  making: "Making",
  creation: "Creation",
  summary: "Scout Summary",
  scatter: "Scatter",
  heatmap: "Heat",
  hex: "Hex",
  value: "Value",
  sprawl: "Sprawl",
  three: "3D",
};

const COURT_LABEL: Record<ChartView, string> = {
  diet: "Shot diet",
  quality: "Shot quality",
  making: "Shot making",
  creation: "Creation context",
  summary: "Scout summary",
  scatter: "Shot scatter",
  heatmap: "Frequency heat",
  hex: "Hex density",
  value: "Value map",
  sprawl: "Sprawl map",
  three: "3D shot scene",
};

const VIEW_DESCRIPTIONS: Record<ChartView, string> = {
  diet: "Where this player gets shots most often, before adding expected-value interpretation.",
  quality: "How favorable the attempt profile is versus league expectation.",
  making: "Where actual conversion beats or trails expected shot value.",
  creation: "Proxy-labeled creation context from action, clock, and linked shot fields.",
  summary: "A scouting-ready identity read built from shot diet, action mix, and coverage.",
  scatter: "Every attempt plotted one by one.",
  heatmap: "A glowing shot-frequency portrait inspired by classic NBA density maps.",
  hex: "Efficiency and volume compressed into hex bins.",
  value: "Where shot diet creates or loses value.",
  sprawl: "A cinematic portrait of spatial pressure.",
  three: "A reconstructed 3D court view with analytical shot arcs to the rim.",
};

const DEFAULT_SITUATIONAL_FILTERS: ShotLabSituationalFilters = {
  periodBucket: "all",
  result: "all",
  shotValue: "all",
};

function describeShotWindow(
  preset: ShotLabWindowPreset,
  filters: ShotLabDateRange
): string {
  if (!filters.startDate && !filters.endDate) {
    return "Full season window";
  }

  if (preset === "last-5-games") return "Last 5 game dates";
  if (preset === "last-10-games") return "Last 10 game dates";
  if (preset === "last-30-days") return "Last 30 days";
  if (filters.startDate && filters.endDate) return `${filters.startDate} to ${filters.endDate}`;
  if (filters.startDate) return `Since ${filters.startDate}`;
  if (filters.endDate) return `Through ${filters.endDate}`;
  return "Filtered window";
}

function describeSituationalFilters(filters: ShotLabSituationalFilters): string {
  const parts: string[] = [];
  if (filters.periodBucket !== "all") {
    parts.push(filters.periodBucket === "ot" ? "OT only" : filters.periodBucket.toUpperCase());
  }
  if (filters.result !== "all") {
    parts.push(filters.result === "made" ? "Makes only" : "Misses only");
  }
  if (filters.shotValue !== "all") {
    parts.push(filters.shotValue === "3pt" ? "3PT only" : "2PT only");
  }
  return parts.length > 0 ? parts.join(" · ") : "All situations";
}

function isLegacyPeriodContext(shots: ShotChartShot[] | undefined): boolean {
  if (!shots || shots.length === 0) return false;
  return !shots.some((shot) => typeof shot.period === "number" && Number.isFinite(shot.period));
}

export default function ShotChart({
  playerId,
  seasons,
  defaultSeason,
}: ShotChartProps) {
  const searchParams = useSearchParams();
  const snapshotId = searchParams.get("shot_snapshot_id");
  const { data: snapshot } = useShotLabSnapshot(snapshotId);
  const [selectedSeason, setSelectedSeason] = useState(defaultSeason);
  const [seasonType, setSeasonType] = useState<"Regular Season" | "Playoffs">("Regular Season");
  const [chartView, setChartView] = useState<ChartView>("diet");
  const [preset, setPreset] = useState<ShotLabWindowPreset>("full");
  const [customRange, setCustomRange] = useState<ShotLabDateRange>({ startDate: null, endDate: null });
  const [situationalFilters, setSituationalFilters] = useState<ShotLabSituationalFilters>(
    DEFAULT_SITUATIONAL_FILTERS
  );
  const [appliedSnapshotId, setAppliedSnapshotId] = useState<string | null>(null);

  const { data: shotChart, isLoading, error } = usePlayerShotChart(
    playerId,
    selectedSeason,
    seasonType
  );

  const availableDates = useMemo(
    () => shotChart?.available_game_dates ?? [],
    [shotChart?.available_game_dates]
  );
  const availableStartDate = shotChart?.available_start_date ?? null;
  const availableEndDate = shotChart?.available_end_date ?? null;

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
    () => ({
      ...filters,
      ...situationalFilters,
    }),
    [filters, situationalFilters]
  );

  function handleSeasonChange(nextSeason: string) {
    setSelectedSeason(nextSeason);
    setPreset("full");
    setCustomRange({ startDate: null, endDate: null });
    setSituationalFilters(DEFAULT_SITUATIONAL_FILTERS);
  }

  function handleSeasonTypeChange(nextSeasonType: "Regular Season" | "Playoffs") {
    setSeasonType(nextSeasonType);
    setPreset("full");
    setCustomRange({ startDate: null, endDate: null });
    setSituationalFilters(DEFAULT_SITUATIONAL_FILTERS);
  }

  function handleCustomRangeChange(nextRange: ShotLabDateRange) {
    setCustomRange(
      clampShotLabCustomRange(nextRange, availableStartDate, availableEndDate)
    );
  }

  const { data: filteredShotChart, isLoading: isFilteredLoading, error: filteredError } = usePlayerShotChart(
    playerId,
    selectedSeason,
    seasonType,
    activeFilters
  );
  const { data: shotQuality, isLoading: isQualityLoading } = usePlayerShotQuality(
    playerId,
    selectedSeason,
    seasonType,
    activeFilters
  );
  const { data: shotCreation, isLoading: isCreationLoading } = usePlayerShotCreation(
    playerId,
    selectedSeason,
    seasonType,
    activeFilters
  );
  const { data: shotIdentity, isLoading: isIdentityLoading } = usePlayerShotIdentity(
    playerId,
    selectedSeason,
    seasonType,
    activeFilters
  );

  const { refresh, isRefreshing } = useShotChartRefresh(
    playerId,
    selectedSeason,
    seasonType,
    activeFilters
  );

  const activeShotChart = filteredShotChart ?? shotChart;

  const fgPct =
    activeShotChart && activeShotChart.attempted > 0
      ? ((activeShotChart.made / activeShotChart.attempted) * 100).toFixed(1)
      : null;
  const dataStatus = activeShotChart?.data_status ?? "missing";
  const isMissing = dataStatus === "missing";
  const isStale = dataStatus === "stale";
  const hasActiveSelection =
    Boolean(filters.startDate || filters.endDate) ||
    situationalFilters.periodBucket !== "all" ||
    situationalFilters.result !== "all" ||
    situationalFilters.shotValue !== "all";
  const hasNoAttemptsInWindow = Boolean(
    activeShotChart &&
      activeShotChart.attempted === 0 &&
      !isMissing &&
      hasActiveSelection
  );
  const needsPeriodRefresh = Boolean(
    situationalFilters.periodBucket !== "all" &&
      shotChart &&
      shotChart.attempted > 0 &&
      isLegacyPeriodContext(shotChart.shots) &&
      activeShotChart &&
      activeShotChart.attempted === 0
  );
  const isLoadingState = isLoading || isFilteredLoading;
  const activeError = filteredError ?? error;
  const windowLabel = describeShotWindow(preset, filters);
  const situationalLabel = describeSituationalFilters(situationalFilters);
  const activeViewLabel = VIEW_LABELS[chartView];
  const isIntelligenceView = chartView === "quality" || chartView === "making" || chartView === "creation" || chartView === "summary";

  useEffect(() => {
    if (!snapshotId || !snapshot || appliedSnapshotId === snapshotId) return;
    if (snapshot.payload.subject_type !== "player" || snapshot.payload.subject_id !== playerId) return;
    startTransition(() => {
      setSelectedSeason(snapshot.payload.season);
      setSeasonType(snapshot.payload.season_type === "Playoffs" ? "Playoffs" : "Regular Season");
      setChartView((snapshot.payload.active_view as ChartView) ?? "diet");
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
  }, [appliedSnapshotId, playerId, snapshot, snapshotId]);

  return (
    <div className="bip-shot-shell bip-shot-shell-accent">
      {/* Header */}
      <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="bip-shot-kicker">
            Player Surface
          </p>
          <h3 className="bip-display mt-2 text-[1.7rem] font-semibold text-[var(--foreground)]">
            Shot Lab
          </h3>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted-strong)]">
            {VIEW_DESCRIPTIONS[chartView]}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <ChartStatusBadge status={dataStatus} compact />
          <ShotSnapshotButton
            payload={{
              subject_type: "player",
              subject_id: playerId,
              season: selectedSeason,
              season_type: seasonType,
              active_view: chartView,
              route_path: `/players/${playerId}`,
              filters: {
                start_date: filters.startDate,
                end_date: filters.endDate,
                period_bucket: situationalFilters.periodBucket,
                result: situationalFilters.result,
                shot_value: situationalFilters.shotValue,
              },
              metadata: {
                intelligence_view: chartView,
                coverage_state: shotQuality?.coverage_state ?? activeShotChart?.completeness_status ?? dataStatus,
                methodology_version: shotQuality?.methodology_version ?? "shot_quality_v1",
                advanced_split_mode: chartView === "creation" ? "proxy-labeled" : "default",
              },
            }}
          />

          {/* Intelligence and classic chart toggles */}
          <div className="flex flex-wrap gap-2 rounded-full border border-[rgba(25,52,42,0.08)] bg-[rgba(255,255,255,0.44)] p-1 text-xs shadow-[inset_0_1px_0_rgba(255,255,255,0.7)]">
            {(["diet", "quality", "making", "creation", "summary", "scatter", "heatmap", "hex", "value", "sprawl", "three"] as ChartView[]).map((view) => (
              <button
                key={view}
                onClick={() => setChartView(view)}
                className={`rounded-full px-3 py-1.5 transition-colors ${
                  chartView === view ? "bip-toggle-active" : "bip-toggle"
                }`}
              >
                {VIEW_LABELS[view]}
              </button>
            ))}
          </div>
        </div>
      </div>

      <ShotLabControls
        seasons={seasons}
        selectedSeason={selectedSeason}
        onSeasonChange={handleSeasonChange}
        seasonType={seasonType}
        onSeasonTypeChange={handleSeasonTypeChange}
        preset={preset}
        onPresetChange={setPreset}
        customRange={customRange}
        onCustomRangeChange={handleCustomRangeChange}
        situationalFilters={situationalFilters}
        onSituationalFiltersChange={setSituationalFilters}
        availableStartDate={availableStartDate}
        availableEndDate={availableEndDate}
      />

      {/* FG% summary */}
      {activeShotChart && !isLoadingState && (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-[1.35rem] border border-[rgba(25,52,42,0.12)] bg-[rgba(255,255,255,0.6)] px-4 py-3 text-sm text-[var(--muted-strong)]">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
              {activeViewLabel}
            </p>
            <p className="mt-1">
            {activeShotChart.made} / {activeShotChart.attempted} FG
            {fgPct !== null && <> ({fgPct}%)</>}
            {activeShotChart.attempted === 0 && !isMissing && (
              <span className="ml-1 italic">— no shot data for this period</span>
            )}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[11px]">{windowLabel}</span>
            <span className="text-[11px]">{situationalLabel}</span>
            {activeShotChart.last_synced_at && (
              <span className="text-[11px]">
                Synced {new Date(activeShotChart.last_synced_at).toLocaleDateString()}
              </span>
            )}
          </div>
        </div>
      )}

      {activeShotChart && !isLoadingState && isMissing && (
        <div className="bip-empty mb-4 flex flex-wrap items-center justify-between gap-3 rounded-[1.25rem] px-4 py-3 text-sm text-[var(--muted-strong)]">
          <span>Shot chart data has not been synced for this player and season yet.</span>
          <button
            onClick={() => refresh(true)}
            disabled={isRefreshing}
            className="rounded-full border border-[rgba(25,52,42,0.12)] bg-white px-3 py-1.5 text-xs font-medium text-[var(--foreground)] transition-colors hover:border-[rgba(25,52,42,0.24)] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isRefreshing ? "Refreshing..." : "Refresh shot chart"}
          </button>
        </div>
      )}

      {needsPeriodRefresh && (
        <div className="bip-empty mb-4 flex flex-wrap items-center justify-between gap-3 rounded-[1.25rem] px-4 py-3 text-sm text-[var(--muted-strong)]">
          <span>
            Period filters need refreshed shot-context data for this selection. Refresh now to pull the richer shot payload.
          </span>
          <button
            onClick={() => refresh(true)}
            disabled={isRefreshing}
            className="rounded-full border border-[rgba(25,52,42,0.12)] bg-white px-3 py-1.5 text-xs font-medium text-[var(--foreground)] transition-colors hover:border-[rgba(25,52,42,0.24)] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isRefreshing ? "Refreshing..." : "Refresh shot chart"}
          </button>
        </div>
      )}

      {hasNoAttemptsInWindow && !needsPeriodRefresh && (
        <div className="bip-empty mb-4 rounded-[1.25rem] px-4 py-3 text-sm text-[var(--muted-strong)]">
          No shot attempts fall inside this selected date window.
        </div>
      )}

      {/* Court SVG */}
      <div className="relative">
        {isLoadingState && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/80 rounded-lg z-10">
            <div className="w-8 h-8 border-2 border-[var(--accent)] border-t-transparent rounded-full animate-spin" />
          </div>
        )}
        {activeError && !isLoadingState && (
          <p className="text-center py-10 text-sm text-red-500">
            Could not load shot data.
          </p>
        )}

        {isIntelligenceView && (
          <ShotIntelligencePanel
            mode={chartView === "quality" ? "quality" : chartView === "making" ? "making" : chartView === "creation" ? "creation" : "summary"}
            quality={shotQuality}
            creation={shotCreation}
            identity={shotIdentity}
            label={activeViewLabel}
            contextLabel={`${windowLabel} · ${situationalLabel}`}
            isLoading={
              chartView === "quality" || chartView === "making"
                ? isQualityLoading
                : chartView === "creation"
                  ? isCreationLoading
                  : isIdentityLoading
            }
          />
        )}

        {isIntelligenceView && (
          <ShotDiagnosisPanel playerId={playerId} season={selectedSeason} />
        )}

        {/* Value map — full replacement for the SVG court section */}
        {chartView === "value" && activeShotChart && activeShotChart.shots.length > 0 && (
          <ShotValueMap shots={activeShotChart.shots} playerLabel={windowLabel} />
        )}

        {/* Sprawl map — full replacement for the SVG court section */}
        {chartView === "sprawl" && activeShotChart && activeShotChart.shots.length > 0 && (
          <ShotSprawlMap shots={activeShotChart.shots} playerLabel={windowLabel} />
        )}

        {chartView === "three" && activeShotChart && activeShotChart.shots.length > 0 && (
          <ShotLab3DScene shots={activeShotChart.shots} />
        )}

        <div className={chartView === "value" || chartView === "sprawl" || chartView === "three" || isIntelligenceView ? "hidden" : ""}>
        <div className="bip-shot-canvas">
          <svg viewBox={`0 0 ${W} ${H}`} className="w-full max-w-lg mx-auto block">
            <defs>
              <linearGradient id="courtWash" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="rgba(255,255,255,0.98)" />
                <stop offset="100%" stopColor="rgba(228,236,232,0.94)" />
              </linearGradient>
              <radialGradient id="heatmapAtmosphere" cx="50%" cy="18%" r="88%">
                <stop offset="0%" stopColor="rgba(145,108,224,0.18)" />
                <stop offset="42%" stopColor="rgba(92,56,164,0.12)" />
                <stop offset="100%" stopColor="rgba(255,255,255,0)" />
              </radialGradient>
              <radialGradient id="heatmapVignette" cx="50%" cy="64%" r="82%">
                <stop offset="0%" stopColor="rgba(255,255,255,0)" />
                <stop offset="100%" stopColor="rgba(72,39,137,0.08)" />
              </radialGradient>
              <filter id="heatmapGlow" x="-35%" y="-35%" width="170%" height="170%">
                <feGaussianBlur stdDeviation="14" />
              </filter>
              <filter id="heatmapCoreGlow" x="-30%" y="-30%" width="160%" height="160%">
                <feGaussianBlur stdDeviation="8" />
              </filter>
            </defs>
            <rect x="0" y="0" width={W} height={H} rx="18" fill="url(#courtWash)" />

            {/* Zone heatmap overlays (behind court markings) */}
            {chartView === "heatmap" && activeShotChart && activeShotChart.shots.length > 0 && (
              <HeatmapZones shots={activeShotChart.shots} />
            )}

            {/* Hexbin layer (behind court markings) */}
            {chartView === "hex" && activeShotChart && activeShotChart.shots.length > 0 && (
              <HexLayer shots={activeShotChart.shots} />
            )}

            <ShotCourt tone={chartView === "heatmap" ? "dark" : "light"} />

            {/* Season / mode label badge */}
            <rect
              x="24"
              y="18"
              width="130"
              height="48"
              rx="14"
              fill={chartView === "heatmap" ? "rgba(255,255,255,0.78)" : "rgba(255,255,255,0.86)"}
            />
            <text
              x="38"
              y="38"
              fontSize="10"
              fontWeight="600"
              fill={chartView === "heatmap" ? "rgba(100,71,167,0.82)" : "var(--muted)"}
              letterSpacing="0.12em"
            >
              {selectedSeason} · {seasonType === "Regular Season" ? "RS" : "PO"}
            </text>
            <text
              x="38"
              y="55"
              fontSize="13"
              fontWeight="600"
              fill={chartView === "heatmap" ? "rgba(43,34,71,0.96)" : "var(--foreground)"}
            >
              {COURT_LABEL[chartView]}
            </text>

            {/* Scatter: individual shots colored by made/missed */}
            {(chartView === "scatter" || chartView === "diet") &&
              activeShotChart?.shots.map((shot, i) => {
                const [x, y] = toSvg(shot.loc_x, shot.loc_y);
                return (
                  <circle
                    key={i}
                    cx={x}
                    cy={y}
                    r="4"
                    fill={shot.shot_made ? "#21483b" : "#b25b4f"}
                    fillOpacity={shot.shot_made ? 0.82 : 0.42}
                    stroke={shot.shot_made ? "#21483b" : "#9f3f31"}
                    strokeWidth="0.5"
                  >
                    <title>
                      {shot.action_type} · {shot.distance} ft ·{" "}
                      {shot.shot_made ? "Made ✓" : "Missed ✗"}
                    </title>
                  </circle>
                );
              })}

          </svg>
        </div>

        {/* Legend */}
        <div className="bip-shot-legend mt-3 justify-center text-xs text-[var(--muted)]">
          {chartView === "scatter" || chartView === "diet" ? (
            <>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-[rgba(25,52,42,0.1)] bg-[rgba(255,255,255,0.72)] px-3 py-1.5">
                <span className="inline-block w-3 h-3 rounded-full bg-[#21483b] opacity-80" />
                Made
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-[rgba(25,52,42,0.1)] bg-[rgba(255,255,255,0.72)] px-3 py-1.5">
                <span className="inline-block w-3 h-3 rounded-full bg-[#b25b4f] opacity-50" />
                Missed
              </span>
            </>
          ) : chartView === "hex" ? (
            <>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-[rgba(25,52,42,0.1)] bg-[rgba(255,255,255,0.72)] px-3 py-1.5">
                <span className="inline-block w-3 h-3 rounded-sm bg-emerald-500" />
                Above avg
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-[rgba(25,52,42,0.1)] bg-[rgba(255,255,255,0.72)] px-3 py-1.5">
                <span className="inline-block w-3 h-3 rounded-sm bg-gray-400" />
                Near avg
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-[rgba(25,52,42,0.1)] bg-[rgba(255,255,255,0.72)] px-3 py-1.5">
                <span className="inline-block w-3 h-3 rounded-sm bg-red-500" />
                Below avg
              </span>
              <span className="inline-flex items-center rounded-full border border-[rgba(25,52,42,0.1)] bg-[rgba(255,255,255,0.72)] px-3 py-1.5">
                Larger hex = more attempts
              </span>
            </>
          ) : (
            <>
              {chartView === "heatmap" ? (
                <>
                  <span className="inline-flex items-center gap-1.5 rounded-full border border-[rgba(25,52,42,0.1)] bg-[rgba(255,255,255,0.72)] px-3 py-1.5">
                    <span className="inline-block h-3 w-8 rounded-full bg-[linear-gradient(90deg,rgba(62,19,128,0.9),rgba(255,123,84,0.95),rgba(255,249,179,0.98))]" />
                    Shot frequency
                  </span>
                  <span className="inline-flex items-center rounded-full border border-[rgba(25,52,42,0.1)] bg-[rgba(255,255,255,0.72)] px-3 py-1.5">
                    Darker glow = hotter shot volume
                  </span>
                </>
              ) : (
                <>
                  <span className="inline-flex items-center gap-1.5 rounded-full border border-[rgba(25,52,42,0.1)] bg-[rgba(255,255,255,0.72)] px-3 py-1.5">
                    <span className="inline-block w-3 h-3 rounded-full bg-emerald-500" />
                    Above avg
                  </span>
                  <span className="inline-flex items-center gap-1.5 rounded-full border border-[rgba(25,52,42,0.1)] bg-[rgba(255,255,255,0.72)] px-3 py-1.5">
                    <span className="inline-block w-3 h-3 rounded-full bg-gray-400" />
                    Near avg
                  </span>
                  <span className="inline-flex items-center gap-1.5 rounded-full border border-[rgba(25,52,42,0.1)] bg-[rgba(255,255,255,0.72)] px-3 py-1.5">
                    <span className="inline-block w-3 h-3 rounded-full bg-red-500" />
                    Below avg
                  </span>
                  <span className="inline-flex items-center rounded-full border border-[rgba(25,52,42,0.1)] bg-[rgba(255,255,255,0.72)] px-3 py-1.5">
                    hover zones for details
                  </span>
                </>
              )}
            </>
          )}
        </div>

        {(isStale || isMissing) && (
          <div className="mt-3 rounded-xl border border-[rgba(25,52,42,0.12)] bg-[rgba(255,255,255,0.68)] px-3 py-2 text-xs text-[var(--muted-strong)]">
            {isStale
              ? "Showing cached shot data while the persisted feed catches up."
              : "This chart is DB-first, and shot data has not been synced for this player-season yet."}
            {(isStale || isMissing) && (
              <button
                onClick={() => refresh(true)}
                disabled={isRefreshing}
                className="ml-3 rounded-full border border-[rgba(25,52,42,0.12)] bg-white px-3 py-1.5 text-[11px] font-medium text-[var(--foreground)] transition-colors hover:border-[rgba(25,52,42,0.24)] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isRefreshing ? "Refreshing..." : "Refresh now"}
              </button>
            )}
          </div>
        )}
        </div>{/* end hidden wrapper for scatter/heat/hex */}
      </div>

      {activeShotChart && activeShotChart.shots.length > 0 && !isIntelligenceView && (
        <div className="mt-5 rounded-[1rem] border border-[rgba(25,52,42,0.1)] bg-[rgba(255,255,255,0.58)] px-4 py-3 text-xs leading-5 text-[var(--muted-strong)]">
          Shot Lab keeps detailed zone, quality, making, creation, and scout identity analysis inside the view tabs above. Use Quality for expected value, Making for actual-minus-expected, and Creation for proxy-labeled shot context.
        </div>
      )}

      {chartView === "diet" && activeShotChart && activeShotChart.shots.length > 0 && (
        <div className="mt-5 space-y-5">
          <ShotActionSignature shots={activeShotChart.shots} />
          <ShotDistanceProfile shots={activeShotChart.shots} playerLabel={windowLabel} />
        </div>
      )}

      {chartView === "creation" && activeShotChart && activeShotChart.shots.length > 0 && (
        <ShotContextPanel shots={activeShotChart.shots} season={selectedSeason} />
      )}
    </div>
  );
}
