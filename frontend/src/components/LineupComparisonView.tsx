"use client";

import Link from "next/link";
import type { LineupStatsResponse } from "@/lib/types";

interface LineupComparisonViewProps {
  teamAAbbr: string;
  teamBAbbr: string;
  teamAName: string;
  teamBName: string;
  season: string;
  teamALineups: LineupStatsResponse[];
  teamBLineups: LineupStatsResponse[];
  selectedLineupA: string | null;
  selectedLineupB: string | null;
  onSelectLineupA: (lineupKey: string) => void;
  onSelectLineupB: (lineupKey: string) => void;
}

function fmt(value: number | null | undefined, digits = 1) {
  return value == null ? "—" : value.toFixed(digits);
}

function signed(value: number | null | undefined, digits = 1) {
  if (value == null) return "—";
  return `${value > 0 ? "+" : ""}${value.toFixed(digits)}`;
}

function lineupTone(value: number | null | undefined) {
  if (value == null) return "text-[var(--muted-strong)]";
  return value >= 0 ? "text-[var(--accent-strong)]" : "text-[var(--danger-ink)]";
}

function selectedLineup(
  lineups: LineupStatsResponse[],
  selectedKey: string | null
) {
  return lineups.find((lineup) => lineup.lineup_key === selectedKey) ?? lineups[0] ?? null;
}

function LineupSummary({
  title,
  lineup,
}: {
  title: string;
  lineup: LineupStatsResponse | null;
}) {
  return (
    <article className="rounded-[1.5rem] border border-[var(--border)] bg-[rgba(255,255,255,0.72)] p-5">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">{title}</p>
      {lineup ? (
        <>
          <h3 className="mt-2 text-xl font-semibold text-[var(--foreground)]">
            {lineup.player_names.join(" · ")}
          </h3>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-2xl bip-metric p-4">
              <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">Minutes</div>
              <div className="mt-2 text-2xl font-semibold text-[var(--foreground)]">{fmt(lineup.minutes)}</div>
            </div>
            <div className="rounded-2xl bip-metric p-4">
              <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">Possessions</div>
              <div className="mt-2 text-2xl font-semibold text-[var(--foreground)]">{lineup.possessions ?? "—"}</div>
            </div>
            <div className="rounded-2xl bip-metric p-4">
              <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">ORTG</div>
              <div className={`mt-2 text-2xl font-semibold ${lineupTone(lineup.ortg)}`}>{fmt(lineup.ortg)}</div>
            </div>
            <div className="rounded-2xl bip-metric p-4">
              <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">DRTG</div>
              <div className="mt-2 text-2xl font-semibold text-[var(--foreground)]">{fmt(lineup.drtg)}</div>
            </div>
          </div>
          <div className="mt-4 rounded-2xl bip-accent-card p-4">
            <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--accent)]">Net rating</div>
            <div className={`mt-2 text-3xl font-semibold ${lineupTone(lineup.net_rating)}`}>
              {signed(lineup.net_rating)}
            </div>
            <div className="mt-1 text-sm text-[var(--muted)]">
              {lineup.plus_minus != null ? `Plus/minus ${signed(lineup.plus_minus)}` : "Plus/minus not available"}
            </div>
          </div>
        </>
      ) : (
        <div className="bip-empty mt-4 rounded-2xl p-4 text-sm">
          No lineup data is available yet for this team.
        </div>
      )}
    </article>
  );
}

export default function LineupComparisonView({
  teamAAbbr,
  teamBAbbr,
  teamAName,
  teamBName,
  season,
  teamALineups,
  teamBLineups,
  selectedLineupA,
  selectedLineupB,
  onSelectLineupA,
  onSelectLineupB,
}: LineupComparisonViewProps) {
  const lineupA = selectedLineup(teamALineups, selectedLineupA);
  const lineupB = selectedLineup(teamBLineups, selectedLineupB);
  const lineupGap =
    lineupA?.net_rating != null && lineupB?.net_rating != null
      ? lineupA.net_rating - lineupB.net_rating
      : null;

  return (
    <div className="space-y-6">
      <section className="grid gap-4 lg:grid-cols-2">
        <label className="space-y-2">
          <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            {teamAAbbr} lineup
          </span>
          <select
            value={selectedLineupA ?? ""}
            onChange={(event) => onSelectLineupA(event.target.value)}
            className="bip-input w-full rounded-2xl px-4 py-3 text-sm"
          >
            {teamALineups.length ? (
              teamALineups.map((lineup) => (
                <option key={lineup.lineup_key} value={lineup.lineup_key}>
                  {lineup.player_names.join(" · ")} ({fmt(lineup.minutes)} min)
                </option>
              ))
            ) : (
              <option value="">No lineups available</option>
            )}
          </select>
        </label>
        <label className="space-y-2">
          <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            {teamBAbbr} lineup
          </span>
          <select
            value={selectedLineupB ?? ""}
            onChange={(event) => onSelectLineupB(event.target.value)}
            className="bip-input w-full rounded-2xl px-4 py-3 text-sm"
          >
            {teamBLineups.length ? (
              teamBLineups.map((lineup) => (
                <option key={lineup.lineup_key} value={lineup.lineup_key}>
                  {lineup.player_names.join(" · ")} ({fmt(lineup.minutes)} min)
                </option>
              ))
            ) : (
              <option value="">No lineups available</option>
            )}
          </select>
        </label>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <LineupSummary title={teamAName} lineup={lineupA} />
        <LineupSummary title={teamBName} lineup={lineupB} />
      </section>

      <section className="rounded-[1.75rem] border border-[var(--border)] bg-[var(--surface)] p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
          Coaching read
        </p>
        <h3 className="mt-2 text-2xl font-semibold text-[var(--foreground)]">
          What the selected lineups suggest
        </h3>
        <p className="mt-3 text-sm leading-6 text-[var(--muted-strong)]">
          {lineupGap == null
            ? "Pick a lineup on each side to get a clean rotation read."
            : `${teamAAbbr} is ${lineupGap >= 0 ? "ahead" : "behind"} by ${signed(lineupGap)} net rating in the selected lineup comparison. Use that gap as a starting point, not a final verdict.`}
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <Link
            href={`/teams/${teamAAbbr}?tab=lineups`}
            className="rounded-full border border-[var(--border-strong)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]"
          >
            Open {teamAAbbr} lineups
          </Link>
          <Link
            href={`/teams/${teamBAbbr}?tab=lineups`}
            className="rounded-full border border-[var(--border-strong)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]"
          >
            Open {teamBAbbr} lineups
          </Link>
          <Link
            href={`/pre-read?team=${teamAAbbr}&opponent=${teamBAbbr}&season=${season}`}
            className="rounded-full border border-[var(--border-strong)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]"
          >
            Open pre-read
          </Link>
        </div>
      </section>
    </div>
  );
}
