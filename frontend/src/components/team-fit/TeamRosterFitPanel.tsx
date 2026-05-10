"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useTeamRosterFit } from "@/hooks/useTeamRosterFit";
import type {
  RosterFitPlayerEntry,
  TeamFitDriver,
  TeamFitOverlapFlag,
  TeamNeedFeature,
} from "@/lib/types";

interface TeamRosterFitPanelProps {
  teamAbbr: string;
  season: string;
  seasonType?: string;
}

type SortKey = "fit" | "skill_supply" | "roster_need" | "role_competition";

function scoreTone(score: number) {
  if (score >= 70) return "text-[var(--accent-strong)]";
  if (score >= 55) return "text-[var(--warning-ink)]";
  return "text-[var(--muted-strong)]";
}

function confidencePill(confidence: string) {
  const cls =
    confidence === "high"
      ? "border-[var(--accent-strong)] bg-[var(--accent-soft)] text-[var(--accent-strong)]"
      : confidence === "medium"
        ? "border-[var(--warning-border)] bg-[var(--warning-soft)] text-[var(--warning-ink)]"
        : "border-[var(--border)] bg-[var(--surface-alt)] text-[var(--muted-strong)]";
  return (
    <span className={`rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.12em] ${cls}`}>
      {confidence} conf
    </span>
  );
}

function NeedChip({ feature, isStrength }: { feature: TeamNeedFeature; isStrength: boolean }) {
  const cls = isStrength
    ? "border-[var(--accent-strong)] bg-[var(--accent-soft)] text-[var(--accent-strong)]"
    : "border-[rgba(180,137,61,0.28)] bg-[rgba(180,137,61,0.10)] text-[var(--warning-ink)]";
  const z = feature.team_z;
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11px] font-semibold ${cls}`}>
      {feature.label}
      <span className="text-[var(--muted)] tabular-nums">
        {z >= 0 ? "+" : ""}
        {z.toFixed(2)}z
      </span>
    </span>
  );
}

function DriverChip({ driver }: { driver: TeamFitDriver }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-[var(--border)] bg-[rgba(255,255,255,0.68)] px-2.5 py-1 text-[11px] font-semibold text-[var(--foreground)]">
      {driver.label}
      <span className="text-[var(--muted)] tabular-nums">+{driver.player_z.toFixed(1)}z</span>
    </span>
  );
}

function OverlapChip({ flag }: { flag: TeamFitOverlapFlag }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-[rgba(180,137,61,0.28)] bg-[rgba(180,137,61,0.10)] px-2.5 py-1 text-[11px] font-semibold text-[var(--warning-ink)]">
      {flag.label}
      <span className="text-[var(--muted)]">via {flag.teammate_name}</span>
    </span>
  );
}

function PlayerExpanded({ entry }: { entry: RosterFitPlayerEntry }) {
  return (
    <div className="space-y-3 rounded-2xl bg-[var(--surface-alt)] p-3 text-sm">
      <p className="text-[var(--muted-strong)]">{entry.summary}</p>
      <div className="grid gap-3 lg:grid-cols-2">
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
            Top contributors
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {entry.value_drivers.length === 0 ? (
              <p className="text-xs text-[var(--muted)]">No dominant value driver.</p>
            ) : (
              entry.value_drivers
                .slice(0, 4)
                .map((d) => <DriverChip key={`${d.feature_key}-${d.label}`} driver={d} />)
            )}
          </div>
        </div>
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
            Already covered
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {entry.overlap_flags.length === 0 ? (
              <p className="text-xs text-[var(--muted)]">No same-team duplicate features.</p>
            ) : (
              entry.overlap_flags
                .slice(0, 4)
                .map((f) => <OverlapChip key={`${f.feature_key}-${f.teammate_id}`} flag={f} />)
            )}
          </div>
        </div>
      </div>
      {entry.cohort_percentiles.length > 0 && (
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
            Position-cohort percentile ({entry.position_bucket})
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {entry.cohort_percentiles.map((c) => (
              <span
                key={c.feature_key}
                className="inline-flex items-center gap-1 rounded-full border border-[var(--border)] bg-[rgba(255,255,255,0.55)] px-2.5 py-1 text-[11px] font-semibold text-[var(--foreground)]"
              >
                {c.label}
                <span className="text-[var(--muted)] tabular-nums">{c.percentile.toFixed(0)}%</span>
              </span>
            ))}
          </div>
        </div>
      )}
      {entry.confidence_notes.length > 0 && (
        <p className="text-xs text-[var(--muted)]">{entry.confidence_notes[0]}</p>
      )}
    </div>
  );
}

function CurrentRosterTable({ entries }: { entries: RosterFitPlayerEntry[] }) {
  const [sortKey, setSortKey] = useState<SortKey>("fit");
  const [expanded, setExpanded] = useState<number | null>(null);

  const sorted = useMemo(() => {
    const accessor: Record<SortKey, (e: RosterFitPlayerEntry) => number> = {
      fit: (e) => e.fit_score,
      skill_supply: (e) => e.skill_supply_score,
      roster_need: (e) => e.roster_need_score,
      role_competition: (e) => e.role_competition_score,
    };
    return [...entries].sort((a, b) => accessor[sortKey](b) - accessor[sortKey](a));
  }, [entries, sortKey]);

  const headerBtn = (key: SortKey, label: string) => (
    <button
      onClick={() => setSortKey(key)}
      className={`text-left text-[10px] font-semibold uppercase tracking-[0.14em] ${
        sortKey === key ? "text-[var(--accent-strong)]" : "text-[var(--muted)]"
      }`}
    >
      {label}
      {sortKey === key ? " ▼" : ""}
    </button>
  );

  if (sorted.length === 0) {
    return (
      <div className="bip-empty rounded-[1.25rem] p-4 text-sm">
        No qualified roster rows for this season.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-[1.5rem] border border-[var(--border)] bg-[rgba(255,255,255,0.62)]">
      <div className="grid grid-cols-12 gap-2 border-b border-[var(--border)] bg-[var(--surface-alt)] px-4 py-2">
        <div className="col-span-4">
          <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
            Player
          </span>
        </div>
        <div className="col-span-2 text-right">{headerBtn("fit", "Fit")}</div>
        <div className="col-span-2 text-right">{headerBtn("skill_supply", "Skill")}</div>
        <div className="col-span-2 text-right">{headerBtn("roster_need", "Runway")}</div>
        <div className="col-span-2 text-right">{headerBtn("role_competition", "Solo")}</div>
      </div>
      <ul className="divide-y divide-[var(--border)]">
        {sorted.map((entry) => {
          const isOpen = expanded === entry.player_id;
          return (
            <li key={entry.player_id}>
              <button
                onClick={() => setExpanded(isOpen ? null : entry.player_id)}
                className="grid w-full grid-cols-12 items-center gap-2 px-4 py-3 text-left transition-colors hover:bg-[var(--surface-alt)]"
              >
                <div className="col-span-4 flex items-center gap-2">
                  <span className="text-sm font-semibold text-[var(--foreground)]">
                    {entry.full_name}
                  </span>
                  <span className="text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">
                    {entry.position || entry.position_bucket}
                  </span>
                  {confidencePill(entry.confidence)}
                </div>
                <div className={`col-span-2 text-right text-base font-bold tabular-nums ${scoreTone(entry.fit_score)}`}>
                  {entry.fit_score.toFixed(0)}
                </div>
                <div className="col-span-2 text-right text-sm tabular-nums text-[var(--muted-strong)]">
                  {entry.skill_supply_score.toFixed(0)}
                </div>
                <div className="col-span-2 text-right text-sm tabular-nums text-[var(--muted-strong)]">
                  {entry.roster_need_score.toFixed(0)}
                </div>
                <div className="col-span-2 text-right text-sm tabular-nums text-[var(--muted-strong)]">
                  {entry.role_competition_score.toFixed(0)}
                </div>
              </button>
              {isOpen && (
                <div className="px-4 pb-4">
                  <PlayerExpanded entry={entry} />
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function CandidateCard({ entry }: { entry: RosterFitPlayerEntry }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <article className="rounded-[1.25rem] border border-[var(--border)] bg-[rgba(255,255,255,0.68)] p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Link
              href={`/beta/players/${entry.player_id}`}
              className="text-base font-semibold text-[var(--foreground)] hover:text-[var(--accent)]"
            >
              {entry.full_name}
            </Link>
            {entry.current_team_abbr && (
              <Link
                href={`/beta/teams/${entry.current_team_abbr}`}
                className="rounded-full border border-[var(--border)] bg-[var(--surface-alt)] px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.12em] text-[var(--muted-strong)]"
              >
                {entry.current_team_abbr}
              </Link>
            )}
            <span className="text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">
              {entry.position || entry.position_bucket}
            </span>
            {confidencePill(entry.confidence)}
          </div>
          <p className="mt-1 text-xs text-[var(--muted)]">
            {entry.gp} GP · {entry.season}
          </p>
        </div>
        <div className={`text-2xl font-black tabular-nums ${scoreTone(entry.fit_score)}`}>
          {entry.fit_score.toFixed(0)}
        </div>
      </div>
      <p className="mt-3 text-sm leading-5 text-[var(--muted-strong)]">{entry.summary}</p>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {entry.value_drivers.slice(0, 3).map((d) => (
          <DriverChip key={`${d.feature_key}-${d.label}`} driver={d} />
        ))}
      </div>
      <button
        onClick={() => setExpanded(!expanded)}
        className="mt-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-[var(--accent-strong)]"
      >
        {expanded ? "Hide details" : "More detail"}
      </button>
      {expanded && (
        <div className="mt-3">
          <PlayerExpanded entry={entry} />
        </div>
      )}
    </article>
  );
}

const POSITION_FILTERS: Array<{ key: string; label: string }> = [
  { key: "ALL", label: "All" },
  { key: "G", label: "Guards" },
  { key: "F", label: "Forwards" },
  { key: "C", label: "Centers" },
];

export function TeamRosterFitPanel({ teamAbbr, season, seasonType = "Regular Season" }: TeamRosterFitPanelProps) {
  const { data, error, isLoading } = useTeamRosterFit(teamAbbr, season, seasonType, 25);
  const [posFilter, setPosFilter] = useState<string>("ALL");

  if (isLoading) {
    return (
      <section className="bip-panel rounded-[1.75rem] p-5 animate-pulse">
        <div className="h-5 w-48 rounded bg-[var(--surface-alt)]" />
        <div className="mt-4 h-28 rounded-2xl bg-[var(--surface-alt)]" />
        <div className="mt-3 h-72 rounded-2xl bg-[var(--surface-alt)]" />
      </section>
    );
  }

  if (error) {
    return (
      <section className="bip-empty rounded-[1.75rem] p-5 text-sm">
        Roster fit intelligence is unavailable for this season.
      </section>
    );
  }

  if (!data) return null;

  const needFeaturesByLabel = new Map(data.team_need_vector.features.map((f) => [f.label, f]));
  const needLabels = data.team_need_vector.primary_needs;
  const strengthLabels = data.team_need_vector.primary_strengths;

  const filteredCandidates =
    posFilter === "ALL"
      ? data.league_candidates
      : data.league_candidates.filter((c) => c.position_bucket === posFilter);

  return (
    <section className="space-y-5">
      <div>
        <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
          Roster Fit Intelligence
        </div>
        <h2 className="bip-display text-xl font-semibold text-[var(--foreground)]">
          Who fits {data.team_abbreviation}, and who would?
        </h2>
        <p className="mt-1 text-sm text-[var(--muted)]">
          Same 13-feature, 3-component math as the player-side Team-Fit panel — inverted to score every
          rostered player against the rest of the roster, then every league player against the full roster.
        </p>
      </div>

      {/* Team need vector */}
      <article className="rounded-[1.5rem] border border-[var(--border)] bg-[rgba(255,255,255,0.72)] p-4">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
              Team need vector
            </div>
            <h3 className="mt-1 text-lg font-semibold text-[var(--foreground)]">
              What this roster lacks vs the league
            </h3>
          </div>
          <div className="text-xs text-[var(--muted)]">
            {data.qualified_roster_count} qualified roster rows · {data.season}
          </div>
        </div>
        <div className="mt-3 grid gap-3 lg:grid-cols-2">
          <div>
            <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
              Primary needs
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {needLabels.length === 0 ? (
                <p className="text-xs text-[var(--muted)]">No feature is meaningfully below league average.</p>
              ) : (
                needLabels.map((label) => {
                  const feature = needFeaturesByLabel.get(label);
                  return feature ? <NeedChip key={label} feature={feature} isStrength={false} /> : null;
                })
              )}
            </div>
          </div>
          <div>
            <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
              Primary strengths
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {strengthLabels.length === 0 ? (
                <p className="text-xs text-[var(--muted)]">No feature is meaningfully above league average.</p>
              ) : (
                strengthLabels.map((label) => {
                  const feature = needFeaturesByLabel.get(label);
                  return feature ? <NeedChip key={label} feature={feature} isStrength={true} /> : null;
                })
              )}
            </div>
          </div>
        </div>
      </article>

      {/* Current roster fits */}
      <div>
        <div className="mb-2 flex items-center justify-between gap-3">
          <h3 className="text-sm font-semibold text-[var(--foreground)]">
            Current roster — fit vs the rest of {data.team_abbreviation}
          </h3>
          <span className="text-xs text-[var(--muted)]">
            {data.current_roster_fits.length} player{data.current_roster_fits.length === 1 ? "" : "s"}
          </span>
        </div>
        <CurrentRosterTable entries={data.current_roster_fits} />
      </div>

      {/* League candidates */}
      <div>
        <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
          <h3 className="text-sm font-semibold text-[var(--foreground)]">
            League candidates — top {data.league_candidates.length} statistical fits
          </h3>
          <div className="flex rounded-xl overflow-hidden border border-[var(--border)] text-xs">
            {POSITION_FILTERS.map((f) => (
              <button
                key={f.key}
                onClick={() => setPosFilter(f.key)}
                className={`px-3 py-1.5 transition-colors ${
                  posFilter === f.key ? "bip-toggle-active" : "bip-toggle"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>
        {filteredCandidates.length === 0 ? (
          <div className="bip-empty rounded-[1.25rem] p-4 text-sm">
            No qualified candidates for this position filter.
          </div>
        ) : (
          <div className="grid gap-3 lg:grid-cols-2">
            {filteredCandidates.map((entry) => (
              <CandidateCard key={entry.player_id} entry={entry} />
            ))}
          </div>
        )}
      </div>

      {data.warnings.length > 0 && (
        <p className="text-xs text-[var(--muted)]">{data.warnings[0]}</p>
      )}

      <details className="rounded-[1.25rem] border border-[var(--border)] bg-[rgba(255,255,255,0.58)] p-4 text-sm text-[var(--muted-strong)]">
        <summary className="cursor-pointer list-none font-semibold text-[var(--foreground)]">
          How Roster Fit ({data.methodology.version}) is calculated
        </summary>
        <div className="mt-3 space-y-2 text-xs leading-5">
          <p>
            The same three-component model as player-side Team-Fit (45% Skill Supply / 25% Roster Need /
            30% Role Competition) on 13 z-scored role features. Inverted: fix the team, score many
            players. Current-roster scoring excludes the subject from the comparison roster so Role
            Competition isn&apos;t inflated by self-overlap.
          </p>
          <p>
            Position-cohort percentile (G / F / C) is shown alongside global percentile so a center
            isn&apos;t graded only against guard rates — display only, the score formula keeps using
            global norms so cross-position rankings stay coherent.
          </p>
          <p>
            Teammate-covered features are flagged when a roster player is within{" "}
            {data.methodology.duplicate_threshold.toFixed(1)}z of the candidate; those features get the{" "}
            {data.methodology.duplicate_penalty.toFixed(1)}× duplicate penalty.
          </p>
          <p>
            League candidates are ranked by statistical fit only. Salary, contract length, free-agent
            status, age, injury history, and trade feasibility are out of scope.
          </p>
          <p className="text-[var(--muted)]">
            Generated {new Date(data.generated_at).toLocaleString()}. Cached 24h after the first cold
            compute.
          </p>
        </div>
      </details>
    </section>
  );
}

export default TeamRosterFitPanel;
