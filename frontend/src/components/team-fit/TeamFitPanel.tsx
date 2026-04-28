"use client";

import Link from "next/link";
import { usePlayerTeamFit } from "@/hooks/useTeamFit";
import { MethodologyEvidenceCard } from "@/components/methodology/MethodologyEvidenceCard";
import type {
  TeamFitAlternativeLabel,
  TeamFitAlternativeTeam,
  TeamFitCurrentTeam,
  TeamFitDriver,
  TeamFitOverlapFlag,
} from "@/lib/types";

interface TeamFitPanelProps {
  playerId: number;
  season: string | null;
}

function scoreTone(score: number) {
  if (score >= 70) return "text-[var(--accent-strong)]";
  if (score >= 55) return "text-[var(--warning-ink)]";
  return "text-[var(--muted-strong)]";
}

function labelText(label: TeamFitAlternativeLabel) {
  if (label === "better_fit") return "Better fit";
  if (label === "similar_fit") return "Similar fit";
  return "Different fit";
}

function signed(value: number) {
  return `${value >= 0 ? "+" : ""}${value.toFixed(1)}`;
}

function DriverChip({ driver }: { driver: TeamFitDriver }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-[var(--border)] bg-[rgba(255,255,255,0.68)] px-2.5 py-1 text-[11px] font-semibold text-[var(--foreground)]">
      {driver.label}
      <span className="text-[var(--muted)]">need {driver.team_need_z.toFixed(1)}z</span>
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

function DriverList({ drivers, empty }: { drivers: TeamFitDriver[]; empty: string }) {
  if (drivers.length === 0) {
    return <p className="text-xs text-[var(--muted)]">{empty}</p>;
  }
  return (
    <div className="flex flex-wrap gap-1.5">
      {drivers.slice(0, 4).map((driver) => (
        <DriverChip key={`${driver.feature_key}-${driver.label}`} driver={driver} />
      ))}
    </div>
  );
}

function OverlapList({ flags }: { flags: TeamFitOverlapFlag[] }) {
  if (flags.length === 0) {
    return <p className="text-xs text-[var(--muted)]">No same-team duplicate role features were detected.</p>;
  }
  return (
    <div className="flex flex-wrap gap-1.5">
      {flags.slice(0, 6).map((flag) => (
        <OverlapChip key={`${flag.feature_key}-${flag.teammate_id}`} flag={flag} />
      ))}
    </div>
  );
}

function CurrentTeamCard({ team }: { team: TeamFitCurrentTeam }) {
  const skillSupply = team.skill_supply_score ?? team.value_supplied_score;
  const rosterNeed = team.roster_need_score ?? team.role_runway_score;
  const roleCompetition = team.role_competition_score ?? team.teammate_overlap_score;
  return (
    <article className="rounded-[1.5rem] border border-[var(--border)] bg-[rgba(255,255,255,0.72)] p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
            Current team
          </div>
          <h3 className="mt-1 text-lg font-semibold text-[var(--foreground)]">
            {team.team_abbreviation} fit read
          </h3>
          {team.confidence && (
            <div className="mt-1 text-xs font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
              {team.confidence} confidence
            </div>
          )}
        </div>
        <div className={`text-3xl font-black tabular-nums ${scoreTone(team.fit_score)}`}>
          {team.fit_score.toFixed(0)}
        </div>
      </div>
      <p className="mt-3 text-sm leading-6 text-[var(--muted-strong)]">{team.summary}</p>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <div className="rounded-2xl bg-[var(--surface-alt)] p-3">
          <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
            Skill supply
          </div>
          <div className="mt-1 text-xl font-bold tabular-nums text-[var(--foreground)]">
            {skillSupply.toFixed(0)}
          </div>
        </div>
        <div className="rounded-2xl bg-[var(--surface-alt)] p-3">
          <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
            Roster need
          </div>
          <div className="mt-1 text-xl font-bold tabular-nums text-[var(--foreground)]">
            {rosterNeed.toFixed(0)}
          </div>
        </div>
        <div className="rounded-2xl bg-[var(--surface-alt)] p-3">
          <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
            Role competition
          </div>
          <div className="mt-1 text-xl font-bold tabular-nums text-[var(--foreground)]">
            {roleCompetition.toFixed(0)}
          </div>
        </div>
      </div>
      {team.confidence_notes.length > 0 && (
        <p className="mt-3 text-xs leading-5 text-[var(--muted)]">{team.confidence_notes[0]}</p>
      )}
      {team.theoretical_usage_score != null && (
        <div className="mt-4 rounded-2xl border border-[var(--border)] bg-[var(--surface-alt)] p-3">
          <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
            Current fit vs best usage
          </div>
          <div className="mt-2 flex flex-wrap gap-3 text-sm text-[var(--muted-strong)]">
            <span>Theoretical {team.theoretical_usage_score.toFixed(0)}</span>
            <span>Gap {signed(team.fit_gap_vs_theoretical ?? 0)}</span>
          </div>
          {team.fit_interpretation ? (
            <p className="mt-2 text-xs leading-5 text-[var(--muted)]">{team.fit_interpretation}</p>
          ) : null}
        </div>
      )}
    </article>
  );
}

function AlternativeCard({ team, season }: { team: TeamFitAlternativeTeam; season: string }) {
  const badge =
    team.label === "better_fit"
      ? "border-[var(--accent-strong)] bg-[var(--accent-soft)] text-[var(--accent-strong)]"
      : team.label === "similar_fit"
      ? "border-[var(--warning-border)] bg-[var(--warning-soft)] text-[var(--warning-ink)]"
      : "border-[var(--border)] bg-[var(--surface-alt)] text-[var(--muted-strong)]";

  return (
    <Link
      href={`/teams/${team.team_abbreviation}?season=${encodeURIComponent(season)}`}
      className="group rounded-[1.25rem] border border-[var(--border)] bg-[rgba(255,255,255,0.68)] p-4 transition-all hover:border-[rgba(33,72,59,0.28)]"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="text-base font-semibold text-[var(--foreground)] group-hover:text-[var(--accent)]">
              {team.team_abbreviation}
            </h4>
            <span className={`rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.12em] ${badge}`}>
              {labelText(team.label)}
            </span>
          </div>
          <p className="mt-1 text-xs text-[var(--muted)]">
            {team.team_name ?? "NBA team"} · delta {signed(team.score_delta_vs_current)}
          </p>
        </div>
        <div className={`text-2xl font-black tabular-nums ${scoreTone(team.fit_score)}`}>
          {team.fit_score.toFixed(0)}
        </div>
      </div>
      <p className="mt-3 text-sm leading-5 text-[var(--muted-strong)]">{team.summary}</p>
      {team.confidence && (
        <p className="mt-2 text-xs font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
          {team.confidence} confidence · role competition {team.role_competition_score?.toFixed(0) ?? "—"}
        </p>
      )}
      <div className="mt-3">
        <DriverList drivers={team.role_runway_drivers.length ? team.role_runway_drivers : team.value_drivers} empty="No dominant alternate-team driver." />
      </div>
    </Link>
  );
}

export function TeamFitPanel({ playerId, season }: TeamFitPanelProps) {
  const { data, error, isLoading } = usePlayerTeamFit(playerId, season ?? "", 5);

  if (!season) return null;

  if (isLoading) {
    return (
      <section className="bip-panel rounded-[1.75rem] p-5 animate-pulse">
        <div className="h-5 w-48 rounded bg-[var(--surface-alt)]" />
        <div className="mt-4 h-28 rounded-2xl bg-[var(--surface-alt)]" />
      </section>
    );
  }

  if (error) {
    return (
      <section className="bip-empty rounded-[1.75rem] p-5 text-sm">
        Team-Fit intelligence is unavailable for this season.
      </section>
    );
  }

  if (!data || !data.current_team) {
    return data?.warnings?.length ? (
      <section className="bip-empty rounded-[1.75rem] p-5 text-sm">
        {data.warnings[0]}
      </section>
    ) : null;
  }

  return (
    <section className="space-y-4">
      <div>
        <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
          Team-Fit Intelligence
        </div>
        <h2 className="bip-display text-xl font-semibold text-[var(--foreground)]">
          Where does {data.player_name} fit best?
        </h2>
        <p className="mt-1 text-sm text-[var(--muted)]">
          Deterministic roster fit only: current value, teammate overlap, and teams with more role runway.
          {data.season !== season ? ` Showing ${data.season}, the latest qualified Team-Fit season.` : ""}
        </p>
      </div>

      <CurrentTeamCard team={data.current_team} />

      <div className="grid gap-4 lg:grid-cols-2">
        <article className="rounded-[1.5rem] border border-[var(--border)] bg-[rgba(255,255,255,0.62)] p-4">
          <h3 className="text-sm font-semibold text-[var(--foreground)]">Team needs from him</h3>
          <div className="mt-3">
            <DriverList drivers={data.current_team.value_drivers} empty="This roster already covers most of his strongest above-cohort skills." />
          </div>
        </article>
        <article className="rounded-[1.5rem] border border-[var(--border)] bg-[rgba(255,255,255,0.62)] p-4">
          <h3 className="text-sm font-semibold text-[var(--foreground)]">Team already has</h3>
          <div className="mt-3">
            <OverlapList flags={data.current_team.overlap_flags} />
          </div>
        </article>
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between gap-3">
          <h3 className="text-sm font-semibold text-[var(--foreground)]">Other roster fits</h3>
          <span className="text-xs text-[var(--muted)]">
            Better fit needs +{data.methodology.better_fit_delta_threshold.toFixed(0)} vs current
          </span>
        </div>
        {data.alternative_teams.length === 0 ? (
          <div className="bip-empty rounded-[1.25rem] p-4 text-sm">
            No alternate team cleared the same-season roster minimum.
          </div>
        ) : (
          <div className="grid gap-3 lg:grid-cols-2">
            {data.alternative_teams.map((team) => (
              <AlternativeCard key={team.team_abbreviation} team={team} season={data.season} />
            ))}
          </div>
        )}
      </div>

      {data.warnings.length > 0 && (
        <p className="text-xs text-[var(--muted)]">{data.warnings[0]}</p>
      )}

      <MethodologyEvidenceCard domain="team_fit" metadata={data.analysis_metadata} title="Team-Fit methodology reliability" />

      <details className="rounded-[1.25rem] border border-[var(--border)] bg-[rgba(255,255,255,0.58)] p-4 text-sm text-[var(--muted-strong)]">
        <summary className="cursor-pointer list-none font-semibold text-[var(--foreground)]">
          How Team-Fit v3 is calculated
        </summary>
        <div className="mt-3 space-y-2 text-xs leading-5">
          <p>
            Team-Fit v2 keeps the deterministic 13-feature role vector, then exposes three auditable
            components: skill supply, roster need, and role competition.
          </p>
          <p>
            Teammate-covered features are flagged when the player and a teammate are within{" "}
            {data.methodology.duplicate_threshold.toFixed(1)} z-score; those features use the{" "}
            {data.methodology.duplicate_penalty.toFixed(1)}x duplicate penalty inherited from the
            Team-Fit comp model.
          </p>
          <p>
            Alternate teams need +{data.methodology.better_fit_delta_threshold.toFixed(0)} points over
            the current team to be called a better fit. Salary and trade feasibility are intentionally excluded.
          </p>
        </div>
      </details>
    </section>
  );
}
