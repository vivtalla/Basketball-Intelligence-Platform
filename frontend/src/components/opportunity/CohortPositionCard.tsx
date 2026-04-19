"use client";

import type { OpportunityPlayerRow } from "@/lib/types";

interface Props {
  row: OpportunityPlayerRow;
}

function pill(label: string, value: string, tone: "neutral" | "pos" | "neg" = "neutral") {
  const toneClass =
    tone === "pos"
      ? "text-[var(--accent-strong)]"
      : tone === "neg"
      ? "text-[var(--danger-ink)]"
      : "text-[var(--foreground)]";
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-2">
      <div className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">
        {label}
      </div>
      <div className={`text-lg font-semibold tabular-nums ${toneClass}`}>{value}</div>
    </div>
  );
}

export function CohortPositionCard({ row }: Props) {
  const pct = row.cohort_percentile;
  return (
    <section className="rounded-[1.25rem] border border-[var(--border)] bg-[var(--surface)] p-4">
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
        Position Cohort Position
      </p>
      <h3 className="mt-0.5 text-base font-semibold text-[var(--foreground)]">
        Where he sits vs {row.position_bucket} peers
      </h3>
      <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {pill(
          "Cohort %ile",
          pct != null ? `${pct.toFixed(0)}th` : "—",
          pct != null ? (pct >= 70 ? "pos" : pct <= 30 ? "neg" : "neutral") : "neutral"
        )}
        {pill(
          "Opportunity Score",
          `${row.opportunity_score > 0 ? "+" : ""}${row.opportunity_score.toFixed(2)}`,
          row.opportunity_score > 0 ? "pos" : row.opportunity_score < 0 ? "neg" : "neutral"
        )}
        {pill(
          "Team Score",
          row.team_opportunity_score != null
            ? `${row.team_opportunity_score > 0 ? "+" : ""}${row.team_opportunity_score.toFixed(2)}`
            : "—"
        )}
        {pill(
          "GP",
          row.gp != null ? String(row.gp) : "—"
        )}
      </div>
      <p className="mt-3 text-[11px] leading-5 text-[var(--muted-strong)]">
        Cohort percentile reflects the player&apos;s blend of per-100 scoring and net
        rating within his position bucket. Team score uses the same signals but
        re-scaled against the current roster — context, not ranking.
      </p>
    </section>
  );
}
