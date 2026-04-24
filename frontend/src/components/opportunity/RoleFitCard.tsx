"use client";

import Link from "next/link";
import type { OpportunityPlayerRow } from "@/lib/types";

interface Props {
  row: OpportunityPlayerRow;
}

function pctText(value: number | null | undefined): string {
  return value == null ? "—" : `${(value * 100).toFixed(1)}%`;
}

function numText(value: number | null | undefined): string {
  return value == null ? "—" : value.toFixed(1);
}

function deltaText(a: number | null | undefined, b: number | null | undefined): string {
  if (a == null || b == null) return "—";
  const d = (a - b) * 100;
  return `${d >= 0 ? "+" : ""}${d.toFixed(1)} pp`;
}

function deltaNum(a: number | null | undefined, b: number | null | undefined): string {
  if (a == null || b == null) return "—";
  const d = a - b;
  return `${d >= 0 ? "+" : ""}${d.toFixed(1)}`;
}

export function RoleFitCard({ row }: Props) {
  const rf = row.role_fit;
  if (!rf) return null;
  const rows: Array<{
    label: string;
    player: number | null | undefined;
    cohort: number | null | undefined;
    hint: string;
    format: "pct" | "num";
  }> = [
    {
      label: "3PA rate",
      player: rf.par3,
      cohort: rf.par3_bucket_avg,
      hint: "Share of field-goal attempts from three",
      format: "pct",
    },
    {
      label: "FT rate",
      player: rf.ftr,
      cohort: rf.ftr_bucket_avg,
      hint: "Free-throw attempts per field-goal attempt",
      format: "pct",
    },
    {
      label: "eFG%",
      player: rf.efg_pct,
      cohort: rf.efg_bucket_avg,
      hint: "Effective field-goal percentage",
      format: "pct",
    },
    {
      label: "AST/G",
      player: rf.ast_pg,
      cohort: rf.ast_bucket_avg,
      hint: "Assists per game vs position cohort",
      format: "num",
    },
    {
      label: "TOV/G",
      player: rf.tov_pg,
      cohort: rf.tov_bucket_avg,
      hint: "Turnovers per game vs position cohort — lower is better",
      format: "num",
    },
  ];
  return (
    <section className="rounded-[1.25rem] border border-[var(--border)] bg-[var(--surface)] p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Role Fit · Shot Diet
          </p>
          <h3 className="mt-0.5 text-base font-semibold text-[var(--foreground)]">
            How his shot profile compares to his position
          </h3>
        </div>
        <div className="flex items-center gap-1.5">
          {row.compare_handoff && row.compare_handoff.positional_peers.length > 0 ? (
            <Link
              href={`/compare?mode=players&p1=${row.compare_handoff.pinned_player_id}&p2=${row.compare_handoff.positional_peers[0]}&source=opportunity&cohort=${row.compare_handoff.cohort_bucket}&peers=${row.compare_handoff.positional_peers.join(",")}`}
              className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1 text-[11px] font-medium text-[var(--muted-strong)] transition hover:border-[var(--accent-strong)] hover:text-[var(--accent-strong)]"
              title={`Compare vs top positional peer (${row.compare_handoff.positional_peers.length} available)`}
            >
              Compare with peers →
            </Link>
          ) : null}
          <Link
            href={`/players/${row.player_id}?tab=shots`}
            className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1 text-[11px] font-medium text-[var(--muted-strong)] transition hover:border-[var(--accent-strong)] hover:text-[var(--accent-strong)]"
          >
            Open Shot Lab →
          </Link>
        </div>
      </div>
      <ul className="mt-3 divide-y divide-[var(--border)] rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] text-sm">
        {rows.map((r) => (
          <li
            key={r.label}
            className="grid grid-cols-4 items-center gap-2 px-3 py-2"
            title={r.hint}
          >
            <span className="text-[11px] uppercase tracking-[0.14em] text-[var(--muted)]">
              {r.label}
            </span>
            <span className="text-right font-semibold tabular-nums text-[var(--foreground)]">
              {r.format === "pct" ? pctText(r.player) : numText(r.player)}
            </span>
            <span className="text-right text-xs text-[var(--muted-strong)]">
              vs {r.format === "pct" ? pctText(r.cohort) : numText(r.cohort)}
            </span>
            <span className="text-right text-xs font-semibold tabular-nums text-[var(--muted-strong)]">
              {r.format === "pct" ? deltaText(r.player, r.cohort) : deltaNum(r.player, r.cohort)}
            </span>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-[11px] leading-5 text-[var(--muted-strong)]">
        A low 3PA rate combined with high eFG% often signals an untapped shot-mix lever.
        Pair with the on/off card before committing to a redistribution.
      </p>
    </section>
  );
}
