"use client";

import { useState } from "react";
import { syncPlayerPbp } from "@/lib/api";
import {
  usePlayerClutch,
  usePlayerOnOff,
  usePlayerPbpCoverage,
} from "@/hooks/usePlayerStats";

interface PlayerPbpInsightsProps {
  playerId: number;
  season: string | null;
}

function fmt(value: number | null | undefined, digits = 1): string {
  if (value == null) return "-";
  return value.toFixed(digits);
}

function fmtSigned(value: number | null | undefined, digits = 1): string {
  if (value == null) return "-";
  return `${value > 0 ? "+" : ""}${value.toFixed(digits)}`;
}

function MetricCard({
  label,
  value,
  sublabel,
  highlight,
}: {
  label: string;
  value: string;
  sublabel?: string;
  highlight?: boolean;
}) {
  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
      <div className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">{label}</div>
      <div className={`mt-1 text-2xl font-semibold tabular-nums ${highlight ? "text-blue-600 dark:text-blue-400" : ""}`}>{value}</div>
      {sublabel ? (
        <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">{sublabel}</div>
      ) : null}
    </div>
  );
}

function SmallMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs text-gray-500 dark:text-gray-400">{label}</span>
      <span className="text-sm font-semibold tabular-nums text-gray-900 dark:text-gray-100">{value}</span>
    </div>
  );
}

export default function PlayerPbpInsights({ playerId, season }: PlayerPbpInsightsProps) {
  const onOffQuery = usePlayerOnOff(playerId, season);
  const clutchQuery = usePlayerClutch(playerId, season);
  const coverageQuery = usePlayerPbpCoverage(playerId, season);
  const { data: onOff, error: onOffError } = onOffQuery;
  const { data: clutch, error: clutchError } = clutchQuery;
  const { data: coverage } = coverageQuery;
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  if (!season) return null;

  const noData = !onOff && !clutch;
  const hasError = Boolean(onOffError) && Boolean(clutchError) && !coverage;
  const coverageStatus = coverage?.status ?? (hasError ? "none" : noData ? "partial" : "ready");

  async function handleSync() {
    if (!season) return;
    setIsSyncing(true);
    setSyncMessage(null);
    try {
      const result = await syncPlayerPbp(playerId, season);
      await Promise.all([
        onOffQuery.mutate(),
        clutchQuery.mutate(),
        coverageQuery.mutate(),
      ]);
      setSyncMessage(
        `Synced ${result.games_processed} games and updated ${result.players_updated} player record${result.players_updated === 1 ? "" : "s"}.`
      );
    } catch (error) {
      setSyncMessage(error instanceof Error ? error.message : "PBP sync failed.");
    } finally {
      setIsSyncing(false);
    }
  }

  return (
    <section className="space-y-3">
      <div>
        <h2 className="text-lg font-semibold">Play-by-Play Insights</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Derived from possession-level events for {season}.
        </p>
      </div>

      {coverage ? (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                Sync Coverage
              </div>
              <div className="mt-1 flex items-center gap-2">
                <span
                  className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${
                    coverageStatus === "ready"
                      ? "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300"
                      : coverageStatus === "partial"
                      ? "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300"
                      : "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300"
                  }`}
                >
                  {coverageStatus === "ready"
                    ? "Ready"
                    : coverageStatus === "partial"
                    ? "Partial"
                    : "Not synced"}
                </span>
                <span className="text-sm text-gray-600 dark:text-gray-300">
                  {coverage.synced_games} / {coverage.eligible_games || 0} games synced
                </span>
              </div>
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              {coverage.last_derived_at
                ? `Last updated ${new Date(coverage.last_derived_at).toLocaleString()}`
                : "No derived play-by-play timestamp yet"}
            </div>
          </div>
        </div>
      ) : null}

      {hasError ? (
        <div className="rounded-xl border border-amber-200 dark:border-amber-800/60 bg-amber-50 dark:bg-amber-900/10 p-4 text-sm text-amber-900 dark:text-amber-300">
          <div className="mb-3">
            No play-by-play stats are available yet for this player in {season}.
          </div>
          <button
            onClick={handleSync}
            disabled={isSyncing}
            className="rounded-lg bg-amber-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-amber-700 disabled:cursor-wait disabled:opacity-60"
          >
            {isSyncing ? "Syncing PBP..." : "Sync Player PBP"}
          </button>
        </div>
      ) : null}

      {coverageStatus !== "ready" && !hasError ? (
        <div className="rounded-xl border border-amber-200 dark:border-amber-800/60 bg-amber-50 dark:bg-amber-900/10 p-4 text-sm text-amber-900 dark:text-amber-300">
          <div className="mb-3">
            {coverageStatus === "none"
              ? `No play-by-play metrics have been synced yet for this player in ${season}.`
              : `Play-by-play metrics are only partially synced for ${season}. Refreshing can fill in missing games or derived splits.`}
          </div>
          <button
            onClick={handleSync}
            disabled={isSyncing}
            className="rounded-lg bg-amber-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-amber-700 disabled:cursor-wait disabled:opacity-60"
          >
            {isSyncing
              ? "Syncing PBP..."
              : coverageStatus === "none"
              ? "Sync Player PBP"
              : "Refresh Player PBP"}
          </button>
        </div>
      ) : null}

      {syncMessage ? (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 text-sm text-gray-600 dark:text-gray-300">
          {syncMessage}
        </div>
      ) : null}

      {!hasError && noData ? (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 text-sm text-gray-500 dark:text-gray-400">
          Loading play-by-play metrics...
        </div>
      ) : null}

      {!hasError && (onOff || clutch) ? (
        <div className="space-y-3">
          {/* On/Off row */}
          {onOff && (
            <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400 font-semibold">On / Off Impact</span>
                <span className="text-xs text-gray-400 dark:text-gray-500">
                  {fmt(onOff.on_minutes)} on-court min &middot; {fmt(onOff.off_minutes)} off
                </span>
              </div>
              <div className="grid grid-cols-3 sm:grid-cols-5 gap-4">
                <SmallMetric label="Net (On)" value={fmtSigned(onOff.on_net_rating)} />
                <SmallMetric label="ORTG (On)" value={fmt(onOff.on_ortg)} />
                <SmallMetric label="DRTG (On)" value={fmt(onOff.on_drtg)} />
                <SmallMetric label="Net (Off)" value={fmtSigned(onOff.off_net_rating)} />
                <div className="flex flex-col gap-0.5">
                  <span className="text-xs text-gray-500 dark:text-gray-400">On/Off Diff</span>
                  <span className={`text-sm font-bold tabular-nums ${(onOff.on_off_net ?? 0) >= 0 ? "text-green-600 dark:text-green-400" : "text-red-500 dark:text-red-400"}`}>
                    {fmtSigned(onOff.on_off_net)}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Clutch + creation row */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <MetricCard
              label="Clutch Points"
              value={fmt(clutch?.clutch_pts, 0)}
              sublabel={
                clutch?.clutch_fg_pct != null && clutch?.clutch_fga != null
                  ? `${(clutch.clutch_fg_pct * 100).toFixed(1)}% on ${clutch.clutch_fga} FGA (Q4/OT ≤5)`
                  : clutch?.clutch_fg_pct != null
                  ? `${(clutch.clutch_fg_pct * 100).toFixed(1)}% FG (Q4/OT ≤5pt ≤5min)`
                  : "No clutch FG attempts"
              }
              highlight
            />
            <MetricCard
              label="2nd Chance Pts"
              value={fmt(clutch?.second_chance_pts, 0)}
              sublabel="Off offensive rebounds"
            />
            <MetricCard
              label="Fast Break Pts"
              value={fmt(clutch?.fast_break_pts, 0)}
              sublabel="In transition"
            />
            {onOff && (
              <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
                <div className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">ORTG / DRTG Off</div>
                <div className="mt-1 text-lg font-semibold tabular-nums">
                  {fmt(onOff.off_ortg)} / {fmt(onOff.off_drtg)}
                </div>
                <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">When player is off court</div>
              </div>
            )}
          </div>
        </div>
      ) : null}
    </section>
  );
}
