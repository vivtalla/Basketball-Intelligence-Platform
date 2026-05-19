"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getDraftBoard } from "@/lib/api";
import type { DraftProspectSummary, ProspectBoardResponse } from "@/lib/types";
import ConsensusRankCell from "@/components/draft/ConsensusRankCell";
import MockSourcesPill from "@/components/draft/MockSourcesPill";
import TierBadge from "@/components/draft/TierBadge";
// Sprint 102 (Stream A) — design-system primitives.
import HeroHardwood from "@/components/HeroHardwood";
import Reveal from "@/components/Reveal";

const POSITION_OPTIONS = [
  { label: "All positions", value: "" },
  { label: "Guards (PG/SG/G)", value: "PG" },
  { label: "Wings (SG/SF)", value: "SF" },
  { label: "Bigs (PF/C)", value: "C" },
] as const;

const SCHOOL_TYPE_OPTIONS = [
  { label: "All sources", value: "" },
  { label: "NCAA D-I", value: "ncaa" },
  { label: "G League", value: "g_league" },
  { label: "International", value: "international" },
];

const SORT_OPTIONS = [
  { label: "Consensus rank", value: "consensus_rank" },
  { label: "Age", value: "age" },
  { label: "Points (per game)", value: "ppg" },
] as const;

// Sprint 101 — projected_tier filter; matches the analysis service output.
const TIER_OPTIONS = [
  { label: "All tiers", value: "" },
  { label: "Lottery (1-14)", value: "lottery" },
  { label: "1st Round (15-30)", value: "first_round" },
  { label: "2nd Round (31-60)", value: "second_round" },
] as const;

// "Polarizing" filter — prospects whose mock-draft rank stddev exceeds this
// threshold. Empirically σ > 5 captures genuinely-contested evaluations
// without surfacing every partially-ranked outlier.
const POLARIZING_VARIANCE_THRESHOLD = 5;

type SortKey = (typeof SORT_OPTIONS)[number]["value"];

function compareProspects(a: DraftProspectSummary, b: DraftProspectSummary, key: SortKey): number {
  if (key === "ppg") {
    return (b.pts_pg ?? -Infinity) - (a.pts_pg ?? -Infinity);
  }
  if (key === "age") {
    return (a.age_on_draft_day ?? Infinity) - (b.age_on_draft_day ?? Infinity);
  }
  // Prefer consensus_rank_float (Sprint 100 mock aggregate); fall back to
  // legacy integer; then push unranked to the bottom.
  const aRank = a.consensus_rank_float ?? a.consensus_rank ?? 9999;
  const bRank = b.consensus_rank_float ?? b.consensus_rank ?? 9999;
  return aRank - bRank;
}

function PositionPill({ pos }: { pos: string | null }) {
  if (!pos) return null;
  return (
    <span className="rounded-full border border-[var(--border)] bg-[var(--surface-alt)] px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide text-[var(--muted)]">
      {pos}
    </span>
  );
}

function StatCell({ value, digits = 1 }: { value: number | null; digits?: number }) {
  if (value === null || value === undefined) return <span className="text-[var(--muted)]">—</span>;
  return <span>{value.toFixed(digits)}</span>;
}

export default function DraftWorkspacePage() {
  const [year, setYear] = useState(2026);
  const [position, setPosition] = useState<string>("");
  const [schoolType, setSchoolType] = useState<string>("");
  const [sortKey, setSortKey] = useState<SortKey>("consensus_rank");
  // Sprint 101 — client-side filters on the new analysis-service fields.
  const [tier, setTier] = useState<string>("");
  const [polarizingOnly, setPolarizingOnly] = useState<boolean>(false);
  // Sprint 104 (Stream A) — second-round toggle. Default off so the
  // front-page board stays focused on the top-30 consensus; analysts
  // who want deeper coverage flip the switch.
  const [showSecondRound, setShowSecondRound] = useState<boolean>(false);
  const [state, setState] = useState<{
    board: ProspectBoardResponse | null;
    error: string | null;
    isLoading: boolean;
  }>({ board: null, error: null, isLoading: true });
  const { board, error, isLoading } = state;

  useEffect(() => {
    let cancelled = false;
    // Sprint 104 (Stream A) — board now requests up to 90 so ranks 31-90
    // are available client-side; the "Show second round" toggle gates
    // their visibility.
    getDraftBoard(year, { limit: 90, position: position || undefined, schoolType: schoolType || undefined })
      .then((data) => {
        if (!cancelled) setState({ board: data, error: null, isLoading: false });
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : String(err);
          setState({ board: null, error: message, isLoading: false });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [year, position, schoolType]);

  const sorted = useMemo(() => {
    if (!board?.prospects) return [];
    // Apply Sprint 101 client-side filters, then sort.
    const filtered = board.prospects.filter((p) => {
      if (tier && p.projected_tier !== tier) return false;
      if (polarizingOnly && (p.consensus_variance ?? 0) <= POLARIZING_VARIANCE_THRESHOLD) {
        return false;
      }
      // Sprint 104 (Stream A) — hide ranks past the top 30 unless the
      // analyst flips the toggle. Prospects with no consensus_rank fall
      // back to top-30 visibility (treated as borderline).
      if (!showSecondRound) {
        const rank = p.consensus_rank_float ?? p.consensus_rank ?? 0;
        if (rank > 30) return false;
      }
      return true;
    });
    return filtered.sort((a, b) => compareProspects(a, b, sortKey));
  }, [board, sortKey, tier, polarizingOnly, showSecondRound]);

  return (
    <div className="space-y-6">
      <Reveal>
      <header className="bip-panel-strong relative overflow-hidden rounded-[2.2rem] p-6 sm:p-8">
        <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 rounded-[2.2rem] overflow-hidden">
          <HeroHardwood opacity={0.10} />
        </div>
        <p className="bip-kicker">Draft prospect workspace</p>
        <h1 className="bip-display mt-2 text-3xl sm:text-4xl font-bold tracking-tight text-[var(--foreground)]">
          {year} Draft Board
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--muted)]">
          Pre-NBA prospects with pace-adjusted NBA translations and veteran comp matches. Per-game
          numbers come from the prospect&apos;s most-recent league season; the per-100 line projects
          onto NBA pace; comps draw from current NBA player-seasons via z-score similarity.
        </p>

        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <label className="text-xs text-[var(--muted)]">
            Draft year
            <select
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              className="mt-1 w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--foreground)]"
            >
              {[2026, 2027].map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </label>

          <label className="text-xs text-[var(--muted)]">
            Position
            <select
              value={position}
              onChange={(e) => setPosition(e.target.value)}
              className="mt-1 w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--foreground)]"
            >
              {POSITION_OPTIONS.map((opt) => (
                <option key={opt.value || "all"} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </label>

          <label className="text-xs text-[var(--muted)]">
            Source league
            <select
              value={schoolType}
              onChange={(e) => setSchoolType(e.target.value)}
              className="mt-1 w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--foreground)]"
            >
              {SCHOOL_TYPE_OPTIONS.map((opt) => (
                <option key={opt.value || "all"} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </label>

          <label className="text-xs text-[var(--muted)]">
            Sort
            <select
              value={sortKey}
              onChange={(e) => setSortKey(e.target.value as SortKey)}
              className="mt-1 w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--foreground)]"
            >
              {SORT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </label>
        </div>

        {/* Sprint 101 — analyzer-fields filter row */}
        <div className="mt-4 flex flex-wrap items-end gap-3">
          <label className="text-xs text-[var(--muted)]">
            Projected tier
            <select
              value={tier}
              onChange={(e) => setTier(e.target.value)}
              className="mt-1 block rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--foreground)]"
            >
              {TIER_OPTIONS.map((opt) => (
                <option key={opt.value || "all"} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </label>
          <label className="inline-flex items-center gap-2 self-end text-xs text-[var(--muted)]">
            <input
              type="checkbox"
              checked={polarizingOnly}
              onChange={(e) => setPolarizingOnly(e.target.checked)}
              className="h-4 w-4 rounded border-[var(--border)]"
            />
            <span>Polarizing only (σ &gt; {POLARIZING_VARIANCE_THRESHOLD})</span>
          </label>
          {/* Sprint 104 (Stream A) — second-round visibility toggle. */}
          <label className="inline-flex items-center gap-2 self-end text-xs text-[var(--muted)]">
            <input
              type="checkbox"
              checked={showSecondRound}
              onChange={(e) => setShowSecondRound(e.target.checked)}
              className="h-4 w-4 rounded border-[var(--border)]"
            />
            <span>Show second round (ranks 31-60)</span>
          </label>
        </div>
      </header>
      </Reveal>

      {error ? (
        <div className="bip-panel rounded-[1.5rem] border border-[var(--border)] p-6 text-sm text-[var(--danger-ink)]">
          Could not load draft board: {error}
        </div>
      ) : null}

      <Reveal>
      <section className="bip-panel rounded-[1.85rem] overflow-hidden">
        <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-[var(--surface-alt)] text-[var(--muted)]">
            <tr>
              <th className="px-4 py-3 text-left font-semibold uppercase tracking-wide text-[11px]">Rank</th>
              <th className="px-4 py-3 text-left font-semibold uppercase tracking-wide text-[11px]">Tier</th>
              <th className="px-4 py-3 text-left font-semibold uppercase tracking-wide text-[11px]">Prospect</th>
              <th className="px-4 py-3 text-left font-semibold uppercase tracking-wide text-[11px]">Pos</th>
              <th className="px-4 py-3 text-left font-semibold uppercase tracking-wide text-[11px]">School / League</th>
              <th className="px-4 py-3 text-right font-semibold uppercase tracking-wide text-[11px]">Age</th>
              <th className="px-4 py-3 text-right font-semibold uppercase tracking-wide text-[11px]">Ht</th>
              <th className="px-4 py-3 text-right font-semibold uppercase tracking-wide text-[11px]">PPG</th>
              <th className="px-4 py-3 text-right font-semibold uppercase tracking-wide text-[11px]">RPG</th>
              <th className="px-4 py-3 text-right font-semibold uppercase tracking-wide text-[11px]">APG</th>
              <th className="px-4 py-3 text-right font-semibold uppercase tracking-wide text-[11px]">TS%</th>
              <th className="px-4 py-3 text-right font-semibold uppercase tracking-wide text-[11px]">USG%</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && !sorted.length ? (
              <tr>
                <td colSpan={12} className="px-4 py-12 text-center text-[var(--muted)]">Loading prospects…</td>
              </tr>
            ) : null}
            {!isLoading && !sorted.length ? (
              <tr>
                <td colSpan={12} className="px-4 py-12 text-center text-[var(--muted)]">
                  No prospects match the current filter set.
                </td>
              </tr>
            ) : null}
            {sorted.map((p) => (
              <tr key={p.prospect_id} className="border-t border-[var(--border)] hover:bg-[var(--surface-alt)] transition">
                <td className="px-4 py-3">
                  {/* Sprint 101 — show consensus aggregate + N-of-3 source pill. */}
                  <div className="flex items-center gap-2">
                    <ConsensusRankCell
                      consensusRankFloat={p.consensus_rank_float}
                      consensusVariance={p.consensus_variance}
                      consensusRank={p.consensus_rank}
                    />
                    <MockSourcesPill count={p.mock_sources_count} />
                  </div>
                </td>
                <td className="px-4 py-3">
                  <TierBadge tier={p.projected_tier} />
                </td>
                <td className="px-4 py-3">
                  <Link
                    href={`/draft/${p.prospect_id}`}
                    className="font-semibold text-[var(--foreground)] hover:text-[var(--accent)] bip-link"
                  >
                    {p.full_name}
                  </Link>
                </td>
                <td className="px-4 py-3"><PositionPill pos={p.primary_position} /></td>
                <td className="px-4 py-3 text-[var(--muted)]">
                  <div>{p.school ?? "—"}</div>
                  {p.school_type ? (
                    <div className="text-[10px] uppercase tracking-wide">{p.school_type.replace(/_/g, " ")}</div>
                  ) : null}
                </td>
                <td className="px-4 py-3 text-right tabular-nums">
                  <StatCell value={p.age_on_draft_day} />
                </td>
                <td className="px-4 py-3 text-right tabular-nums">
                  {p.height_inches
                    ? `${Math.floor(p.height_inches / 12)}'${(p.height_inches % 12).toFixed(0)}"`
                    : "—"}
                </td>
                <td className="px-4 py-3 text-right tabular-nums"><StatCell value={p.pts_pg} /></td>
                <td className="px-4 py-3 text-right tabular-nums"><StatCell value={p.reb_pg} /></td>
                <td className="px-4 py-3 text-right tabular-nums"><StatCell value={p.ast_pg} /></td>
                <td className="px-4 py-3 text-right tabular-nums">
                  {p.ts_pct !== null && p.ts_pct !== undefined ? `${(p.ts_pct * 100).toFixed(1)}%` : "—"}
                </td>
                <td className="px-4 py-3 text-right tabular-nums">
                  <StatCell value={p.usg_pct} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      </section>
      </Reveal>
    </div>
  );
}
