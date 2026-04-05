"use client";

import { useMemo, useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { ShotChartShot } from "@/lib/types";
import { LEAGUE_AVG_FG, ZONE_ORDER, ZONE_PATHS, heatColor } from "@/lib/shotchart-constants";
import { usePlayerShotChart } from "@/hooks/usePlayerStats";
import { chartPalette } from "@/lib/chart-system";
import { ShotLabLegendItem, ShotLabSurface } from "./ShotLabSurface";
import ShotCourt from "./ShotCourt";

interface ShotSeasonEvolutionProps {
  playerId: number;
  seasons: string[]; // ordered oldest→newest, max 10
  playoffSeasons?: string[];
}

// ─── Pre-allocated hook slots (React rules: no conditional hooks) ─────────────
// The CLAUDE.md requirement: allocate a fixed maximum number of hook slots.
// SWR returns undefined for null keys (empty-string season → null key in hook).

function useTenShotChartSlots(
  playerId: number,
  seasons: string[],
  seasonType: "Regular Season" | "Playoffs"
) {
  const s = (i: number) => seasons[i] ?? "";
  const slot0 = usePlayerShotChart(playerId, s(0), seasonType);
  const slot1 = usePlayerShotChart(playerId, s(1), seasonType);
  const slot2 = usePlayerShotChart(playerId, s(2), seasonType);
  const slot3 = usePlayerShotChart(playerId, s(3), seasonType);
  const slot4 = usePlayerShotChart(playerId, s(4), seasonType);
  const slot5 = usePlayerShotChart(playerId, s(5), seasonType);
  const slot6 = usePlayerShotChart(playerId, s(6), seasonType);
  const slot7 = usePlayerShotChart(playerId, s(7), seasonType);
  const slot8 = usePlayerShotChart(playerId, s(8), seasonType);
  const slot9 = usePlayerShotChart(playerId, s(9), seasonType);
  return [slot0, slot1, slot2, slot3, slot4, slot5, slot6, slot7, slot8, slot9];
}

// ─── Zone heatmap for a mini court ──────────────────────────────────────────

interface MiniZoneStat {
  zone: string;
  diff: number | null;
}

function buildMiniZoneStats(shots: ShotChartShot[]): MiniZoneStat[] {
  const totals: Record<string, { made: number; attempted: number }> = {};
  for (const shot of shots) {
    const z = shot.zone_basic || "Unknown";
    if (!totals[z]) totals[z] = { made: 0, attempted: 0 };
    totals[z].attempted++;
    if (shot.shot_made) totals[z].made++;
  }
  return ZONE_ORDER.filter((z) => ZONE_PATHS[z]).map((zone) => {
    const stat = totals[zone];
    const avg = LEAGUE_AVG_FG[zone] ?? null;
    const fgPct = stat && stat.attempted >= 5 ? stat.made / stat.attempted : null;
    const diff = fgPct !== null && avg !== null ? fgPct - avg : null;
    return { zone, diff };
  });
}

// 3PT made/attempted from raw shots
function compute3PtPct(shots: ShotChartShot[]): number | null {
  const threes = shots.filter((s) => s.shot_type === "3PT Field Goal");
  if (threes.length < 5) return null;
  return threes.filter((s) => s.shot_made).length / threes.length;
}

// ─── Mini court component ─────────────────────────────────────────────────────

interface MiniCourtProps {
  shots: ShotChartShot[];
  season: string;
  isCurrent: boolean;
  isLoading: boolean;
}

function MiniCourt({ shots, season, isCurrent, isLoading }: MiniCourtProps) {
  const zoneStats = buildMiniZoneStats(shots);
  const total = shots.length;
  const made = shots.filter((s) => s.shot_made).length;
  const fgPct = total >= 5 ? (made / total) * 100 : null;
  const threePct = compute3PtPct(shots);

  // Short season label: "24-25" from "2024-25"
  const shortSeason = season.slice(2);

  return (
    <div className="flex flex-col items-center">
      <div
        className={`rounded-xl overflow-hidden border ${
          isCurrent
            ? "border-[rgba(33,72,59,0.5)] shadow-[0_0_0_2px_rgba(33,72,59,0.18),0_14px_36px_rgba(47,43,36,0.08)]"
            : "border-[rgba(25,52,42,0.12)] shadow-[0_10px_28px_rgba(47,43,36,0.06)]"
        }`}
        style={{ width: 150, height: 144 }}
      >
        {isLoading || total === 0 ? (
          <div className="w-full h-full flex items-center justify-center bg-[linear-gradient(180deg,rgba(255,252,247,0.9),rgba(228,236,232,0.62))]">
            {isLoading ? (
              <div className="w-5 h-5 rounded-full border-2 border-[var(--accent)] border-t-transparent animate-spin" />
            ) : (
              <div className="text-center">
                <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Empty lane</div>
                <div className="mt-1 text-[10px] text-[var(--muted)]">No shot data</div>
              </div>
            )}
          </div>
        ) : (
          <svg
            viewBox="0 0 500 480"
            width="150"
            height="144"
            aria-label={`Shot zones for ${season}`}
          >
            <defs>
              <linearGradient id={`mini-wash-${season}`} x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="rgba(255,255,255,0.98)" />
                <stop offset="100%" stopColor="rgba(228,236,232,0.94)" />
              </linearGradient>
            </defs>
            <rect x="0" y="0" width="500" height="480" fill={`url(#mini-wash-${season})`} />

            {/* Zone fills */}
            {zoneStats.map(({ zone, diff }) => {
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

            <ShotCourt />

            {/* Current season ring */}
            {isCurrent && (
              <rect
                x="2" y="2" width="496" height="476"
                rx="6"
                fill="none"
                stroke="rgba(33,72,59,0.35)"
                strokeWidth="4"
              />
            )}
          </svg>
        )}
      </div>

      {/* Season label + stats */}
      <div className="mt-2 text-center">
        <p className={`text-[11px] font-semibold ${isCurrent ? "text-[var(--accent-strong)]" : "text-[var(--muted-strong)]"}`}>
          {shortSeason}
        </p>
        {total >= 5 && (
          <p className="text-[9px] text-[var(--muted)] tabular-nums">
            {total} FGA
            {fgPct !== null ? ` · ${fgPct.toFixed(0)}% FG` : ""}
            {threePct !== null ? ` · ${(threePct * 100).toFixed(0)}% 3P` : ""}
          </p>
        )}
      </div>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function ShotSeasonEvolution({
  playerId,
  seasons,
  playoffSeasons = [],
}: ShotSeasonEvolutionProps) {
  const [seasonType, setSeasonType] = useState<"Regular Season" | "Playoffs">("Regular Season");
  const allSeasons = useMemo(
    () => Array.from(new Set([...seasons, ...playoffSeasons])).sort((left, right) => left.localeCompare(right)),
    [playoffSeasons, seasons]
  );
  const cappedSeasons = allSeasons.slice(0, 10);
  const slots = useTenShotChartSlots(playerId, cappedSeasons, seasonType);

  // Build timeline data for the Recharts chart
  const timelineData = cappedSeasons.map((season, i) => {
    const d = slots[i].data;
    const shots = d?.shots ?? [];
    const total = d?.attempted ?? 0;
    const made = d?.made ?? 0;
    const fgPct = total >= 5 ? (made / total) * 100 : null;
    const threePct = shots.length >= 5 ? compute3PtPct(shots) : null;
    const threeAttempts = shots.filter((s) => s.shot_type === "3PT Field Goal").length;
    const threeRate = total >= 5 ? (threeAttempts / total) * 100 : null;
    return {
      season: season.slice(2), // "24-25"
      fgPct,
      threePct: threePct !== null ? threePct * 100 : null,
      threeRate,
    };
  });

  const currentSeason = cappedSeasons[cappedSeasons.length - 1];

  if (cappedSeasons.length === 0) return null;

  return (
    <ShotLabSurface
      kicker="EVOLUTION"
      title="Shot profile evolution"
      subtitle={`${seasonType === "Regular Season" ? "Regular season" : "Playoff"} zone efficiency across every season, with the active year held apart from the rest of the strip.`}
      headerAside={
        <div className="flex overflow-hidden rounded-xl border border-[var(--border)] bg-[rgba(255,255,255,0.56)] p-1 text-xs w-fit">
          {(["Regular Season", "Playoffs"] as const).map((type) => (
            <button
              key={type}
              onClick={() => setSeasonType(type)}
              className={`rounded-lg px-3 py-2 transition-colors ${
                seasonType === type ? "bip-toggle-active" : "bip-toggle"
              }`}
            >
              {type}
            </button>
          ))}
        </div>
      }
      legend={
        <>
          <ShotLabLegendItem
            swatch={<span className="inline-block h-3.5 w-6 rounded-sm bg-emerald-500/80" />}
            label="Above avg zone"
          />
          <ShotLabLegendItem
            swatch={<span className="inline-block h-3.5 w-6 rounded-sm bg-gray-300" />}
            label="Near avg"
          />
          <ShotLabLegendItem
            swatch={<span className="inline-block h-3.5 w-6 rounded-sm bg-red-400/80" />}
            label="Below avg"
          />
          <ShotLabLegendItem
            swatch={<span className="inline-block h-3.5 w-6 rounded-sm border-2 border-[rgba(33,72,59,0.5)]" />}
            label="Current season"
          />
        </>
      }
    >
      <div className="flex flex-wrap gap-4 justify-start">
        {cappedSeasons.map((season, i) => {
          const slot = slots[i];
          return (
            <MiniCourt
              key={season}
              shots={slot.data?.shots ?? []}
              season={season}
              isCurrent={season === currentSeason}
              isLoading={slot.isLoading}
            />
          );
        })}
      </div>

      {/* Recharts timeline */}
      {timelineData.some((d) => d.fgPct !== null) && (
        <div className="mt-6 border-t border-[rgba(25,52,42,0.08)] pt-5">
          <p className="bip-kicker mb-3">Efficiency Trend</p>
          <div className="rounded-[1.35rem] border border-[rgba(25,52,42,0.1)] bg-[rgba(255,255,255,0.62)] p-3" style={{ height: 164 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timelineData} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                <defs>
                  <linearGradient id="sse-fg-grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={chartPalette.accent} stopOpacity={0.18} />
                    <stop offset="95%" stopColor={chartPalette.accent} stopOpacity={0.02} />
                  </linearGradient>
                  <linearGradient id="sse-3p-grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={chartPalette.signal} stopOpacity={0.18} />
                    <stop offset="95%" stopColor={chartPalette.signal} stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={chartPalette.grid} />
                <XAxis
                  dataKey="season"
                  tick={{ fontSize: 10, fill: "var(--muted)" }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fontSize: 9, fill: "var(--muted)" }}
                  axisLine={false}
                  tickLine={false}
                  domain={[20, 70]}
                  tickFormatter={(v: number) => `${v}%`}
                  width={32}
                />
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (!active || !payload || payload.length === 0) return null;
                    return (
                      <div className="rounded-lg border border-[rgba(25,52,42,0.12)] bg-white/95 px-2.5 py-1.5 text-xs shadow-sm">
                        <p className="font-semibold text-[var(--foreground)] mb-1">{label}</p>
                        {payload.map((p) => (
                          <p key={p.name} style={{ color: p.color as string }}>
                            {p.name}:{" "}
                            {p.value !== null && p.value !== undefined
                              ? `${(p.value as number).toFixed(1)}%`
                              : "—"}
                          </p>
                        ))}
                      </div>
                    );
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="fgPct"
                  name="FG%"
                  stroke={chartPalette.accent}
                  strokeWidth={2}
                  fill="url(#sse-fg-grad)"
                  dot={{ r: 3, fill: chartPalette.accent, strokeWidth: 0 }}
                  connectNulls
                />
                <Area
                  type="monotone"
                  dataKey="threePct"
                  name="3P%"
                  stroke={chartPalette.signal}
                  strokeWidth={1.5}
                  fill="url(#sse-3p-grad)"
                  dot={{ r: 2.5, fill: chartPalette.signal, strokeWidth: 0 }}
                  connectNulls
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
      <p className="text-[11px] text-[var(--muted)]">
        {seasonType === "Playoffs" ? "Empty cards mark seasons without playoff shot data." : "At least 5 attempts are required before zone efficiency surfaces in the mini courts."}
      </p>
    </ShotLabSurface>
  );
}
