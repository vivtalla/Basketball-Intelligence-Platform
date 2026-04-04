"use client";

import { useId, useMemo } from "react";
import type { ShotChartShot } from "@/lib/types";
import {
  LEAGUE_AVG_FG,
  ZONE_CENTROIDS,
  ZONE_ORDER,
  ZONE_POINTS,
  heatColor,
} from "@/lib/shotchart-constants";

interface ShotValueMapProps {
  shots: ShotChartShot[];
  playerLabel?: string;
  scaleMaxFreq?: number;
  idPrefix?: string;
}

interface ZoneValueStat {
  zone: string;
  attempted: number;
  made: number;
  freq: number;           // share of total FGA (0–1)
  fgPct: number | null;  // null if < 5 attempts
  diff: number | null;   // fgPct − leagueAvg
  valuePerShot: number | null; // diff × zone_points  (pts added vs expected per shot)
  pps: number | null;
  avgPps: number;
}

// SVG viewport matches the rest of the platform
const W = 500;
const H = 480;

const BASE_R = 16; // reference radius; actual bubble scales by √(freq/maxFreq)
const SCALE = 2.2; // max multiplier → maxRadius ≈ 35

function buildZoneValueStats(shots: ShotChartShot[]): ZoneValueStat[] {
  const totals: Record<string, { made: number; attempted: number }> = {};
  const total = shots.length;

  for (const shot of shots) {
    const z = shot.zone_basic || "Unknown";
    if (!totals[z]) totals[z] = { made: 0, attempted: 0 };
    totals[z].attempted++;
    if (shot.shot_made) totals[z].made++;
  }

  return ZONE_ORDER.filter((z) => ZONE_CENTROIDS[z]).map((zone) => {
    const stat = totals[zone] ?? { made: 0, attempted: 0 };
    const avg = LEAGUE_AVG_FG[zone] ?? 0;
    const pts = ZONE_POINTS[zone] ?? 2;
    const fgPct = stat.attempted >= 5 ? stat.made / stat.attempted : null;
    const diff = fgPct !== null ? fgPct - avg : null;
    const valuePerShot = diff !== null ? diff * pts : null;
    const pps = fgPct !== null ? fgPct * pts : null;
    return {
      zone,
      attempted: stat.attempted,
      made: stat.made,
      freq: total > 0 ? stat.attempted / total : 0,
      fgPct,
      diff,
      valuePerShot,
      pps,
      avgPps: avg * pts,
    };
  });
}

function CourtMarkings() {
  return (
    <g stroke="rgba(33,72,59,0.30)" strokeWidth="1.5" fill="none">
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

export default function ShotValueMap({
  shots,
  playerLabel,
  scaleMaxFreq,
  idPrefix,
}: ShotValueMapProps) {
  const reactId = useId();
  const gradientId = `${idPrefix ?? reactId}-svm-wash`;
  const stats = useMemo(() => buildZoneValueStats(shots), [shots]);
  const maxFreq = useMemo(() => {
    if (scaleMaxFreq && scaleMaxFreq > 0) {
      return scaleMaxFreq;
    }
    return Math.max(...stats.map((s) => s.freq), 0.01);
  }, [scaleMaxFreq, stats]);

  if (shots.length === 0) {
    return (
      <p className="text-center py-8 text-sm text-[var(--muted)]">
        No shot data available for this period.
      </p>
    );
  }

  // Shot diet bar — proportional segments, one per zone with shots
  const dietZones = stats.filter((s) => s.attempted > 0);
  const totalAttempted = shots.length;

  return (
    <div>
      {/* Court SVG */}
      <div className="rounded-[1.75rem] border border-[rgba(25,52,42,0.12)] bg-[rgba(255,255,255,0.72)] p-3">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="w-full max-w-lg mx-auto block"
          aria-label="Shot value map — zone bubbles sized by frequency, colored by value"
        >
          <defs>
            <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="rgba(255,255,255,0.98)" />
              <stop offset="100%" stopColor="rgba(228,236,232,0.94)" />
            </linearGradient>
          </defs>

          <rect x="0" y="0" width={W} height={H} rx="18" fill={`url(#${gradientId})`} />

          <CourtMarkings />

          {/* Court label badge */}
          <rect x="24" y="18" width="122" height={playerLabel ? 60 : 48} rx="14" fill="rgba(255,255,255,0.86)" />
          <text x="38" y="38" fontSize="10" fontWeight="600" fill="rgba(33,72,59,0.6)" letterSpacing="0.12em">
            GOLDSBERRY
          </text>
          <text x="38" y="55" fontSize="13" fontWeight="600" fill="rgba(33,72,59,0.9)">
            Value map
          </text>
          {playerLabel ? (
            <text x="38" y="69" fontSize="9" fontWeight="500" fill="rgba(33,72,59,0.6)">
              {playerLabel}
            </text>
          ) : null}

          {/* Zone bubbles */}
          {stats.map((s) => {
            if (s.attempted === 0) return null;
            const centroid = ZONE_CENTROIDS[s.zone];
            if (!centroid) return null;
            const [cx, cy] = centroid;

            // Bubble radius — area proportional to frequency
            const r = Math.max(6, BASE_R * Math.sqrt(s.freq / maxFreq) * SCALE);

            // Color: value per shot (pts above expected). Scale to FG%-diff space (/2) for heatColor tiers.
            const colorDiff = s.valuePerShot !== null ? s.valuePerShot / 2 : null;
            const bubbleFill = heatColor(colorDiff, 0.82);
            const bubbleStroke = heatColor(colorDiff, 0.96);

            // Label positioning — keep rect within viewport
            const labelW = 56;
            const labelH = s.fgPct !== null ? 50 : 30;
            const rectX = Math.max(2, Math.min(W - labelW - 2, cx - labelW / 2));
            const rectY = cy - labelH / 2;

            const fgLabel = s.fgPct !== null ? `${(s.fgPct * 100).toFixed(1)}%` : "—";
            const valLabel =
              s.valuePerShot !== null
                ? `${s.valuePerShot >= 0 ? "+" : ""}${s.valuePerShot.toFixed(2)} pts`
                : null;
            const valColor =
              s.valuePerShot !== null && s.valuePerShot >= 0.04
                ? "#16a34a"
                : s.valuePerShot !== null && s.valuePerShot <= -0.04
                ? "#dc2626"
                : "#6f655a";

            return (
              <g key={s.zone}>
                {/* Reference ring — shows BASE_R as "average volume" anchor */}
                <circle
                  cx={cx}
                  cy={cy}
                  r={BASE_R}
                  fill="none"
                  stroke="rgba(33,72,59,0.12)"
                  strokeWidth="1"
                  strokeDasharray="3 3"
                />

                {/* Value bubble */}
                <circle
                  cx={cx}
                  cy={cy}
                  r={r}
                  fill={bubbleFill}
                  stroke={bubbleStroke}
                  strokeWidth="1.5"
                >
                  <title>
                    {s.zone}
                    {`\n${s.made}/${s.attempted} FGM/FGA (${(s.freq * 100).toFixed(0)}% of shots)`}
                    {s.fgPct !== null
                      ? `\nFG%: ${(s.fgPct * 100).toFixed(1)}%`
                      : "\n< 5 attempts"}
                    {s.valuePerShot !== null
                      ? `\nValue: ${s.valuePerShot >= 0 ? "+" : ""}${s.valuePerShot.toFixed(2)} pts/shot vs avg`
                      : ""}
                  </title>
                </circle>

                {/* Frosted label — FG% + value/shot */}
                <rect
                  x={rectX}
                  y={rectY}
                  width={labelW}
                  height={labelH}
                  rx="7"
                  fill="rgba(255,255,255,0.88)"
                  stroke="rgba(255,255,255,0.6)"
                  strokeWidth="0.5"
                />
                <text
                  x={rectX + labelW / 2}
                  y={rectY + 14}
                  textAnchor="middle"
                  fontSize="11"
                  fontWeight="700"
                  fill="#201a16"
                >
                  {fgLabel}
                </text>
                {valLabel && (
                  <text
                    x={rectX + labelW / 2}
                    y={rectY + 27}
                    textAnchor="middle"
                    fontSize="8.5"
                    fontWeight="600"
                    fill={valColor}
                  >
                    {valLabel}
                  </text>
                )}
                <text
                  x={rectX + labelW / 2}
                  y={rectY + labelH - 5}
                  textAnchor="middle"
                  fontSize="7.5"
                  fontWeight="400"
                  fill="#9d8f82"
                >
                  {(s.freq * 100).toFixed(0)}% of FGA
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center justify-center gap-5 mt-3 text-xs text-[var(--muted)]">
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded-full bg-emerald-500 opacity-80" />
          Value above avg
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded-full bg-gray-300" />
          Near avg
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded-full bg-red-400 opacity-80" />
          Value below avg
        </span>
        <span>· Bubble area ∝ shot frequency · dashed ring = volume baseline</span>
      </div>

      {/* Shot diet strip */}
      <div className="mt-5 border-t border-[rgba(25,52,42,0.08)] pt-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)] mb-3">
          Shot Diet
        </p>

        {/* Proportional bar */}
        <div className="flex h-5 rounded-full overflow-hidden mb-3">
          {dietZones.map((s) => {
            const pct = (s.attempted / totalAttempted) * 100;
            const colorDiff = s.valuePerShot !== null ? s.valuePerShot / 2 : null;
            const bg = heatColor(colorDiff, 0.7);
            return (
              <div
                key={s.zone}
                style={{ width: `${pct}%`, background: bg }}
                title={`${s.zone}: ${pct.toFixed(0)}% of FGA`}
              />
            );
          })}
        </div>

        {/* Zone rows */}
        <div className="grid grid-cols-1 gap-1">
          {dietZones.map((s) => {
            const pct = (s.attempted / totalAttempted) * 100;
            const diffLabel =
              s.diff !== null
                ? `${s.diff >= 0 ? "+" : ""}${(s.diff * 100).toFixed(1)}%`
                : "—";
            const diffCls =
              s.diff !== null && s.diff >= 0.03
                ? "text-emerald-600"
                : s.diff !== null && s.diff <= -0.03
                ? "text-red-500"
                : "text-[var(--muted)]";
            const valLabel =
              s.valuePerShot !== null
                ? `${s.valuePerShot >= 0 ? "+" : ""}${s.valuePerShot.toFixed(2)} pts/shot`
                : "—";
            const colorDiff = s.valuePerShot !== null ? s.valuePerShot / 2 : null;

            return (
              <div key={s.zone} className="flex items-center gap-2 text-xs">
                <span
                  className="inline-block w-2 h-2 rounded-full flex-shrink-0"
                  style={{ background: heatColor(colorDiff, 0.8) }}
                />
                <span className="w-44 truncate text-[var(--muted-strong)]">{s.zone}</span>
                <div className="flex-1 h-1.5 rounded-full bg-[rgba(25,52,42,0.08)] overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${Math.min(100, pct * 2)}%`,
                      background: heatColor(colorDiff, 0.6),
                    }}
                  />
                </div>
                <span className="w-10 text-right tabular-nums text-[var(--muted)]">
                  {pct.toFixed(0)}%
                </span>
                <span className={`w-12 text-right tabular-nums ${diffCls}`}>
                  {diffLabel}
                </span>
                <span className={`w-24 text-right tabular-nums text-[11px] ${diffCls}`}>
                  {valLabel}
                </span>
              </div>
            );
          })}
        </div>

        <p className="text-[10px] text-[var(--muted)] mt-2">
          Value = (FG% − league avg) × zone points · bubble area ∝ freq · &lt;5 attempts shown as —
        </p>
      </div>
    </div>
  );
}
