"use client";

import type { OpportunityPlayerRow, OpportunityUplift } from "@/lib/types";

interface Props {
  row: OpportunityPlayerRow;
}

function tone(value: number): "pos" | "neg" | "neutral" {
  if (value > 0.001) return "pos";
  if (value < -0.001) return "neg";
  return "neutral";
}

function toneClass(t: "pos" | "neg" | "neutral") {
  if (t === "pos") return "text-[var(--accent-strong)]";
  if (t === "neg") return "text-[var(--danger-ink)]";
  return "text-[var(--foreground)]";
}

function formatTs(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(4)}`;
}

function confidencePillClass(confidence: OpportunityUplift["evidence_confidence"]) {
  if (confidence === "high") return "bg-[rgba(33,72,59,0.1)] text-[var(--accent-strong)]";
  if (confidence === "medium") return "bg-[rgba(181,145,78,0.12)] text-[rgb(123,93,42)]";
  return "bg-[rgba(47,43,36,0.08)] text-[var(--muted-strong)]";
}

function ConfidencePill({ uplift }: { uplift: OpportunityUplift }) {
  return (
    <span
      className={`rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] ${confidencePillClass(uplift.evidence_confidence)}`}
      title={`${uplift.neighbor_count} comparable historical role expansions`}
    >
      {uplift.evidence_confidence} · {uplift.neighbor_count}
    </span>
  );
}

function ComparableChip({
  comparable,
}: {
  comparable: OpportunityUplift["comparable_examples"][number];
}) {
  const t = tone(comparable.ts_delta);
  return (
    <div className="flex items-baseline justify-between gap-3 rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-2">
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-semibold text-[var(--foreground)]">
          {comparable.player_name}
        </div>
        <div className="text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">
          {comparable.from_season} → {comparable.to_season} · USG {comparable.usg_delta > 0 ? "+" : ""}
          {(comparable.usg_delta * 100).toFixed(1)}%
        </div>
      </div>
      <div className={`text-sm font-bold tabular-nums ${toneClass(t)}`}>
        {formatTs(comparable.ts_delta)}
      </div>
    </div>
  );
}

export function UpliftEvidenceCard({ row }: Props) {
  const uplift = row.uplift;

  return (
    <section className="rounded-[1.25rem] border border-[var(--border)] bg-[var(--surface)] p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Role Expansion Uplift
          </p>
          <h3 className="mt-0.5 text-base font-semibold text-[var(--foreground)]">
            Historical TS% movement for comparable role bumps
          </h3>
        </div>
        {uplift && <ConfidencePill uplift={uplift} />}
      </div>

      {!uplift ? (
        <p className="mt-4 text-sm text-[var(--muted-strong)]">
          Insufficient comparable role expansions to ground an uplift estimate yet.
          KNN needs at least five qualifying historical neighbors.
        </p>
      ) : (
        <>
          <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-2">
              <div className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">
                Mean TS% shift
              </div>
              <div className={`text-2xl font-bold tabular-nums ${toneClass(tone(uplift.mean_uplift))}`}>
                {formatTs(uplift.mean_uplift)}
              </div>
              <div className="mt-1 text-[11px] text-[var(--muted)]">
                from {uplift.neighbor_count} comparable players
              </div>
            </div>
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-2">
              <div className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">
                ±IQR band
              </div>
              <div className="text-base font-semibold tabular-nums text-[var(--foreground)]">
                [{formatTs(uplift.uplift_band_lower)}, {formatTs(uplift.uplift_band_upper)}]
              </div>
              <div className="mt-1 text-[11px] uppercase tracking-[0.12em] text-[var(--muted)]">
                Confidence: {uplift.evidence_confidence}
              </div>
            </div>
          </div>

          {uplift.comparable_examples.length > 0 && (
            <div className="mt-4">
              <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
                Top {Math.min(3, uplift.comparable_examples.length)} historical cases
              </div>
              <div className="mt-2 grid grid-cols-1 gap-2">
                {uplift.comparable_examples.slice(0, 3).map((c, i) => (
                  <ComparableChip
                    key={`${c.player_name}-${c.from_season}-${i}`}
                    comparable={c}
                  />
                ))}
              </div>
            </div>
          )}

          <p className="mt-3 text-[11px] leading-5 text-[var(--muted-strong)]">
            Descriptive evidence band, not a causal projection. Depends on team
            context, role scope, and fit.
          </p>
        </>
      )}
    </section>
  );
}

export default UpliftEvidenceCard;
