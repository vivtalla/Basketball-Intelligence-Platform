"use client";

import { useState } from "react";
import { syncPlayerPbp } from "@/lib/api";
import { usePlayerClutch, usePlayerOnOff } from "@/hooks/usePlayerStats";

interface PlayerPbpInsightsProps {
  playerId: number;
  season: string | null;
}

function fmt(value: number | null | undefined, digits = 1): string {
  if (value == null) return "-";
  return value.toFixed(digits);
}

function MetricCard({
  label,
  value,
  sublabel,
}: {
  label: string;
  value: string;
  sublabel?: string;
}) {
  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
      <div className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums">{value}</div>
      {sublabel ? (
        <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">{sublabel}</div>
      ) : null}
    </div>
  );
}

export default function PlayerPbpInsights({ playerId, season }: PlayerPbpInsightsProps) {
  const onOffQuery = usePlayerOnOff(playerId, season);
  const clutchQuery = usePlayerClutch(playerId, season);
  const { data: onOff, error: onOffError } = onOffQuery;
  const { data: clutch, error: clutchError } = clutchQuery;
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  if (!season) return null;

  const noData = !onOff && !clutch;
  const hasError = Boolean(onOffError) && Boolean(clutchError);

  async function handleSync() {
    setIsSyncing(true);
    setSyncMessage(null);
    try {
      const result = await syncPlayerPbp(playerId, season);
      await Promise.all([onOffQuery.mutate(), clutchQuery.mutate()]);
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
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <MetricCard
            label="On/Off Net"
            value={fmt(onOff?.on_off_net)}
            sublabel={`On: ${fmt(onOff?.on_net_rating)} | Off: ${fmt(onOff?.off_net_rating)}`}
          />
          <MetricCard
            label="On Minutes"
            value={fmt(onOff?.on_minutes)}
            sublabel={`Off Minutes: ${fmt(onOff?.off_minutes)}`}
          />
          <MetricCard
            label="Clutch Points"
            value={fmt(clutch?.clutch_pts, 0)}
            sublabel={`Clutch FG%: ${clutch?.clutch_fg_pct != null ? (clutch.clutch_fg_pct * 100).toFixed(1) : "-"}`}
          />
          <MetricCard
            label="Creation"
            value={`${fmt(clutch?.second_chance_pts, 0)} / ${fmt(clutch?.fast_break_pts, 0)}`}
            sublabel="2nd chance / fast break pts"
          />
        </div>
      ) : null}
    </section>
  );
}
