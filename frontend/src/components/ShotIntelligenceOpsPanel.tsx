"use client";

import { useState } from "react";
import useSWR from "swr";
import {
  getShotIntelligenceOps,
  refreshShotQualityBaseline,
  refreshStaleShotPlayers,
} from "@/lib/api";
import type {
  ShotIntelligenceOpsResponse,
  ShotIntelligenceOpsTeam,
} from "@/lib/types";

interface Props {
  season: string;
  seasonType?: string;
}

const READINESS_TONE: Record<ShotIntelligenceOpsTeam["readiness"], string> = {
  ready: "bg-emerald-50 text-emerald-800 border-emerald-200 dark:bg-emerald-950/30 dark:text-emerald-300",
  partial: "bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-950/30 dark:text-amber-300",
  stale: "bg-orange-50 text-orange-800 border-orange-200 dark:bg-orange-950/30 dark:text-orange-300",
  missing: "bg-gray-100 text-gray-700 border-gray-200 dark:bg-gray-800 dark:text-gray-300",
};

const BASELINE_TONE: Record<string, string> = {
  ready: "bg-emerald-50 text-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-300",
  stale: "bg-orange-50 text-orange-800 dark:bg-orange-950/30 dark:text-orange-300",
  missing: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
};

function formatTs(iso?: string | null): string {
  if (!iso) return "never";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export default function ShotIntelligenceOpsPanel({ season, seasonType = "Regular Season" }: Props) {
  const { data, isLoading, mutate } = useSWR<ShotIntelligenceOpsResponse>(
    season ? ["shot-intel-ops", season, seasonType] : null,
    () => getShotIntelligenceOps(season, seasonType)
  );

  const [busy, setBusy] = useState<"baseline" | "stale" | null>(null);
  const [flash, setFlash] = useState<string | null>(null);

  const handleRefreshBaseline = async () => {
    setBusy("baseline");
    setFlash(null);
    try {
      const next = await refreshShotQualityBaseline(season, seasonType);
      await mutate(next, { revalidate: false });
      setFlash(`Baseline refreshed (sample n=${next.baseline.sample_n.toLocaleString()}).`);
    } catch (err) {
      setFlash(`Baseline refresh failed: ${(err as Error).message}`);
    } finally {
      setBusy(null);
    }
  };

  const handleRefreshStale = async () => {
    setBusy("stale");
    setFlash(null);
    try {
      const result = await refreshStaleShotPlayers(season, seasonType, 40);
      setFlash(`${result.queued} stale-player refresh jobs enqueued.`);
      await mutate();
    } catch (err) {
      setFlash(`Stale refresh failed: ${(err as Error).message}`);
    } finally {
      setBusy(null);
    }
  };

  if (!season) {
    return (
      <div className="rounded-xl border border-dashed border-gray-300 p-4 text-sm text-gray-500 dark:border-gray-700">
        Select a season to view Shot Intelligence ops.
      </div>
    );
  }

  return (
    <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-900">
      <header className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Shot Intelligence Ops · {season}
          </h2>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Roster-wide shot lab readiness · methodology {data?.methodology_version ?? "shot_quality_v2"}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            disabled={busy !== null || isLoading}
            onClick={handleRefreshBaseline}
            className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-800 hover:bg-emerald-100 disabled:opacity-50 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-300"
          >
            {busy === "baseline" ? "Refreshing..." : "Refresh baseline"}
          </button>
          <button
            type="button"
            disabled={busy !== null || isLoading || (data?.stale_players.length ?? 0) === 0}
            onClick={handleRefreshStale}
            className="rounded-lg border border-orange-200 bg-orange-50 px-3 py-1.5 text-xs font-semibold text-orange-800 hover:bg-orange-100 disabled:opacity-50 dark:border-orange-900 dark:bg-orange-950/30 dark:text-orange-300"
          >
            {busy === "stale" ? "Queuing..." : `Refresh stale players (${data?.stale_players.length ?? 0})`}
          </button>
        </div>
      </header>

      {flash && (
        <div className="mb-3 rounded-lg bg-gray-50 px-3 py-2 text-xs text-gray-700 dark:bg-gray-800 dark:text-gray-300">
          {flash}
        </div>
      )}

      {isLoading ? (
        <div className="text-sm text-gray-500 dark:text-gray-400">Loading ops…</div>
      ) : !data ? (
        <div className="text-sm text-gray-500 dark:text-gray-400">No ops data available.</div>
      ) : (
        <div className="space-y-5">
          <div className="grid gap-3 sm:grid-cols-3">
            <div className={`rounded-xl border p-3 ${BASELINE_TONE[data.baseline.status] ?? BASELINE_TONE.missing}`}>
              <p className="text-[10px] font-semibold uppercase tracking-widest">Baseline</p>
              <p className="mt-1 text-sm font-semibold capitalize">{data.baseline.status}</p>
              <p className="mt-1 text-[11px] opacity-80">
                n={data.baseline.sample_n.toLocaleString()} · {formatTs(data.baseline.computed_at)}
              </p>
            </div>
            <div className="rounded-xl border border-gray-200 p-3 dark:border-gray-700">
              <p className="text-[10px] font-semibold uppercase tracking-widest text-gray-500">Roster</p>
              <p className="mt-1 text-sm font-semibold text-gray-900 dark:text-gray-100">
                {data.totals.roster ?? 0} players
              </p>
              <p className="mt-1 text-[11px] text-gray-500">
                ready {data.totals.ready ?? 0} · stale {data.totals.stale ?? 0} · missing {data.totals.missing ?? 0}
              </p>
            </div>
            <div className="rounded-xl border border-gray-200 p-3 dark:border-gray-700">
              <p className="text-[10px] font-semibold uppercase tracking-widest text-gray-500">Missing context fields</p>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {Object.entries(data.missing_context_histogram).length === 0 ? (
                  <span className="text-xs text-gray-500">none</span>
                ) : (
                  Object.entries(data.missing_context_histogram)
                    .sort((a, b) => b[1] - a[1])
                    .slice(0, 6)
                    .map(([field, count]) => (
                      <span key={field} className="rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-medium text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                        {field} · {count}
                      </span>
                    ))
                )}
              </div>
            </div>
          </div>

          <div>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-widest text-gray-500">Teams</h3>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {data.teams.map((team) => (
                <div
                  key={team.team_id}
                  className={`rounded-xl border p-3 ${READINESS_TONE[team.readiness]}`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold">{team.team_abbreviation}</span>
                    <span className="text-[10px] font-semibold uppercase tracking-wider">{team.readiness}</span>
                  </div>
                  <p className="mt-1 text-[11px] opacity-90">
                    {team.ready_count}/{team.roster_size} ready · {team.stale_count} stale · {team.missing_count} missing
                  </p>
                </div>
              ))}
            </div>
          </div>

          {data.stale_players.length > 0 && (
            <div>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-widest text-gray-500">
                Stale / missing players ({data.stale_players.length})
              </h3>
              <ul className="divide-y divide-gray-200 rounded-xl border border-gray-200 bg-gray-50 dark:divide-gray-700 dark:border-gray-700 dark:bg-gray-900">
                {data.stale_players.slice(0, 12).map((p) => (
                  <li key={p.player_id} className="flex items-center justify-between px-3 py-2 text-xs">
                    <div>
                      <span className="font-semibold text-gray-900 dark:text-gray-100">{p.player_name}</span>
                      <span className="ml-2 text-gray-500">{p.team_abbreviation ?? "—"}</span>
                    </div>
                    <div className="flex items-center gap-2 text-gray-500">
                      <span className="uppercase tracking-wider">{p.state}</span>
                      <span>· {formatTs(p.last_synced_at)}</span>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
