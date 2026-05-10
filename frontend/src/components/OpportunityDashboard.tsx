"use client";

import Link from "next/link";
import { useState } from "react";
import {
  useOpportunityReport,
} from "@/hooks/usePlayerStats";
import { useLineupContext } from "@/hooks/useTrajectory";
import type { OpportunityPlayerRow, OpportunitySignal } from "@/lib/types";
import { OpportunityRow } from "./opportunity/OpportunityRow";
import { TeamRollup } from "./opportunity/TeamRollup";
import { EfficiencyLoadCard } from "./opportunity/EfficiencyLoadCard";
import { TeamImpactCard } from "./opportunity/TeamImpactCard";
import { RoleFitCard } from "./opportunity/RoleFitCard";
import { CohortPositionCard } from "./opportunity/CohortPositionCard";
import { UpliftEvidenceCard } from "./opportunity/UpliftEvidenceCard";
import { DirectionalHintBanner } from "./opportunity/DirectionalHintBanner";
import { MethodologyDrawer } from "./opportunity/MethodologyDrawer";
import { MethodologyEvidenceCard } from "@/components/methodology/MethodologyEvidenceCard";
import {
  OpportunityDriverBar,
  SIGNAL_DESCRIPTIONS,
  SIGNAL_LABELS,
} from "./opportunity/OpportunityDriverBar";

type SignalFilter = "all" | OpportunitySignal;

interface OpportunityDashboardProps {
  season: string;
  team: string;
  pinnedPlayerId: number | null;
  signal: string;
  onPlayerPin: (playerId: number | null) => void;
  onSignalChange: (signal: string | null) => void;
}

const POSITION_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "", label: "All positions" },
  { value: "G", label: "Guards" },
  { value: "F", label: "Forwards" },
  { value: "C", label: "Centers" },
];

const SIGNAL_FILTER_OPTIONS: Array<{ value: SignalFilter; label: string }> = [
  { value: "all", label: "All drivers" },
  { value: "efficiency_load_gap", label: SIGNAL_LABELS.efficiency_load_gap },
  { value: "team_impact_swing", label: SIGNAL_LABELS.team_impact_swing },
  { value: "lineup_synergy_lift", label: SIGNAL_LABELS.lineup_synergy_lift },
  { value: "role_fit_gap", label: SIGNAL_LABELS.role_fit_gap },
  { value: "cohort_percentile", label: SIGNAL_LABELS.cohort_percentile },
];

function isSignalFilter(value: string): value is OpportunitySignal {
  return SIGNAL_FILTER_OPTIONS.some((option) => option.value === value && value !== "all");
}

export default function OpportunityDashboard({
  season,
  team,
  pinnedPlayerId,
  signal,
  onPlayerPin,
  onSignalChange,
}: OpportunityDashboardProps) {
  const [position, setPosition] = useState("");
  const [minMinutes, setMinMinutes] = useState(15);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const signalFilter: SignalFilter = isSignalFilter(signal) ? signal : "all";

  const { data: report, isLoading, error } = useOpportunityReport(
    season,
    team || null,
    minMinutes,
    position || null
  );

  // Apply signal filter in the client so the methodology stays consistent.
  const allRows: OpportunityPlayerRow[] = report?.rows ?? [];
  const filteredRows: OpportunityPlayerRow[] =
    signalFilter === "all"
      ? allRows
      : allRows.filter((r) => r.top_driver === signalFilter);

  const selectedMatch =
    (pinnedPlayerId ?? selectedId) != null
      ? filteredRows.find((r) => r.player_id === (pinnedPlayerId ?? selectedId))
      : undefined;
  const selectedRow: OpportunityPlayerRow | null =
    selectedMatch ?? filteredRows[0] ?? null;

  function handleSignalSelect(nextSignal: SignalFilter) {
    onSignalChange(nextSignal === "all" ? null : nextSignal);
  }

  function handleRollupSelect(nextSignal: string) {
    if (!isSignalFilter(nextSignal)) return;
    const firstMatch = allRows.find((row) => row.top_driver === nextSignal);
    handleSignalSelect(nextSignal);
    if (firstMatch) {
      setSelectedId(firstMatch.player_id);
      onPlayerPin(firstMatch.player_id);
    }
  }

  function handlePlayerSelect(playerId: number) {
    setSelectedId(playerId);
    onPlayerPin(playerId);
  }

  // Hooks must be pre-allocated: always call useLineupContext, even when no player.
  const lineupCtxQuery = useLineupContext(
    selectedRow?.player_id ?? null,
    season
  );

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      {/* Hero + filters */}
      <section className="rounded-[2rem] border border-[var(--border-strong)] bg-[linear-gradient(135deg,rgba(248,244,232,0.98),rgba(239,232,214,0.96))] p-6 shadow-[0_24px_80px_rgba(47,43,36,0.08)]">
        <div className="flex flex-wrap items-end justify-between gap-5">
          <div className="max-w-3xl">
            <p className="bip-kicker mb-2">Coach Workflow</p>
            <h1 className="bip-display text-4xl font-semibold text-[var(--foreground)]">
              Opportunity Workspace
            </h1>
            <p className="mt-3 text-sm leading-6 text-[var(--muted-strong)]">
              Multi-axis ranking that explains <em>why</em> a qualifying player has
              untapped role opportunity — efficiency vs load, team impact, lineup
              synergy, role fit, and cohort position. Every score is decomposed into
              capped z-scores; every hint is labeled with confidence.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                Context
              </span>
              <div className="mt-1 text-sm font-semibold text-[var(--foreground)]">
                {team || "All teams"} · {season}
              </div>
            </div>
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                Position
              </span>
              <select
                value={position}
                onChange={(e) => setPosition(e.target.value)}
                className="bip-input w-full rounded-2xl px-4 py-3 text-sm"
              >
                {POSITION_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                Min MPG
              </span>
              <input
                type="number"
                min={0}
                step={1}
                value={minMinutes}
                onChange={(e) => setMinMinutes(Number(e.target.value) || 0)}
                className="bip-input w-full rounded-2xl px-4 py-3 text-sm"
              />
            </label>
          </div>
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
            Top driver
          </span>
          {SIGNAL_FILTER_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => handleSignalSelect(opt.value)}
              title={
                opt.value === "all"
                  ? "Show every candidate regardless of which driver is leading their Opportunity Score."
                  : SIGNAL_DESCRIPTIONS[opt.value]
              }
              className={`rounded-full border px-3 py-1 text-[11px] font-medium transition ${
                signalFilter === opt.value
                  ? "border-[var(--accent-strong)] bg-[var(--accent-strong)] text-white"
                  : "border-[var(--border)] bg-[var(--surface)] text-[var(--muted-strong)] hover:border-[var(--accent-strong)] hover:text-[var(--accent-strong)]"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </section>

      {report?.team_rollup ? (
        <TeamRollup report={report} onSelectSignal={handleRollupSelect} />
      ) : null}

      {error ? (
        <section className="rounded-[1.25rem] border border-[rgba(159,63,49,0.24)] bg-[rgba(159,63,49,0.08)] px-5 py-4 text-sm text-[var(--danger-ink)]">
          Opportunity report failed to load. Try relaxing the filters.
        </section>
      ) : null}

      {report?.warnings?.length ? (
        <section className="rounded-[1.25rem] border border-[rgba(181,145,78,0.24)] bg-[rgba(181,145,78,0.08)] px-5 py-4">
          <ul className="space-y-1 text-sm text-[var(--muted-strong)]">
            {report.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {/* Two-column workspace */}
      <div className="grid gap-6 xl:grid-cols-[minmax(320px,400px),1fr]">
        {/* Left: ranked list */}
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
              Ranked Opportunities{signalFilter !== "all" ? ` · ${SIGNAL_LABELS[signalFilter]}` : ""}
            </h2>
            <span className="text-[11px] text-[var(--muted)]">
              {filteredRows.length} shown
            </span>
          </div>
          <div className="space-y-3">
            {isLoading ? (
              Array.from({ length: 6 }).map((_, i) => (
                <div
                  key={i}
                  className="h-32 animate-pulse rounded-[1.25rem] bg-[var(--surface-alt)]"
                />
              ))
            ) : filteredRows.length ? (
              filteredRows.map((r, i) => (
                <OpportunityRow
                  key={`${r.player_id}-${r.team_abbreviation}`}
                  row={r}
                  rank={i + 1}
                  isSelected={selectedRow?.player_id === r.player_id}
                  onSelect={() => handlePlayerSelect(r.player_id)}
                />
              ))
            ) : (
              <div className="rounded-[1.25rem] border border-[var(--border)] bg-[var(--surface)] px-5 py-8 text-sm text-[var(--muted-strong)]">
                No qualifying candidates. Try loosening minutes or clearing the top-driver
                filter.
              </div>
            )}
          </div>
        </section>

        {/* Right: detail panel */}
        <section className="space-y-4">
          {selectedRow ? (
            <>
              <div className="rounded-[1.5rem] border border-[var(--border)] bg-[var(--surface)] p-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                      {selectedRow.position_bucket} cohort · {selectedRow.team_abbreviation}
                    </p>
                    <h2 className="mt-0.5 text-2xl font-semibold text-[var(--foreground)]">
                      <Link
                        href={`/beta/players/${selectedRow.player_id}`}
                        className="bip-link"
                      >
                        {selectedRow.player_name}
                      </Link>
                    </h2>
                    <p className="mt-1 text-sm text-[var(--muted-strong)]">
                      {selectedRow.minutes_pg != null
                        ? `${selectedRow.minutes_pg.toFixed(1)} MPG`
                        : "— MPG"}{" "}
                      · Opportunity Score{" "}
                      <span className="font-semibold text-[var(--foreground)]">
                        {selectedRow.opportunity_score > 0 ? "+" : ""}
                        {selectedRow.opportunity_score.toFixed(2)}
                      </span>
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Link
                      href={`/beta/insights?tab=trajectory&team=${selectedRow.team_abbreviation}&season=${season}&player_id=${selectedRow.player_id}`}
                      className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1 text-[11px] font-medium text-[var(--muted-strong)] transition hover:border-[var(--accent-strong)] hover:text-[var(--accent-strong)]"
                    >
                      See Trajectory →
                    </Link>
                    <Link
                      href={`/beta/players/${selectedRow.player_id}`}
                      className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1 text-[11px] font-medium text-[var(--muted-strong)] transition hover:border-[var(--accent-strong)] hover:text-[var(--accent-strong)]"
                    >
                      Player page →
                    </Link>
                  </div>
                </div>
                <div className="mt-4">
                  <OpportunityDriverBar contributions={selectedRow.driver_contributions} />
                </div>
              </div>

              <DirectionalHintBanner row={selectedRow} />

              <div className="grid gap-4 md:grid-cols-2">
                <EfficiencyLoadCard row={selectedRow} />
                <TeamImpactCard row={selectedRow} lineupCtx={lineupCtxQuery.data} />
                <RoleFitCard row={selectedRow} />
                <CohortPositionCard row={selectedRow} />
              </div>

              {/* Sprint 90 — full-width uplift evidence card sits below the
                  2x2 grid because the IQR band + top-3 historical comparables
                  benefit from the wider layout. */}
              <UpliftEvidenceCard row={selectedRow} />

              {report?.methodology ? (
                <>
                  <MethodologyEvidenceCard domain="opportunity" metadata={report.analysis_metadata} title="Opportunity methodology reliability" compact />
                  <MethodologyDrawer methodology={report.methodology} />
                </>
              ) : null}
            </>
          ) : !isLoading ? (
            <div className="rounded-[1.5rem] border border-[var(--border)] bg-[var(--surface)] px-6 py-16 text-center text-sm text-[var(--muted-strong)]">
              Select a player on the left to see the full opportunity breakdown.
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}
