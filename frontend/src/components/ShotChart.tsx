"use client";

import { useState } from "react";
import { usePlayerShotChart } from "@/hooks/usePlayerStats";
import type { ShotChartShot } from "@/lib/types";

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

// League-average FG% by zone (approximate, current era)
const LEAGUE_AVG: Record<string, number> = {
  "Restricted Area": 0.64,
  "In The Paint (Non-RA)": 0.40,
  "Mid-Range": 0.41,
  "Left Corner 3": 0.38,
  "Right Corner 3": 0.38,
  "Above the Break 3": 0.36,
  "Backcourt": 0.02,
};

// Point value per zone (2 or 3)
const ZONE_POINTS: Record<string, number> = {
  "Restricted Area": 2,
  "In The Paint (Non-RA)": 2,
  "Mid-Range": 2,
  "Left Corner 3": 3,
  "Right Corner 3": 3,
  "Above the Break 3": 3,
  "Backcourt": 3,
};

const ZONE_ORDER = [
  "Restricted Area",
  "In The Paint (Non-RA)",
  "Mid-Range",
  "Left Corner 3",
  "Right Corner 3",
  "Above the Break 3",
  "Backcourt",
];

// SVG paths for each zone (half-court, basket at cx=250 cy=430)
// Paint: x 170-330, y 240-430 | RA: cx=250 cy=430 r=40
// Corner 3 lines: x=30 and x=470 from y=480 to y=341
// 3pt arc: (30,341) A 237.5,237.5 0 0 0 (470,341)
const ZONE_PATHS: Record<string, string> = {
  "Restricted Area":
    "M 210,430 A 40,40 0 0 0 290,430 L 250,430 Z",
  "In The Paint (Non-RA)":
    "M 170,240 L 330,240 L 330,430 L 290,430 A 40,40 0 0 1 210,430 L 170,430 Z",
  "Left Corner 3":
    "M 0,341 L 30,341 L 30,480 L 0,480 Z",
  "Right Corner 3":
    "M 470,341 L 500,341 L 500,480 L 470,480 Z",
  // Mid-range: inside 3pt arc & corner lines, outside paint
  "Mid-Range":
    "M 30,341 A 237.5,237.5 0 0 0 470,341 L 470,480 L 330,480 L 330,240 L 170,240 L 170,480 L 30,480 Z",
  // Above the break 3: outside 3pt arc (upper court)
  "Above the Break 3":
    "M 0,0 L 500,0 L 500,341 L 470,341 A 237.5,237.5 0 0 1 30,341 L 0,341 Z",
  "Backcourt": "",
};

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

// Green → gray → red gradient based on efficiency delta vs league avg
function heatColor(diff: number | null, alpha = 0.55): string {
  if (diff === null) return `rgba(156,163,175,${alpha})`;
  if (diff >= 0.08) return `rgba(22,163,74,${alpha})`;
  if (diff >= 0.04) return `rgba(74,222,128,${alpha})`;
  if (diff >= 0) return `rgba(134,239,172,${alpha})`;
  if (diff >= -0.04) return `rgba(252,165,165,${alpha})`;
  if (diff >= -0.08) return `rgba(248,113,113,${alpha})`;
  return `rgba(220,38,38,${alpha})`;
}

function HeatmapZones({ shots }: { shots: ShotChartShot[] }) {
  const zoneStats = buildZoneStats(shots);
  const total = shots.length;

  return (
    <>
      {ZONE_ORDER.filter((z) => ZONE_PATHS[z]).map((zone) => {
        const stat = zoneStats[zone];
        const avg = LEAGUE_AVG[zone] ?? null;
        const pct = stat && stat.attempted >= 5 ? stat.made / stat.attempted : null;
        const diff = pct !== null && avg !== null ? pct - avg : null;
        const freqPct = stat && total > 0 ? ((stat.attempted / total) * 100).toFixed(0) : "0";
        const path = ZONE_PATHS[zone];
        if (!path) return null;
        return (
          <path
            key={zone}
            d={path}
            fill={heatColor(diff)}
            stroke="rgba(255,255,255,0.25)"
            strokeWidth="1"
          >
            <title>
              {zone}
              {stat ? `\n${stat.made}/${stat.attempted} FGM/FGA` : "\nNo shots"}
              {pct !== null
                ? `\n${(pct * 100).toFixed(1)}% FG (${diff !== null ? (diff >= 0 ? "+" : "") + (diff * 100).toFixed(1) : "—"}% vs avg)`
                : "\n< 5 attempts"}
              {`\n${freqPct}% of shots`}
            </title>
          </path>
        );
      })}
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

function CourtMarkings() {
  return (
    <g
      stroke="currentColor"
      strokeWidth="1.5"
      fill="none"
      className="text-gray-300 dark:text-gray-600"
    >
      <rect x="0" y="0" width={W} height={H} />
      <rect x="170" y="240" width="160" height="190" />
      <path d="M 170,240 A 60,60 0 0 0 330,240" />
      <path d="M 170,240 A 60,60 0 0 1 330,240" strokeDasharray="5 4" />
      <path d="M 210,430 A 40,40 0 0 0 290,430" />
      <circle cx="250" cy="430" r="7.5" />
      <line x1="220" y1="438" x2="280" y2="438" strokeWidth="2.5" />
      <line x1="30" y1={H} x2="30" y2="341" />
      <line x1="470" y1={H} x2="470" y2="341" />
      <path d="M 30,341 A 237.5,237.5 0 0 0 470,341" />
    </g>
  );
}

type ChartView = "scatter" | "heatmap";

export default function ShotChart({
  playerId,
  seasons,
  defaultSeason,
}: ShotChartProps) {
  const [selectedSeason, setSelectedSeason] = useState(defaultSeason);
  const [seasonType, setSeasonType] = useState<"Regular Season" | "Playoffs">("Regular Season");
  const [chartView, setChartView] = useState<ChartView>("scatter");

  const { data: shotChart, isLoading, error } = usePlayerShotChart(
    playerId,
    selectedSeason,
    seasonType
  );

  const fgPct =
    shotChart && shotChart.attempted > 0
      ? ((shotChart.made / shotChart.attempted) * 100).toFixed(1)
      : null;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 p-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <h3 className="font-semibold text-gray-900 dark:text-gray-100">Shot Chart</h3>

        <div className="flex flex-wrap items-center gap-3">
          {/* Scatter / Heatmap */}
          <div className="flex rounded-lg overflow-hidden border border-gray-200 dark:border-gray-600 text-xs">
            {(["scatter", "heatmap"] as ChartView[]).map((view) => (
              <button
                key={view}
                onClick={() => setChartView(view)}
                className={`px-3 py-1.5 capitalize transition-colors ${
                  chartView === view
                    ? "bip-toggle-active"
                    : "bip-toggle"
                }`}
              >
                {view}
              </button>
            ))}
          </div>

          {/* Season selector */}
          <select
            value={selectedSeason}
            onChange={(e) => setSelectedSeason(e.target.value)}
            className="text-sm border border-gray-200 dark:border-gray-600 rounded-lg px-2 py-1 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {seasons.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>

          {/* RS / Playoffs */}
          <div className="flex rounded-lg overflow-hidden border border-gray-200 dark:border-gray-600 text-xs">
            {(["Regular Season", "Playoffs"] as const).map((type) => (
              <button
                key={type}
                onClick={() => setSeasonType(type)}
                className={`px-3 py-1.5 transition-colors ${
                  seasonType === type
                    ? "bip-toggle-active"
                    : "bip-toggle"
                }`}
              >
                {type}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* FG% summary */}
      {shotChart && !isLoading && (
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
          {shotChart.made} / {shotChart.attempted} FG
          {fgPct !== null && <> ({fgPct}%)</>}
          {shotChart.attempted === 0 && (
            <span className="ml-1 italic">— no shot data for this period</span>
          )}
        </p>
      )}

      {/* Court SVG */}
      <div className="relative">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/80 dark:bg-gray-800/80 rounded-lg z-10">
            <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          </div>
        )}
        {error && !isLoading && (
          <p className="text-center py-10 text-sm text-red-500 dark:text-red-400">
            Could not load shot data.
          </p>
        )}

        <svg viewBox={`0 0 ${W} ${H}`} className="w-full max-w-lg mx-auto block">
          {/* Zone heatmap overlays */}
          {chartView === "heatmap" && shotChart && shotChart.shots.length > 0 && (
            <HeatmapZones shots={shotChart.shots} />
          )}

          <CourtMarkings />

          {/* Scatter: individual shots colored by made/missed */}
          {chartView === "scatter" &&
            shotChart?.shots.map((shot, i) => {
              const [x, y] = toSvg(shot.loc_x, shot.loc_y);
              return (
                <circle
                  key={i}
                  cx={x}
                  cy={y}
                  r="4"
                  fill={shot.shot_made ? "#22c55e" : "#ef4444"}
                  fillOpacity={shot.shot_made ? 0.75 : 0.45}
                  stroke={shot.shot_made ? "#16a34a" : "#dc2626"}
                  strokeWidth="0.5"
                >
                  <title>
                    {shot.action_type} · {shot.distance} ft ·{" "}
                    {shot.shot_made ? "Made ✓" : "Missed ✗"}
                  </title>
                </circle>
              );
            })}

          {/* Heatmap: shots colored by zone efficiency vs league avg */}
          {chartView === "heatmap" &&
            shotChart &&
            (() => {
              const zoneStats = buildZoneStats(shotChart.shots);
              return shotChart.shots.map((shot, i) => {
                const [x, y] = toSvg(shot.loc_x, shot.loc_y);
                const stat = zoneStats[shot.zone_basic];
                const avg = LEAGUE_AVG[shot.zone_basic] ?? null;
                const pct = stat && stat.attempted >= 5 ? stat.made / stat.attempted : null;
                const diff = pct !== null && avg !== null ? pct - avg : null;
                return (
                  <circle
                    key={i}
                    cx={x}
                    cy={y}
                    r="3.5"
                    fill={heatColor(diff, 0.7)}
                    stroke="rgba(255,255,255,0.15)"
                    strokeWidth="0.5"
                  >
                    <title>
                      {shot.zone_basic} · {shot.action_type} · {shot.distance} ft ·{" "}
                      {shot.shot_made ? "Made ✓" : "Missed ✗"}
                    </title>
                  </circle>
                );
              });
            })()}
        </svg>

        {/* Legend */}
        <div className="flex items-center justify-center gap-5 mt-3 text-xs text-gray-500 dark:text-gray-400">
          {chartView === "scatter" ? (
            <>
              <span className="flex items-center gap-1.5">
                <span className="inline-block w-3 h-3 rounded-full bg-green-500 opacity-75" />
                Made
              </span>
              <span className="flex items-center gap-1.5">
                <span className="inline-block w-3 h-3 rounded-full bg-red-500 opacity-50" />
                Missed
              </span>
            </>
          ) : (
            <>
              <span className="flex items-center gap-1.5">
                <span className="inline-block w-3 h-3 rounded-full bg-emerald-500" />
                Above avg
              </span>
              <span className="flex items-center gap-1.5">
                <span className="inline-block w-3 h-3 rounded-full bg-gray-400" />
                Near avg
              </span>
              <span className="flex items-center gap-1.5">
                <span className="inline-block w-3 h-3 rounded-full bg-red-500" />
                Below avg
              </span>
              <span className="text-gray-400 dark:text-gray-500">· hover zones for details</span>
            </>
          )}
        </div>
      </div>

      {/* Zone breakdown table */}
      {shotChart && shotChart.shots.length > 0 && (
        <ZoneBreakdown shots={shotChart.shots} />
      )}
    </div>
  );
}
