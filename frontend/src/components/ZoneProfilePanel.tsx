"use client";

import type { ZoneProfileResponse, ZoneStat } from "@/lib/types";
import { LEAGUE_AVG_FG, ZONE_POINTS } from "@/lib/shotchart-constants";

interface ZoneProfilePanelProps {
  data: ZoneProfileResponse | undefined;
  isLoading: boolean;
  playerLabel?: string;
}

const TILE_CONFIG = [
  { key: "Restricted Area",         label: "Paint" },
  { key: "In The Paint (Non-RA)",   label: "Non-RA Paint" },
  { key: "Mid-Range",               label: "Mid-Range" },
  { key: "Left Corner 3",           label: "Left Corner 3" },
  { key: "Right Corner 3",          label: "Right Corner 3" },
  { key: "Above the Break 3",       label: "Above Break 3" },
] as const;

function ZoneTile({ config, stat }: { config: { key: string; label: string }; stat: ZoneStat | undefined }) {
  const avg = LEAGUE_AVG_FG[config.key];
  const pts = ZONE_POINTS[config.key] ?? 2;

  if (!stat || stat.attempts < 5) {
    return (
      <div className="bip-panel rounded-xl p-3 flex flex-col gap-1">
        <p className="bip-kicker text-[10px]">{config.label}</p>
        <p className="text-lg font-semibold text-[var(--muted)]">—</p>
        <p className="text-[10px] text-[var(--muted)]">
          {stat ? `n=${stat.attempts}` : "no data"}
        </p>
      </div>
    );
  }

  const fgPct = stat.fg_pct!;
  const diff = avg != null ? fgPct - avg : null;
  const pps = stat.pps ?? fgPct * pts;
  const freqPct = Math.round(stat.freq * 100);

  const diffColor =
    diff == null
      ? ""
      : diff > 0.02
      ? "text-emerald-600 dark:text-emerald-400"
      : diff < -0.02
      ? "text-red-500 dark:text-red-400"
      : "text-[var(--muted)]";

  return (
    <div className="bip-panel rounded-xl p-3 flex flex-col gap-1">
      <p className="bip-kicker text-[10px]">{config.label}</p>
      <div className="flex items-baseline gap-1.5">
        <p className="text-lg font-semibold text-[var(--foreground)] tabular-nums">
          {(fgPct * 100).toFixed(1)}%
        </p>
        {diff != null && (
          <p className={`text-[11px] font-medium tabular-nums ${diffColor}`}>
            {diff >= 0 ? "+" : ""}
            {(diff * 100).toFixed(1)}
          </p>
        )}
      </div>
      <p className="text-[11px] text-[var(--muted)] tabular-nums">
        {pps.toFixed(2)} PPS · {freqPct}% freq
      </p>
      {/* Frequency bar */}
      <div className="mt-1 h-1 rounded-full bg-[var(--surface-alt)] overflow-hidden">
        <div
          className="h-full rounded-full bg-[var(--accent)] opacity-60"
          style={{ width: `${Math.min(freqPct * 2, 100)}%` }}
        />
      </div>
    </div>
  );
}

export default function ZoneProfilePanel({
  data,
  isLoading,
  playerLabel,
}: ZoneProfilePanelProps) {
  if (isLoading) {
    return (
      <div className="bip-panel rounded-2xl p-4 space-y-3 animate-pulse">
        <div className="h-4 w-32 rounded bg-[var(--surface-alt)]" />
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {TILE_CONFIG.map((t) => (
            <div key={t.key} className="bip-panel rounded-xl p-3 h-20 bg-[var(--surface-alt)]" />
          ))}
        </div>
      </div>
    );
  }

  if (!data || data.total_attempts === 0) {
    return (
      <div className="bip-panel rounded-2xl p-4">
        {playerLabel && (
          <p className="bip-kicker mb-2">{playerLabel}</p>
        )}
        <p className="text-sm text-[var(--muted)]">
          No shot data cached for this player/season.
        </p>
      </div>
    );
  }

  // Build lookup by zone_basic (use the first/largest-freq entry per zone_basic)
  const zoneMap: Record<string, ZoneStat> = {};
  for (const z of data.zones) {
    if (!zoneMap[z.zone_basic] || z.attempts > zoneMap[z.zone_basic].attempts) {
      zoneMap[z.zone_basic] = z;
    }
  }

  return (
    <div className="bip-panel rounded-2xl p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          {playerLabel && <p className="bip-kicker text-[10px] mb-0.5">{playerLabel}</p>}
          <h3 className="text-sm font-semibold text-[var(--foreground)]">Zone Efficiency</h3>
        </div>
        <p className="text-[11px] text-[var(--muted)] tabular-nums">
          {data.total_attempts} FGA · {data.season}
        </p>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {TILE_CONFIG.map((config) => (
          <ZoneTile key={config.key} config={config} stat={zoneMap[config.key]} />
        ))}
      </div>
      <p className="text-[10px] text-[var(--muted)]">
        +/− vs league avg · {data.season_type}
      </p>
    </div>
  );
}
