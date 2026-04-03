"use client";

import type { ZoneStat } from "@/lib/types";
import { LEAGUE_AVG_FG, ZONE_POINTS } from "@/lib/shotchart-constants";

const FINGERPRINT_ZONES = [
  { key: "Restricted Area", label: "Paint" },
  { key: "In The Paint (Non-RA)", label: "Touch" },
  { key: "Mid-Range", label: "Mid" },
  { key: "Left Corner 3", label: "LC3" },
  { key: "Right Corner 3", label: "RC3" },
  { key: "Above the Break 3", label: "ATB3" },
] as const;

function aggregateZones(zones: ZoneStat[], totalAttempts: number) {
  const grouped: Record<string, ZoneStat> = {};
  for (const zone of zones) {
    const current = grouped[zone.zone_basic];
    if (!current) {
      grouped[zone.zone_basic] = {
        zone_basic: zone.zone_basic,
        zone_area: "All",
        attempts: zone.attempts,
        made: zone.made,
        fg_pct: zone.fg_pct,
        pps: zone.pps,
        freq: totalAttempts > 0 ? zone.attempts / totalAttempts : 0,
      };
      continue;
    }
    current.attempts += zone.attempts;
    current.made += zone.made;
    current.freq = totalAttempts > 0 ? current.attempts / totalAttempts : 0;
    if (current.attempts >= 5) {
      current.fg_pct = current.made / current.attempts;
      current.pps = current.fg_pct * (ZONE_POINTS[zone.zone_basic] ?? 2);
    }
  }
  return grouped;
}

function polar(cx: number, cy: number, radius: number, angleDeg: number) {
  const radians = (angleDeg - 90) * (Math.PI / 180);
  return {
    x: cx + radius * Math.cos(radians),
    y: cy + radius * Math.sin(radians),
  };
}

function diffColor(diff: number | null) {
  if (diff == null) return "rgba(123,137,131,0.45)";
  if (diff >= 0.06) return "rgba(33,72,59,0.95)";
  if (diff >= 0.02) return "rgba(52,120,94,0.82)";
  if (diff <= -0.06) return "rgba(159,63,49,0.88)";
  if (diff <= -0.02) return "rgba(194,122,44,0.82)";
  return "rgba(181,145,78,0.75)";
}

interface ShotProfileFingerprintProps {
  zones: ZoneStat[];
  totalAttempts: number;
  playerLabel?: string;
}

export default function ShotProfileFingerprint({
  zones,
  totalAttempts,
  playerLabel,
}: ShotProfileFingerprintProps) {
  const aggregated = aggregateZones(zones, totalAttempts);
  const cx = 170;
  const cy = 170;
  const rings = [44, 74, 104];

  const spokes = FINGERPRINT_ZONES.map((zone, index) => {
    const stat = aggregated[zone.key];
    const angle = (360 / FINGERPRINT_ZONES.length) * index;
    const freq = stat?.freq ?? 0;
    const fgPct = stat?.attempts && stat.attempts >= 5 ? stat.fg_pct : null;
    const diff = fgPct != null && LEAGUE_AVG_FG[zone.key] != null ? fgPct - LEAGUE_AVG_FG[zone.key] : null;
    const radius = 40 + freq * 110;
    const point = polar(cx, cy, radius, angle);
    const labelPoint = polar(cx, cy, 134, angle);
    return {
      ...zone,
      stat,
      diff,
      point,
      labelPoint,
      angle,
      radius,
      color: diffColor(diff),
    };
  });

  const polygon = spokes.map((spoke) => `${spoke.point.x},${spoke.point.y}`).join(" ");

  return (
    <div className="rounded-[1.75rem] border border-[var(--border)] bg-[linear-gradient(145deg,rgba(247,243,232,0.9),rgba(228,236,232,0.92))] p-5">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Shot Fingerprint
          </p>
          <h3 className="mt-1 text-xl font-semibold text-[var(--foreground)]">
            {playerLabel ?? "Zone signature"}
          </h3>
        </div>
        <div className="text-right text-[11px] text-[var(--muted)]">
          <div>{totalAttempts} attempts</div>
          <div>Frequency drives shape, efficiency drives color</div>
        </div>
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-[360px,1fr]">
        <div className="overflow-hidden rounded-[1.5rem] border border-[rgba(25,52,42,0.12)] bg-[rgba(255,255,255,0.55)] p-3">
          <svg viewBox="0 0 340 340" className="h-full w-full">
            <defs>
              <linearGradient id="fingerprintFill" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="rgba(33,72,59,0.34)" />
                <stop offset="100%" stopColor="rgba(181,145,78,0.22)" />
              </linearGradient>
            </defs>
            {rings.map((ring) => (
              <circle
                key={ring}
                cx={cx}
                cy={cy}
                r={ring}
                fill="none"
                stroke="rgba(25,52,42,0.12)"
                strokeDasharray="4 6"
              />
            ))}
            {spokes.map((spoke) => (
              <line
                key={`axis-${spoke.key}`}
                x1={cx}
                y1={cy}
                x2={spoke.labelPoint.x}
                y2={spoke.labelPoint.y}
                stroke="rgba(25,52,42,0.12)"
              />
            ))}
            <polygon
              points={polygon}
              fill="url(#fingerprintFill)"
              stroke="rgba(33,72,59,0.65)"
              strokeWidth="2"
            />
            {spokes.map((spoke) => (
              <g key={spoke.key}>
                <circle cx={spoke.point.x} cy={spoke.point.y} r="6" fill={spoke.color} />
                <text
                  x={spoke.labelPoint.x}
                  y={spoke.labelPoint.y}
                  textAnchor="middle"
                  className="fill-[var(--muted-strong)] text-[10px] font-semibold uppercase tracking-[0.12em]"
                >
                  {spoke.label}
                </text>
              </g>
            ))}
            <circle cx={cx} cy={cy} r="26" fill="rgba(255,255,255,0.86)" stroke="rgba(25,52,42,0.12)" />
            <text x={cx} y={cy - 4} textAnchor="middle" className="fill-[var(--foreground)] text-[11px] font-semibold uppercase tracking-[0.14em]">
              CourtVue
            </text>
            <text x={cx} y={cy + 12} textAnchor="middle" className="fill-[var(--muted)] text-[10px]">
              profile
            </text>
          </svg>
        </div>

        <div className="grid gap-2 sm:grid-cols-2">
          {spokes.map((spoke) => {
            const attempts = spoke.stat?.attempts ?? 0;
            const fgPct = spoke.stat?.attempts && spoke.stat.attempts >= 5 ? spoke.stat.fg_pct : null;
            const diff = spoke.diff;
            const freqPct = Math.round((spoke.stat?.freq ?? 0) * 100);
            return (
              <div
                key={spoke.key}
                className="rounded-2xl border border-[rgba(25,52,42,0.12)] bg-[rgba(255,255,255,0.64)] p-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
                      {spoke.label}
                    </p>
                    <div className="mt-1 text-lg font-semibold tabular-nums text-[var(--foreground)]">
                      {fgPct != null ? `${(fgPct * 100).toFixed(1)}%` : "—"}
                    </div>
                  </div>
                  <div className="text-right text-[11px] text-[var(--muted)]">
                    <div>{attempts} FGA</div>
                    <div>{freqPct}% share</div>
                  </div>
                </div>
                <div className="mt-3 h-2 overflow-hidden rounded-full bg-[rgba(25,52,42,0.08)]">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${Math.min(100, Math.max(8, freqPct * 1.6))}%`,
                      background: spoke.color,
                    }}
                  />
                </div>
                <div
                  className="mt-2 text-xs font-medium tabular-nums"
                  style={{ color: diffColor(diff) }}
                >
                  {diff != null ? `${diff >= 0 ? "+" : ""}${(diff * 100).toFixed(1)}% vs league` : "Small sample"}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
