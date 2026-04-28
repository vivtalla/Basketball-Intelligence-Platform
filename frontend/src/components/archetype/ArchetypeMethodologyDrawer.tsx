"use client";

import { MethodologyEvidenceCard } from "@/components/methodology/MethodologyEvidenceCard";

export function ArchetypeMethodologyDrawer() {
  return (
    <div className="space-y-3">
    <MethodologyEvidenceCard domain="archetype" title="Archetype methodology reliability" compact />
    <details className="rounded-[1.25rem] border border-[var(--border)] bg-[var(--surface)] p-4 text-sm text-[var(--muted-strong)]">
      <summary className="cursor-pointer list-none font-semibold text-[var(--foreground)]">
        How the player archetype is built
      </summary>
      <div className="mt-3 space-y-3 text-xs leading-5">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
            Inputs
          </div>
          <p className="mt-1">
            A player&apos;s season is summarized as a role vector: usage, assists per 36, 3-point
            attempt rate, free-throw rate, true-shooting, steals and blocks per 36, offensive-rebound
            %, OBPM, DBPM, and 3-point accuracy (sample-gated at 50 attempts). Each feature is
            z-scored against a peer pool of rotation players in the same season (gp ≥ 20, min/g ≥ 15).
            Size (parsed from listed height) is used as a gating feature, not scored.
          </p>
        </div>
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
            Archetype rules (fired in order — first match wins)
          </div>
          <ol className="mt-1 list-decimal space-y-1 pl-5">
            <li><strong>Heliocentric Creator</strong> — elite usage, assists, and OBPM.</li>
            <li><strong>Lead Ball-Handler</strong> — high usage with heavy on-ball playmaking.</li>
            <li><strong>Iso Scorer</strong> — high usage, mid-range-heavy, moderate assists.</li>
            <li><strong>Secondary Playmaker</strong> — high assists at controlled usage with low turnovers.</li>
            <li><strong>Movement Shooter</strong> — specialist perimeter volume + accuracy at low usage.</li>
            <li><strong>3-and-D Wing</strong> — above-average perimeter shooting at wing size + wing defense.</li>
            <li><strong>Rim Pressure Guard</strong> — foul-drawing paint-first guard with on-ball usage.</li>
            <li><strong>Connective Forward</strong> — playmaking at forward/wing size regardless of shot diet.</li>
            <li><strong>Defensive Anchor</strong> — elite rim protection + team-D impact at center size.</li>
            <li><strong>Interior Finisher</strong> — paint-bound efficient scorer with rebound activity.</li>
            <li><strong>Stretch Big</strong> — frontcourt size with a real perimeter shot.</li>
            <li><strong>Switchable Stopper</strong> — perimeter disruption at wing/combo-guard size.</li>
            <li><strong>Rotational Energy</strong> — low-usage hustle role.</li>
            <li><strong>Balanced Role</strong> — rotation minutes but no feature crosses any rule&apos;s trigger.</li>
            <li><strong>Developmental</strong> — sample too thin to classify.</li>
          </ol>
        </div>
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
            Confidence
          </div>
          <p className="mt-1">
            Confidence is the average |z| of the features that fired the matching rule:
            <strong> high ≥ 1.0</strong>, <strong>medium ≥ 0.6</strong>, otherwise low.
            Balanced Role and Developmental always report low confidence.
          </p>
        </div>
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
            Similarity comps
          </div>
          <p className="mt-1">
            Comps use a 13-feature Euclidean distance on z-scored role stats.
            <strong> Season mode</strong> compares within the same season.
            <strong> Age mode</strong> compares to players within ±1 year of age across all seasons
            (the subject player is excluded from his own comps).
            <strong> Team-Fit mode</strong> stays same-season but softens features already covered
            by a teammate, using a 0.4× distance multiplier when the player and teammate are
            within 0.5 z-score on a role feature. The Team-Fit v3 panel uses the same overlap rule
            plus skill-supply, roster-need, role-competition, and confidence explainers to audit
            current-team value and alternate team runway.
          </p>
        </div>
      </div>
    </details>
    </div>
  );
}
