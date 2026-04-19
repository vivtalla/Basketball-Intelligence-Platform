"use client";

import type { OpportunityPlayerRow } from "@/lib/types";
import { OpportunityDriverBar, SIGNAL_LABELS } from "./OpportunityDriverBar";

function confidencePill(confidence: OpportunityPlayerRow["confidence"]) {
  if (confidence === "high") {
    return "bg-[rgba(33,72,59,0.1)] text-[var(--accent-strong)]";
  }
  if (confidence === "medium") {
    return "bg-[rgba(181,145,78,0.12)] text-[rgb(123,93,42)]";
  }
  return "bg-[rgba(47,43,36,0.08)] text-[var(--muted-strong)]";
}

interface Props {
  row: OpportunityPlayerRow;
  rank: number;
  isSelected: boolean;
  onSelect: () => void;
}

export function OpportunityRow({ row, rank, isSelected, onSelect }: Props) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full rounded-[1.25rem] border bg-[rgba(255,255,255,0.75)] p-4 text-left transition ${
        isSelected
          ? "border-[var(--accent-strong)] shadow-[0_12px_36px_rgba(33,72,59,0.14)]"
          : "border-[var(--border)] hover:border-[var(--accent-strong)]"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
            #{rank}
            {row.position ? ` · ${row.position}` : ""}
          </div>
          <div className="mt-1 truncate text-lg font-semibold text-[var(--foreground)]">
            {row.player_name}{" "}
            <span className="text-sm font-medium text-[var(--muted-strong)]">
              {row.team_abbreviation}
            </span>
          </div>
          <div className="mt-1 text-xs text-[var(--muted)]">
            {row.minutes_pg != null ? `${row.minutes_pg.toFixed(1)} MPG` : "— MPG"} ·{" "}
            USG {row.usg_pct != null ? row.usg_pct.toFixed(1) : "—"} · TS{" "}
            {row.ts_pct != null ? `${(row.ts_pct * 100).toFixed(1)}%` : "—"}
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
          <div
            className="rounded-full bg-[var(--surface-alt)] px-3 py-1 text-sm font-semibold tabular-nums text-[var(--foreground)]"
            title="Opportunity Score — composite of five capped z-scores"
          >
            {row.opportunity_score > 0 ? "+" : ""}
            {row.opportunity_score.toFixed(2)}
          </div>
          <span
            className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] ${confidencePill(row.confidence)}`}
          >
            {row.confidence}
          </span>
        </div>
      </div>
      <div className="mt-3">
        <OpportunityDriverBar contributions={row.driver_contributions} compact />
      </div>
      {row.top_driver ? (
        <div className="mt-2 text-[11px] text-[var(--muted-strong)]">
          Top driver ·{" "}
          <span className="font-semibold text-[var(--foreground)]">
            {SIGNAL_LABELS[row.top_driver] ?? row.top_driver}
          </span>
          {row.cohort_percentile != null
            ? ` · cohort ${row.cohort_percentile.toFixed(0)}th`
            : null}
        </div>
      ) : null}
    </button>
  );
}
