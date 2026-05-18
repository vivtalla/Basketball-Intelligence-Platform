// Sprint 101 (Stream B) — outcome-aware NBA comps grid.
//
// Each card: comp player name, similarity score, outcome_tier badge,
// career_summary chips. Sorted by similarity descending. Shows the
// neighbourhood_confidence chip at the top of the section (high/medium/
// low — derived in Sprint 100's comp service from tier homogeneity).
//
// Falls back to nothing when the array is empty — the parent prospect-
// detail page keeps the v1 nba_comps grid as the visible-by-default fallback,
// so removing this section doesn't leave the page comp-less.

import type { HistoricalComp } from "@/lib/types";
import TierBadge from "./TierBadge";

interface Props {
  comps: HistoricalComp[] | null | undefined;
}

function NeighbourhoodConfidenceChip({ confidence }: { confidence: string | null | undefined }) {
  if (!confidence) return null;
  const styles: Record<string, { bg: string; color: string; label: string }> = {
    high:   { bg: "rgba(33,72,59,0.10)",    color: "#21483b", label: "High confidence" },
    medium: { bg: "rgba(180,137,61,0.10)",  color: "#9a6f24", label: "Medium confidence" },
    low:    { bg: "rgba(120,120,120,0.10)", color: "#878787", label: "Low confidence" },
  };
  const style = styles[confidence] ?? styles.low;
  return (
    <span
      className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
      style={{ backgroundColor: style.bg, color: style.color }}
      title="Confidence based on outcome-tier homogeneity across the top comps"
    >
      {style.label}
    </span>
  );
}

function CareerChip({ label, value }: { label: string; value: string | number }) {
  return (
    <span className="inline-flex items-baseline gap-1 rounded border border-[var(--border)] bg-[var(--surface-alt)] px-2 py-0.5 text-[11px]">
      <span className="text-[var(--muted)] uppercase tracking-wide text-[9px]">{label}</span>
      <span className="tabular-nums font-semibold text-[var(--foreground)]">{value}</span>
    </span>
  );
}

export default function HistoricalCompsGrid({ comps }: Props) {
  if (!comps || comps.length === 0) return null;

  const sorted = [...comps].sort((a, b) => b.similarity - a.similarity);
  const sharedConfidence = sorted[0]?.neighbourhood_confidence ?? null;

  return (
    <section className="bip-panel rounded-[1.85rem] p-5 sm:p-6">
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <div>
          <p className="bip-kicker">Historical comps</p>
          <h2 className="bip-display mt-1 text-xl font-bold text-[var(--foreground)]">
            Outcome-weighted NBA matches
          </h2>
        </div>
        <NeighbourhoodConfidenceChip confidence={sharedConfidence} />
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {sorted.map((comp, i) => {
          const summary = comp.career_summary;
          return (
            <div
              key={`${comp.player_id}-${i}`}
              className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-3"
            >
              <div className="flex items-baseline justify-between gap-2">
                <div className="font-semibold text-[var(--foreground)] truncate">
                  {comp.player_name}
                </div>
                <span className="tabular-nums text-[11px] font-medium text-[var(--accent)]">
                  {comp.similarity.toFixed(0)} sim
                </span>
              </div>
              <div className="mt-2 flex items-center gap-2 flex-wrap">
                <TierBadge tier={comp.outcome_tier} />
                {comp.season ? (
                  <span className="text-[10px] uppercase tracking-wide text-[var(--muted)]">
                    {comp.season}
                  </span>
                ) : null}
              </div>
              {summary ? (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {summary.games != null ? <CareerChip label="GP" value={summary.games} /> : null}
                  {summary.ppg != null ? <CareerChip label="PPG" value={summary.ppg.toFixed(1)} /> : null}
                  {summary.all_star != null && summary.all_star > 0 ? (
                    <CareerChip label="All-Star" value={`×${summary.all_star}`} />
                  ) : null}
                  {summary.all_nba != null && summary.all_nba > 0 ? (
                    <CareerChip label="All-NBA" value={`×${summary.all_nba}`} />
                  ) : null}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </section>
  );
}
