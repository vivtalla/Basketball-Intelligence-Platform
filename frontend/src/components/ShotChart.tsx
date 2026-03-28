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

const ZONE_ORDER = [
  "Restricted Area",
  "In The Paint (Non-RA)",
  "Mid-Range",
  "Left Corner 3",
  "Right Corner 3",
  "Above the Break 3",
  "Backcourt",
];

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

function ZoneBreakdown({ shots }: { shots: ShotChartShot[] }) {
  const zoneStats = buildZoneStats(shots);
  const zones = ZONE_ORDER.filter((z) => zoneStats[z]);

  if (zones.length === 0) return null;

  return (
    <div className="mt-6 border-t border-gray-100 dark:border-gray-700 pt-5">
      <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-3">
        Zone Breakdown
      </h4>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-gray-400 dark:text-gray-500 border-b border-gray-100 dark:border-gray-700">
              <th className="text-left pb-2 font-medium">Zone</th>
              <th className="text-right pb-2 font-medium">FGM</th>
              <th className="text-right pb-2 font-medium">FGA</th>
              <th className="text-right pb-2 font-medium">FG%</th>
              <th className="text-right pb-2 font-medium">vs Avg</th>
            </tr>
          </thead>
          <tbody>
            {zones.map((zone) => {
              const { made, attempted } = zoneStats[zone];
              const pct = attempted > 0 ? made / attempted : null;
              const avg = LEAGUE_AVG[zone] ?? null;
              const diff = pct !== null && avg !== null ? pct - avg : null;
              const lowSample = attempted < 5;

              let diffColor = "text-gray-400 dark:text-gray-500";
              if (!lowSample && diff !== null) {
                diffColor =
                  diff >= 0.03
                    ? "text-green-600 dark:text-green-400"
                    : diff <= -0.03
                    ? "text-red-500 dark:text-red-400"
                    : "text-gray-500 dark:text-gray-400";
              }

              return (
                <tr
                  key={zone}
                  className="border-b border-gray-50 dark:border-gray-700/50 last:border-0"
                >
                  <td className="py-2 pr-4 text-gray-700 dark:text-gray-300 whitespace-nowrap">
                    {zone}
                  </td>
                  <td className="py-2 text-right tabular-nums text-gray-600 dark:text-gray-400">
                    {made}
                  </td>
                  <td className="py-2 text-right tabular-nums text-gray-600 dark:text-gray-400">
                    {attempted}
                  </td>
                  <td className="py-2 text-right tabular-nums font-medium text-gray-900 dark:text-gray-100">
                    {lowSample
                      ? <span className="text-gray-400 dark:text-gray-500">—</span>
                      : pct !== null
                      ? `${(pct * 100).toFixed(1)}%`
                      : "—"}
                  </td>
                  <td className={`py-2 text-right tabular-nums font-medium ${diffColor}`}>
                    {lowSample
                      ? <span className="text-gray-400 dark:text-gray-500 text-xs">small</span>
                      : diff !== null
                      ? `${diff >= 0 ? "+" : ""}${(diff * 100).toFixed(1)}%`
                      : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-gray-400 dark:text-gray-500 mt-2">
        vs Avg = player FG% minus league average for that zone. Zones with &lt;5 attempts shown as —.
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
      {/* Court outline */}
      <rect x="0" y="0" width={W} height={H} />
      {/* Paint / key */}
      <rect x="170" y="240" width="160" height="190" />
      {/* Free throw circle — solid upper half */}
      <path d="M 170,240 A 60,60 0 0 0 330,240" />
      {/* Free throw circle — dashed lower half */}
      <path d="M 170,240 A 60,60 0 0 1 330,240" strokeDasharray="5 4" />
      {/* Restricted area arc */}
      <path d="M 210,430 A 40,40 0 0 0 290,430" />
      {/* Basket rim */}
      <circle cx="250" cy="430" r="7.5" />
      {/* Backboard */}
      <line x1="220" y1="438" x2="280" y2="438" strokeWidth="2.5" />
      {/* Three-point corner lines */}
      <line x1="30" y1={H} x2="30" y2="341" />
      <line x1="470" y1={H} x2="470" y2="341" />
      {/* Three-point arc */}
      <path d="M 30,341 A 237.5,237.5 0 0 0 470,341" />
    </g>
  );
}

export default function ShotChart({
  playerId,
  seasons,
  defaultSeason,
}: ShotChartProps) {
  const [selectedSeason, setSelectedSeason] = useState(defaultSeason);
  const [seasonType, setSeasonType] = useState<"Regular Season" | "Playoffs">(
    "Regular Season"
  );

  const {
    data: shotChart,
    isLoading,
    error,
  } = usePlayerShotChart(playerId, selectedSeason, seasonType);

  const fgPct =
    shotChart && shotChart.attempted > 0
      ? ((shotChart.made / shotChart.attempted) * 100).toFixed(1)
      : null;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 p-6">
      {/* Header row */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <h3 className="font-semibold text-gray-900 dark:text-gray-100">
          Shot Chart
        </h3>

        <div className="flex flex-wrap items-center gap-3">
          {/* Season selector */}
          <select
            value={selectedSeason}
            onChange={(e) => setSelectedSeason(e.target.value)}
            className="text-sm border border-gray-200 dark:border-gray-600 rounded-lg px-2 py-1 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {seasons.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>

          {/* Season type toggle */}
          <div className="flex rounded-lg overflow-hidden border border-gray-200 dark:border-gray-600 text-xs">
            {(["Regular Season", "Playoffs"] as const).map((type) => (
              <button
                key={type}
                onClick={() => setSeasonType(type)}
                className={`px-3 py-1.5 transition-colors ${
                  seasonType === type
                    ? "bg-blue-500 text-white"
                    : "bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-600"
                }`}
              >
                {type}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* FG% summary line */}
      {shotChart && !isLoading && (
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
          {shotChart.made} / {shotChart.attempted} FG
          {fgPct !== null && <> ({fgPct}%)</>}
          {shotChart.attempted === 0 && (
            <span className="ml-1 italic">— no shot data for this period</span>
          )}
        </p>
      )}

      {/* Court */}
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

        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="w-full max-w-lg mx-auto block"
        >
          <CourtMarkings />

          {shotChart?.shots.map((shot, i) => {
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
        </svg>

        {/* Legend */}
        <div className="flex items-center justify-center gap-5 mt-3 text-xs text-gray-500 dark:text-gray-400">
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-3 h-3 rounded-full bg-green-500 opacity-75" />
            Made
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-3 h-3 rounded-full bg-red-500 opacity-50" />
            Missed
          </span>
        </div>
      </div>

      {/* Zone breakdown */}
      {shotChart && shotChart.shots.length > 0 && (
        <ZoneBreakdown shots={shotChart.shots} />
      )}
    </div>
  );
}
