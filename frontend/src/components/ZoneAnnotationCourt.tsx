"use client";

import type { ZoneStat, ShotChartShot } from "@/lib/types";
import { LEAGUE_AVG_FG, ZONE_CENTROIDS, ZONE_ORDER, ZONE_PATHS, heatColor } from "@/lib/shotchart-constants";

interface ZoneAnnotationCourtProps {
  zones?: ZoneStat[] | null;
  shots?: ShotChartShot[];
  compact?: boolean;
}

// SVG viewport: 500 × 480, basket at (250, 430)
const W = 500;
const H = 480;

interface ResolvedZoneStat {
  fgPct: number | null;
  diff: number | null;
  freq: number;
  n: number;
}

function resolveFromZones(zones: ZoneStat[]): Record<string, ResolvedZoneStat> {
  const result: Record<string, ResolvedZoneStat> = {};
  for (const z of zones) {
    const avg = LEAGUE_AVG_FG[z.zone_basic] ?? null;
    const fgPct = z.fg_pct;
    const diff = fgPct !== null && avg !== null ? fgPct - avg : null;
    result[z.zone_basic] = {
      fgPct,
      diff,
      freq: z.freq,
      n: z.attempts,
    };
  }
  return result;
}

function resolveFromShots(shots: ShotChartShot[]): Record<string, ResolvedZoneStat> {
  const totals: Record<string, { made: number; attempted: number }> = {};
  const total = shots.length;
  for (const shot of shots) {
    const z = shot.zone_basic || "Unknown";
    if (!totals[z]) totals[z] = { made: 0, attempted: 0 };
    totals[z].attempted++;
    if (shot.shot_made) totals[z].made++;
  }
  const result: Record<string, ResolvedZoneStat> = {};
  for (const [zone, stat] of Object.entries(totals)) {
    const avg = LEAGUE_AVG_FG[zone] ?? null;
    const fgPct = stat.attempted >= 5 ? stat.made / stat.attempted : null;
    const diff = fgPct !== null && avg !== null ? fgPct - avg : null;
    result[zone] = {
      fgPct,
      diff,
      freq: total > 0 ? stat.attempted / total : 0,
      n: stat.attempted,
    };
  }
  return result;
}

function CourtMarkings() {
  return (
    <g stroke="rgba(33,72,59,0.35)" strokeWidth="1.5" fill="none">
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

export default function ZoneAnnotationCourt({
  zones,
  shots,
  compact = false,
}: ZoneAnnotationCourtProps) {
  const resolvedStats: Record<string, ResolvedZoneStat> =
    zones && zones.length > 0
      ? resolveFromZones(zones)
      : shots && shots.length > 0
      ? resolveFromShots(shots)
      : {};

  const hasData = Object.keys(resolvedStats).length > 0;

  return (
    <div className={compact ? "" : "mt-4"}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className={compact ? "w-full max-w-md mx-auto block" : "w-full max-w-lg mx-auto block"}
        aria-label="Shot zone efficiency court"
      >
        <defs>
          <linearGradient id="zac-wash" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="rgba(255,255,255,0.98)" />
            <stop offset="100%" stopColor="rgba(228,236,232,0.94)" />
          </linearGradient>
        </defs>

        {/* Court background */}
        <rect x="0" y="0" width={W} height={H} rx="18" fill="url(#zac-wash)" />

        {/* Zone fills colored by efficiency */}
        {ZONE_ORDER.filter((z) => ZONE_PATHS[z]).map((zone) => {
          const stat = resolvedStats[zone];
          const diff = stat ? stat.diff : null;
          const path = ZONE_PATHS[zone];
          if (!path) return null;
          return (
            <path
              key={zone}
              d={path}
              fill={heatColor(diff, 0.68)}
              stroke="rgba(255,255,255,0.3)"
              strokeWidth="1"
            />
          );
        })}

        <CourtMarkings />

        {/* Zone stat annotations */}
        {hasData &&
          ZONE_ORDER.filter((z) => ZONE_CENTROIDS[z]).map((zone) => {
            const centroid = ZONE_CENTROIDS[zone];
            const stat = resolvedStats[zone];
            if (!stat || stat.n < 5) return null;

            const [cx, cy] = centroid;
            const fgLabel =
              stat.fgPct !== null ? `${(stat.fgPct * 100).toFixed(1)}%` : "—";
            const diffLabel =
              stat.diff !== null
                ? `${stat.diff >= 0 ? "+" : ""}${(stat.diff * 100).toFixed(1)}%`
                : "";
            const diffColor =
              stat.diff !== null && stat.diff >= 0.02
                ? "#16a34a"
                : stat.diff !== null && stat.diff <= -0.02
                ? "#dc2626"
                : "#6f655a";
            const volLabel = `n=${stat.n}`;

            // Clamp rect x so corner labels don't clip at SVG edges
            const rectX = Math.max(2, Math.min(W - 58, cx - 28));

            return (
              <g key={zone}>
                {/* Frosted-glass backing rect */}
                <rect
                  x={rectX}
                  y={cy - 26}
                  width="56"
                  height="48"
                  rx="7"
                  fill="rgba(255,255,255,0.88)"
                  stroke="rgba(255,255,255,0.6)"
                  strokeWidth="0.5"
                />
                {/* FG% — large bold */}
                <text
                  x={rectX + 28}
                  y={cy - 10}
                  textAnchor="middle"
                  fontSize="11"
                  fontWeight="700"
                  fill="#201a16"
                >
                  {fgLabel}
                </text>
                {/* Delta — medium, colored */}
                {diffLabel && (
                  <text
                    x={rectX + 28}
                    y={cy + 4}
                    textAnchor="middle"
                    fontSize="9"
                    fontWeight="600"
                    fill={diffColor}
                  >
                    {diffLabel}
                  </text>
                )}
                {/* Volume — smallest, muted */}
                <text
                  x={rectX + 28}
                  y={cy + 17}
                  textAnchor="middle"
                  fontSize="8"
                  fontWeight="400"
                  fill="#6f655a"
                >
                  {volLabel}
                </text>
              </g>
            );
          })}

        {/* No-data message */}
        {!hasData && (
          <>
            <rect x="140" y="195" width="220" height="44" rx="12" fill="rgba(255,255,255,0.82)" />
            <text x="250" y="214" textAnchor="middle" fontSize="12" fill="#6f655a">
              No zone data available
            </text>
            <text x="250" y="230" textAnchor="middle" fontSize="10" fill="#9d8f82">
              Sync shot data to see zone analytics
            </text>
          </>
        )}
      </svg>

      {/* Legend */}
      {hasData && (
        <div className="flex flex-wrap items-center justify-center gap-4 mt-2 text-[10px] text-[var(--muted)]">
          <span className="flex items-center gap-1">
            <span className="inline-block w-2.5 h-2.5 rounded-[2px] bg-emerald-500 opacity-80" />
            Above avg
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-2.5 h-2.5 rounded-[2px] bg-gray-300" />
            Near avg
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-2.5 h-2.5 rounded-[2px] bg-red-400 opacity-80" />
            Below avg
          </span>
          <span>FG% · delta · n shown per zone (≥5 attempts)</span>
        </div>
      )}
    </div>
  );
}
