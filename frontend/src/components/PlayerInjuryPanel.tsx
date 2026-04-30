"use client";

/**
 * PlayerInjuryPanel — Sprint 78 FO5
 *
 * Mounted on the player profile when a duration estimate is available
 * (which is essentially always — the model falls back to a hardcoded
 * prior on small samples). Shows:
 *   - Current injury status (if any)
 *   - Expected return distribution (median/p25/p75)
 *   - Up to 3 similar historical injuries
 *   - Methodology popover explaining the duration model
 */

import { useState } from "react";
import useSWR from "swr";

import { getInjuryDurationEstimate } from "@/lib/api";
import type {
  PlayerDurationEstimateResponse,
  SimilarPastInjury,
} from "@/lib/types";

interface Props {
  playerId: number;
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

function gamesLabel(n: number | null | undefined): string {
  if (n == null) return "—";
  return `${n} ${n === 1 ? "game" : "games"}`;
}

function similarLine(injury: SimilarPastInjury): string {
  const tag = injury.severity ? ` (${injury.severity})` : "";
  const ageBit =
    injury.age_at_start != null ? ` · age ${injury.age_at_start.toFixed(0)}` : "";
  return `${injury.player_name}${tag}${ageBit} — missed ${gamesLabel(
    injury.games_missed
  )}`;
}

export default function PlayerInjuryPanel({ playerId }: Props) {
  const [methodologyOpen, setMethodologyOpen] = useState(false);

  const { data, isLoading, error } = useSWR<PlayerDurationEstimateResponse>(
    playerId ? ["injury-duration", playerId] : null,
    () => getInjuryDurationEstimate(playerId)
  );

  if (isLoading) {
    return (
      <section className="rounded-[1.8rem] border border-[var(--border)] bg-[var(--surface)] p-6">
        <div className="animate-pulse space-y-3">
          <div className="h-4 w-48 rounded bg-[var(--surface-alt)]" />
          <div className="h-8 w-72 rounded bg-[var(--surface-alt)]" />
          <div className="grid gap-3 md:grid-cols-3">
            <div className="h-24 rounded-2xl bg-[var(--surface-alt)]" />
            <div className="h-24 rounded-2xl bg-[var(--surface-alt)]" />
            <div className="h-24 rounded-2xl bg-[var(--surface-alt)]" />
          </div>
        </div>
      </section>
    );
  }

  if (error || !data) {
    return null;
  }

  const { estimate, similar_past_injuries, current_injury_status } = data;
  const hasCurrent =
    !!current_injury_status &&
    current_injury_status.toLowerCase() !== "available";

  // Don't render the panel if there's no current injury AND the empirical
  // estimate is sample-size 0 — nothing meaningful to show.
  if (!hasCurrent && estimate.sample_size === 0 && similar_past_injuries.length === 0) {
    return null;
  }

  return (
    <section className="rounded-[1.8rem] border border-[var(--border)] bg-[var(--surface)] p-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="bip-kicker">Injury status</p>
          <h3 className="bip-display mt-2 text-2xl font-semibold text-[var(--foreground)]">
            {hasCurrent
              ? `${data.current_injury_status} · ${data.body_part ?? "injury"}`
              : `Health profile · ${data.body_part ?? "history"}`}
          </h3>
          {data.current_injury_detail ? (
            <p className="mt-1 text-sm text-[var(--muted)]">
              {data.current_injury_detail}
            </p>
          ) : null}
          <p className="mt-1 text-xs text-[var(--muted)]">
            {data.current_injury_report_date
              ? `Last report ${formatDate(data.current_injury_report_date)}`
              : "No active CDN report — modeling is based on history alone."}
            {data.current_injury_return_date
              ? ` · estimated return ${formatDate(data.current_injury_return_date)}`
              : ""}
          </p>
        </div>
        <button
          type="button"
          onClick={() => setMethodologyOpen((open) => !open)}
          className="bip-btn-secondary inline-flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold"
          aria-label="Methodology"
          aria-expanded={methodologyOpen}
        >
          ⓘ
        </button>
      </div>

      {methodologyOpen ? (
        <div className="mt-4 rounded-2xl border border-dashed border-[var(--border)] bg-[var(--surface-alt)] p-4 text-xs leading-5 text-[var(--muted-strong)]">
          <p className="font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Methodology
          </p>
          <p className="mt-2">{data.methodology_note}</p>
          <p className="mt-2">
            Cohort:{" "}
            {estimate.is_fallback
              ? `hardcoded prior for ${estimate.body_part}`
              : `${estimate.sample_size} comparable injuries${
                  estimate.cohort_age_low != null
                    ? ` (ages ${estimate.cohort_age_low.toFixed(
                        0
                      )}–${estimate.cohort_age_high?.toFixed(0)})`
                    : ""
                }`}
            .
          </p>
        </div>
      ) : null}

      <div className="mt-5 grid gap-3 md:grid-cols-3">
        <div className="rounded-2xl bip-metric p-4">
          <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
            Median absence
          </div>
          <div className="mt-2 text-3xl font-bold text-[var(--foreground)]">
            {gamesLabel(estimate.median_games)}
          </div>
          <div className="mt-1 text-xs text-[var(--muted)]">
            {estimate.is_fallback
              ? "Hardcoded prior — no cohort signal"
              : `n=${estimate.sample_size} similar injuries`}
          </div>
        </div>
        <div className="rounded-2xl bip-metric p-4">
          <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
            P25 (best case)
          </div>
          <div className="mt-2 text-3xl font-bold text-[var(--foreground)]">
            {gamesLabel(estimate.p25_games)}
          </div>
          <div className="mt-1 text-xs text-[var(--muted)]">
            25% of comparable cases returned within this window
          </div>
        </div>
        <div className="rounded-2xl bip-metric p-4">
          <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
            P75 (worst case)
          </div>
          <div className="mt-2 text-3xl font-bold text-[var(--foreground)]">
            {gamesLabel(estimate.p75_games)}
          </div>
          <div className="mt-1 text-xs text-[var(--muted)]">
            75% of comparable cases returned within this window
          </div>
        </div>
      </div>

      {similar_past_injuries.length > 0 ? (
        <div className="mt-6">
          <h4 className="text-sm font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Similar past injuries
          </h4>
          <ul className="mt-3 space-y-2">
            {similar_past_injuries.map((injury, index) => (
              <li
                key={`${injury.player_id}-${injury.started_on}-${index}`}
                className="rounded-2xl border border-[var(--border)] bg-[var(--surface-alt)] px-4 py-3 text-sm text-[var(--foreground)]"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium">{similarLine(injury)}</span>
                  <span className="text-xs text-[var(--muted)]">
                    {formatDate(injury.started_on)}
                    {injury.resolved_on
                      ? ` → ${formatDate(injury.resolved_on)}`
                      : ""}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
