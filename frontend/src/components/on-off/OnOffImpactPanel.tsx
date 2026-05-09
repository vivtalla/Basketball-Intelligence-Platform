"use client";

import { useEnhancedPlayerOnOff } from "@/hooks/usePlayerStats";
import OnOffImpactBadge from "./OnOffImpactBadge";
import OnOffConfidenceCallout from "./OnOffConfidenceCallout";
import OnOffDecompositionBar from "./OnOffDecompositionBar";
import OnOffLineupPanel from "./OnOffLineupPanel";
import OnOffExternalValidationPanel from "./OnOffExternalValidationPanel";
import OnOffMethodologyDrawer from "./OnOffMethodologyDrawer";

interface Props {
  playerId: number;
  season: string | null;
  playerName?: string;
}

function fmt(v: number | null | undefined, digits = 1): string {
  if (v == null) return "—";
  return v.toFixed(digits);
}

function fmtSigned(v: number | null | undefined, digits = 1): string {
  if (v == null) return "—";
  return `${v >= 0 ? "+" : ""}${v.toFixed(digits)}`;
}

function HeroChip({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  const isPositive = value.startsWith("+");
  const isNegative = value.startsWith("-") && !value.startsWith("—");
  const textColor = accent
    ? isPositive
      ? "text-green-600 dark:text-green-400"
      : isNegative
      ? "text-red-500 dark:text-red-400"
      : "text-gray-600 dark:text-gray-300"
    : "text-gray-800 dark:text-gray-200";
  return (
    <div className="flex flex-col items-center rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-3 min-w-[80px]">
      <span className="text-[10px] uppercase tracking-wide text-gray-500 dark:text-gray-400 whitespace-nowrap">{label}</span>
      <span className={`mt-0.5 text-xl font-bold tabular-nums ${textColor}`}>{value}</span>
    </div>
  );
}

export default function OnOffImpactPanel({ playerId, season, playerName = "Player" }: Props) {
  const { data, error, isLoading, mutate } = useEnhancedPlayerOnOff(
    playerId,
    season ?? "2024-25",
    "Regular Season"
  );

  if (isLoading) {
    return (
      <div className="space-y-3 animate-pulse">
        <div className="h-7 w-48 rounded bg-gray-200 dark:bg-gray-700" />
        <div className="h-24 rounded-xl bg-gray-100 dark:bg-gray-800" />
        <div className="h-36 rounded-xl bg-gray-100 dark:bg-gray-800" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {error ? "Failed to load impact data." : "No on/off data available for this season."}
        </p>
        {error && (
          <button
            onClick={() => mutate()}
            className="mt-2 text-xs text-blue-600 dark:text-blue-400 hover:underline"
          >
            Retry
          </button>
        )}
      </div>
    );
  }

  const hasExternalValidation =
    data.external_validation &&
    (data.external_validation.rapm != null ||
      data.external_validation.epm != null ||
      data.external_validation.pipm != null);

  return (
    <div className="space-y-4">
      {/* Header row: classification badge + confidence callout */}
      <div className="flex flex-wrap items-center gap-2">
        <OnOffImpactBadge
          classification={data.impact_classification ?? null}
          confidenceTier={data.confidence_tier}
          size="md"
        />
        <OnOffConfidenceCallout
          confidenceTier={data.confidence_tier}
          onMinutes={data.on_minutes ?? null}
        />
      </div>

      {/* Hero stats row */}
      <div className="flex flex-wrap gap-2">
        <HeroChip label="On Net" value={fmtSigned(data.on_net_rating)} accent />
        <HeroChip label="Off Net" value={fmtSigned(data.off_net_rating)} accent />
        <HeroChip label="Swing" value={fmtSigned(data.on_off_net)} accent />
        {data.decomposition?.ortg_impact != null && (
          <HeroChip label="ORTG Δ" value={fmtSigned(data.decomposition.ortg_impact)} accent />
        )}
        {data.decomposition?.drtg_impact != null && (
          <HeroChip label="DRTG Δ" value={fmtSigned(data.decomposition.drtg_impact)} accent />
        )}
      </div>

      {/* Decomposition bars */}
      {data.decomposition && (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
            Side-of-ball decomposition
          </p>
          <OnOffDecompositionBar
            decomposition={data.decomposition}
            teamNetRating={data.team_net_rating ?? null}
          />
        </div>
      )}

      {/* Lineup context */}
      {(data.top_lineups.length > 0 || data.worst_lineups.length > 0) && (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
          <p className="mb-3 text-[10px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
            Lineup context · min. 100 possessions
          </p>
          <OnOffLineupPanel
            topLineups={data.top_lineups}
            worstLineups={data.worst_lineups}
            playerName={playerName}
          />
        </div>
      )}

      {/* External validation */}
      {hasExternalValidation && (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
            External validation
          </p>
          <OnOffExternalValidationPanel
            validation={data.external_validation ?? null}
            onOffNet={data.on_off_net ?? null}
          />
        </div>
      )}

      {/* Methodology drawer */}
      <OnOffMethodologyDrawer />

      {/* Raw splits reference */}
      <div className="rounded-lg border border-gray-100 dark:border-gray-700/60 bg-gray-50 dark:bg-gray-800/40 px-3 py-2 text-[10px] text-gray-400 dark:text-gray-500 grid grid-cols-2 sm:grid-cols-4 gap-x-4 gap-y-1">
        <span>On ORTG: {fmt(data.on_ortg)}</span>
        <span>Off ORTG: {fmt(data.off_ortg)}</span>
        <span>On DRTG: {fmt(data.on_drtg)}</span>
        <span>Off DRTG: {fmt(data.off_drtg)}</span>
      </div>
    </div>
  );
}
