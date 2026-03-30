"use client";

import { useState } from "react";
import { useSWRConfig } from "swr";
import { useWarehouseSeasonHealth, useWarehouseJobs } from "@/hooks/usePlayerStats";
import {
  queueSeasonBackfill,
  queueCurrentSeason,
  retryFailedJobs,
  runNextWarehouseJob,
} from "@/lib/api";
import type { IngestionJobResponse, SourceRunResponse } from "@/lib/types";

interface Props {
  season: string;
}

const PIPELINE_STEPS = [
  { key: "scheduled_games" as const, label: "Scheduled" },
  { key: "games_with_box_score" as const, label: "Box Score" },
  { key: "games_with_pbp_payload" as const, label: "PBP Payload" },
  { key: "games_with_parsed_pbp" as const, label: "Parsed PBP" },
  { key: "games_materialized" as const, label: "Materialized" },
] as const;

type StepKey = typeof PIPELINE_STEPS[number]["key"];

function stepColor(count: number, total: number): string {
  if (total === 0 || count === 0) return "bg-gray-200 dark:bg-gray-700";
  if (count >= total) return "bg-emerald-500";
  return "bg-amber-400";
}

function stepTextColor(count: number, total: number): string {
  if (total === 0 || count === 0) return "text-gray-400 dark:text-gray-500";
  if (count >= total) return "text-emerald-700 dark:text-emerald-400";
  return "text-amber-700 dark:text-amber-400";
}

function runStatusBadge(status: string): string {
  if (status === "complete") return "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300";
  if (status === "failed") return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300";
  if (status === "running") return "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300";
  return "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400";
}

function fmtTs(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export default function WarehousePipelinePanel({ season }: Props) {
  const { data: health, error, isLoading, mutate } = useWarehouseSeasonHealth(season);
  const { data: failedJobs } = useWarehouseJobs("failed", season);
  const { mutate: globalMutate } = useSWRConfig();

  const [actionMsg, setActionMsg] = useState<string | null>(null);
  const [actionErr, setActionErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [runsExpanded, setRunsExpanded] = useState(false);
  const [failedExpanded, setFailedExpanded] = useState(false);

  async function handleAction(
    fn: () => Promise<{ queued?: number; status?: string }>,
    label: string
  ) {
    setBusy(true);
    setActionMsg(null);
    setActionErr(null);
    try {
      const res = await fn();
      if ("queued" in res && res.queued !== undefined) {
        setActionMsg(`${label}: ${res.queued} job${res.queued !== 1 ? "s" : ""} queued`);
      } else if ("status" in res && res.status !== undefined) {
        setActionMsg(`${label}: ${res.status}`);
      } else {
        setActionMsg(`${label}: done`);
      }
      await mutate();
      await globalMutate("warehouse-jobs-all");
      await globalMutate(`warehouse-jobs-failed-${season}`);
      await globalMutate(`pbp-dashboard-${season}`);
      await globalMutate("pbp-dashboard-seasons");
    } catch (e: unknown) {
      setActionErr(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  const total = health?.total_games ?? 0;

  // "Sync Today" queues jobs for the last 3 calendar days — only meaningful
  // for the active NBA season. Derive from season string end year vs current year.
  const isCurrentSeason = (() => {
    const parts = season.split("-");
    if (parts.length < 2) return false;
    const endYear = parseInt(parts[1], 10) + 2000;
    return endYear >= new Date().getFullYear();
  })();

  // Failed jobs scoped to this season for the details panel
  const seasonFailedJobs = (failedJobs ?? []).filter(
    (j: IngestionJobResponse) => j.season === season
  );
  const hasFailedJobs = (health?.failed_jobs ?? 0) > 0;

  return (
    <section className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5 space-y-5">
      <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide">
        Warehouse Pipeline — {season}
      </h2>

      {/* Loading skeleton */}
      {isLoading && (
        <div className="space-y-3 animate-pulse">
          <div className="flex gap-2">
            {PIPELINE_STEPS.map((s) => (
              <div key={s.key} className="flex-1 h-14 rounded-lg bg-gray-100 dark:bg-gray-800" />
            ))}
          </div>
          <div className="flex gap-3">
            <div className="h-8 w-28 rounded bg-gray-100 dark:bg-gray-800" />
            <div className="h-8 w-28 rounded bg-gray-100 dark:bg-gray-800" />
            <div className="h-8 w-28 rounded bg-gray-100 dark:bg-gray-800" />
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <p className="text-sm text-red-600 dark:text-red-400">
          Failed to load warehouse health.
        </p>
      )}

      {/* Empty state */}
      {!isLoading && !error && health && health.total_games === 0 && (
        <div className="rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-4 text-sm text-gray-500 dark:text-gray-400">
          No warehouse games found for {season}.{" "}
          <button
            disabled={busy}
            onClick={() => handleAction(() => queueSeasonBackfill(season), "Backfill")}
            className="underline text-blue-600 dark:text-blue-400 disabled:opacity-50"
          >
            Queue a backfill
          </button>{" "}
          to start ingestion.
        </div>
      )}

      {/* Pipeline funnel */}
      {!isLoading && !error && health && health.total_games > 0 && (
        <>
          <div className="flex gap-2">
            {PIPELINE_STEPS.map((step) => {
              const count = health[step.key as StepKey] as number;
              const pct = total > 0 ? Math.round((count / total) * 100) : 0;
              return (
                <div key={step.key} className="flex-1 flex flex-col gap-1">
                  <div className="h-2 rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${stepColor(count, total)}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <div className={`text-xs font-medium ${stepTextColor(count, total)}`}>
                    {count}/{total}
                  </div>
                  <div className="text-xs text-gray-400 dark:text-gray-500">{step.label}</div>
                </div>
              );
            })}
          </div>

          {/* Job queue stats + actions */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex gap-3 text-sm">
              <span className="px-2 py-1 rounded bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300">
                <span className="font-medium">{health.pending_jobs}</span> pending
              </span>
              <span className="px-2 py-1 rounded bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300">
                <span className="font-medium">{health.running_jobs}</span> running
              </span>
              {hasFailedJobs && (
                <span className="px-2 py-1 rounded bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300">
                  <span className="font-medium">{health.failed_jobs}</span> failed
                </span>
              )}
            </div>

            <div className="flex gap-2 ml-auto flex-wrap">
              <button
                disabled={busy}
                onClick={() => handleAction(() => runNextWarehouseJob(season), "Run next")}
                title={`Dispatches the next pending job for ${season}`}
                className="text-xs px-3 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                Run Next Job
              </button>
              {isCurrentSeason && (
                <button
                  disabled={busy}
                  onClick={() => handleAction(() => queueCurrentSeason(season), "Daily sync")}
                  className="text-xs px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 transition-colors"
                >
                  Sync Today
                </button>
              )}
              <button
                disabled={busy}
                onClick={() => handleAction(() => queueSeasonBackfill(season), "Backfill")}
                className="text-xs px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 transition-colors"
              >
                Queue Backfill
              </button>
              {hasFailedJobs && (
                <button
                  disabled={busy}
                  onClick={() => handleAction(() => retryFailedJobs(season), "Retry failed")}
                  className="text-xs px-3 py-1.5 rounded-lg border border-red-300 dark:border-red-700 text-red-700 dark:text-red-300 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-50 transition-colors"
                >
                  Retry Failed
                </button>
              )}
            </div>
          </div>

          {/* Action feedback */}
          {actionMsg && (
            <p className="text-xs text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20 rounded px-3 py-2">
              {actionMsg}
            </p>
          )}
          {actionErr && (
            <p className="text-xs text-red-700 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded px-3 py-2">
              {actionErr}
            </p>
          )}

          {/* Failed jobs (collapsible) — only when there are failures */}
          {hasFailedJobs && seasonFailedJobs.length > 0 && (
            <div>
              <button
                onClick={() => setFailedExpanded((v) => !v)}
                className="text-xs text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-200 flex items-center gap-1"
              >
                <span>{failedExpanded ? "▾" : "▸"}</span>
                Failed jobs ({seasonFailedJobs.length})
              </button>
              {failedExpanded && (
                <div className="mt-2 rounded-lg border border-red-100 dark:border-red-900/40 overflow-hidden">
                  <table className="w-full text-xs">
                    <thead className="bg-red-50 dark:bg-red-900/20 text-gray-500 dark:text-gray-400">
                      <tr>
                        <th className="text-left px-3 py-2 font-medium">Type</th>
                        <th className="text-left px-3 py-2 font-medium">Key</th>
                        <th className="text-left px-3 py-2 font-medium">Error</th>
                        <th className="text-right px-3 py-2 font-medium">Attempts</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-red-100 dark:divide-red-900/30">
                      {seasonFailedJobs.slice(0, 10).map((job: IngestionJobResponse) => (
                        <tr key={job.id} className="bg-white dark:bg-gray-900">
                          <td className="px-3 py-2 font-mono text-gray-600 dark:text-gray-300 whitespace-nowrap">
                            {job.job_type}
                          </td>
                          <td className="px-3 py-2 text-gray-500 dark:text-gray-400 truncate max-w-[120px]">
                            {job.job_key}
                          </td>
                          <td className="px-3 py-2 text-red-600 dark:text-red-400 truncate max-w-[200px]" title={job.last_error ?? undefined}>
                            {job.last_error ?? "—"}
                          </td>
                          <td className="px-3 py-2 text-right text-gray-500 dark:text-gray-400">
                            {job.attempt_count}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Recent runs (collapsible) */}
          {health.latest_runs.length > 0 && (
            <div>
              <button
                onClick={() => setRunsExpanded((v) => !v)}
                className="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 flex items-center gap-1"
              >
                <span>{runsExpanded ? "▾" : "▸"}</span>
                Recent runs ({health.latest_runs.length})
              </button>
              {runsExpanded && (
                <div className="mt-2 rounded-lg border border-gray-100 dark:border-gray-800 overflow-hidden">
                  <table className="w-full text-xs">
                    <thead className="bg-gray-50 dark:bg-gray-800 text-gray-500 dark:text-gray-400">
                      <tr>
                        <th className="text-left px-3 py-2 font-medium">Source</th>
                        <th className="text-left px-3 py-2 font-medium">Entity</th>
                        <th className="text-left px-3 py-2 font-medium">Status</th>
                        <th className="text-right px-3 py-2 font-medium">Written</th>
                        <th className="text-right px-3 py-2 font-medium">Started</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                      {health.latest_runs.slice(0, 5).map((run: SourceRunResponse) => (
                        <tr key={run.id} className="bg-white dark:bg-gray-900">
                          <td className="px-3 py-2 font-mono text-gray-600 dark:text-gray-300">{run.source}</td>
                          <td className="px-3 py-2 text-gray-500 dark:text-gray-400 truncate max-w-[120px]">{run.entity_id}</td>
                          <td className="px-3 py-2">
                            <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${runStatusBadge(run.status)}`}>
                              {run.status}
                            </span>
                          </td>
                          <td className="px-3 py-2 text-right text-gray-500 dark:text-gray-400">{run.records_written}</td>
                          <td className="px-3 py-2 text-right text-gray-400 dark:text-gray-500">{fmtTs(run.started_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </section>
  );
}
