"use client";

import { useMemo, useState, type ReactNode } from "react";
import Image from "next/image";
import Link from "next/link";
import type { MvpCandidate, MvpRaceResponse, MvpScorePillar } from "@/lib/types";
import MvpImpactRadar from "./MvpImpactRadar";
import MvpClutchCard from "./MvpClutchCard";
import MvpSignatureGames from "./MvpSignatureGames";

interface MvpRacePanelProps {
  data: MvpRaceResponse;
}

const VALUE_PILLAR_ORDER = ["impact", "efficiency", "scoring_load", "playmaking_load", "team_value", "availability"];
const AWARD_MODIFIER_ORDER = ["team_framing", "eligibility_pressure", "clutch", "momentum", "signature_games"];
const MAP_AXES = [
  { key: "team_success", label: "Team Success" },
  { key: "impact", label: "Impact" },
  { key: "production", label: "Production" },
  { key: "efficiency", label: "Efficiency" },
  { key: "availability", label: "Availability" },
  { key: "momentum", label: "Momentum" },
  { key: "gravity", label: "Gravity" },
] as const;
type MapAxis = (typeof MAP_AXES)[number]["key"];

function fmt(value: number | null | undefined, digits = 1): string {
  if (value == null || Number.isNaN(value)) return "-";
  return value.toFixed(digits);
}

function fmtSigned(value: number | null | undefined, digits = 1): string {
  if (value == null || Number.isNaN(value)) return "-";
  return `${value >= 0 ? "+" : ""}${value.toFixed(digits)}`;
}

function fmtPct(value: number | null | undefined, digits = 1): string {
  if (value == null || Number.isNaN(value)) return "-";
  return `${(value * 100).toFixed(digits)}%`;
}

function fmtPercentish(value: number | null | undefined, digits = 1): string {
  if (value == null || Number.isNaN(value)) return "-";
  return value <= 1 ? fmtPct(value, digits) : `${value.toFixed(digits)}%`;
}

function confidenceClass(confidence: string | null | undefined): string {
  if (confidence === "high") return "text-[var(--success-ink)]";
  if (confidence === "medium") return "text-[var(--accent)]";
  return "text-[var(--muted)]";
}

function eligibilityClass(status: string | null | undefined): string {
  if (status === "eligible") return "border-[rgba(42,125,87,0.35)] bg-[rgba(42,125,87,0.10)] text-[var(--success-ink)]";
  if (status === "at_risk") return "border-[rgba(180,137,61,0.40)] bg-[rgba(180,137,61,0.12)] text-[var(--accent)]";
  if (status === "ineligible") return "border-[rgba(176,70,70,0.35)] bg-[rgba(176,70,70,0.10)] text-[var(--danger-ink)]";
  return "border-[var(--border)] bg-[var(--surface-alt)] text-[var(--muted)]";
}

function coordinateFor(candidate: MvpCandidate, axis: MapAxis): number {
  const visual = candidate.visual_coordinates;
  const pillars = candidate.score_pillars ?? {};
  if (axis === "team_success") return visual?.x_team_success ?? pillars.team_context?.display_score ?? 50;
  if (axis === "impact") return visual?.y_individual_impact ?? pillars.impact?.display_score ?? 50;
  if (axis === "production") return visual?.production ?? pillars.production?.display_score ?? 50;
  if (axis === "efficiency") return visual?.efficiency ?? pillars.efficiency?.display_score ?? 50;
  if (axis === "availability") return visual?.availability ?? Math.min(100, (candidate.gp / 65) * 100);
  if (axis === "gravity") return candidate.gravity_profile?.overall_gravity ?? 50;
  return visual?.momentum ?? pillars.momentum?.display_score ?? 50;
}

function MvpCaseMap({
  candidates,
  selectedId,
  onSelect,
}: {
  candidates: MvpCandidate[];
  selectedId: number | null;
  onSelect: (id: number) => void;
}) {
  const [xAxis, setXAxis] = useState<MapAxis>("team_success");
  const [yAxis, setYAxis] = useState<MapAxis>("impact");
  const selected = candidates.find((candidate) => candidate.player_id === selectedId) ?? candidates[0];

  return (
    <section className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase text-[var(--accent)]">MVP Case Map</p>
          <h2 className="bip-display mt-1 text-2xl font-semibold text-[var(--foreground)]">Who has the clearest path?</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--muted)]">
            X-axis defaults to team success, Y-axis to individual impact. Bubble size reflects minutes and availability; color follows recent form. Gravity can be selected as an axis to surface off-box-score defensive attention.
          </p>
          <MethodNote label="How to read it">
            This is a context map, not the leaderboard formula. Use it to compare the shape of each case: team value, individual value, availability, momentum, and Gravity can each be inspected as axes.
          </MethodNote>
        </div>
        <div className="grid gap-2 sm:grid-cols-2">
          <label className="text-xs text-[var(--muted)]">
            X axis
            <select
              value={xAxis}
              onChange={(event) => setXAxis(event.target.value as MapAxis)}
              className="mt-1 w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--foreground)]"
            >
              {MAP_AXES.map((axis) => (
                <option key={axis.key} value={axis.key}>{axis.label}</option>
              ))}
            </select>
          </label>
          <label className="text-xs text-[var(--muted)]">
            Y axis
            <select
              value={yAxis}
              onChange={(event) => setYAxis(event.target.value as MapAxis)}
              className="mt-1 w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--foreground)]"
            >
              {MAP_AXES.map((axis) => (
                <option key={axis.key} value={axis.key}>{axis.label}</option>
              ))}
            </select>
          </label>
        </div>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-[minmax(0,1fr)_280px]">
        <div className="relative h-[420px] min-h-[320px] overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--surface-alt)]">
          <div className="absolute inset-x-6 bottom-8 top-6 border-l border-b border-[var(--border)]" />
          <div className="absolute left-3 top-5 text-[10px] uppercase text-[var(--muted)]">{MAP_AXES.find((axis) => axis.key === yAxis)?.label}</div>
          <div className="absolute bottom-2 right-6 text-[10px] uppercase text-[var(--muted)]">{MAP_AXES.find((axis) => axis.key === xAxis)?.label}</div>
          <div className="absolute left-6 right-6 top-1/2 border-t border-dashed border-[var(--border)]" />
          <div className="absolute bottom-8 top-6 left-1/2 border-l border-dashed border-[var(--border)]" />
          {candidates.map((candidate) => {
            const x = Math.max(4, Math.min(96, coordinateFor(candidate, xAxis)));
            const y = Math.max(4, Math.min(96, coordinateFor(candidate, yAxis)));
            const size = Math.max(18, Math.min(46, candidate.visual_coordinates?.bubble_size ?? 24));
            const isSelected = candidate.player_id === selected?.player_id;
            const color =
              candidate.momentum === "hot"
                ? "bg-[var(--accent)]"
                : candidate.momentum === "cold"
                  ? "bg-[var(--danger-ink)]"
                  : "bg-[var(--foreground)]";
            return (
              <button
                key={candidate.player_id}
                type="button"
                onClick={() => onSelect(candidate.player_id)}
                className={`absolute flex -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border text-[10px] font-bold text-white shadow-sm transition-transform hover:scale-110 ${
                  isSelected ? "border-[var(--accent)] ring-2 ring-[rgba(33,72,59,0.24)]" : "border-white"
                } ${color}`}
                style={{ left: `${x}%`, top: `${100 - y}%`, width: size, height: size }}
                title={`${candidate.player_name}: ${fmt(candidate.composite_score)} score`}
              >
                {candidate.rank}
              </button>
            );
          })}
        </div>

        <aside className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-4">
          {selected ? (
            <>
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs text-[var(--muted)]">Selected</p>
                  <p className="mt-1 text-sm font-semibold text-[var(--foreground)]">{selected.player_name}</p>
                </div>
                <span className={`rounded border px-2 py-1 text-[10px] uppercase ${eligibilityClass(selected.eligibility?.eligibility_status)}`}>
                  {selected.eligibility?.eligibility_status ?? "unknown"}
                </span>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
                <StatTile label="Award" value={fmt(selected.award_case_score ?? selected.composite_score)} />
                <StatTile label="Value" value={fmt(selected.basketball_value_score)} />
                <StatTile label="Gravity" value={fmt(selected.gravity_profile?.overall_gravity)} />
                <StatTile label="Qualified" value={`${selected.eligibility?.eligible_games ?? selected.gp}/65`} />
              </div>
              <div className="mt-4 space-y-2 text-xs leading-5 text-[var(--muted)]">
                {(selected.case_summary ?? []).slice(0, 3).map((line) => (
                  <p key={line}>{line}</p>
                ))}
              </div>
              <div className="mt-4 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3 text-xs leading-5 text-[var(--muted)]">
                {selected.visual_coordinates?.explanation ?? "Map placement uses pillar scores, availability, and momentum."}
              </div>
              <MethodNote label="Score split">
                Award is the ballot-facing rank. Value is the season-long basketball base. Gravity is context-only unless you choose it as an axis.
              </MethodNote>
            </>
          ) : null}
        </aside>
      </div>
    </section>
  );
}

function SkeletonCard() {
  return (
    <div className="flex items-center gap-4 p-4 rounded-lg border border-[var(--border)] bg-[var(--surface)] animate-pulse">
      <div className="w-8 h-8 rounded bg-[var(--border)]" />
      <div className="w-12 h-12 rounded-full bg-[var(--border)]" />
      <div className="flex-1 space-y-2">
        <div className="h-3 w-32 rounded bg-[var(--border)]" />
        <div className="h-2 w-20 rounded bg-[var(--border)]" />
      </div>
      <div className="hidden sm:flex gap-3">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-10 w-16 rounded bg-[var(--border)]" />
        ))}
      </div>
    </div>
  );
}

export function MvpRacePanelSkeleton() {
  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.35fr)]">
      <div className="space-y-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
      <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5 animate-pulse">
        <div className="h-5 w-44 rounded bg-[var(--border)]" />
        <div className="mt-5 grid grid-cols-2 gap-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-20 rounded bg-[var(--border)]" />
          ))}
        </div>
      </div>
    </div>
  );
}

function PillarBar({ pillar }: { pillar: MvpScorePillar }) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between gap-2 text-[11px]">
        <span className="font-medium text-[var(--foreground)]">{pillar.label}</span>
        <span className="tabular-nums text-[var(--muted)]">{fmt(pillar.display_score, 0)}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded bg-[var(--border)]">
        <div
          className="h-full rounded bg-[var(--accent)]"
          style={{ width: `${Math.max(0, Math.min(100, pillar.display_score)).toFixed(0)}%` }}
        />
      </div>
    </div>
  );
}

function ModifierBar({ modifier }: { modifier: NonNullable<MvpCandidate["award_modifiers"]>[string] }) {
  const width = Math.max(0, Math.min(100, modifier.display_score));
  return (
    <div>
      <div className="mb-1 flex items-center justify-between gap-2 text-[11px]">
        <span className="font-medium text-[var(--foreground)]">{modifier.label}</span>
        <span className="tabular-nums text-[var(--muted)]">{fmtSigned(modifier.modifier)}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded bg-[var(--border)]">
        <div className="h-full rounded bg-[var(--accent)]" style={{ width: `${width.toFixed(0)}%` }} />
      </div>
      <p className="mt-1 text-[10px] uppercase text-[var(--muted)]">{modifier.confidence} confidence</p>
    </div>
  );
}

function CandidateRow({
  candidate,
  selected,
  onSelect,
}: {
  candidate: MvpCandidate;
  selected: boolean;
  onSelect: () => void;
}) {
  const team = candidate.team_context;
  const awardScore = candidate.award_case_score ?? candidate.composite_score;
  const valueScore = candidate.basketball_value_score;

  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full rounded-lg border p-4 text-left transition-colors ${
        selected
          ? "border-[var(--accent)] bg-[rgba(33,72,59,0.08)]"
          : "border-[var(--border)] bg-[var(--surface)] hover:border-[var(--accent)]"
      }`}
    >
      <div className="flex items-center gap-3">
        <div className="w-7 shrink-0 text-center text-lg font-bold tabular-nums text-[var(--accent)]">
          {candidate.rank}
        </div>
        <div className="relative h-12 w-12 shrink-0 overflow-hidden rounded-full bg-[var(--surface-alt)]">
          {candidate.headshot_url ? (
            <Image src={candidate.headshot_url} alt={candidate.player_name} fill className="object-cover object-top" unoptimized />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-xs font-bold text-[var(--muted)]">
              {candidate.player_name.split(" ").map((name) => name[0]).join("").slice(0, 2)}
            </div>
          )}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="truncate text-sm font-semibold text-[var(--foreground)]">{candidate.player_name}</p>
            <span className="rounded border border-[var(--border)] px-1.5 py-0.5 text-[10px] uppercase text-[var(--muted)]">
              {candidate.momentum}
            </span>
            <span className={`rounded border px-1.5 py-0.5 text-[10px] uppercase ${eligibilityClass(candidate.eligibility?.eligibility_status)}`}>
              {candidate.eligibility?.eligible_games ?? candidate.gp}/65
            </span>
          </div>
          <p className="mt-0.5 text-xs text-[var(--muted)]">
            {candidate.team_abbreviation} - {candidate.gp} GP - Award {fmt(awardScore, 1)}
            {candidate.context_adjusted_score != null ? ` - Context ${fmt(candidate.context_adjusted_score, 1)}` : ""}
          </p>
        </div>
      </div>
      <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
        <StatTile label="Award" value={fmt(awardScore)} />
        <StatTile label="Value" value={fmt(valueScore)} />
        <StatTile label="Confidence" value={candidate.confidence?.overall ?? "-"} />
      </div>
      <div className="mt-3 text-xs text-[var(--muted)]">
        {team?.wins != null && team?.losses != null
          ? `${candidate.team_abbreviation} ${team.wins}-${team.losses}, net ${fmtSigned(team.net_rating)}`
          : "Team context pending"}
      </div>
    </button>
  );
}

function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-2 py-2">
      <div className="text-[10px] uppercase tracking-[0.08em] text-[var(--muted)]">{label}</div>
      <div className="mt-1 font-semibold tabular-nums text-[var(--foreground)]">{value}</div>
    </div>
  );
}

function MetricBlock({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-3">
      <p className="text-[10px] uppercase tracking-[0.08em] text-[var(--muted)]">{label}</p>
      <p className="mt-1 text-lg font-semibold tabular-nums text-[var(--foreground)]">{value}</p>
      {sub && <p className="mt-1 text-xs text-[var(--muted)]">{sub}</p>}
    </div>
  );
}

function MethodNote({ label, children }: { label: string; children: ReactNode }) {
  return (
    <p className="mt-2 rounded border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-2 text-xs leading-5 text-[var(--muted)]">
      <span className="font-semibold uppercase text-[var(--accent)]">{label}:</span> {children}
    </p>
  );
}

function CandidateCase({ candidate, asOfDate }: { candidate: MvpCandidate; asOfDate: string }) {
  const valuePillars = candidate.basketball_value_pillars ?? {};
  const awardModifiers = candidate.award_modifiers ?? {};
  const warnings = candidate.data_coverage?.warnings ?? [];
  const styleRows = candidate.play_style ?? [];
  const topStyle = styleRows.slice(0, 4);
  const advanced = candidate.advanced_profile;
  const onOff = candidate.on_off;
  const clutch = candidate.clutch_and_pace;
  const team = candidate.team_context;
  const eligibility = candidate.eligibility;
  const opponentRows = candidate.opponent_context?.rows ?? candidate.split_profile ?? [];
  const support = candidate.support_burden;
  const impactCoverage = candidate.impact_metric_coverage;
  const awardScore = candidate.award_case_score ?? candidate.composite_score;
  const valueScore = candidate.basketball_value_score;

  return (
    <section className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
        <div className="relative h-20 w-20 shrink-0 overflow-hidden rounded-full bg-[var(--surface-alt)]">
          {candidate.headshot_url ? (
            <Image src={candidate.headshot_url} alt={candidate.player_name} fill className="object-cover object-top" unoptimized />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-lg font-bold text-[var(--muted)]">
              {candidate.player_name.split(" ").map((name) => name[0]).join("").slice(0, 2)}
            </div>
          )}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded border border-[var(--accent)] px-2 py-1 text-xs font-semibold text-[var(--accent)]">
              Rank {candidate.rank}
            </span>
            <span className="rounded border border-[var(--border)] px-2 py-1 text-xs text-[var(--muted)]">
              {candidate.team_abbreviation}
            </span>
            <span className="rounded border border-[var(--border)] px-2 py-1 text-xs text-[var(--muted)]">
              As of {asOfDate}
            </span>
          </div>
          <h2 className="bip-display mt-3 text-3xl font-semibold text-[var(--foreground)]">{candidate.player_name}</h2>
          <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
            Award Case {fmt(awardScore, 1)} from Basketball Value plus capped award modifiers. Basketball Value {fmt(valueScore, 1)} keeps the on-court season separate from voter-facing candidacy.
          </p>
          <MethodNote label="Why two scores">
            Basketball Value asks who has delivered the strongest season on the floor. Award Case asks how that season translates to an MVP ballot after eligibility, team framing, clutch, momentum, and signature moments.
          </MethodNote>
        </div>
        <Link href={`/players/${candidate.player_id}`} className="rounded-lg border border-[var(--border)] px-3 py-2 text-sm font-medium text-[var(--accent)] hover:border-[var(--accent)]">
          Player profile
        </Link>
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-3">
        <MetricBlock label="Award Case" value={fmt(awardScore)} sub={`Rank ${candidate.award_case_rank ?? candidate.rank}`} />
        <MetricBlock label="Basketball Value" value={fmt(valueScore)} sub={candidate.basketball_value_rank ? `Value rank ${candidate.basketball_value_rank}` : "Core season score"} />
        <MetricBlock label="Confidence" value={candidate.confidence?.overall ?? "-"} sub={`Coverage ${fmt(candidate.confidence?.coverage_score, 0)}`} />
        <MetricBlock label="Eligibility" value={`${eligibility?.eligible_games ?? candidate.gp}/65`} sub={eligibility?.eligibility_status ?? "unknown"} />
      </div>

      <section className="mt-6 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-4">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase text-[var(--accent)]">Box Score vs Gravity</p>
            <h3 className="mt-1 text-sm font-semibold text-[var(--foreground)]">How invisible attention changes the case</h3>
            <p className="mt-2 max-w-2xl text-xs leading-5 text-[var(--muted)]">
              The main MVP score stays box-score visible. The context-adjusted score applies only a capped Gravity modifier so spacing, rim pressure, and off-ball attention are visible without letting a noisy proxy dominate.
            </p>
          </div>
          <div className="grid min-w-[260px] grid-cols-3 gap-2 text-xs">
            <StatTile label="Award" value={fmt(awardScore)} />
            <StatTile label="Gravity" value={fmt(candidate.gravity_profile?.overall_gravity)} />
            <StatTile label="Adjusted" value={fmt(candidate.context_adjusted_score)} />
          </div>
        </div>
      </section>

      <div className="mt-6 grid gap-5 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
        <div>
          <h3 className="text-sm font-semibold text-[var(--foreground)]">Case</h3>
          <div className="mt-3 space-y-2">
            {(candidate.case_summary ?? []).map((line) => (
              <p key={line} className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-3 text-sm leading-6 text-[var(--foreground)]">
                {line}
              </p>
            ))}
          </div>
        </div>
        <div>
          <h3 className="text-sm font-semibold text-[var(--foreground)]">Basketball Value Pillars</h3>
          <p className="mt-1 text-xs leading-5 text-[var(--muted)]">
            These are the core score inputs. They reduce double-counting by separating impact, efficiency, scoring burden, playmaking burden, team value, and availability.
          </p>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            {VALUE_PILLAR_ORDER.map((key) => valuePillars[key]).filter(Boolean).map((pillar) => (
              <PillarBar key={pillar.label} pillar={pillar} />
            ))}
          </div>
        </div>
      </div>

      <div className="mt-6 grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <section>
          <h3 className="text-sm font-semibold text-[var(--foreground)]">Award Case Modifiers</h3>
          <p className="mt-1 text-xs leading-5 text-[var(--muted)]">
            These are capped voter-facing adjustments. They can move the Award Case, but they are intentionally smaller than the Basketball Value base.
          </p>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            {AWARD_MODIFIER_ORDER.map((key) => awardModifiers[key]).filter(Boolean).map((modifier) => (
              <ModifierBar key={modifier.key} modifier={modifier} />
            ))}
          </div>
        </section>
        <section>
          <h3 className="text-sm font-semibold text-[var(--foreground)]">Methodology Labels</h3>
          <p className="mt-1 text-xs leading-5 text-[var(--muted)]">
            Each label tells you whether a metric drives the score, modifies the award case, provides context, or supports the analyst interpretation.
          </p>
          <div className="mt-3 space-y-2">
            {(candidate.methodology_labels ?? []).map((label) => (
              <div key={label.key} className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-3 text-xs leading-5 text-[var(--muted)]">
                <span className="font-semibold text-[var(--foreground)]">{label.label}:</span> {label.description}
              </div>
            ))}
          </div>
        </section>
      </div>

      {candidate.qualitative_lenses && candidate.qualitative_lenses.length > 0 ? (
        <section className="mt-6">
          <h3 className="text-sm font-semibold text-[var(--foreground)]">Structured Analyst Lenses</h3>
          <p className="mt-1 text-xs leading-5 text-[var(--muted)]">
            These lenses translate the numbers into basketball language. They do not override the model; they explain role difficulty, scalability, game control, two-way pressure, and playoff translation using evidence already on the page.
          </p>
          <div className="mt-3 grid gap-3 lg:grid-cols-5">
            {candidate.qualitative_lenses.map((lens) => (
              <article key={lens.key} className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-3">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-semibold text-[var(--foreground)]">{lens.label}</p>
                  <span className={`text-[10px] uppercase ${confidenceClass(lens.confidence)}`}>{lens.confidence}</span>
                </div>
                <p className="mt-2 text-xs leading-5 text-[var(--muted)]">{lens.summary}</p>
                <ul className="mt-2 space-y-1 text-xs leading-5 text-[var(--muted)]">
                  {lens.evidence.slice(0, 3).map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      <div className="mt-6 grid gap-5 lg:grid-cols-2">
        <section>
          <h3 className="text-sm font-semibold text-[var(--foreground)]">Gravity</h3>
          <p className="mt-1 text-xs leading-5 text-[var(--muted)]">
            Context signal. Gravity estimates the attention a player draws beyond the box score. It is shown separately so a proxy or partial source cannot dominate the default leaderboard.
          </p>
          {candidate.gravity_profile ? (
            <>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <MetricBlock label="Overall" value={fmt(candidate.gravity_profile.overall_gravity)} sub={candidate.gravity_profile.source_label} />
                <MetricBlock label="Shooting" value={fmt(candidate.gravity_profile.shooting_gravity)} sub="perimeter attention" />
                <MetricBlock label="Rim" value={fmt(candidate.gravity_profile.rim_gravity)} sub="paint pressure" />
                <MetricBlock label="Creation" value={fmt(candidate.gravity_profile.creation_gravity)} sub="on-ball load" />
                <MetricBlock label="Roll/Screen" value={fmt(candidate.gravity_profile.roll_or_screen_gravity)} sub="screen and roll pressure" />
                <MetricBlock label="Off Ball" value={fmt(candidate.gravity_profile.off_ball_gravity)} sub={`confidence ${candidate.gravity_profile.gravity_confidence}`} />
                <MetricBlock label="Spacing Lift" value={fmt(candidate.gravity_profile.spacing_lift)} sub={`${fmt(candidate.gravity_profile.gravity_minutes, 0)} gravity minutes`} />
              </div>
              <p className="mt-3 text-xs leading-5 text-[var(--muted)]">
                {candidate.gravity_profile.source_note}
              </p>
              {candidate.gravity_profile.warnings.length > 0 && (
                <ul className="mt-2 space-y-1 text-xs leading-5 text-[var(--muted)]">
                  {candidate.gravity_profile.warnings.slice(0, 3).map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              )}
            </>
          ) : (
            <p className="mt-3 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-3 text-sm text-[var(--muted)]">
              Gravity context is not available for this candidate yet.
            </p>
          )}
        </section>

        <section>
          <h3 className="text-sm font-semibold text-[var(--foreground)]">Team Lift</h3>
          <p className="mt-1 text-xs leading-5 text-[var(--muted)]">
            Mixed signal. Team Value helps the Basketball Value score when tied to the player&apos;s participation; full team record and support burden explain the environment around that value.
          </p>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <MetricBlock label="Team Record" value={team?.wins != null && team.losses != null ? `${team.wins}-${team.losses}` : "-"} sub={team?.win_pct_rank ? `Win% rank ${team.win_pct_rank}` : undefined} />
            <MetricBlock label="Team Net" value={fmtSigned(team?.net_rating)} sub={team?.net_rating_rank ? `Net rank ${team.net_rating_rank}` : undefined} />
            <MetricBlock label="On Net" value={fmtSigned(onOff?.on_net_rating)} sub={`${fmt(onOff?.on_minutes, 0)} on minutes`} />
            <MetricBlock label="Off Net" value={fmtSigned(onOff?.off_net_rating)} sub={`${fmt(onOff?.off_minutes, 0)} off minutes`} />
            <MetricBlock label="Top Support" value={support?.top_teammate_name ?? "-"} sub={support?.top_teammate_pts_pg != null ? `${fmt(support.top_teammate_pts_pg)} PPG, ${support.top_teammate_games ?? "-"} GP` : support?.support_note ?? undefined} />
            <MetricBlock label="Usage Burden" value={fmtPercentish(support?.candidate_usage_pct)} sub={support?.teammate_availability_avg_gp != null ? `Avg teammate GP ${fmt(support.teammate_availability_avg_gp)}` : undefined} />
          </div>
        </section>

        <section>
          <h3 className="text-sm font-semibold text-[var(--foreground)]">Advanced</h3>
          <p className="mt-1 text-xs leading-5 text-[var(--muted)]">
            Diagnostic layer. These metrics help explain impact, efficiency, usage, and coverage, but the v3 model avoids letting overlapping box-derived metrics count in too many places.
          </p>
          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            <MetricBlock label="USG%" value={fmtPercentish(advanced?.usg_pct)} />
            <MetricBlock label="BPM" value={fmtSigned(advanced?.bpm)} />
            <MetricBlock label="VORP" value={fmt(advanced?.vorp)} />
            <MetricBlock label="WS" value={fmt(advanced?.ws)} />
            <MetricBlock label="WS/48" value={fmt(advanced?.win_shares_per_48, 3)} />
            <MetricBlock label="PIE" value={fmtPct(advanced?.pie)} />
            <MetricBlock label="Net" value={fmtSigned(advanced?.net_rating)} />
            <MetricBlock label="External" value={impactCoverage?.external_metrics_present.length ? impactCoverage.external_metrics_present.join(", ") : "None"} sub={impactCoverage?.external_metrics_missing.length ? `${impactCoverage.external_metrics_missing.length} optional missing` : undefined} />
          </div>
        </section>
      </div>

      <div className="mt-6 grid gap-5 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
        <MvpImpactRadar profile={candidate.impact_consensus} playerName={candidate.player_name} />
        <MvpClutchCard clutch={candidate.clutch_profile} />
      </div>

      {candidate.signature_games && candidate.signature_games.length > 0 ? (
        <div className="mt-6">
          <MvpSignatureGames games={candidate.signature_games} />
        </div>
      ) : null}

      <div className="mt-6 grid gap-5 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
        <section>
          <h3 className="text-sm font-semibold text-[var(--foreground)]">Opponent Context</h3>
          <p className="mt-1 text-xs leading-5 text-[var(--muted)]">
            Context and efficiency support. Strong samples against elite defenses can support the Efficiency pillar; broader split rows mainly show whether production travels across opponent quality.
          </p>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            {opponentRows.slice(0, 8).map((row) => (
              <div key={row.key} className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-xs font-semibold text-[var(--foreground)]">{row.label}</p>
                  <span className={`text-[10px] uppercase ${confidenceClass(row.confidence)}`}>{row.confidence}</span>
                </div>
                <div className="mt-2 grid grid-cols-3 gap-2 text-xs text-[var(--muted)]">
                  <span>{row.games} GP</span>
                  <span>{fmt(row.pts_pg)} PPG</span>
                  <span>{fmtPct(row.ts_pct)}</span>
                </div>
              </div>
            ))}
          </div>
          <p className="mt-2 text-xs leading-5 text-[var(--muted)]">
            Best split: {candidate.opponent_context?.best_split ?? "-"} · Pressure point: {candidate.opponent_context?.biggest_weakness ?? "-"}
          </p>
        </section>

        <section>
          <h3 className="text-sm font-semibold text-[var(--foreground)]">Eligibility</h3>
          <p className="mt-1 text-xs leading-5 text-[var(--muted)]">
            Award modifier and availability signal. Missed games do not erase Basketball Value, but the Award Case reflects 65-game pressure and ballot viability.
          </p>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <MetricBlock label="Qualified Games" value={`${eligibility?.eligible_games ?? 0}`} sub={`${eligibility?.games_needed ?? 65} needed`} />
            <MetricBlock label="20+ Minute Games" value={`${eligibility?.minutes_qualified_games ?? 0}`} sub={`${eligibility?.near_miss_games ?? 0} near misses`} />
            <MetricBlock label="Games Played" value={`${eligibility?.games_played ?? candidate.gp}`} />
            <MetricBlock label="Minutes" value={fmt(eligibility?.minutes_played, 0)} />
          </div>
          {eligibility?.warning && (
            <p className="mt-3 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-3 text-xs leading-5 text-[var(--muted)]">
              {eligibility.warning}
            </p>
          )}
        </section>
      </div>

      <div className="mt-6 grid gap-5 lg:grid-cols-2">
        <section>
          <h3 className="text-sm font-semibold text-[var(--foreground)]">Style</h3>
          <p className="mt-1 text-xs leading-5 text-[var(--muted)]">
            Context signal. Style is inferred from play-by-play descriptions, so it explains how value is created rather than acting as a heavy direct ranking input.
          </p>
          <div className="mt-3 space-y-2">
            {topStyle.length ? topStyle.map((row) => (
              <div key={row.action_family} className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-medium text-[var(--foreground)]">{row.label}</p>
                  <span className={`text-xs font-medium ${confidenceClass(row.confidence)}`}>{row.confidence}</span>
                </div>
                <div className="mt-2 grid grid-cols-3 gap-2 text-xs text-[var(--muted)]">
                  <span>Usage {fmtPct(row.usage_share, 1)}</span>
                  <span>PPP {fmt(row.points_per_possession, 2)}</span>
                  <span>EV {fmt(row.ev_score, 2)}</span>
                </div>
              </div>
            )) : (
              <p className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-3 text-sm text-[var(--muted)]">
                No qualifying play-style proxy events yet.
              </p>
            )}
          </div>
          <p className="mt-2 text-xs leading-5 text-[var(--muted)]">
            Style values are inferred from play-by-play descriptions and outcomes.
          </p>
        </section>

        <section>
          <h3 className="text-sm font-semibold text-[var(--foreground)]">Recent Form</h3>
          <p className="mt-1 text-xs leading-5 text-[var(--muted)]">
            Award modifier. Recent form captures how the race feels right now, but it stays capped so a short hot streak cannot overpower the full-season case.
          </p>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <MetricBlock label="PTS Trend" value={fmtSigned(candidate.pts_delta)} sub={`Last ${candidate.last_games} games`} />
            <MetricBlock label="REB Trend" value={fmtSigned(candidate.reb_delta)} />
            <MetricBlock label="AST Trend" value={fmtSigned(candidate.ast_delta)} />
            <MetricBlock label="TS Trend" value={fmtSigned(candidate.ts_delta == null ? null : candidate.ts_delta * 100)} sub="percentage points" />
            <MetricBlock label="Clutch PTS" value={fmt(clutch?.clutch_pts)} sub={`${fmt(clutch?.clutch_fga, 0)} FGA`} />
            <MetricBlock label="Pace PTS" value={`${fmt(clutch?.fast_break_pts, 0)} / ${fmt(clutch?.second_chance_pts, 0)}`} sub="fast break / second chance" />
          </div>
        </section>
      </div>

      {warnings.length > 0 && (
        <div className="mt-6 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-3">
          <p className="text-xs font-semibold uppercase tracking-[0.08em] text-[var(--muted)]">Coverage Notes</p>
          <p className="mt-1 text-xs leading-5 text-[var(--muted)]">
            These notes are part of the confidence system. They flag missing or low-stability evidence so the viewer can judge how much trust to place in the comparison.
          </p>
          <ul className="mt-2 space-y-1 text-xs leading-5 text-[var(--muted)]">
            {warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

export default function MvpRacePanel({ data }: MvpRacePanelProps) {
  const [selectedId, setSelectedId] = useState<number | null>(data.candidates[0]?.player_id ?? null);

  const selected = useMemo(
    () => data.candidates.find((candidate) => candidate.player_id === selectedId) ?? data.candidates[0],
    [data.candidates, selectedId]
  );

  if (data.candidates.length === 0 || !selected) {
    return (
      <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] py-16 text-center text-[var(--muted)]">
        <p className="text-sm">No MVP candidates found for {data.season}.</p>
        <p className="mt-1 text-xs">Requires enough regular-season games and synced season stats.</p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <MvpCaseMap candidates={data.candidates} selectedId={selected.player_id} onSelect={setSelectedId} />
      <div className="grid gap-5 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.35fr)]">
        <div className="space-y-3">
          {data.candidates.map((candidate) => (
            <CandidateRow
              key={candidate.player_id}
              candidate={candidate}
              selected={candidate.player_id === selected.player_id}
              onSelect={() => setSelectedId(candidate.player_id)}
            />
          ))}
        </div>
        <CandidateCase candidate={selected} asOfDate={data.as_of_date} />
      </div>
    </div>
  );
}
