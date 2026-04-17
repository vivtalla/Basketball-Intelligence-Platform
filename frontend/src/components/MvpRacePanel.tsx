"use client";

import { useMemo, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import type { MvpCandidate, MvpRaceResponse, MvpScorePillar } from "@/lib/types";

interface MvpRacePanelProps {
  data: MvpRaceResponse;
}

const PILLAR_ORDER = ["production", "efficiency", "impact", "team_context", "momentum", "play_style"];

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

function confidenceClass(confidence: string | null | undefined): string {
  if (confidence === "high") return "text-[var(--success-ink)]";
  if (confidence === "medium") return "text-[var(--accent)]";
  return "text-[var(--muted)]";
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

function CandidateRow({
  candidate,
  selected,
  onSelect,
}: {
  candidate: MvpCandidate;
  selected: boolean;
  onSelect: () => void;
}) {
  const pillars = candidate.score_pillars ?? {};
  const impact = pillars.impact?.display_score;
  const team = candidate.team_context;

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
          </div>
          <p className="mt-0.5 text-xs text-[var(--muted)]">
            {candidate.team_abbreviation} - {candidate.gp} GP - Score {fmt(candidate.composite_score, 1)}
          </p>
        </div>
      </div>
      <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
        <StatTile label="PTS" value={fmt(candidate.pts_pg)} />
        <StatTile label="TS" value={fmtPct(candidate.ts_pct)} />
        <StatTile label="Impact" value={impact == null ? "-" : fmt(impact, 0)} />
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

function CandidateCase({ candidate, asOfDate }: { candidate: MvpCandidate; asOfDate: string }) {
  const pillars = candidate.score_pillars ?? {};
  const warnings = candidate.data_coverage?.warnings ?? [];
  const styleRows = candidate.play_style ?? [];
  const topStyle = styleRows.slice(0, 4);
  const advanced = candidate.advanced_profile;
  const onOff = candidate.on_off;
  const clutch = candidate.clutch_and_pace;
  const team = candidate.team_context;

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
            Score {fmt(candidate.composite_score, 1)} from production, efficiency, impact, team context, momentum, and transparent style proxies.
          </p>
        </div>
        <Link href={`/players/${candidate.player_id}`} className="rounded-lg border border-[var(--border)] px-3 py-2 text-sm font-medium text-[var(--accent)] hover:border-[var(--accent)]">
          Player profile
        </Link>
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-3">
        <MetricBlock label="Production" value={`${fmt(candidate.pts_pg)} / ${fmt(candidate.reb_pg)} / ${fmt(candidate.ast_pg)}`} sub="PTS / REB / AST" />
        <MetricBlock label="Efficiency" value={fmtPct(candidate.ts_pct)} sub={`eFG ${fmtPct(advanced?.efg_pct)}`} />
        <MetricBlock label="Impact" value={fmtSigned(onOff?.on_off_net)} sub={`On/off confidence ${onOff?.confidence ?? "low"}`} />
      </div>

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
          <h3 className="text-sm font-semibold text-[var(--foreground)]">Score Pillars</h3>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            {PILLAR_ORDER.map((key) => pillars[key]).filter(Boolean).map((pillar) => (
              <PillarBar key={pillar.label} pillar={pillar} />
            ))}
          </div>
        </div>
      </div>

      <div className="mt-6 grid gap-5 lg:grid-cols-2">
        <section>
          <h3 className="text-sm font-semibold text-[var(--foreground)]">Team Lift</h3>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <MetricBlock label="Team Record" value={team?.wins != null && team.losses != null ? `${team.wins}-${team.losses}` : "-"} sub={team?.win_pct_rank ? `Win% rank ${team.win_pct_rank}` : undefined} />
            <MetricBlock label="Team Net" value={fmtSigned(team?.net_rating)} sub={team?.net_rating_rank ? `Net rank ${team.net_rating_rank}` : undefined} />
            <MetricBlock label="On Net" value={fmtSigned(onOff?.on_net_rating)} sub={`${fmt(onOff?.on_minutes, 0)} on minutes`} />
            <MetricBlock label="Off Net" value={fmtSigned(onOff?.off_net_rating)} sub={`${fmt(onOff?.off_minutes, 0)} off minutes`} />
          </div>
        </section>

        <section>
          <h3 className="text-sm font-semibold text-[var(--foreground)]">Advanced</h3>
          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            <MetricBlock label="USG%" value={fmtPct(advanced?.usg_pct)} />
            <MetricBlock label="BPM" value={fmtSigned(advanced?.bpm)} />
            <MetricBlock label="VORP" value={fmt(advanced?.vorp)} />
            <MetricBlock label="WS" value={fmt(advanced?.ws)} />
            <MetricBlock label="WS/48" value={fmt(advanced?.win_shares_per_48, 3)} />
            <MetricBlock label="PIE" value={fmtPct(advanced?.pie)} />
            <MetricBlock label="Net" value={fmtSigned(advanced?.net_rating)} />
          </div>
        </section>
      </div>

      <div className="mt-6 grid gap-5 lg:grid-cols-2">
        <section>
          <h3 className="text-sm font-semibold text-[var(--foreground)]">Style</h3>
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
  );
}
