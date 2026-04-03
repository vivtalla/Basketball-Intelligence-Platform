"use client";

import { useEffect, useMemo, useState } from "react";
import { useSWRConfig } from "swr";
import {
  useWarehouseJobSummary,
  useWarehouseSeasonHealth,
} from "@/hooks/usePlayerStats";
import {
  queueCurrentSeason,
  queueSeasonBackfill,
  resetStaleWarehouseJobs,
  retryFailedJobs,
  runNextWarehouseJob,
} from "@/lib/api";
import type {
  IngestionJobResponse,
  SourceRunResponse,
  WarehouseJobTypeSummary,
} from "@/lib/types";

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

const POLL_INTERVAL_MS = 15000;

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
  if (status === "queued") return "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300";
  return "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400";
}

function fmtTs(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function summarizeJobType(jobType: WarehouseJobTypeSummary): string {
  const parts: string[] = [];
  if (jobType.queued) parts.push(`${jobType.queued} queued`);
  if (jobType.running) parts.push(`${jobType.running} running`);
  if (jobType.failed) parts.push(`${jobType.failed} failed`);
  if (jobType.complete) parts.push(`${jobType.complete} complete`);
  return parts.join(" • ") || "idle";
}

export default function WarehousePipelinePanel({ season }: Props) {
  const { data: health, error, isLoading, mutate } = useWarehouseSeasonHealth(season);
  const { data: summary, mutate: mutateSummary } = useWarehouseJobSummary(season);
  const { mutate: globalMutate } = useSWRConfig();

  const [actionMsg, setActionMsg] = useState<string | null>(null);
  const [actionErr, setActionErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [runsExpanded, setRunsExpanded] = useState(false);
  const [failedExpanded, setFailedExpanded] = useState(false);
  const [queueExpanded, setQueueExpanded] = useState(true);
  const [stalledExpanded, setStalledExpanded] = useState(false);
  const [autoPollEnabled, setAutoPollEnabled] = useState(true);

  async function refreshWarehouseViews() {
    await Promise.all([
      mutate(),
      mutateSummary(),
      globalMutate("warehouse-jobs-all"),
      globalMutate(`warehouse-jobs-failed-${season}`),
      globalMutate(`warehouse-job-summary-${season}`),
      globalMutate(`warehouse-readiness-${season}`),
      globalMutate(`pbp-dashboard-${season}`),
      globalMutate("pbp-dashboard-seasons"),
    ]);
  }

  const total = health?.total_games ?? 0;
  const failedJobTypes = useMemo(
    () => (summary?.job_types ?? []).filter((jobType) => jobType.failed > 0),
    [summary]
  );
  const activeJobTypes = useMemo(
    () =>
      (summary?.job_types ?? []).filter(
        (jobType) => jobType.queued > 0 || jobType.running > 0 || jobType.failed > 0
      ),
    [summary]
  );

  const isCurrentSeason = (() => {
    const parts = season.split("-");
    if (parts.length < 2) return false;
    const endYear = parseInt(parts[1], 10) + 2000;
    return endYear >= new Date().getFullYear();
  })();

  const isPipelineActive =
    (health?.pending_jobs ?? 0) > 0 ||
    (health?.running_jobs ?? 0) > 0 ||
    (summary?.stalled_running_count ?? 0) > 0;

  useEffect(() => {
    if (!autoPollEnabled || !season || !isPipelineActive) return;
    const intervalId = window.setInterval(() => {
      void Promise.all([
        mutate(),
        mutateSummary(),
        globalMutate(`pbp-dashboard-${season}`),
        globalMutate("pbp-dashboard-seasons"),
        globalMutate(`warehouse-readiness-${season}`),
      ]);
    }, POLL_INTERVAL_MS);
    return () => window.clearInterval(intervalId);
  }, [autoPollEnabled, globalMutate, isPipelineActive, mutate, mutateSummary, season]);

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
        setActionMsg(`${label}: ${res.queued} job${res.queued !== 1 ? "s" : ""} affected`);
      } else if ("status" in res && res.status !== undefined) {
        setActionMsg(`${label}: ${res.status}`);
      } else {
        setActionMsg(`${label}: done`);
      }
      await refreshWarehouseViews();
    } catch (e: unknown) {
      setActionErr(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  const hasFailedJobs = (health?.failed_jobs ?? 0) > 0 || failedJobTypes.length > 0;
  const recentFailedJobs = summary?.recent_failed_jobs ?? [];
  const stalledJobs = summary?.stalled_running_jobs ?? [];

  return (
    <section className="rounded-xl border border-gray-200 bg-white p-5 space-y-5 dark:border-gray-700 dark:bg-gray-900">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-700 dark:text-gray-300">
            Warehouse Pipeline — {season}
          </h2>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Shared queue health, recovery controls, and live ingest progress for the selected season.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setAutoPollEnabled((value) => !value)}
          className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
            autoPollEnabled
              ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300"
              : "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300"
          }`}
        >
          Auto-poll {autoPollEnabled ? "on" : "off"}
        </button>
      </div>

      {autoPollEnabled && isPipelineActive && (
        <div className="rounded-lg border border-blue-100 bg-blue-50 px-3 py-2 text-xs text-blue-700 dark:border-blue-900/40 dark:bg-blue-950/20 dark:text-blue-300">
          Auto-refresh is active while jobs are queued or running. Coverage cards will update every{" "}
          {Math.round(POLL_INTERVAL_MS / 1000)} seconds.
        </div>
      )}

      {summary?.global_request_throttle && (
        <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-xs text-gray-600 dark:border-gray-800 dark:bg-gray-950 dark:text-gray-300">
          Shared throttle: next request available {summary.global_request_throttle.seconds_until_available > 0.05 ? "in" : "at"}{" "}
          {summary.global_request_throttle.seconds_until_available > 0.05
            ? `${summary.global_request_throttle.seconds_until_available.toFixed(1)}s`
            : fmtTs(summary.global_request_throttle.available_at)}
          . Last outbound NBA request {fmtTs(summary.global_request_throttle.last_request_at)}.
        </div>
      )}

      {isLoading && (
        <div className="space-y-3 animate-pulse">
          <div className="flex gap-2">
            {PIPELINE_STEPS.map((step) => (
              <div key={step.key} className="h-14 flex-1 rounded-lg bg-gray-100 dark:bg-gray-800" />
            ))}
          </div>
          <div className="flex gap-3">
            <div className="h-8 w-28 rounded bg-gray-100 dark:bg-gray-800" />
            <div className="h-8 w-28 rounded bg-gray-100 dark:bg-gray-800" />
            <div className="h-8 w-28 rounded bg-gray-100 dark:bg-gray-800" />
          </div>
        </div>
      )}

      {error && (
        <p className="text-sm text-red-600 dark:text-red-400">
          Failed to load warehouse health.
        </p>
      )}

      {!isLoading && !error && health && health.total_games === 0 && (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400">
          No warehouse games found for {season}.{" "}
          <button
            disabled={busy}
            onClick={() => handleAction(() => queueSeasonBackfill(season), "Backfill")}
            className="text-blue-600 underline disabled:opacity-50 dark:text-blue-400"
          >
            Queue a backfill
          </button>{" "}
          to start ingestion.
        </div>
      )}

      {!isLoading && !error && health && health.total_games > 0 && (
        <>
          <div className="flex gap-2">
            {PIPELINE_STEPS.map((step) => {
              const count = health[step.key as StepKey] as number;
              const pct = total > 0 ? Math.round((count / total) * 100) : 0;
              return (
                <div key={step.key} className="flex flex-1 flex-col gap-1">
                  <div className="h-2 overflow-hidden rounded-full bg-gray-100 dark:bg-gray-800">
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

          <div className="flex flex-wrap items-center gap-3">
            <div className="flex flex-wrap gap-3 text-sm">
              <span className="rounded bg-gray-100 px-2 py-1 text-gray-600 dark:bg-gray-800 dark:text-gray-300">
                <span className="font-medium">{health.pending_jobs}</span> pending
              </span>
              <span className="rounded bg-blue-50 px-2 py-1 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300">
                <span className="font-medium">{health.running_jobs}</span> running
              </span>
              {hasFailedJobs && (
                <span className="rounded bg-red-50 px-2 py-1 text-red-700 dark:bg-red-900/20 dark:text-red-300">
                  <span className="font-medium">{health.failed_jobs}</span> failed
                </span>
              )}
              {(summary?.stalled_running_count ?? 0) > 0 && (
                <span className="rounded bg-amber-50 px-2 py-1 text-amber-700 dark:bg-amber-900/20 dark:text-amber-300">
                  <span className="font-medium">{summary?.stalled_running_count}</span> stalled
                </span>
              )}
            </div>

            <div className="ml-auto flex flex-wrap gap-2">
              <button
                disabled={busy}
                onClick={() => handleAction(() => runNextWarehouseJob(season), "Run next")}
                className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
              >
                Run Next Job
              </button>
              {isCurrentSeason && (
                <button
                  disabled={busy}
                  onClick={() => handleAction(() => queueCurrentSeason(season), "Daily sync")}
                  className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
                >
                  Sync Today
                </button>
              )}
              <button
                disabled={busy}
                onClick={() => handleAction(() => queueSeasonBackfill(season), "Backfill")}
                className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
              >
                Queue Backfill
              </button>
              {hasFailedJobs && (
                <button
                  disabled={busy}
                  onClick={() => handleAction(() => retryFailedJobs(season), "Retry failed")}
                  className="rounded-lg border border-red-300 px-3 py-1.5 text-xs text-red-700 transition-colors hover:bg-red-50 disabled:opacity-50 dark:border-red-700 dark:text-red-300 dark:hover:bg-red-900/20"
                >
                  Retry Failed
                </button>
              )}
              {(summary?.stalled_running_count ?? 0) > 0 && (
                <button
                  disabled={busy}
                  onClick={() => handleAction(() => resetStaleWarehouseJobs(season), "Reset stale")}
                  className="rounded-lg border border-amber-300 px-3 py-1.5 text-xs text-amber-700 transition-colors hover:bg-amber-50 disabled:opacity-50 dark:border-amber-700 dark:text-amber-300 dark:hover:bg-amber-900/20"
                >
                  Reset Stale
                </button>
              )}
            </div>
          </div>

          {actionMsg && (
            <p className="rounded px-3 py-2 text-xs text-emerald-700 bg-emerald-50 dark:bg-emerald-900/20 dark:text-emerald-400">
              {actionMsg}
            </p>
          )}
          {actionErr && (
            <p className="rounded px-3 py-2 text-xs text-red-700 bg-red-50 dark:bg-red-900/20 dark:text-red-400">
              {actionErr}
            </p>
          )}

          {summary && (
            <div>
              <button
                onClick={() => setQueueExpanded((value) => !value)}
                className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              >
                <span>{queueExpanded ? "▾" : "▸"}</span>
                Queue breakdown ({activeJobTypes.length || 0} active job types)
              </button>
              {queueExpanded && (
                <div className="mt-2 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                  {activeJobTypes.length > 0 ? (
                    activeJobTypes.map((jobType) => (
                      <div
                        key={jobType.job_type}
                        className="rounded-lg border border-gray-200 bg-gray-50 p-3 dark:border-gray-800 dark:bg-gray-950"
                      >
                        <div className="font-mono text-xs text-gray-700 dark:text-gray-200">
                          {jobType.job_type}
                        </div>
                        <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                          {summarizeJobType(jobType)}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 text-xs text-gray-500 dark:border-gray-800 dark:bg-gray-950 dark:text-gray-400">
                      No active queued, running, or failed job types for this season.
                    </div>
                  )}
                  {summary.oldest_queued_job && (
                    <div className="rounded-lg border border-blue-100 bg-blue-50 p-3 dark:border-blue-900/40 dark:bg-blue-950/20">
                      <div className="text-xs font-medium uppercase tracking-wide text-blue-700 dark:text-blue-300">
                        Oldest queued job
                      </div>
                      <div className="mt-2 font-mono text-xs text-gray-700 dark:text-gray-200">
                        {summary.oldest_queued_job.job_type}
                      </div>
                      <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                        {summary.oldest_queued_job.job_key}
                      </div>
                      <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                        Ready since {fmtTs(summary.oldest_queued_job.run_after)}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {hasFailedJobs && (
            <div>
              <button
                onClick={() => setFailedExpanded((value) => !value)}
                className="flex items-center gap-1 text-xs text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-200"
              >
                <span>{failedExpanded ? "▾" : "▸"}</span>
                Failed jobs ({health.failed_jobs})
              </button>
              {failedExpanded && (
                <div className="mt-2 space-y-3">
                  {failedJobTypes.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {failedJobTypes.map((jobType) => (
                        <span
                          key={jobType.job_type}
                          className="rounded-full bg-red-50 px-2.5 py-1 text-xs text-red-700 dark:bg-red-900/20 dark:text-red-300"
                        >
                          {jobType.job_type}: {jobType.failed}
                        </span>
                      ))}
                    </div>
                  )}
                  <div className="overflow-hidden rounded-lg border border-red-100 dark:border-red-900/40">
                    <table className="w-full text-xs">
                      <thead className="bg-red-50 text-gray-500 dark:bg-red-900/20 dark:text-gray-400">
                        <tr>
                          <th className="px-3 py-2 text-left font-medium">Type</th>
                          <th className="px-3 py-2 text-left font-medium">Key</th>
                          <th className="px-3 py-2 text-left font-medium">Error</th>
                          <th className="px-3 py-2 text-right font-medium">Attempts</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-red-100 dark:divide-red-900/30">
                        {recentFailedJobs.length > 0 ? (
                          recentFailedJobs.map((job: IngestionJobResponse) => (
                            <tr key={job.id} className="bg-white dark:bg-gray-900">
                              <td className="px-3 py-2 font-mono text-gray-600 dark:text-gray-300">
                                {job.job_type}
                              </td>
                              <td className="max-w-[140px] truncate px-3 py-2 text-gray-500 dark:text-gray-400">
                                {job.job_key}
                              </td>
                              <td
                                className="max-w-[260px] truncate px-3 py-2 text-red-600 dark:text-red-400"
                                title={job.last_error ?? undefined}
                              >
                                {job.last_error ?? "—"}
                              </td>
                              <td className="px-3 py-2 text-right text-gray-500 dark:text-gray-400">
                                {job.attempt_count}
                              </td>
                            </tr>
                          ))
                        ) : (
                          <tr className="bg-white dark:bg-gray-900">
                            <td colSpan={4} className="px-3 py-3 text-gray-500 dark:text-gray-400">
                              No recent failed jobs were returned for this season.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {(summary?.stalled_running_count ?? 0) > 0 && (
            <div>
              <button
                onClick={() => setStalledExpanded((value) => !value)}
                className="flex items-center gap-1 text-xs text-amber-700 hover:text-amber-900 dark:text-amber-300 dark:hover:text-amber-100"
              >
                <span>{stalledExpanded ? "▾" : "▸"}</span>
                Stalled running jobs ({summary?.stalled_running_count})
              </button>
              {stalledExpanded && (
                <div className="mt-2 overflow-hidden rounded-lg border border-amber-100 dark:border-amber-900/40">
                  <table className="w-full text-xs">
                    <thead className="bg-amber-50 text-gray-500 dark:bg-amber-900/20 dark:text-gray-400">
                      <tr>
                        <th className="px-3 py-2 text-left font-medium">Type</th>
                        <th className="px-3 py-2 text-left font-medium">Key</th>
                        <th className="px-3 py-2 text-right font-medium">Lease expired</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-amber-100 dark:divide-amber-900/30">
                      {stalledJobs.map((job) => (
                        <tr key={job.id} className="bg-white dark:bg-gray-900">
                          <td className="px-3 py-2 font-mono text-gray-600 dark:text-gray-300">
                            {job.job_type}
                          </td>
                          <td className="max-w-[180px] truncate px-3 py-2 text-gray-500 dark:text-gray-400">
                            {job.job_key}
                          </td>
                          <td className="px-3 py-2 text-right text-gray-500 dark:text-gray-400">
                            {fmtTs(job.leased_until)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {health.latest_runs.length > 0 && (
            <div>
              <button
                onClick={() => setRunsExpanded((value) => !value)}
                className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              >
                <span>{runsExpanded ? "▾" : "▸"}</span>
                Recent runs ({health.latest_runs.length})
              </button>
              {runsExpanded && (
                <div className="mt-2 overflow-hidden rounded-lg border border-gray-100 dark:border-gray-800">
                  <table className="w-full text-xs">
                    <thead className="bg-gray-50 text-gray-500 dark:bg-gray-800 dark:text-gray-400">
                      <tr>
                        <th className="px-3 py-2 text-left font-medium">Source</th>
                        <th className="px-3 py-2 text-left font-medium">Entity</th>
                        <th className="px-3 py-2 text-left font-medium">Status</th>
                        <th className="px-3 py-2 text-right font-medium">Written</th>
                        <th className="px-3 py-2 text-right font-medium">Started</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                      {health.latest_runs.slice(0, 5).map((run: SourceRunResponse) => (
                        <tr key={run.id} className="bg-white dark:bg-gray-900">
                          <td className="px-3 py-2 font-mono text-gray-600 dark:text-gray-300">
                            {run.source}
                          </td>
                          <td className="max-w-[120px] truncate px-3 py-2 text-gray-500 dark:text-gray-400">
                            {run.entity_id}
                          </td>
                          <td className="px-3 py-2">
                            <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${runStatusBadge(run.status)}`}>
                              {run.status}
                            </span>
                          </td>
                          <td className="px-3 py-2 text-right text-gray-500 dark:text-gray-400">
                            {run.records_written}
                          </td>
                          <td className="px-3 py-2 text-right text-gray-400 dark:text-gray-500">
                            {fmtTs(run.started_at)}
                          </td>
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
