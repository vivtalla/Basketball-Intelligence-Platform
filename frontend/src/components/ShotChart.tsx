"use client";

import { useMemo, useState } from "react";
import { usePlayerShotChart } from "@/hooks/usePlayerStats";
import type { ShotChartShot, ShotLabDateRange, ShotLabWindowPreset } from "@/lib/types";
import { LEAGUE_AVG_FG, ZONE_POINTS, ZONE_ORDER, heatColor } from "@/lib/shotchart-constants";
import { clampShotLabCustomRange, resolveShotLabRange } from "@/lib/shotlab";
import ChartStatusBadge from "./ChartStatusBadge";
import ZoneAnnotationCourt from "./ZoneAnnotationCourt";
import ShotCourt from "./ShotCourt";
import ShotValueMap from "./ShotValueMap";
import ShotSprawlMap from "./ShotSprawlMap";
import ShotDistanceProfile from "./ShotDistanceProfile";
import ShotLabControls from "./ShotLabControls";

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

// Zone constants imported from shared module
const LEAGUE_AVG = LEAGUE_AVG_FG;

interface ZoneStat {
  made: number;
  attempted: number;
}

function buildZoneStats(shots: ShotChartShot[]): Record<string, ZoneStat> {
  const stats: Record<string, ZoneStat> = {};
  for (const shot of shots) {
    const z = shot.zone_basic || "Unknown";
    if (!stats[z]) stats[z] = { made: 0, attempted: 0 };
    stats[z].attempted++;
    if (shot.shot_made) stats[z].made++;
  }
  return stats;
}

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

function ZoneBreakdown({ shots }: { shots: ShotChartShot[] }) {
  const zoneStats = buildZoneStats(shots);
  const zones = ZONE_ORDER.filter((z) => zoneStats[z]);
  const total = shots.length;

  if (zones.length === 0) return null;

  return (
    <div className="mt-6 border-t border-gray-100 dark:border-gray-700 pt-5">
      <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-3">
        Zone Breakdown
      </h4>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-gray-400 dark:text-gray-500 border-b border-gray-100 dark:border-gray-700">
              <th className="text-left pb-2 font-medium">Zone</th>
              <th className="text-right pb-2 font-medium">Freq</th>
              <th className="text-right pb-2 font-medium">FGM-A</th>
              <th className="text-right pb-2 font-medium">FG%</th>
              <th className="text-right pb-2 font-medium">PPS</th>
              <th className="pb-2 pl-4 font-medium w-36">vs League Avg</th>
            </tr>
          </thead>
          <tbody>
            {zones.map((zone) => {
              const { made, attempted } = zoneStats[zone];
              const pct = attempted > 0 ? made / attempted : null;
              const avg = LEAGUE_AVG[zone] ?? null;
              const pts = ZONE_POINTS[zone] ?? 2;
              const pps = pct !== null ? pct * pts : null;
              const avgPps = avg !== null ? avg * pts : null;
              const diff = pct !== null && avg !== null ? pct - avg : null;
              const freqPct = total > 0 ? (attempted / total) * 100 : 0;
              const lowSample = attempted < 5;

              let diffCls = "text-gray-400 dark:text-gray-500";
              if (!lowSample && diff !== null) {
                diffCls =
                  diff >= 0.03
                    ? "text-emerald-600 dark:text-emerald-400"
                    : diff <= -0.03
                    ? "text-red-500 dark:text-red-400"
                    : "text-gray-500 dark:text-gray-400";
              }

              const barMax = avg ? avg * 1.6 : 0.8;
              const playerBarW = pct !== null && !lowSample ? Math.min(100, (pct / barMax) * 100) : 0;
              const avgBarW = avg ? Math.min(100, (avg / barMax) * 100) : 0;

              return (
                <tr
                  key={zone}
                  className="border-b border-gray-50 dark:border-gray-700/50 last:border-0"
                >
                  <td className="py-2 pr-3 text-gray-700 dark:text-gray-300 whitespace-nowrap">
                    {zone}
                  </td>
                  <td className="py-2 text-right tabular-nums text-gray-500 dark:text-gray-400">
                    {freqPct.toFixed(0)}%
                  </td>
                  <td className="py-2 text-right tabular-nums text-gray-600 dark:text-gray-400">
                    {made}-{attempted}
                  </td>
                  <td className="py-2 text-right tabular-nums font-medium text-gray-900 dark:text-gray-100">
                    {lowSample ? (
                      <span className="text-gray-400 dark:text-gray-500">—</span>
                    ) : pct !== null ? (
                      `${(pct * 100).toFixed(1)}%`
                    ) : "—"}
                  </td>
                  <td className={`py-2 text-right tabular-nums font-medium ${lowSample ? "text-gray-400" : diffCls}`}>
                    {lowSample ? "—" : pps !== null ? pps.toFixed(2) : "—"}
                  </td>
                  <td className="py-2 pl-4">
                    {lowSample ? (
                      <span className="text-gray-400 dark:text-gray-500">small sample</span>
                    ) : (
                      <div className="space-y-0.5">
                        <div className="h-1.5 w-32 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${diff !== null && diff >= 0 ? "bg-emerald-500" : "bg-red-400"}`}
                            style={{ width: `${playerBarW}%` }}
                          />
                        </div>
                        <div className="h-1.5 w-32 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
                          <div
                            className="h-full rounded-full bg-gray-400 dark:bg-gray-500"
                            style={{ width: `${avgBarW}%` }}
                          />
                        </div>
                        <div className={`text-[10px] tabular-nums ${diffCls}`}>
                          {diff !== null
                            ? `${diff >= 0 ? "+" : ""}${(diff * 100).toFixed(1)}% · avg PPS ${avgPps?.toFixed(2)}`
                            : ""}
                        </div>
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="text-[10px] text-gray-400 dark:text-gray-500 mt-3">
        Freq = % of total FGA · PPS = FG% × point value · Top bar = player, bottom bar = league avg · &lt;5 attempts shown as —
      </p>
    </div>
  );
}

type ChartView = "scatter" | "heatmap" | "hex" | "value" | "sprawl";

const VIEW_LABELS: Record<ChartView, string> = {
  scatter: "Scatter",
  heatmap: "Heat",
  hex: "Hex",
  value: "Value",
  sprawl: "Sprawl",
};

const COURT_LABEL: Record<ChartView, string> = {
  scatter: "Shot scatter",
  heatmap: "Frequency heat",
  hex: "Hex density",
  value: "Value map",
  sprawl: "Sprawl map",
};

const VIEW_DESCRIPTIONS: Record<ChartView, string> = {
  scatter: "Every attempt plotted one by one.",
  heatmap: "A glowing shot-frequency portrait inspired by classic NBA density maps.",
  hex: "Efficiency and volume compressed into hex bins.",
  value: "Where shot diet creates or loses value.",
  sprawl: "A cinematic portrait of spatial pressure.",
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

export default function ShotChart({
  playerId,
  seasons,
  defaultSeason,
}: ShotChartProps) {
  const [selectedSeason, setSelectedSeason] = useState(defaultSeason);
  const [seasonType, setSeasonType] = useState<"Regular Season" | "Playoffs">("Regular Season");
  const [chartView, setChartView] = useState<ChartView>("scatter");
  const [preset, setPreset] = useState<ShotLabWindowPreset>("full");
  const [customRange, setCustomRange] = useState<ShotLabDateRange>({ startDate: null, endDate: null });

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

  function handleSeasonChange(nextSeason: string) {
    setSelectedSeason(nextSeason);
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

  const { data: filteredShotChart, isLoading: isFilteredLoading, error: filteredError } = usePlayerShotChart(
    playerId,
    selectedSeason,
    seasonType,
    filters
  );

  const activeShotChart = filteredShotChart ?? shotChart;

  const fgPct =
    activeShotChart && activeShotChart.attempted > 0
      ? ((activeShotChart.made / activeShotChart.attempted) * 100).toFixed(1)
      : null;
  const dataStatus = activeShotChart?.data_status ?? "missing";
  const isMissing = dataStatus === "missing";
  const isStale = dataStatus === "stale";
  const hasNoAttemptsInWindow = Boolean(
    activeShotChart &&
      activeShotChart.attempted === 0 &&
      !isMissing &&
      (filters.startDate || filters.endDate)
  );
  const isLoadingState = isLoading || isFilteredLoading;
  const activeError = filteredError ?? error;
  const windowLabel = describeShotWindow(preset, filters);
  const activeViewLabel = VIEW_LABELS[chartView];

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

          {/* Scatter / Heat / Hex / Value / Sprawl toggle */}
          <div className="flex flex-wrap gap-2 rounded-full border border-[rgba(25,52,42,0.08)] bg-[rgba(255,255,255,0.44)] p-1 text-xs shadow-[inset_0_1px_0_rgba(255,255,255,0.7)]">
            {(["scatter", "heatmap", "hex", "value", "sprawl"] as ChartView[]).map((view) => (
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
            {activeShotChart.last_synced_at && (
              <span className="text-[11px]">
                Synced {new Date(activeShotChart.last_synced_at).toLocaleDateString()}
              </span>
            )}
          </div>
        </div>
      )}

      {activeShotChart && !isLoadingState && isMissing && (
        <div className="bip-empty mb-4 rounded-[1.25rem] px-4 py-3 text-sm text-[var(--muted-strong)]">
          Shot chart data has not been synced for this player and season yet.
        </div>
      )}

      {hasNoAttemptsInWindow && (
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

        {/* Value map — full replacement for the SVG court section */}
        {chartView === "value" && activeShotChart && activeShotChart.shots.length > 0 && (
          <ShotValueMap shots={activeShotChart.shots} playerLabel={windowLabel} />
        )}

        {/* Sprawl map — full replacement for the SVG court section */}
        {chartView === "sprawl" && activeShotChart && activeShotChart.shots.length > 0 && (
          <ShotSprawlMap shots={activeShotChart.shots} playerLabel={windowLabel} />
        )}

        <div className={chartView === "value" || chartView === "sprawl" ? "hidden" : ""}>
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
            {chartView === "scatter" &&
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
          {chartView === "scatter" ? (
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
          </div>
        )}
        </div>{/* end hidden wrapper for scatter/heat/hex */}
      </div>

      {/* Zone annotation court — primary zone view */}
      {activeShotChart && activeShotChart.shots.length > 0 && (
        <div className="mt-6 border-t border-[rgba(25,52,42,0.08)] pt-5">
          <p className="bip-kicker mb-3">Zone Efficiency</p>
          <ZoneAnnotationCourt shots={activeShotChart.shots} compact />
        </div>
      )}

      {/* Zone breakdown table — secondary detail */}
      {activeShotChart && activeShotChart.shots.length > 0 && (
        <ZoneBreakdown shots={activeShotChart.shots} />
      )}

      {/* Distance signature strip */}
      {activeShotChart && activeShotChart.shots.length > 0 && (
        <div className="mt-6 border-t border-[rgba(25,52,42,0.08)] pt-5">
          <p className="bip-kicker mb-3">Distance Signature</p>
          <ShotDistanceProfile shots={activeShotChart.shots} playerLabel={windowLabel} />
        </div>
      )}
    </div>
  );
}
