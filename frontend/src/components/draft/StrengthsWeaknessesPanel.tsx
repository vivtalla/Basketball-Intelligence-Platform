// Sprint 104 (Stream B) — strengths/weaknesses synthesis panel.
//
// Renders the prospect's top 2 strengths + bottom 2 weaknesses (derived
// from z-scores against the same-year same-bucket pool) and an
// archetype label. Slop-free synthesis: every chip is derived from a
// real stat, not a fabricated scouting blurb.

import type { ProspectProfile } from "@/lib/types";

interface Props {
  profile: ProspectProfile | null | undefined;
}

export default function StrengthsWeaknessesPanel({ profile }: Props) {
  if (!profile) return null;

  const { archetype_label, strengths, weaknesses, pool_size, insufficient_pool } = profile;

  return (
    <section className="bip-panel rounded-[1.85rem] p-6">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div>
          <p className="bip-kicker">Profile synthesis</p>
          <h2 className="bip-display mt-1 text-xl font-bold text-[var(--foreground)]">
            Strengths &amp; weaknesses
          </h2>
        </div>
        <span className="inline-flex items-center gap-1 rounded-full bg-[var(--surface-alt)] px-3 py-1 text-xs font-semibold uppercase tracking-wide text-[var(--muted-strong)]">
          {archetype_label}
        </span>
      </div>

      {insufficient_pool ? (
        <p className="text-sm text-[var(--muted)]">
          Pool too small to synthesize ({pool_size} peers). More prospects in this
          draft year + position bucket are needed for reliable z-score comparison.
        </p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-[var(--muted)] mb-2">
              Strengths
            </p>
            {strengths.length === 0 ? (
              <p className="text-sm text-[var(--muted)]">
                No standout features (no feature reached z ≥ +0.7 vs peers).
              </p>
            ) : (
              <ul className="space-y-1.5">
                {strengths.map((s) => (
                  <li
                    key={s.feature_key}
                    className="flex items-center justify-between rounded-lg border border-[rgba(33,72,59,0.18)] bg-[rgba(33,72,59,0.08)] px-3 py-1.5"
                  >
                    <span className="text-sm font-medium text-[var(--foreground)]">{s.label}</span>
                    <span className="text-xs tabular-nums text-[var(--muted-strong)]">
                      z = {s.z_score >= 0 ? "+" : ""}{s.z_score.toFixed(2)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-[var(--muted)] mb-2">
              Weaknesses
            </p>
            {weaknesses.length === 0 ? (
              <p className="text-sm text-[var(--muted)]">
                No notable weaknesses (no feature reached z ≤ -0.7 vs peers).
              </p>
            ) : (
              <ul className="space-y-1.5">
                {weaknesses.map((w) => (
                  <li
                    key={w.feature_key}
                    className="flex items-center justify-between rounded-lg border border-[rgba(168,117,58,0.22)] bg-[rgba(168,117,58,0.10)] px-3 py-1.5"
                  >
                    <span className="text-sm font-medium text-[var(--foreground)]">{w.label}</span>
                    <span className="text-xs tabular-nums text-[var(--muted-strong)]">
                      z = {w.z_score.toFixed(2)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}

      <p className="mt-4 text-[10px] text-[var(--muted)]">
        Algorithmic synthesis vs {pool_size} same-year peers
        {profile.pool_bucket ? ` (position bucket: ${profile.pool_bucket})` : ""}. Methodology: {profile.methodology_version}.
      </p>
    </section>
  );
}
