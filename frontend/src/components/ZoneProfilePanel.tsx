"use client";

import type { PersistedZoneProfileResponse, TeamDefenseZoneProfileResponse, ZoneStat } from "@/lib/types";
import { LEAGUE_AVG_FG, ZONE_POINTS } from "@/lib/shotchart-constants";
import ChartStatusBadge from "./ChartStatusBadge";
import ShotProfileFingerprint from "./ShotProfileFingerprint";
import ZoneAnnotationCourt from "./ZoneAnnotationCourt";

interface ZoneProfilePanelProps {
  data: PersistedZoneProfileResponse | TeamDefenseZoneProfileResponse | undefined;
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

function aggregateZonesByBasic(zones: ZoneStat[], totalAttempts: number) {
  const grouped: Record<string, { attempts: number; made: number }> = {};

  for (const zone of zones) {
    if (!grouped[zone.zone_basic]) {
      grouped[zone.zone_basic] = { attempts: 0, made: 0 };
    }
    grouped[zone.zone_basic].attempts += zone.attempts;
    grouped[zone.zone_basic].made += zone.made;
  }

  const aggregated: Record<string, ZoneStat> = {};
  for (const [zoneBasic, counts] of Object.entries(grouped)) {
    const fgPct =
      counts.attempts >= 5 ? counts.made / counts.attempts : null;
    const pts = ZONE_POINTS[zoneBasic] ?? 2;

    aggregated[zoneBasic] = {
      zone_basic: zoneBasic,
      zone_area: "All",
      attempts: counts.attempts,
      made: counts.made,
      fg_pct: fgPct != null ? Number(fgPct.toFixed(4)) : null,
      pps: fgPct != null ? Number((fgPct * pts).toFixed(4)) : null,
      freq: totalAttempts > 0 ? Number((counts.attempts / totalAttempts).toFixed(4)) : 0,
    };
  }

  return aggregated;
}

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
      <div className="bip-shot-shell bip-shot-shell-neutral space-y-3 animate-pulse">
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
      <div className="bip-shot-shell bip-shot-shell-neutral">
        <div className="mb-2 flex items-center justify-between gap-3">
          <div>
            {playerLabel && (
              <p className="bip-kicker mb-0.5">{playerLabel}</p>
            )}
            <h3 className="text-sm font-semibold text-[var(--foreground)]">Zone Efficiency</h3>
          </div>
          <ChartStatusBadge status={data?.data_status ?? "missing"} compact />
        </div>
        <p className="text-sm text-[var(--muted)]">
          {data?.data_status === "missing"
            ? "Shot chart data has not been synced for this player and season yet."
            : "No shot attempts are available in the cached shot-chart data for this period."}
        </p>
      </div>
    );
  }

  const zoneMap = aggregateZonesByBasic(data.zones, data.total_attempts);

  return (
    <div className="bip-shot-shell bip-shot-shell-neutral space-y-3">
      <div className="flex items-center justify-between">
        <div>
          {playerLabel && <p className="bip-kicker text-[10px] mb-0.5">{playerLabel}</p>}
          <h3 className="text-sm font-semibold text-[var(--foreground)]">Zone Efficiency</h3>
        </div>
        <div className="text-right">
          <div className="flex items-center justify-end gap-2">
            <ChartStatusBadge status={data.data_status} compact />
            <p className="text-[11px] text-[var(--muted)] tabular-nums">
              {data.total_attempts} FGA · {data.season}
            </p>
          </div>
          {data.last_synced_at && (
            <p className="mt-1 text-[10px] text-[var(--muted)]">
              Synced {new Date(data.last_synced_at).toLocaleDateString()}
            </p>
          )}
        </div>
      </div>
      <ShotProfileFingerprint
        zones={data.zones}
        totalAttempts={data.total_attempts}
        playerLabel={playerLabel}
      />
      {/* Zone annotation court — half-court with efficiency stats per zone */}
      <ZoneAnnotationCourt zones={data.zones} />
      {/* Tile grid — compact secondary detail */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {TILE_CONFIG.map((config) => (
          <ZoneTile key={config.key} config={config} stat={zoneMap[config.key]} />
        ))}
      </div>
      <p className="text-[10px] text-[var(--muted)]">
        +/− vs league avg · {data.season_type}
        {data.data_status === "stale" ? " · showing cached data while a refresh is pending" : ""}
      </p>
    </div>
  );
}
