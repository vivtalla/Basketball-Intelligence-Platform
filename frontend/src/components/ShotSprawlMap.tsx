"use client";

import { useId, useMemo } from "react";
import type { ShotChartShot } from "@/lib/types";

interface ShotSprawlMapProps {
  shots: ShotChartShot[];
  playerLabel?: string;
  idPrefix?: string;
}

// SVG viewport matches the rest of the platform
const W = 500;
const H = 480;

// Grid dimensions — each cell covers 20×20 SVG units
const COLS = 25; // 25 × 20 = 500
const ROWS = 24; // 24 × 20 = 480
const CELL = 20;

// NBA half-court is 47 × 50 ft = 2350 sq ft; SVG area = 500 × 480 = 240 000 sq units
const SQ_FT_PER_SQ_UNIT = 2350 / 240000;

// ─── Court coordinate helpers ────────────────────────────────────────────────

function toSvg(locX: number, locY: number): [number, number] {
  return [locX + 250, 430 - locY];
}

// ─── 5×5 Gaussian kernel ─────────────────────────────────────────────────────

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

// ─── Convex hull (Jarvis march / gift-wrapping) ───────────────────────────────

function cross(
  o: [number, number],
  a: [number, number],
  b: [number, number]
): number {
  return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
}

function convexHull(pts: Array<[number, number]>): Array<[number, number]> {
  const n = pts.length;
  if (n < 3) return pts;

  // Find leftmost point
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

// ─── Density levels ──────────────────────────────────────────────────────────

// Fraction of total shots per cell to trigger each contour level
// Level 1 = outermost (sparsest), Level 4 = innermost (densest)
const DENSITY_LEVELS = [
  { threshold: 0.002, fill: "rgba(237,230,200,0.55)", label: "< 1% density" },
  { threshold: 0.005, fill: "rgba(217,119,6,0.45)",   label: "1–3%" },
  { threshold: 0.012, fill: "rgba(194,65,12,0.60)",   label: "3–8%" },
  { threshold: 0.025, fill: "rgba(33,72,59,0.70)",    label: "> 8%" },
];

// ─── Court markings ───────────────────────────────────────────────────────────

function CourtMarkings() {
  return (
    <g stroke="rgba(33,72,59,0.28)" strokeWidth="1.5" fill="none">
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

// ─── Main component ───────────────────────────────────────────────────────────

export default function ShotSprawlMap({
  shots,
  playerLabel,
  idPrefix,
}: ShotSprawlMapProps) {
  const reactId = useId();
  const gradientId = `${idPrefix ?? reactId}-ssm-wash`;
  const { hull, coverageSqFt, cellRects } = useMemo(() => {
    if (shots.length === 0) {
      return { hull: [], coverageSqFt: 0, cellRects: [] };
    }

    // 1. Build raw shot count grid
    const rawGrid: number[][] = Array.from({ length: COLS }, () =>
      new Array(ROWS).fill(0)
    );
    const svgPoints: Array<[number, number]> = [];

    for (const shot of shots) {
      const [sx, sy] = toSvg(shot.loc_x, shot.loc_y);
      svgPoints.push([sx, sy]);
      const col = Math.min(COLS - 1, Math.max(0, Math.floor(sx / CELL)));
      const row = Math.min(ROWS - 1, Math.max(0, Math.floor(sy / CELL)));
      rawGrid[col][row]++;
    }

    // 2. Gaussian smooth
    const smoothed = gaussianBlur(rawGrid);

    // 3. Build cell rects per density level (outermost → innermost)
    // We render from level 0 → 3 so higher levels paint over lower ones
    const totalShots = shots.length;
    const rects: Array<{ col: number; row: number; levelIdx: number }> = [];

    for (let c = 0; c < COLS; c++) {
      for (let r = 0; r < ROWS; r++) {
        const density = smoothed[c][r] / totalShots;
        // Assign to the highest level this cell qualifies for
        let levelIdx = -1;
        for (let li = DENSITY_LEVELS.length - 1; li >= 0; li--) {
          if (density >= DENSITY_LEVELS[li].threshold) {
            levelIdx = li;
            break;
          }
        }
        if (levelIdx >= 0) rects.push({ col: c, row: r, levelIdx });
      }
    }

    // 4. Convex hull over all shot positions (subsample if needed for performance)
    const sample =
      svgPoints.length > 600
        ? svgPoints.filter((_, i) => i % Math.ceil(svgPoints.length / 600) === 0)
        : svgPoints;
    const hull = convexHull(sample);
    const hullArea = hull.length >= 3 ? polygonArea(hull) : 0;
    const coverageSqFt = Math.round(hullArea * SQ_FT_PER_SQ_UNIT);

    return { hull, coverageSqFt, cellRects: rects };
  }, [shots]);

  if (shots.length === 0) {
    return (
      <p className="text-center py-8 text-sm text-[var(--muted)]">
        No shot data available for sprawl analysis.
      </p>
    );
  }

  const hullPoints =
    hull.length > 0
      ? hull.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ")
      : "";

  return (
    <div>
      {/* Coverage stat summary */}
      {coverageSqFt > 0 && (
        <div className="mb-3 flex items-center gap-2 text-sm text-[var(--muted-strong)]">
          <span className="text-[var(--muted)]">Court coverage:</span>
          <span className="font-semibold text-[var(--foreground)]">
            ~{coverageSqFt.toLocaleString()} sq ft
          </span>
          <span className="text-[var(--muted)] text-xs">
            ({((coverageSqFt / 2350) * 100).toFixed(0)}% of half-court)
          </span>
        </div>
      )}

      {/* Court SVG */}
      <div className="rounded-[1.75rem] border border-[rgba(25,52,42,0.12)] bg-[rgba(255,255,255,0.72)] p-3">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="w-full max-w-lg mx-auto block"
          aria-label="Shot sprawl density map with convex hull coverage"
        >
          <defs>
            <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="rgba(255,255,255,0.98)" />
              <stop offset="100%" stopColor="rgba(228,236,232,0.94)" />
            </linearGradient>
          </defs>

          <rect x="0" y="0" width={W} height={H} rx="18" fill={`url(#${gradientId})`} />

          {/* Density cells — render each level's cells as filled rects */}
          {cellRects.map(({ col, row, levelIdx }) => (
            <rect
              key={`${col}-${row}`}
              x={col * CELL}
              y={row * CELL}
              width={CELL}
              height={CELL}
              fill={DENSITY_LEVELS[levelIdx].fill}
            />
          ))}

          {/* Convex hull outline */}
          {hullPoints && (
            <polygon
              points={hullPoints}
              fill="none"
              stroke="rgba(33,72,59,0.45)"
              strokeWidth="1.5"
              strokeDasharray="6 4"
            />
          )}

          <CourtMarkings />

          {/* Court label badge */}
          <rect x="24" y="18" width="118" height={playerLabel ? 60 : 48} rx="14" fill="rgba(255,255,255,0.86)" />
          <text x="38" y="38" fontSize="10" fontWeight="600" fill="rgba(33,72,59,0.6)" letterSpacing="0.12em">
            GOLDSBERRY
          </text>
          <text x="38" y="55" fontSize="13" fontWeight="600" fill="rgba(33,72,59,0.9)">
            Sprawl map
          </text>
          {playerLabel ? (
            <text x="38" y="69" fontSize="9" fontWeight="500" fill="rgba(33,72,59,0.6)">
              {playerLabel}
            </text>
          ) : null}
        </svg>
      </div>

      {/* Density legend */}
      <div className="flex flex-wrap items-center justify-center gap-4 mt-3 text-[10px] text-[var(--muted)]">
        {DENSITY_LEVELS.map((lv) => (
          <span key={lv.label} className="flex items-center gap-1.5">
            <span
              className="inline-block w-3 h-3 rounded-[2px]"
              style={{ background: lv.fill, opacity: 0.95 }}
            />
            {lv.label}
          </span>
        ))}
        <span className="flex items-center gap-1.5">
          <svg width="18" height="8" viewBox="0 0 18 8">
            <line
              x1="0" y1="4" x2="18" y2="4"
              stroke="rgba(33,72,59,0.5)"
              strokeWidth="1.5"
              strokeDasharray="5 3"
            />
          </svg>
          Hull boundary
        </span>
      </div>
    </div>
  );
}
