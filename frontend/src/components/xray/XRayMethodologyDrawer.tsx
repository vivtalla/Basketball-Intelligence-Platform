"use client";

export function XRayMethodologyDrawer() {
  return (
    <details className="rounded-[1.25rem] border border-[var(--border)] bg-[var(--surface)] p-4 text-sm text-[var(--muted-strong)]">
      <summary className="cursor-pointer list-none font-semibold text-[var(--foreground)]">
        How the Style X-Ray is built
      </summary>
      <div className="mt-3 space-y-3 text-xs leading-5">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
            Inputs
          </div>
          <p className="mt-1">
            Every team&apos;s season is summarized as a style vector: pace, true-shooting, eFG%,
            3PA rate, free-throw rate, offensive-rebound rate, turnover rate, assist rate, a
            play-by-play transition proxy, and a paint-pressure proxy. Each metric is z-scored
            against the league distribution for the selected season.
          </p>
        </div>
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
            Archetype rules (fired in order)
          </div>
          <ul className="mt-1 list-disc space-y-1 pl-5">
            <li><strong>Spread Pick-and-Roll</strong> — assist, three-rate, and TS% all elevated.</li>
            <li><strong>Transition Defense Disruptors</strong> — above-average transition rate with top-tier defensive rating.</li>
            <li><strong>Tempo + Spacing</strong> — fast pace + elevated perimeter volume.</li>
            <li><strong>Run-and-Pressure</strong> — high transition rate + pace.</li>
            <li><strong>Halfcourt Interior Pressure</strong> — slower pace + strong paint / free-throw pressure.</li>
            <li><strong>Iso-Heavy Halfcourt</strong> — slow pace, below-average ball movement, light perimeter diet.</li>
            <li><strong>Glass and Grind</strong> — elite offensive rebounding with low three-rate.</li>
            <li><strong>Control + Efficiency</strong> — low turnover with strong true-shooting.</li>
            <li><strong>Defensive Anchor</strong> — defense dominates the profile even without a signature offensive lean.</li>
            <li><strong>Balanced</strong> — default when no single axis dominates.</li>
          </ul>
        </div>
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
            Confidence
          </div>
          <p className="mt-1">
            Archetype confidence is the average |z| of the triggers that fired the rule:
            <strong> high ≥ 1.0</strong>, <strong>medium ≥ 0.6</strong>, otherwise low.
            Balanced always reports low confidence.
          </p>
        </div>
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
            Neighbor quality
          </div>
          <p className="mt-1">
            Euclidean distance across the style vector vs. every other team. Closest third ={" "}
            <strong>high</strong>, middle third = <strong>medium</strong>, farthest third ={" "}
            <strong>low</strong>. Quality reflects how close the style match is, not quality of team.
          </p>
        </div>
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
            Movement
          </div>
          <p className="mt-1">
            Each feature&apos;s baseline-season z-score is compared to the same z-score computed on
            the selected recent window. |Δz| &lt; 0.25 is <strong>stable</strong>; larger positive
            shifts are <strong>gaining</strong>, negative shifts <strong>fading</strong>. The drift
            archetype, if present, is what the last window alone classifies as.
          </p>
        </div>
      </div>
    </details>
  );
}
