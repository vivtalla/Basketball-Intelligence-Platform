"use client";

import { useState } from "react";
import type { TeamSplitsResponse, TeamSplitRow } from "@/lib/types";

interface TeamSplitsPanelProps {
  splits: TeamSplitsResponse;
}

const FAMILY_LABELS: Record<string, string> = {
  Location: "Home / Away",
  "Win/Loss": "W / L",
  "Days Rest": "Days Rest",
  Month: "Month",
  "Pre/Post All-Star": "Pre / Post All-Star",
};

const FAMILY_ORDER = ["Location", "Win/Loss", "Days Rest", "Month", "Pre/Post All-Star"];

function fmt(value: number | null | undefined, digits = 1): string {
  if (value == null) return "—";
  return value.toFixed(digits);
}

function fmtPct(value: number | null | undefined): string {
  if (value == null) return "—";
  return (value * 100).toFixed(1) + "%";
}

function fmtPlusMinus(value: number | null | undefined): string {
  if (value == null) return "—";
  return (value >= 0 ? "+" : "") + value.toFixed(1);
}

function plusMinusTone(value: number | null | undefined): string {
  if (value == null) return "text-[var(--muted)]";
  return value > 0 ? "text-[var(--success-ink)]" : value < 0 ? "text-[var(--danger-ink)]" : "text-[var(--muted)]";
}

function wPctTone(value: number): string {
  if (value >= 0.6) return "text-[var(--success-ink)]";
  if (value >= 0.45) return "text-[var(--foreground)]";
  return "text-[var(--danger-ink)]";
}

function SplitTable({ rows }: { rows: TeamSplitRow[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--border)]">
            <th className="py-2 pr-4 text-left text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
              Split
            </th>
            <th className="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
              GP
            </th>
            <th className="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
              W
            </th>
            <th className="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
              L
            </th>
            <th className="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
              W%
            </th>
            <th className="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
              PTS
            </th>
            <th className="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
              AST
            </th>
            <th className="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
              REB
            </th>
            <th className="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
              FG%
            </th>
            <th className="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
              +/-
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--border)]">
          {rows.map((row) => (
            <tr
              key={`${row.split_family}-${row.split_value}`}
              className="hover:bg-[rgba(255,255,255,0.4)] transition-colors"
            >
              <td className="py-3 pr-4 font-medium text-[var(--foreground)]">
                {row.label}
              </td>
              <td className="px-3 py-3 text-right tabular-nums text-[var(--muted-strong)]">
                {row.gp}
              </td>
              <td className="px-3 py-3 text-right tabular-nums text-[var(--muted-strong)]">
                {row.w}
              </td>
              <td className="px-3 py-3 text-right tabular-nums text-[var(--muted-strong)]">
                {row.l}
              </td>
              <td className={`px-3 py-3 text-right tabular-nums font-semibold ${wPctTone(row.w_pct)}`}>
                {fmtPct(row.w_pct)}
              </td>
              <td className="px-3 py-3 text-right tabular-nums text-[var(--muted-strong)]">
                {fmt(row.pts)}
              </td>
              <td className="px-3 py-3 text-right tabular-nums text-[var(--muted-strong)]">
                {fmt(row.ast)}
              </td>
              <td className="px-3 py-3 text-right tabular-nums text-[var(--muted-strong)]">
                {fmt(row.reb)}
              </td>
              <td className="px-3 py-3 text-right tabular-nums text-[var(--muted-strong)]">
                {fmtPct(row.fg_pct)}
              </td>
              <td className={`px-3 py-3 text-right tabular-nums font-semibold ${plusMinusTone(row.plus_minus)}`}>
                {fmtPlusMinus(row.plus_minus)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function TeamSplitsPanel({ splits }: TeamSplitsPanelProps) {
  const families = FAMILY_ORDER.filter((f) =>
    splits.splits.some((r) => r.split_family === f)
  );

  const otherFamilies = Array.from(
    new Set(splits.splits.map((r) => r.split_family))
  ).filter((f) => !FAMILY_ORDER.includes(f));

  const allFamilies = [...families, ...otherFamilies];

  const [activeFamily, setActiveFamily] = useState<string>(allFamilies[0] ?? "");

  const activeRows = splits.splits.filter((r) => r.split_family === activeFamily);

  if (splits.splits.length === 0) {
    return (
      <div className="bip-panel rounded-[1.8rem] p-6 text-sm leading-6 text-[var(--muted-strong)]">
        No split data available for {splits.abbreviation} {splits.season}. Run a splits sync to populate this view.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section className="bip-panel-strong rounded-[2rem] p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="bip-kicker">Situational Splits</p>
            <h2 className="bip-display mt-3 text-3xl font-semibold text-[var(--foreground)]">
              Team performance by game context
            </h2>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-[var(--muted-strong)]">
              Official general split data showing how this team performs across location, win/loss record, days rest, month, and schedule position.
            </p>
          </div>
          <div className="text-right space-y-1">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
              {splits.season}
            </p>
            {splits.canonical_source && (
              <p className="text-xs text-[var(--muted)]">
                Source: {splits.canonical_source}
              </p>
            )}
            {splits.last_synced_at && (
              <p className="text-xs text-[var(--muted)]">
                Synced {new Date(splits.last_synced_at).toLocaleDateString()}
              </p>
            )}
          </div>
        </div>

        {/* Family toggle */}
        <div className="mt-6 flex flex-wrap gap-2">
          {allFamilies.map((family) => (
            <button
              key={family}
              type="button"
              onClick={() => setActiveFamily(family)}
              className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                activeFamily === family
                  ? "bip-toggle-active"
                  : "bip-toggle"
              }`}
            >
              {FAMILY_LABELS[family] ?? family}
            </button>
          ))}
        </div>
      </section>

      {activeRows.length > 0 && (
        <section className="bip-panel rounded-[1.8rem] p-6">
          <h3 className="mb-4 text-sm font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            {FAMILY_LABELS[activeFamily] ?? activeFamily}
          </h3>
          <SplitTable rows={activeRows} />
        </section>
      )}
    </div>
  );
}
