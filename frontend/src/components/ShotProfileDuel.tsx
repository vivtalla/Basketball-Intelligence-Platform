"use client";

import type { PersistedZoneProfileResponse } from "@/lib/types";
import { LEAGUE_AVG_FG } from "@/lib/shotchart-constants";
import ChartStatusBadge from "./ChartStatusBadge";

const DUEL_ZONES = [
  { key: "Restricted Area", label: "Paint" },
  { key: "In The Paint (Non-RA)", label: "Touch" },
  { key: "Mid-Range", label: "Mid" },
  { key: "Left Corner 3", label: "LC3" },
  { key: "Right Corner 3", label: "RC3" },
  { key: "Above the Break 3", label: "ATB3" },
] as const;

function zoneMap(data?: PersistedZoneProfileResponse) {
  const grouped = new Map<string, { attempts: number; made: number; fgPct: number | null; freq: number }>();
  for (const zone of data?.zones ?? []) {
    const current = grouped.get(zone.zone_basic) ?? { attempts: 0, made: 0, fgPct: null, freq: 0 };
    current.attempts += zone.attempts;
    current.made += zone.made;
    current.fgPct = current.attempts >= 5 ? current.made / current.attempts : null;
    current.freq = data && data.total_attempts > 0 ? current.attempts / data.total_attempts : 0;
    grouped.set(zone.zone_basic, current);
  }
  return grouped;
}

function duelColor(diff: number | null) {
  if (diff == null) return "rgba(123,137,131,0.38)";
  if (diff >= 0.04) return "rgba(33,72,59,0.92)";
  if (diff <= -0.04) return "rgba(159,63,49,0.88)";
  return "rgba(181,145,78,0.78)";
}

interface ShotProfileDuelProps {
  left: PersistedZoneProfileResponse | undefined;
  right: PersistedZoneProfileResponse | undefined;
  leftLabel: string;
  rightLabel: string;
}

export default function ShotProfileDuel({
  left,
  right,
  leftLabel,
  rightLabel,
}: ShotProfileDuelProps) {
  const leftMap = zoneMap(left);
  const rightMap = zoneMap(right);

  return (
    <section className="rounded-[2rem] border border-[var(--border)] bg-[linear-gradient(145deg,rgba(247,243,232,0.96),rgba(228,236,232,0.94))] p-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Shooting Duel
          </p>
          <h3 className="mt-1 text-2xl font-semibold text-[var(--foreground)]">
            Head-to-head zone pressure
          </h3>
        </div>
        <div className="flex flex-wrap gap-2">
          <ChartStatusBadge status={left?.data_status ?? "missing"} compact />
          <ChartStatusBadge status={right?.data_status ?? "missing"} compact />
        </div>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-[1fr_auto_1fr] md:items-end">
        <div>
          <div className="text-sm font-semibold text-[var(--foreground)]">{leftLabel}</div>
          <div className="text-xs text-[var(--muted)]">{left?.total_attempts ?? 0} attempts</div>
        </div>
        <div className="text-center text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
          zone split
        </div>
        <div className="text-right">
          <div className="text-sm font-semibold text-[var(--foreground)]">{rightLabel}</div>
          <div className="text-xs text-[var(--muted)]">{right?.total_attempts ?? 0} attempts</div>
        </div>
      </div>

      <div className="mt-5 space-y-3">
        {DUEL_ZONES.map((zone) => {
          const leftStat = leftMap.get(zone.key);
          const rightStat = rightMap.get(zone.key);
          const leftFreq = leftStat?.freq ?? 0;
          const rightFreq = rightStat?.freq ?? 0;
          const leftDiff =
            leftStat?.fgPct != null && LEAGUE_AVG_FG[zone.key] != null ? leftStat.fgPct - LEAGUE_AVG_FG[zone.key] : null;
          const rightDiff =
            rightStat?.fgPct != null && LEAGUE_AVG_FG[zone.key] != null ? rightStat.fgPct - LEAGUE_AVG_FG[zone.key] : null;

          return (
            <div
              key={zone.key}
              className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 rounded-[1.25rem] border border-[rgba(25,52,42,0.12)] bg-[rgba(255,255,255,0.68)] px-4 py-3"
            >
              <div className="flex items-center justify-end gap-3">
                <div className="text-right">
                  <div className="text-sm font-semibold tabular-nums text-[var(--foreground)]">
                    {leftStat?.fgPct != null ? `${(leftStat.fgPct * 100).toFixed(1)}%` : "—"}
                  </div>
                  <div className="text-[11px] text-[var(--muted)]">{Math.round(leftFreq * 100)}% freq</div>
                </div>
                <div className="h-2 w-full max-w-[180px] overflow-hidden rounded-full bg-[rgba(25,52,42,0.08)]">
                  <div
                    className="ml-auto h-full rounded-full"
                    style={{
                      width: `${Math.min(100, Math.max(4, leftFreq * 180))}%`,
                      background: duelColor(leftDiff),
                    }}
                  />
                </div>
              </div>

              <div className="min-w-[88px] text-center">
                <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
                  {zone.label}
                </div>
                <div className="mt-1 text-[11px] text-[var(--muted)]">
                  vs league
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="h-2 w-full max-w-[180px] overflow-hidden rounded-full bg-[rgba(25,52,42,0.08)]">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${Math.min(100, Math.max(4, rightFreq * 180))}%`,
                      background: duelColor(rightDiff),
                    }}
                  />
                </div>
                <div>
                  <div className="text-sm font-semibold tabular-nums text-[var(--foreground)]">
                    {rightStat?.fgPct != null ? `${(rightStat.fgPct * 100).toFixed(1)}%` : "—"}
                  </div>
                  <div className="text-[11px] text-[var(--muted)]">{Math.round(rightFreq * 100)}% freq</div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
