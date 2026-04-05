"use client";

import { useId, useMemo } from "react";
import type { ShotChartShot } from "@/lib/types";
import {
  ShotLabLegendItem,
  ShotLabStat,
  ShotLabSurface,
} from "./ShotLabSurface";
import ShotCourt from "./ShotCourt";

interface ShotSprawlMapProps {
  shots: ShotChartShot[];
  playerLabel?: string;
  idPrefix?: string;
}

const W = 500;
const H = 480;
const COLS = 25;
const ROWS = 24;
const CELL = 20;
const SQ_FT_PER_SQ_UNIT = 2350 / 240000;

function toSvg(locX: number, locY: number): [number, number] {
  return [locX + 250, 430 - locY];
}

const KERNEL_5 = [
  [1, 4, 7, 4, 1],
  [4, 16, 26, 16, 4],
  [7, 26, 41, 26, 7],
  [4, 16, 26, 16, 4],
  [1, 4, 7, 4, 1],
];
const KERNEL_SUM = 273;

function gaussianBlur(grid: number[][]): number[][] {
  const out: number[][] = Array.from({ length: COLS }, () => new Array(ROWS).fill(0));
  for (let c = 0; c < COLS; c++) {
    for (let r = 0; r < ROWS; r++) {
      let val = 0;
      for (let ki = 0; ki < 5; ki++) {
        for (let kj = 0; kj < 5; kj++) {
          const nc = c + ki - 2;
          const nr = r + kj - 2;
          if (nc >= 0 && nc < COLS && nr >= 0 && nr < ROWS) {
            val += KERNEL_5[ki][kj] * grid[nc][nr];
          }
        }
      }
      out[c][r] = val / KERNEL_SUM;
    }
  }
  return out;
}

function cross(o: [number, number], a: [number, number], b: [number, number]): number {
  return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
}

function convexHull(pts: Array<[number, number]>): Array<[number, number]> {
  const n = pts.length;
  if (n < 3) return pts;

  let startIdx = 0;
  for (let i = 1; i < n; i++) {
    if (pts[i][0] < pts[startIdx][0]) startIdx = i;
  }

  const hull: Array<[number, number]> = [];
  let current = startIdx;

  do {
    hull.push(pts[current]);
    let next = (current + 1) % n;
    for (let i = 0; i < n; i++) {
      if (cross(pts[current], pts[next], pts[i]) < 0) {
        next = i;
      }
    }
    current = next;
  } while (current !== startIdx && hull.length <= n);

  return hull;
}

function polygonArea(pts: Array<[number, number]>): number {
  const n = pts.length;
  let area = 0;
  for (let i = 0; i < n; i++) {
    const j = (i + 1) % n;
    area += pts[i][0] * pts[j][1];
    area -= pts[j][0] * pts[i][1];
  }
  return Math.abs(area) / 2;
}

const DENSITY_LEVELS = [
  {
    threshold: 0.002,
    fill: "rgba(232,214,171,0.22)",
    stroke: "rgba(232,214,171,0.18)",
    radius: 16,
    label: "Reach",
  },
  {
    threshold: 0.005,
    fill: "rgba(207,151,84,0.32)",
    stroke: "rgba(207,151,84,0.22)",
    radius: 19,
    label: "Flow",
  },
  {
    threshold: 0.012,
    fill: "rgba(178,92,63,0.36)",
    stroke: "rgba(178,92,63,0.26)",
    radius: 22,
    label: "Pressure",
  },
  {
    threshold: 0.025,
    fill: "rgba(33,72,59,0.52)",
    stroke: "rgba(33,72,59,0.3)",
    radius: 26,
    label: "Core",
  },
];

const ZONE_LABELS: Record<string, string> = {
  "Restricted Area": "Rim",
  "In The Paint (Non-RA)": "Touch paint",
  "Mid-Range": "Mid-range",
  "Left Corner 3": "Left corner",
  "Right Corner 3": "Right corner",
  "Above the Break 3": "Above break",
  Backcourt: "Backcourt",
};

function descriptorForSpread(rimShare: number, threeShare: number, midShare: number) {
  if (rimShare >= 0.34 && threeShare >= 0.34) {
    return "Pressure at the rim with enough arc gravity to stretch the floor.";
  }
  if (rimShare >= 0.4) {
    return "A downhill footprint that keeps collapsing the paint.";
  }
  if (threeShare >= 0.44) {
    return "An orbit that lives on the perimeter and bends the shell outward.";
  }
  if (midShare >= 0.26) {
    return "A wandering mid-range map with touch pockets all over the lane line.";
  }
  return "A balanced half-court footprint with layered touch points across the shell.";
}

export default function ShotSprawlMap({
  shots,
  playerLabel,
  idPrefix,
}: ShotSprawlMapProps) {
  const reactId = useId();
  const scoped = (suffix: string) => `${idPrefix ?? reactId}-${suffix}`;
  const {
    hull,
    coverageSqFt,
    densityNodes,
    pressureZones,
    rimShare,
    threeShare,
    descriptor,
  } = useMemo(() => {
    if (shots.length === 0) {
      return {
        hull: [] as Array<[number, number]>,
        coverageSqFt: 0,
        densityNodes: [] as Array<{ x: number; y: number; levelIdx: number; density: number }>,
        pressureZones: [] as string[],
        rimShare: 0,
        threeShare: 0,
        descriptor: "",
      };
    }

    const rawGrid: number[][] = Array.from({ length: COLS }, () => new Array(ROWS).fill(0));
    const svgPoints: Array<[number, number]> = [];
    const zoneCounts = new Map<string, number>();

    let rimAttempts = 0;
    let threeAttempts = 0;
    let midAttempts = 0;

    for (const shot of shots) {
      const [sx, sy] = toSvg(shot.loc_x, shot.loc_y);
      svgPoints.push([sx, sy]);
      const col = Math.min(COLS - 1, Math.max(0, Math.floor(sx / CELL)));
      const row = Math.min(ROWS - 1, Math.max(0, Math.floor(sy / CELL)));
      rawGrid[col][row]++;

      const zone = shot.zone_basic || "Unknown";
      zoneCounts.set(zone, (zoneCounts.get(zone) ?? 0) + 1);
      if (zone === "Restricted Area" || zone === "In The Paint (Non-RA)") rimAttempts++;
      else if (zone === "Left Corner 3" || zone === "Right Corner 3" || zone === "Above the Break 3") threeAttempts++;
      else if (zone === "Mid-Range") midAttempts++;
    }

    const smoothed = gaussianBlur(rawGrid);
    const totalShots = shots.length;
    const nodes: Array<{ x: number; y: number; levelIdx: number; density: number }> = [];

    for (let c = 0; c < COLS; c++) {
      for (let r = 0; r < ROWS; r++) {
        const density = smoothed[c][r] / totalShots;
        let levelIdx = -1;
        for (let li = DENSITY_LEVELS.length - 1; li >= 0; li--) {
          if (density >= DENSITY_LEVELS[li].threshold) {
            levelIdx = li;
            break;
          }
        }
        if (levelIdx >= 0) {
          nodes.push({
            x: c * CELL + CELL / 2,
            y: r * CELL + CELL / 2,
            levelIdx,
            density,
          });
        }
      }
    }

    const sample =
      svgPoints.length > 600
        ? svgPoints.filter((_, i) => i % Math.ceil(svgPoints.length / 600) === 0)
        : svgPoints;
    const hull = convexHull(sample);
    const hullArea = hull.length >= 3 ? polygonArea(hull) : 0;
    const coverageSqFt = Math.round(hullArea * SQ_FT_PER_SQ_UNIT);

    const pressureZones = Array.from(zoneCounts.entries())
      .sort((left, right) => right[1] - left[1])
      .slice(0, 2)
      .map(([zone]) => ZONE_LABELS[zone] ?? zone);

    const rimShare = rimAttempts / totalShots;
    const threeShare = threeAttempts / totalShots;
    const midShare = midAttempts / totalShots;

    return {
      hull,
      coverageSqFt,
      densityNodes: nodes,
      pressureZones,
      rimShare,
      threeShare,
      descriptor: descriptorForSpread(rimShare, threeShare, midShare),
    };
  }, [shots]);

  if (shots.length === 0) {
    return (
      <p className="text-center py-8 text-sm text-[var(--muted)]">
        No shot data available for sprawl analysis.
      </p>
    );
  }

  const hullPoints = hull.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const coveragePct = coverageSqFt > 0 ? `${((coverageSqFt / 2350) * 100).toFixed(0)}%` : "—";
  const rimArcLabel = `${Math.round(rimShare * 100)} / ${Math.round(threeShare * 100)}`;

  return (
    <ShotLabSurface
      kicker="SPRAWL MAP"
      title="Court occupation portrait"
      subtitle={playerLabel ? `${playerLabel} · ${descriptor}` : descriptor}
      tone="accent"
      stats={
        <>
          <ShotLabStat
            label="Coverage"
            value={`~${coverageSqFt.toLocaleString()} sq ft`}
            detail={`${coveragePct} of the half-court shell`}
          />
          <ShotLabStat
            label="Pressure Zones"
            value={pressureZones.join(" · ") || "Mixed"}
            detail="The densest recurring touch pockets"
          />
          <ShotLabStat
            label="Rim / Arc"
            value={rimArcLabel}
            detail="Share of attempts living inside vs outside"
          />
        </>
      }
      legend={
        <>
          {DENSITY_LEVELS.map((level) => (
            <ShotLabLegendItem
              key={level.label}
              swatch={
                <span
                  className="inline-block h-3.5 w-6 rounded-full"
                  style={{ background: level.fill, boxShadow: `0 0 18px ${level.fill}` }}
                />
              }
              label={level.label}
            />
          ))}
          <ShotLabLegendItem
            swatch={
              <svg width="26" height="10" viewBox="0 0 26 10" aria-hidden="true">
                <path d="M1 8 C6 1, 20 1, 25 8" fill="rgba(33,72,59,0.12)" stroke="rgba(33,72,59,0.38)" strokeWidth="1.3" />
              </svg>
            }
            label="Footprint veil"
          />
        </>
      }
    >
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full max-w-[36rem] mx-auto block"
        aria-label="Shot sprawl density portrait with softened coverage footprint"
      >
        <defs>
          <linearGradient id={scoped("wash")} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="rgba(255,255,255,0.98)" />
            <stop offset="55%" stopColor="rgba(243,236,220,0.96)" />
            <stop offset="100%" stopColor="rgba(225,236,231,0.96)" />
          </linearGradient>
          <radialGradient id={scoped("mist")} cx="50%" cy="42%" r="58%">
            <stop offset="0%" stopColor="rgba(255,255,255,0.7)" />
            <stop offset="100%" stopColor="rgba(255,255,255,0)" />
          </radialGradient>
          <filter id={scoped("blur-soft")} x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="8" />
          </filter>
          <filter id={scoped("blur-heavy")} x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="14" />
          </filter>
        </defs>

        <rect x="0" y="0" width={W} height={H} rx="20" fill={`url(#${scoped("wash")})`} />
        <rect x="0" y="0" width={W} height={H} rx="20" fill={`url(#${scoped("mist")})`} className="bip-shot-mist" />

        {hullPoints ? (
          <>
            <polygon
              points={hullPoints}
              fill="rgba(33,72,59,0.08)"
              stroke="none"
              filter={`url(#${scoped("blur-heavy")})`}
            />
            <polygon
              points={hullPoints}
              fill="rgba(33,72,59,0.08)"
              stroke="rgba(33,72,59,0.34)"
              strokeWidth="1.4"
              strokeLinejoin="round"
            />
          </>
        ) : null}

        <g opacity="0.88">
          {DENSITY_LEVELS.map((level, levelIdx) => (
            <g
              key={level.label}
              filter={`url(#${levelIdx >= 2 ? scoped("blur-heavy") : scoped("blur-soft")})`}
            >
              {densityNodes
                .filter((node) => node.levelIdx === levelIdx)
                .map((node) => (
                  <circle
                    key={`${level.label}-${node.x}-${node.y}`}
                    cx={node.x}
                    cy={node.y}
                    r={level.radius + node.density * 180}
                    fill={level.fill}
                    stroke={level.stroke}
                    strokeWidth="0.6"
                  />
                ))}
            </g>
          ))}
        </g>

        <g opacity="0.45">
          {shots.map((shot, index) => {
            const [x, y] = toSvg(shot.loc_x, shot.loc_y);
            return (
              <circle
                key={`${shot.loc_x}-${shot.loc_y}-${index}`}
                cx={x}
                cy={y}
                r="1.2"
                fill={shot.shot_made ? "rgba(33,72,59,0.42)" : "rgba(159,63,49,0.22)"}
              />
            );
          })}
        </g>

        <ShotCourt />

        <g>
          <rect x="24" y="22" width="152" height={playerLabel ? 66 : 52} rx="16" fill="rgba(255,255,255,0.78)" />
          <text x="40" y="42" fontSize="10" fontWeight="700" fill="rgba(181,145,78,0.92)" letterSpacing="0.16em">
            SPRAWL
          </text>
          <text x="40" y="60" fontSize="14" fontWeight="600" fill="rgba(33,72,59,0.92)">
            Shot footprint
          </text>
          {playerLabel ? (
            <text x="40" y="76" fontSize="9.5" fontWeight="500" fill="rgba(33,72,59,0.62)">
              {playerLabel}
            </text>
          ) : null}
        </g>
      </svg>
    </ShotLabSurface>
  );
}
