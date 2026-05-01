"use client";

import { useEffect } from "react";

interface Props {
  open: boolean;
  onClose: () => void;
}

export function GravityMethodologyModal({ open, onClose }: Props) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="gravity-methodology-title"
    >
      <div
        className="bip-panel w-full max-w-2xl max-h-[85vh] overflow-y-auto rounded-2xl p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2
              id="gravity-methodology-title"
              className="text-lg font-semibold text-[var(--foreground)]"
            >
              How Gravity is Calculated
            </h2>
            <p className="mt-1 text-xs text-[var(--muted)]">
              Methodology version: <span className="tabular-nums">gravity_proxy_v1</span>
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-[var(--border)] px-3 py-1 text-xs text-[var(--muted)] transition hover:bg-[var(--surface-alt)]"
            aria-label="Close gravity methodology"
          >
            Close
          </button>
        </div>

        <section className="mt-5 space-y-2 text-sm text-[var(--muted-strong)]">
          <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
            Two Sources
          </h3>
          <ul className="space-y-2">
            <li className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-2">
              <span className="font-semibold text-[var(--foreground)]">Official NBA Gravity</span>{" "}
              — pulled from the Inside the Game feed when available. Components include
              on-ball / off-ball perimeter and interior gravity. Confidence is marked{" "}
              <span className="font-medium">high</span>.
            </li>
            <li className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-2">
              <span className="font-semibold text-[var(--foreground)]">CourtVue Proxy Gravity</span>{" "}
              — labeled fallback derived from persisted shot-chart, play-type, tracking,
              hustle, and on/off data. Used when the official feed has not been ingested
              for that player-season.
            </li>
          </ul>
        </section>

        <section className="mt-5 space-y-2 text-sm text-[var(--muted-strong)]">
          <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
            Proxy Component Formulas
          </h3>
          <p className="text-xs leading-5">
            Each component is clamped to <span className="tabular-nums">0–100</span>{" "}
            <span className="text-[var(--muted)]">
              (clamp = if a number falls outside the range, snap it to the nearest bound — anything below 0 becomes 0, anything above 100 becomes 100)
            </span>
            . Inputs use season totals and per-game rates from{" "}
            <code className="rounded bg-[var(--surface-alt)] px-1 py-0.5 text-[11px]">
              season_stats
            </code>
            , Synergy <code className="rounded bg-[var(--surface-alt)] px-1 py-0.5 text-[11px]">play_type_stats</code>,
            shot-chart shares, and player-tracking rows.
          </p>
          <ul className="space-y-1.5 font-mono text-[11px] leading-5">
            <li className="rounded bg-[var(--surface-alt)] px-3 py-2">
              <span className="font-semibold text-[var(--foreground)]">shooting</span> = clamp(38 + 3PA/g·5 + 3PA_rate·28 + deep3_rate·25 + spot_up_PPP·6)
            </li>
            <li className="rounded bg-[var(--surface-alt)] px-3 py-2">
              <span className="font-semibold text-[var(--foreground)]">rim</span> = clamp(35 + FTA/g·5 + rim_rate·30 + usage·0.35)
            </li>
            <li className="rounded bg-[var(--surface-alt)] px-3 py-2">
              <span className="font-semibold text-[var(--foreground)]">creation</span> = clamp(35 + AST/g·4 + usage·0.7 + drives·0.25 + iso_PPP·5 + PnR_PPP·5)
            </li>
            <li className="rounded bg-[var(--surface-alt)] px-3 py-2">
              <span className="font-semibold text-[var(--foreground)]">roll/screen</span> = clamp(35 + screen_assists·1.4 + roll_PPP·12)
            </li>
            <li className="rounded bg-[var(--surface-alt)] px-3 py-2">
              <span className="font-semibold text-[var(--foreground)]">off_ball</span> = clamp(35 + catch_shoot_FGA·0.35 + passes_received·0.08 + 3PA_rate·25)
            </li>
            <li className="rounded bg-[var(--surface-alt)] px-3 py-2">
              <span className="font-semibold text-[var(--foreground)]">spacing_lift</span> = clamp(50 + on_off_net·1.4 + (TS%−57)·1.1)
            </li>
            <li className="rounded bg-[var(--surface-alt)] px-3 py-2">
              <span className="font-semibold text-[var(--foreground)]">overall</span> = mean(shooting, rim, creation, roll/screen, off_ball, spacing_lift)
            </li>
          </ul>
        </section>

        <section className="mt-5 space-y-2 text-sm text-[var(--muted-strong)]">
          <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
            Confidence Bands (Proxy Only)
          </h3>
          <p className="text-xs leading-5">
            Coverage = how many of the 5 input families are present (shot chart,
            play-type, tracking, hustle, on/off).
          </p>
          <ul className="grid gap-1.5 text-xs sm:grid-cols-3">
            <li className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-2">
              <span className="font-semibold text-[var(--foreground)]">High</span>{" "}
              <span className="text-[var(--muted)]">— ≥4 of 5 families</span>
            </li>
            <li className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-2">
              <span className="font-semibold text-[var(--foreground)]">Medium</span>{" "}
              <span className="text-[var(--muted)]">— ≥2 of 5 families</span>
            </li>
            <li className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-2">
              <span className="font-semibold text-[var(--foreground)]">Low</span>{" "}
              <span className="text-[var(--muted)]">— fewer than 2</span>
            </li>
          </ul>
        </section>

        <section className="mt-5 space-y-2 text-xs text-[var(--muted-strong)] leading-5">
          <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
            Notes
          </h3>
          <ul className="list-disc space-y-1 pl-5">
            <li>Proxy values are platform-derived approximations and never presented as official NBA Gravity.</li>
            <li>Constants (38, 35, 50, weights) are tuned anchors — not calibrated coefficients — so cross-player ranks are more reliable than absolute scores.</li>
            <li>Spacing Lift folds team-context into the player score and uses on/off net rating, so very small samples should be interpreted with caution.</li>
            <li>See <code className="rounded bg-[var(--surface-alt)] px-1 py-0.5 text-[11px]">backend/services/gravity_service.py</code> and <code className="rounded bg-[var(--surface-alt)] px-1 py-0.5 text-[11px]">specs/platform-methodology.md</code> for the canonical implementation.</li>
          </ul>
        </section>
      </div>
    </div>
  );
}
