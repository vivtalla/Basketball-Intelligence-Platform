"use client";

import Image from "next/image";
import CareerArcChart from "@/components/CareerArcChart";
import { Stat, Pill } from "@/components/brand";
import type { PillTone } from "@/components/brand";
import { usePlayerLegacy } from "@/hooks/usePlayerLegacy";
import type { SeasonStats } from "@/lib/types";

interface LegacyTabProps {
  playerId: number;
  /** All regular-season seasons; reused by `<CareerArcChart>`. */
  seasons: SeasonStats[];
  birthDate?: string | null;
}

const PROJECTION_TONES: Record<string, PillTone> = {
  "Likely HOF": "accent",
  Borderline: "signal",
  Tracking: "default",
};

function formatTsDelta(delta: number | null): string {
  if (delta == null) return "—";
  const pp = (delta * 100);
  return `${pp >= 0 ? "+" : ""}${pp.toFixed(1)}pp`;
}

function formatTs(value: number | null): string {
  if (value == null) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

/**
 * Sprint 78 / CF3 — Career Hall of Fame view.
 *
 * Mounts on the player profile under a "Legacy" tab. Composes:
 * - Era-adjusted stat strip (PPG/RPG/APG/TS%)
 * - Career arc chart (reused from `CareerArcChart`) with milestone markers
 * - Era-peer grid
 * - HOF projection card (right rail on wide screens)
 */
export default function LegacyTab({ playerId, seasons, birthDate }: LegacyTabProps) {
  const { data, error, isLoading } = usePlayerLegacy(playerId);

  if (error) {
    return (
      <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface-alt)] p-6 text-sm text-[var(--muted)]">
        Could not load legacy data for this player.
      </div>
    );
  }

  if (isLoading || !data) {
    return (
      <div className="space-y-4">
        <div className="h-24 rounded-2xl bg-[var(--surface-alt)] animate-pulse" />
        <div className="h-72 rounded-2xl bg-[var(--surface-alt)] animate-pulse" />
        <div className="h-56 rounded-2xl bg-[var(--surface-alt)] animate-pulse" />
      </div>
    );
  }

  const { era_adjusted_summary: summary, milestones_achieved, next_milestone, era_peers, hof_projection } = data;

  // Build a compact map of season → milestone labels for the chart overlay.
  const milestoneSeasons = new Map<string, string[]>();
  for (const m of milestones_achieved) {
    const season = m.achieved_in_season ?? null;
    if (!season) continue;
    const arr = milestoneSeasons.get(season) ?? [];
    arr.push(m.milestone_label);
    milestoneSeasons.set(season, arr);
  }

  const projectionTone: PillTone = PROJECTION_TONES[hof_projection.label] ?? "default";

  return (
    <div className="space-y-6">
      {/* Era-adjusted summary strip */}
      <section>
        <p className="bip-kicker mb-2">Era-Adjusted Career Line</p>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat
            label="PPG (era-adj)"
            value={summary.pts_pg_era_adj ?? "—"}
            decimals={1}
            tone="default"
          />
          <Stat
            label="RPG"
            value={summary.reb_pg ?? "—"}
            decimals={1}
            tone="default"
          />
          <Stat
            label="APG"
            value={summary.ast_pg ?? "—"}
            decimals={1}
            tone="default"
          />
          <Stat
            label="TS% vs league"
            value={formatTsDelta(summary.ts_pct_delta_vs_league_avg)}
            tone="soft"
          >
            <div className="mt-1 font-mono text-[10px] uppercase opacity-70">
              {formatTs(summary.ts_pct)} career
            </div>
          </Stat>
        </div>
        <p className="mt-2 text-[11px] text-[var(--muted)]">
          {summary.games_played} GP · {summary.seasons_played} seasons · pace-normalized to league average
        </p>
      </section>

      {/* Career arc + milestone overlay + HOF projection card */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-3">
          <CareerArcChart seasons={seasons} birthDate={birthDate} />
          {milestoneSeasons.size > 0 && (
            <div className="rounded-[1.5rem] border border-[var(--border)] bg-[rgba(255,251,246,0.7)] p-4">
              <p className="bip-kicker mb-2">Milestone Markers</p>
              <ul className="flex flex-wrap gap-2">
                {[...milestoneSeasons.entries()].map(([season, labels]) => (
                  <li key={season} className="flex items-center gap-2">
                    <span
                      aria-hidden
                      className="inline-block h-2.5 w-2.5 rounded-full"
                      style={{ background: "var(--signal)" }}
                    />
                    <span className="text-xs font-medium text-[var(--foreground)]">
                      {season}
                    </span>
                    <span className="text-xs text-[var(--muted)]">
                      {labels.join(" · ")}
                    </span>
                  </li>
                ))}
              </ul>
              {next_milestone && (
                <p className="mt-3 text-xs text-[var(--muted)]">
                  Next: {next_milestone.milestone_label} —{" "}
                  {next_milestone.points_remaining.toLocaleString()} to go
                  {next_milestone.games_to_milestone != null
                    ? ` (~${next_milestone.games_to_milestone} games at current pace)`
                    : ""}
                </p>
              )}
            </div>
          )}
        </div>

        {/* HOF projection card (right rail) */}
        <aside className="lg:col-span-1">
          <div className="rounded-[1.75rem] border border-[var(--border)] bg-[linear-gradient(160deg,rgba(247,243,232,0.96),rgba(228,236,232,0.92))] p-5 shadow-[0_18px_48px_rgba(47,43,36,0.07)]">
            <p className="bip-kicker">Legacy Projection</p>
            <div className="mt-2 flex items-baseline gap-3">
              <span
                className="bip-display tabular-nums text-5xl font-bold text-[var(--foreground)]"
                style={{ fontVariantNumeric: "tabular-nums" }}
              >
                {hof_projection.score}
              </span>
              <Pill tone={projectionTone}>
                {hof_projection.label}
              </Pill>
            </div>
            {/* Score gauge */}
            <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-[rgba(47,43,36,0.08)]">
              <div
                className="h-full rounded-full"
                style={{
                  width: `${Math.max(2, Math.min(100, hof_projection.score))}%`,
                  background:
                    hof_projection.label === "Likely HOF"
                      ? "var(--accent)"
                      : hof_projection.label === "Borderline"
                      ? "var(--signal)"
                      : "var(--muted)",
                }}
              />
            </div>
            {hof_projection.drivers.length > 0 && (
              <div className="mt-4">
                <p className="bip-kicker mb-2 text-[10px]">Top Drivers</p>
                <ul className="space-y-1.5">
                  {hof_projection.drivers.map((driver, idx) => (
                    <li
                      key={`${idx}-${driver}`}
                      className="text-sm text-[var(--foreground)]"
                    >
                      <span className="mr-1 text-[var(--signal-ink)]">▸</span>
                      {driver}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <p className="mt-4 text-[10px] text-[var(--muted)]">
              80+ Likely HOF · 50–79 Borderline · &lt;50 Tracking
            </p>
          </div>
        </aside>
      </div>

      {/* Era-peer grid */}
      <section>
        <p className="bip-kicker mb-2">All-Time Peer Cohort</p>
        {era_peers.length === 0 ? (
          <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface-alt)] p-5 text-sm text-[var(--muted)]">
            Not enough qualifying seasons to compute era peers yet.
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {era_peers.map((peer) => (
              <a
                key={peer.player_id}
                href={`/beta/players/${peer.player_id}`}
                className="group block rounded-[1.5rem] border border-[var(--border)] bg-[rgba(255,251,246,0.78)] p-4 transition-colors hover:bg-[rgba(255,251,246,1)]"
              >
                <div className="flex items-center gap-3">
                  <div className="relative h-12 w-12 shrink-0 overflow-hidden rounded-full bg-[var(--surface-alt)]">
                    {peer.headshot_url ? (
                      <Image
                        src={peer.headshot_url}
                        alt={peer.player_name}
                        fill
                        sizes="48px"
                        className="object-cover object-top"
                      />
                    ) : null}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-[var(--foreground)] group-hover:text-[var(--accent-ink)]">
                      {peer.player_name}
                    </p>
                    <p className="text-[11px] text-[var(--muted)]">
                      {peer.seasons_played} seasons · sim {peer.similarity_score.toFixed(1)}
                    </p>
                  </div>
                </div>
                <p className="mt-2 text-[11px] text-[var(--accent-strong)]">
                  {peer.comp_basis}
                </p>
              </a>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
