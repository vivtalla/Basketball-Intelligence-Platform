"use client";

import Link from "next/link";
import { useMemo } from "react";
import type { ShotChartShot } from "@/lib/types";

interface ShotContextPanelProps {
  shots: ShotChartShot[];
  season: string;
}

function parseClockToSeconds(clock: string | null | undefined): number {
  if (!clock) return Number.POSITIVE_INFINITY;
  const parts = clock.split(":");
  if (parts.length !== 2) return Number.POSITIVE_INFINITY;
  const minutes = Number(parts[0]);
  const seconds = Number(parts[1]);
  if (!Number.isFinite(minutes) || !Number.isFinite(seconds)) {
    return Number.POSITIVE_INFINITY;
  }
  return minutes * 60 + seconds;
}

function buildGameExplorerHref(shot: ShotChartShot, season: string, index: number): string | null {
  if (!shot.game_id) return null;
  const params = new URLSearchParams({
    source: "shot-lab",
    source_id: shot.shot_event_id ?? `${shot.game_id}-${index}`,
    season,
    event_type: shot.shot_value === 3 ? "3pt" : "2pt",
    query: shot.action_type || shot.zone_basic || "shot",
  });
  if (shot.period != null) {
    params.set("period", String(shot.period));
  }
  if (shot.shot_event_id) {
    params.set("shot_event_id", shot.shot_event_id);
  }
  if (shot.action_number != null) {
    params.set("action_number", String(shot.action_number));
  }
  return `/games/${shot.game_id}?${params.toString()}`;
}

function linkageLabel(mode: string | null | undefined): string {
  if (mode === "exact") return "Exact link";
  if (mode === "derived") return "Derived link";
  return "Timeline context";
}

function linkageTone(mode: string | null | undefined): string {
  if (mode === "exact") {
    return "bg-blue-100 text-blue-700";
  }
  if (mode === "derived") {
    return "bg-amber-100 text-amber-700";
  }
  return "bg-slate-100 text-slate-700";
}

export default function ShotContextPanel({
  shots,
  season,
}: ShotContextPanelProps) {
  const topActions = useMemo(() => {
    const actionMap = new Map<string, { attempts: number; made: number }>();
    for (const shot of shots) {
      const label = shot.action_type || "Unclassified attempt";
      const current = actionMap.get(label) ?? { attempts: 0, made: 0 };
      current.attempts += 1;
      if (shot.shot_made) current.made += 1;
      actionMap.set(label, current);
    }
    return Array.from(actionMap.entries())
      .map(([label, value]) => ({
        label,
        attempts: value.attempts,
        made: value.made,
        freq: shots.length > 0 ? value.attempts / shots.length : 0,
      }))
      .sort((left, right) => right.attempts - left.attempts || right.made - left.made)
      .slice(0, 5);
  }, [shots]);

  const recentShots = useMemo(() => {
    return [...shots]
      .sort((left, right) => {
        const dateCompare = (right.game_date ?? "").localeCompare(left.game_date ?? "");
        if (dateCompare !== 0) return dateCompare;
        const periodCompare = (right.period ?? 0) - (left.period ?? 0);
        if (periodCompare !== 0) return periodCompare;
        return parseClockToSeconds(left.clock) - parseClockToSeconds(right.clock);
      })
      .slice(0, 8);
  }, [shots]);

  if (shots.length === 0) {
    return null;
  }

  return (
    <div className="mt-6 space-y-4 border-t border-[rgba(25,52,42,0.08)] pt-5">
      <div>
        <p className="bip-kicker mb-2">Shot Context</p>
        <h4 className="text-base font-semibold text-[var(--foreground)]">
          What this filtered shot diet is made of
        </h4>
      </div>

      <div className="grid gap-3 lg:grid-cols-[0.95fr,1.05fr]">
        <div className="space-y-3 rounded-[1.4rem] border border-[rgba(25,52,42,0.12)] bg-[rgba(255,255,255,0.62)] p-4">
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
            Top Actions
          </p>
          <div className="space-y-3">
            {topActions.map((action) => {
              const fgPct = action.attempts > 0 ? (action.made / action.attempts) * 100 : null;
              return (
                <div key={action.label} className="space-y-1.5">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-medium text-[var(--foreground)]">{action.label}</span>
                    <span className="text-xs text-[var(--muted)] tabular-nums">
                      {action.attempts} FGA · {fgPct != null ? `${fgPct.toFixed(0)}% FG` : "—"}
                    </span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-[rgba(25,52,42,0.08)]">
                    <div
                      className="h-full rounded-full bg-[linear-gradient(90deg,var(--accent),var(--signal))]"
                      style={{ width: `${Math.max(8, action.freq * 100)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="space-y-3 rounded-[1.4rem] border border-[rgba(25,52,42,0.12)] bg-[rgba(255,255,255,0.62)] p-4">
          <div className="flex items-center justify-between gap-3">
            <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
              Recent Filtered Shots
            </p>
            <span className="text-xs text-[var(--muted)]">Open any row in Game Explorer</span>
          </div>
          <div className="space-y-2">
            {recentShots.map((shot, index) => {
              const href = buildGameExplorerHref(shot, season, index);
              const contextBits = [
                shot.game_date,
                shot.period != null ? `Q${shot.period}` : null,
                shot.clock ?? null,
              ].filter(Boolean);
              return (
                <div
                  key={`${shot.game_id ?? "shot"}-${shot.shot_event_id ?? index}`}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-[1rem] border border-[rgba(25,52,42,0.08)] bg-[rgba(255,255,255,0.78)] px-3 py-2"
                >
                  <div>
                    <p className="text-sm font-medium text-[var(--foreground)]">
                      {shot.action_type || "Shot attempt"}
                    </p>
                    <p className="text-xs text-[var(--muted)]">
                      {contextBits.join(" · ")}
                      {shot.zone_basic ? ` · ${shot.zone_basic}` : ""}
                      {shot.distance ? ` · ${shot.distance} ft` : ""}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] ${linkageTone(shot.linkage_mode)}`}>
                      {linkageLabel(shot.linkage_mode)}
                    </span>
                    <span
                      className={`rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] ${
                        shot.shot_made
                          ? "bg-[rgba(33,72,59,0.12)] text-[var(--accent-strong)]"
                          : "bg-[rgba(159,63,49,0.12)] text-[var(--danger-ink)]"
                      }`}
                    >
                      {shot.shot_made ? "Made" : "Missed"}
                    </span>
                    {href ? (
                      <Link
                        href={href}
                        className="rounded-full border border-[rgba(25,52,42,0.1)] bg-[rgba(255,255,255,0.92)] px-3 py-1.5 text-xs font-medium text-[var(--foreground)] transition-colors hover:border-[rgba(25,52,42,0.2)] hover:bg-white"
                      >
                        Open in Game Explorer
                      </Link>
                    ) : (
                      <span className="text-xs text-[var(--muted)]">No game link</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
