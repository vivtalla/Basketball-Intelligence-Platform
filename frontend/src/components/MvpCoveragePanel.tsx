"use client";

import { useState } from "react";
import { useMvpCoverage } from "@/hooks/usePlayerStats";
import { queueMvpSnapshot } from "@/lib/api";

function statusTone(status?: string) {
  if (status === "ready") return "bg-emerald-100 text-emerald-700";
  if (status === "partial") return "bg-amber-100 text-amber-700";
  return "bg-gray-100 text-gray-600";
}

export default function MvpCoveragePanel({ season }: { season: string }) {
  const { data, isLoading, mutate } = useMvpCoverage(season, { top: 10, minGp: 20 });
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleQueueSnapshot() {
    setBusy(true);
    setMessage(null);
    try {
      const response = await queueMvpSnapshot(season);
      setMessage(`Queued ${response.queued} MVP snapshot job.`);
      await mutate();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not queue MVP snapshot.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-xl border border-gray-200 bg-white p-5 space-y-5 dark:border-gray-700 dark:bg-gray-900">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-700 dark:text-gray-300">MVP Coverage - {season}</h2>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Source health for MVP snapshots, weekly timeline inputs, impact, Gravity, clutch, and opponent context.
          </p>
        </div>
        <button
          type="button"
          onClick={handleQueueSnapshot}
          disabled={busy}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
        >
          {busy ? "Queueing..." : "Queue MVP snapshot"}
        </button>
      </div>

      {message && <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-xs text-gray-600">{message}</div>}
      {isLoading && <div className="rounded-lg bg-gray-50 p-4 text-sm text-gray-500">Loading MVP coverage...</div>}

      {data && (
        <>
          <div className="grid gap-3 md:grid-cols-3">
            {data.domains.map((domain) => (
              <div key={domain.key} className="rounded-lg border border-gray-200 p-4 dark:border-gray-800">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">{domain.label}</p>
                  <span className={`rounded-full px-2 py-1 text-[10px] font-semibold uppercase ${statusTone(domain.status)}`}>{domain.status}</span>
                </div>
                <p className="mt-2 text-lg font-semibold text-gray-900 dark:text-gray-100">{domain.ready_count}/{domain.total_count}</p>
                <p className="mt-1 text-xs leading-5 text-gray-500 dark:text-gray-400">{domain.detail}</p>
              </div>
            ))}
          </div>

          <div className="rounded-lg border border-gray-200 p-4 dark:border-gray-800">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Candidate warnings</p>
            <div className="mt-3 grid gap-2 md:grid-cols-2">
              {data.candidates.map((candidate) => (
                <div key={candidate.player_id} className="rounded-lg bg-gray-50 p-3 text-sm dark:bg-gray-950">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-gray-900 dark:text-gray-100">#{candidate.rank} {candidate.player_name}</span>
                    <span className="text-xs text-gray-500">{candidate.warning_count} warnings</span>
                  </div>
                  <p className="mt-1 text-xs text-gray-500">{candidate.warnings[0] ?? "Coverage looks stable."}</p>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </section>
  );
}
