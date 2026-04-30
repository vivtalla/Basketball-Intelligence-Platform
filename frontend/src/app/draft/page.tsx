"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getDraftBoard } from "@/lib/api";
import type { DraftProspectSummary, ProspectBoardResponse } from "@/lib/types";

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

type SortKey = (typeof SORT_OPTIONS)[number]["value"];

function compareProspects(a: DraftProspectSummary, b: DraftProspectSummary, key: SortKey): number {
  if (key === "ppg") {
    return (b.pts_pg ?? -Infinity) - (a.pts_pg ?? -Infinity);
  }
  if (key === "age") {
    return (a.age_on_draft_day ?? Infinity) - (b.age_on_draft_day ?? Infinity);
  }
  return (a.consensus_rank ?? 9999) - (b.consensus_rank ?? 9999);
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
  const [board, setBoard] = useState<ProspectBoardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);
    getDraftBoard(year, { limit: 60, position: position || undefined, schoolType: schoolType || undefined })
      .then((data) => {
        if (!cancelled) setBoard(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : String(err);
          setError(message);
          setBoard(null);
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [year, position, schoolType]);

  const sorted = useMemo(() => {
    if (!board?.prospects) return [];
    return [...board.prospects].sort((a, b) => compareProspects(a, b, sortKey));
  }, [board, sortKey]);

  return (
    <div className="space-y-6">
      <header className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5">
        <p className="bip-kicker">Draft prospect workspace</p>
        <h1 className="bip-display mt-2 text-3xl font-bold tracking-tight text-[var(--foreground)]">
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
      </header>

      {error ? (
        <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-6 text-sm text-[var(--danger-ink)]">
          Could not load draft board: {error}
        </div>
      ) : null}

      <section className="rounded-lg border border-[var(--border)] bg-[var(--surface)] overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-[var(--surface-alt)] text-[var(--muted)]">
            <tr>
              <th className="px-4 py-3 text-left font-semibold uppercase tracking-wide text-[11px]">Rank</th>
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
                <td colSpan={11} className="px-4 py-12 text-center text-[var(--muted)]">Loading prospects…</td>
              </tr>
            ) : null}
            {!isLoading && !sorted.length ? (
              <tr>
                <td colSpan={11} className="px-4 py-12 text-center text-[var(--muted)]">
                  No prospects match the current filter set.
                </td>
              </tr>
            ) : null}
            {sorted.map((p) => (
              <tr key={p.prospect_id} className="border-t border-[var(--border)] hover:bg-[var(--surface-alt)] transition">
                <td className="px-4 py-3 text-[var(--muted)] tabular-nums">
                  {p.consensus_rank ?? "—"}
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
      </section>
    </div>
  );
}
