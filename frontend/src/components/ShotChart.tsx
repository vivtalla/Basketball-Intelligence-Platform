"use client";

import { useState } from "react";
import { usePlayerShotChart } from "@/hooks/usePlayerStats";
import type { ShotChartShot } from "@/lib/types";
import { LEAGUE_AVG_FG, ZONE_POINTS, ZONE_ORDER, ZONE_PATHS, heatColor } from "@/lib/shotchart-constants";
import ChartStatusBadge from "./ChartStatusBadge";
import ZoneAnnotationCourt from "./ZoneAnnotationCourt";
import ShotValueMap from "./ShotValueMap";
import ShotSprawlMap from "./ShotSprawlMap";
import ShotDistanceProfile from "./ShotDistanceProfile";

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
  heatmap: "Zone wash",
  hex: "Hex density",
  value: "Value map",
  sprawl: "Sprawl map",
};

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
  const dataStatus = shotChart?.data_status ?? "missing";
  const isMissing = dataStatus === "missing";
  const isStale = dataStatus === "stale";

  return (
    <div className="rounded-[2rem] border border-[var(--border)] bg-[linear-gradient(145deg,rgba(247,243,232,0.96),rgba(228,236,232,0.92))] p-6 shadow-[0_24px_80px_rgba(47,43,36,0.08)]">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Player Surface
          </p>
          <h3 className="mt-1 text-xl font-semibold text-[var(--foreground)]">Shot Chart</h3>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <ChartStatusBadge status={dataStatus} compact />

          {/* Scatter / Heat / Hex / Value / Sprawl toggle */}
          <div className="flex rounded-lg overflow-hidden border border-[var(--border)] text-xs">
            {(["scatter", "heatmap", "hex", "value", "sprawl"] as ChartView[]).map((view) => (
              <button
                key={view}
                onClick={() => setChartView(view)}
                className={`px-3 py-1.5 transition-colors ${
                  chartView === view ? "bip-toggle-active" : "bip-toggle"
                }`}
              >
                {VIEW_LABELS[view]}
              </button>
            ))}
          </div>

          {/* Season selector */}
          <select
            value={selectedSeason}
            onChange={(e) => setSelectedSeason(e.target.value)}
            className="text-sm border border-[var(--border)] rounded-lg px-2 py-1 bg-[rgba(255,251,246,0.96)] text-[var(--foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
          >
            {seasons.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>

          {/* RS / Playoffs */}
          <div className="flex rounded-lg overflow-hidden border border-[var(--border)] text-xs">
            {(["Regular Season", "Playoffs"] as const).map((type) => (
              <button
                key={type}
                onClick={() => setSeasonType(type)}
                className={`px-3 py-1.5 transition-colors ${
                  seasonType === type ? "bip-toggle-active" : "bip-toggle"
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
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-[1.25rem] border border-[rgba(25,52,42,0.12)] bg-[rgba(255,255,255,0.7)] px-4 py-3 text-sm text-[var(--muted-strong)]">
          <p>
            {shotChart.made} / {shotChart.attempted} FG
            {fgPct !== null && <> ({fgPct}%)</>}
            {shotChart.attempted === 0 && !isMissing && (
              <span className="ml-1 italic">— no shot data for this period</span>
            )}
          </p>
          <div className="flex items-center gap-2">
            {shotChart.last_synced_at && (
              <span className="text-[11px]">
                Synced {new Date(shotChart.last_synced_at).toLocaleDateString()}
              </span>
            )}
          </div>
        </div>
      )}

      {shotChart && !isLoading && isMissing && (
        <div className="mb-4 rounded-xl border border-dashed border-[rgba(25,52,42,0.16)] bg-[rgba(255,255,255,0.66)] px-4 py-3 text-sm text-[var(--muted-strong)]">
          Shot chart data has not been synced for this player and season yet.
        </div>
      )}

      {/* Court SVG */}
      <div className="relative">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/80 rounded-lg z-10">
            <div className="w-8 h-8 border-2 border-[var(--accent)] border-t-transparent rounded-full animate-spin" />
          </div>
        )}
        {error && !isLoading && (
          <p className="text-center py-10 text-sm text-red-500">
            Could not load shot data.
          </p>
        )}

        {/* Value map — full replacement for the SVG court section */}
        {chartView === "value" && shotChart && shotChart.shots.length > 0 && (
          <ShotValueMap shots={shotChart.shots} />
        )}

        {/* Sprawl map — full replacement for the SVG court section */}
        {chartView === "sprawl" && shotChart && shotChart.shots.length > 0 && (
          <ShotSprawlMap shots={shotChart.shots} />
        )}

        <div className={chartView === "value" || chartView === "sprawl" ? "hidden" : ""}>
        <div className="rounded-[1.75rem] border border-[rgba(25,52,42,0.12)] bg-[rgba(255,255,255,0.72)] p-3">
          <svg viewBox={`0 0 ${W} ${H}`} className="w-full max-w-lg mx-auto block">
            <defs>
              <linearGradient id="courtWash" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="rgba(255,255,255,0.98)" />
                <stop offset="100%" stopColor="rgba(228,236,232,0.94)" />
              </linearGradient>
            </defs>
            <rect x="0" y="0" width={W} height={H} rx="18" fill="url(#courtWash)" />

            {/* Zone heatmap overlays (behind court markings) */}
            {chartView === "heatmap" && shotChart && shotChart.shots.length > 0 && (
              <HeatmapZones shots={shotChart.shots} />
            )}

            {/* Hexbin layer (behind court markings) */}
            {chartView === "hex" && shotChart && shotChart.shots.length > 0 && (
              <HexLayer shots={shotChart.shots} />
            )}

            <CourtMarkings />

            {/* Season / mode label badge */}
            <rect x="24" y="18" width="130" height="48" rx="14" fill="rgba(255,255,255,0.86)" />
            <text x="38" y="38" fontSize="10" fontWeight="600" fill="var(--muted)" letterSpacing="0.12em">
              {selectedSeason}
            </text>
            <text x="38" y="55" fontSize="13" fontWeight="600" fill="var(--foreground)">
              {COURT_LABEL[chartView]}
            </text>

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

            {/* Heatmap: per-shot dots colored by zone efficiency */}
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
        </div>

        {/* Legend */}
        <div className="flex flex-wrap items-center justify-center gap-5 mt-3 text-xs text-[var(--muted)]">
          {chartView === "scatter" ? (
            <>
              <span className="flex items-center gap-1.5">
                <span className="inline-block w-3 h-3 rounded-full bg-[#21483b] opacity-80" />
                Made
              </span>
              <span className="flex items-center gap-1.5">
                <span className="inline-block w-3 h-3 rounded-full bg-[#b25b4f] opacity-50" />
                Missed
              </span>
            </>
          ) : chartView === "hex" ? (
            <>
              <span className="flex items-center gap-1.5">
                <span className="inline-block w-3 h-3 rounded-sm bg-emerald-500" />
                Above avg
              </span>
              <span className="flex items-center gap-1.5">
                <span className="inline-block w-3 h-3 rounded-sm bg-gray-400" />
                Near avg
              </span>
              <span className="flex items-center gap-1.5">
                <span className="inline-block w-3 h-3 rounded-sm bg-red-500" />
                Below avg
              </span>
              <span>· Larger hex = more attempts</span>
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
              <span>· hover zones for details</span>
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
      {shotChart && shotChart.shots.length > 0 && (
        <div className="mt-6 border-t border-[rgba(25,52,42,0.08)] pt-5">
          <p className="bip-kicker mb-3">Zone Efficiency</p>
          <ZoneAnnotationCourt shots={shotChart.shots} compact />
        </div>
      )}

      {/* Zone breakdown table — secondary detail */}
      {shotChart && shotChart.shots.length > 0 && (
        <ZoneBreakdown shots={shotChart.shots} />
      )}

      {/* Distance signature strip */}
      {shotChart && shotChart.shots.length > 0 && (
        <div className="mt-6 border-t border-[rgba(25,52,42,0.08)] pt-5">
          <p className="bip-kicker mb-3">Distance Signature</p>
          <ShotDistanceProfile shots={shotChart.shots} />
        </div>
      )}
    </div>
  );
}
