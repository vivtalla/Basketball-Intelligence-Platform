"use client";

import { useId, useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import type { ShotChartShot } from "@/lib/types";
import { LEAGUE_AVG_FG, heatColor } from "@/lib/shotchart-constants";

interface ShotDistanceProfileProps {
  shots: ShotChartShot[];
  playerLabel?: string;
  scaleMaxFrequency?: number;
  idPrefix?: string;
}

interface DistanceBin {
  dist: number;       // bin start in feet
  attempts: number;
  made: number;
  fgPct: number | null;    // null if attempts < 3
  freq: number;            // bin_attempts / total_attempts
  diff: number | null;     // fgPct - expectedFg
  expectedFg: number;
}

// Map shot distance to approximate expected FG% using zone averages
function expectedFgForDist(dist: number, zoneArea?: string): number {
  if (dist < 4) return LEAGUE_AVG_FG["Restricted Area"] ?? 0.64;
  if (dist < 14) return LEAGUE_AVG_FG["In The Paint (Non-RA)"] ?? 0.40;
  if (dist < 22) return LEAGUE_AVG_FG["Mid-Range"] ?? 0.41;
  // Corner 3 (≈22–23.75 ft) vs Above-break 3
  if (zoneArea && (zoneArea.includes("Left") || zoneArea.includes("Right"))) {
    return LEAGUE_AVG_FG["Left Corner 3"] ?? 0.38;
  }
  return LEAGUE_AVG_FG["Above the Break 3"] ?? 0.36;
}

function buildDistanceBins(shots: ShotChartShot[]): DistanceBin[] {
  const total = shots.length;
  if (total === 0) return [];

  const binMap: Record<number, { made: number; attempted: number; zoneArea: string }> = {};
  let maxDist = 0;

  for (const shot of shots) {
    const d = Math.floor(Math.max(0, shot.distance));
    if (!binMap[d]) binMap[d] = { made: 0, attempted: 0, zoneArea: shot.zone_area || "" };
    binMap[d].attempted++;
    if (shot.shot_made) binMap[d].made++;
    if (d > maxDist) maxDist = d;
  }

  const bins: DistanceBin[] = [];
  const cap = Math.min(maxDist + 1, 33);

  for (let d = 0; d < cap; d++) {
    const stat = binMap[d] ?? { made: 0, attempted: 0, zoneArea: "" };
    const expectedFg = expectedFgForDist(d, stat.zoneArea);
    const fgPct = stat.attempted >= 3 ? stat.made / stat.attempted : null;
    const diff = fgPct !== null ? fgPct - expectedFg : null;
    bins.push({
      dist: d,
      attempts: stat.attempted,
      made: stat.made,
      fgPct,
      freq: stat.attempted / total,
      diff,
      expectedFg,
    });
  }

  return bins;
}

// Build smooth SVG area path from frequency values
// Returns the path data string for the filled area curve
function buildAreaPath(
  bins: DistanceBin[],
  chartW: number,
  chartH: number,
  maxFreq: number
): string {
  if (bins.length === 0) return "";

  const xStep = chartW / Math.max(bins.length - 1, 1);

  // Map freq to y position (inverted — higher freq = lower y number = visually taller)
  const toY = (freq: number) => chartH - (freq / maxFreq) * chartH * 0.92;
  const toX = (i: number) => i * xStep;

  // Build smooth cubic Bezier using cardinal spline tension
  const points = bins.map((b, i) => ({ x: toX(i), y: toY(b.freq) }));

  let d = `M ${points[0].x.toFixed(2)},${points[0].y.toFixed(2)}`;

  for (let i = 1; i < points.length; i++) {
    const prev = points[i - 1];
    const curr = points[i];
    const cpx = (prev.x + curr.x) / 2;
    d += ` C ${cpx.toFixed(2)},${prev.y.toFixed(2)} ${cpx.toFixed(2)},${curr.y.toFixed(2)} ${curr.x.toFixed(2)},${curr.y.toFixed(2)}`;
  }

  // Close to baseline
  const lastX = points[points.length - 1].x;
  d += ` L ${lastX.toFixed(2)},${chartH} L 0,${chartH} Z`;

  return d;
}

// Landmark vertical lines on the distance axis
const LANDMARKS = [
  { dist: 4,    label: "RA edge" },
  { dist: 14,   label: "Paint" },
  { dist: 22,   label: "Corner 3" },
  { dist: 23.75, label: "Arc 3" },
];

// Format tooltip values
function fmt(val: number | null | undefined, suffix = ""): string {
  if (val === null || val === undefined) return "—";
  return `${(val * 100).toFixed(1)}${suffix}`;
}

export default function ShotDistanceProfile({
  shots,
  playerLabel,
  scaleMaxFrequency,
  idPrefix,
}: ShotDistanceProfileProps) {
  const reactId = useId();
  const scopedId = (suffix: string) => `${idPrefix ?? reactId}-${suffix}`;
  const bins = useMemo(() => buildDistanceBins(shots), [shots]);

  if (bins.length === 0) {
    return (
      <p className="text-center py-6 text-sm text-[var(--muted)]">
        No shot data available for distance profile.
      </p>
    );
  }

  const maxFreq = scaleMaxFrequency && scaleMaxFrequency > 0
    ? scaleMaxFrequency
    : Math.max(...bins.map((b) => b.freq), 0.001);
  const maxDist = bins[bins.length - 1].dist;

  // SVG dimensions for the ribbon
  const CHART_W = 460;
  const CHART_H = 100;
  const PAD_L = 28;
  const PAD_B = 22;

  const areaPath = buildAreaPath(bins, CHART_W, CHART_H, maxFreq);

  // Build per-2ft gradient segments in <defs>
  // Each segment covers 2 distance bins, colored by the average diff in that range
  const gradientSegments: Array<{ id: string; color: string; x1Pct: number; x2Pct: number }> = [];
  for (let start = 0; start < bins.length; start += 2) {
    const end = Math.min(start + 2, bins.length);
    const segBins = bins.slice(start, end).filter((b) => b.diff !== null);
    const avgDiff =
      segBins.length > 0
        ? segBins.reduce((sum, b) => sum + (b.diff ?? 0), 0) / segBins.length
        : null;
    const color = heatColor(avgDiff, 0.72);
    const x1Pct = (start / (bins.length - 1)) * 100;
    const x2Pct = (end / (bins.length - 1)) * 100;
    gradientSegments.push({ id: scopedId(`sdp-seg-${start}`), color, x1Pct, x2Pct });
  }

  // Recharts sparkline data (FG% per bin)
  const sparkData = bins.map((b) => ({
    dist: b.dist,
    fgPct: b.fgPct !== null ? b.fgPct * 100 : null,
    expectedFg: b.expectedFg * 100,
    attempts: b.attempts,
  }));

  return (
    <div>
      {playerLabel && (
        <p className="text-xs text-[var(--muted)] mb-2">{playerLabel}</p>
      )}

      {/* Distance ribbon SVG */}
      <div className="rounded-[1.25rem] border border-[rgba(25,52,42,0.10)] bg-[rgba(255,255,255,0.72)] p-4 overflow-hidden">
        <svg
          viewBox={`0 0 ${CHART_W + PAD_L + 8} ${CHART_H + PAD_B + 8}`}
          className="w-full block"
          aria-label="Shot frequency and efficiency by distance"
        >
          <defs>
            {/* One linearGradient per 2-ft segment for continuous coloring */}
            {gradientSegments.map((seg) => (
              <linearGradient
                key={seg.id}
                id={seg.id}
                x1="0%"
                y1="0%"
                x2="100%"
                y2="0%"
              >
                <stop offset="0%" stopColor={seg.color} />
                <stop offset="100%" stopColor={seg.color} />
              </linearGradient>
            ))}
          </defs>

          <g transform={`translate(${PAD_L}, 4)`}>
            {/* Landmark vertical reference lines */}
            {LANDMARKS.filter((lm) => lm.dist <= maxDist).map((lm) => {
              const x = (lm.dist / maxDist) * CHART_W;
              return (
                <g key={lm.label}>
                  <line
                    x1={x}
                    y1={0}
                    x2={x}
                    y2={CHART_H}
                    stroke="rgba(33,72,59,0.18)"
                    strokeWidth="1"
                    strokeDasharray="3 3"
                  />
                  <text
                    x={x}
                    y={CHART_H + 14}
                    textAnchor="middle"
                    fontSize="7.5"
                    fill="rgba(33,72,59,0.45)"
                  >
                    {lm.label}
                  </text>
                </g>
              );
            })}

            {/* Clipping mask so segments stay within the area curve */}
            <clipPath id={scopedId("sdp-clip")}>
              <path d={areaPath} />
            </clipPath>

            {/* Colored fill segments (clipped to area shape) */}
            {gradientSegments.map((seg) => {
              const segW =
                ((seg.x2Pct - seg.x1Pct) / 100) * CHART_W + 2;
              const segX = (seg.x1Pct / 100) * CHART_W - 1;
              return (
                <rect
                  key={seg.id}
                  x={segX}
                  y={0}
                  width={segW}
                  height={CHART_H}
                  fill={seg.color}
                  clipPath={`url(#${scopedId("sdp-clip")})`}
                />
              );
            })}

            {/* Outline of area curve (no fill — fill done via segments above) */}
            <path
              d={areaPath}
              fill="none"
              stroke="rgba(33,72,59,0.25)"
              strokeWidth="1.2"
            />

            {/* Y-axis label */}
            <text
              x={-PAD_L + 2}
              y={CHART_H / 2}
              fontSize="8"
              fill="rgba(33,72,59,0.4)"
              textAnchor="middle"
              transform={`rotate(-90, ${-PAD_L + 10}, ${CHART_H / 2})`}
            >
              freq
            </text>

            {/* X-axis labels (0, 10, 20, 30 ft) */}
            {[0, 10, 20, 30].filter((d) => d <= maxDist).map((d) => (
              <text
                key={d}
                x={(d / maxDist) * CHART_W}
                y={CHART_H + PAD_B - 2}
                textAnchor="middle"
                fontSize="8.5"
                fill="rgba(33,72,59,0.5)"
              >
                {d} ft
              </text>
            ))}
          </g>
        </svg>

        {/* Recharts sparkline — FG% per bin with expected line */}
        <div className="mt-1" style={{ height: 72 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={sparkData}
              margin={{ top: 4, right: 8, bottom: 0, left: PAD_L }}
            >
              <XAxis dataKey="dist" hide />
              <YAxis
                hide
                domain={[0, 100]}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (!active || !payload || payload.length === 0) return null;
                  const d = payload[0].payload as (typeof sparkData)[number];
                  return (
                    <div className="rounded-lg border border-[rgba(25,52,42,0.12)] bg-white/95 px-2.5 py-1.5 text-xs shadow-sm">
                      <p className="font-semibold text-[var(--foreground)]">{d.dist} ft</p>
                      <p className="text-[var(--muted)]">
                        FG%: {d.fgPct !== null ? `${d.fgPct.toFixed(1)}%` : "—"}
                      </p>
                      <p className="text-[var(--muted)]">
                        Expected: {fmt(d.expectedFg / 100)}%
                      </p>
                      <p className="text-[var(--muted)]">
                        Attempts: {d.attempts}
                      </p>
                    </div>
                  );
                }}
              />
              {/* League expected FG% reference */}
              <Line
                type="monotone"
                dataKey="expectedFg"
                stroke="rgba(33,72,59,0.22)"
                strokeWidth={1}
                strokeDasharray="4 3"
                dot={false}
                name="Expected"
                connectNulls
              />
              {/* Player actual FG% */}
              <Line
                type="monotone"
                dataKey="fgPct"
                stroke="rgba(33,72,59,0.75)"
                strokeWidth={1.5}
                dot={false}
                name="FG%"
                connectNulls
              />
              {/* Landmark reference lines */}
              {LANDMARKS.filter((lm) => lm.dist <= maxDist).map((lm) => (
                <ReferenceLine
                  key={lm.label}
                  x={lm.dist}
                  stroke="rgba(33,72,59,0.12)"
                  strokeDasharray="3 3"
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Axis label */}
        <p className="text-center text-[9px] text-[var(--muted)] mt-0.5">
          Distance (feet) · FG% (solid) vs expected (dashed)
        </p>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center justify-center gap-4 mt-2 text-[10px] text-[var(--muted)]">
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-8 h-1.5 rounded-full bg-emerald-400 opacity-80" />
          Above expected
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-8 h-1.5 rounded-full bg-red-400 opacity-80" />
          Below expected
        </span>
        <span>· Ribbon height = shot frequency · ≥3 attempts to show FG%</span>
      </div>
    </div>
  );
}
