"use client";

import { useState } from "react";
import type { TeamShootingSplitRow, TeamShootingSplitsResponse } from "@/lib/types";

interface TeamShootingSplitsPanelProps {
  splits: TeamShootingSplitsResponse;
}

const FAMILY_LABELS: Record<string, string> = {
  ShotAreaTeamDashboard: "Shot Area",
  ShotTypeTeamDashboard: "Shot Type",
  Shot8FTTeamDashboard: "Shot Distance (8ft)",
  Shot5FTTeamDashboard: "Shot Distance (5ft)",
  AssitedShotTeamDashboard: "Assisted Shot",
  OverallTeamDashboard: "Overall",
};

const FAMILY_ORDER = [
  "ShotAreaTeamDashboard",
  "ShotTypeTeamDashboard",
  "Shot8FTTeamDashboard",
  "Shot5FTTeamDashboard",
  "AssitedShotTeamDashboard",
  "OverallTeamDashboard",
];

function fmt(value: number | null | undefined, digits = 1): string {
  if (value == null) return "—";
  return value.toFixed(digits);
}

function fmtPct(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

function AssistedMix({ row }: { row: TeamShootingSplitRow }) {
  if (row.pct_ast_fgm == null && row.pct_uast_fgm == null) {
    return <span className="text-[var(--muted)]">—</span>;
  }
  return (
    <span className="tabular-nums text-[var(--muted-strong)]">
      {fmtPct(row.pct_ast_fgm)} / {fmtPct(row.pct_uast_fgm)}
    </span>
  );
}

function ShootingTable({ rows }: { rows: TeamShootingSplitRow[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--border)]">
            <th className="py-2 pr-4 text-left text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
              Split
            </th>
            <th className="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
              FGA
            </th>
            <th className="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
              FG%
            </th>
            <th className="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
              3PA
            </th>
            <th className="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
              3P%
            </th>
            <th className="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
              eFG%
            </th>
            <th className="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
              Ast / UAst
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--border)]">
          {rows.map((row) => (
            <tr
              key={`${row.split_family}-${row.split_value}`}
              className="transition-colors hover:bg-[rgba(255,255,255,0.4)]"
            >
              <td className="py-3 pr-4 font-medium text-[var(--foreground)]">{row.label}</td>
              <td className="px-3 py-3 text-right tabular-nums text-[var(--muted-strong)]">{fmt(row.fga, 0)}</td>
              <td className="px-3 py-3 text-right tabular-nums text-[var(--muted-strong)]">{fmtPct(row.fg_pct)}</td>
              <td className="px-3 py-3 text-right tabular-nums text-[var(--muted-strong)]">{fmt(row.fg3a, 0)}</td>
              <td className="px-3 py-3 text-right tabular-nums text-[var(--muted-strong)]">{fmtPct(row.fg3_pct)}</td>
              <td className="px-3 py-3 text-right tabular-nums font-semibold text-[var(--foreground)]">{fmtPct(row.efg_pct)}</td>
              <td className="px-3 py-3 text-right text-[11px]"><AssistedMix row={row} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function TeamShootingSplitsPanel({ splits }: TeamShootingSplitsPanelProps) {
  const families = FAMILY_ORDER.filter((family) =>
    splits.splits.some((row) => row.split_family === family)
  );
  const [activeFamily, setActiveFamily] = useState<string>(families[0] ?? "");
  const activeRows = splits.splits.filter((row) => row.split_family === activeFamily);

  if (splits.splits.length === 0) {
    return (
      <div className="bip-panel rounded-[1.8rem] p-6 text-sm leading-6 text-[var(--muted-strong)]">
        No shooting split data available for {splits.abbreviation} {splits.season}. Run an official sync
        to populate this view.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section className="bip-panel-strong rounded-[2rem] p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="bip-kicker">Shooting Splits</p>
            <h2 className="bip-display mt-3 text-3xl font-semibold text-[var(--foreground)]">
              Team shot profile by bucket
            </h2>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-[var(--muted-strong)]">
              Official shooting dashboards showing where the attempts come from, how the team converts
              them, and how much of the profile is assisted versus self-created.
            </p>
          </div>
          <div className="space-y-1 text-right">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
              {splits.season}
            </p>
            {splits.canonical_source ? (
              <p className="text-xs text-[var(--muted)]">Source: {splits.canonical_source}</p>
            ) : null}
            {splits.last_synced_at ? (
              <p className="text-xs text-[var(--muted)]">
                Synced {new Date(splits.last_synced_at).toLocaleDateString()}
              </p>
            ) : null}
          </div>
        </div>

        <div className="mt-6 flex flex-wrap gap-2">
          {families.map((family) => (
            <button
              key={family}
              type="button"
              onClick={() => setActiveFamily(family)}
              className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                activeFamily === family ? "bip-toggle-active" : "bip-toggle"
              }`}
            >
              {FAMILY_LABELS[family] ?? family}
            </button>
          ))}
        </div>
      </section>

      {activeRows.length > 0 ? (
        <section className="bip-panel rounded-[1.8rem] p-6">
          <h3 className="mb-4 text-sm font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            {FAMILY_LABELS[activeFamily] ?? activeFamily}
          </h3>
          <ShootingTable rows={activeRows} />
        </section>
      ) : null}
    </div>
  );
}
