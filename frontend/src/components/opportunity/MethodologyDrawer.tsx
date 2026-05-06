"use client";

import type { OpportunityMethodology } from "@/lib/types";
import { SIGNAL_DESCRIPTIONS, SIGNAL_LABELS } from "./OpportunityDriverBar";

interface Props {
  methodology: OpportunityMethodology;
}

export function MethodologyDrawer({ methodology }: Props) {
  return (
    <details className="rounded-[1.25rem] border border-[var(--border)] bg-[var(--surface)] p-4 text-sm text-[var(--muted-strong)]">
      <summary className="cursor-pointer list-none font-semibold text-[var(--foreground)]">
        How the Opportunity Score is calculated
      </summary>
      <div className="mt-3 space-y-3">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
            Weights (clamped ±{methodology.z_score_cap} per signal)
          </div>
          <ul className="mt-2 grid gap-2 text-xs sm:grid-cols-2">
            {Object.entries(methodology.weights).map(([signal, weight]) => (
              <li
                key={signal}
                className="flex flex-col gap-1 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-2"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-[var(--foreground)]">
                    {SIGNAL_LABELS[signal] ?? signal}
                  </span>
                  <span className="tabular-nums text-[var(--muted-strong)]">
                    weight {weight.toFixed(2)}
                  </span>
                </div>
                <p className="text-[11px] leading-4 text-[var(--muted-strong)]">
                  {SIGNAL_DESCRIPTIONS[signal] ?? ""}
                </p>
              </li>
            ))}
          </ul>
        </div>
        <div className="grid gap-2 text-xs sm:grid-cols-2">
          <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-2">
            <div className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">
              Min. minutes per game
            </div>
            <div className="font-semibold tabular-nums text-[var(--foreground)]">
              {methodology.min_minutes}
            </div>
          </div>
          <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-2">
            <div className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">
              Min. possessions per lineup
            </div>
            <div className="font-semibold tabular-nums text-[var(--foreground)]">
              {methodology.min_lineup_possessions}
            </div>
          </div>
        </div>
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
            Confidence thresholds
          </div>
          <ul className="mt-2 space-y-1 text-xs">
            {Object.entries(methodology.confidence_thresholds).map(([key, bands]) => (
              <li key={key} className="flex items-center justify-between">
                <span className="text-[var(--muted-strong)]">{key}</span>
                <span className="tabular-nums text-[var(--foreground)]">
                  {Object.entries(bands)
                    .map(([band, v]) => `${band} ≥ ${v}`)
                    .join(" · ")}
                </span>
              </li>
            ))}
          </ul>
        </div>
        <ul className="list-disc space-y-1 pl-5 text-xs leading-5">
          {methodology.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>

        {/* Sprint 90 — opportunity_v2 uplift methodology subsection. */}
        <details className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-3 text-xs leading-5">
          <summary className="cursor-pointer list-none font-semibold text-[var(--foreground)]">
            How the Role Expansion Uplift card works
          </summary>
          <div className="mt-2 space-y-2 text-[var(--muted-strong)]">
            <p>
              The Role Expansion Uplift card is a descriptive evidence band, not
              a causal projection. It says: &ldquo;players similar to this one
              who took on a comparable usage bump historically saw X TS%
              shift.&rdquo;
            </p>
            <p>
              <span className="font-semibold text-[var(--foreground)]">Source:</span>{" "}
              KNN over <span className="tabular-nums">~286</span> historical
              role-expansion observations materialized from{" "}
              <code className="rounded bg-[var(--surface)] px-1 py-0.5 text-[10px]">
                role_expansion_observations
              </code>
              .
            </p>
            <p>
              <span className="font-semibold text-[var(--foreground)]">Distance:</span>{" "}
              shrunk-Mahalanobis on archetype + USG + TS%. K=20 nearest
              neighbors; minimum 5 to surface a band.
            </p>
            <p>
              <span className="font-semibold text-[var(--foreground)]">Confidence bands:</span>{" "}
              high ≥ 15 neighbors · medium ≥ 8 · low &lt; 8.
            </p>
            <p>
              <span className="font-semibold text-[var(--foreground)]">Caveat:</span>{" "}
              role expansion outcome depends on team context, lineup fit, and
              role scope — none of which the KNN encodes. Read the band as
              &ldquo;what happened historically&rdquo;, not &ldquo;what will
              happen.&rdquo;
            </p>
          </div>
        </details>

        <p className="text-[10px] text-[var(--muted)]">
          Methodology version: {methodology.version}
        </p>
      </div>
    </details>
  );
}
