"use client";

export default function OnOffMethodologyDrawer() {
  return (
    <details className="rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60">
      <summary className="cursor-pointer select-none px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300">
        Methodology
      </summary>
      <div className="px-3 pb-3 pt-1 space-y-2 text-[10px] text-gray-500 dark:text-gray-400 leading-relaxed">
        <p><span className="font-semibold text-gray-700 dark:text-gray-300">ORTG Δ</span> = On-court offensive rating − off-court offensive rating. Positive means the offense runs better when the player is on the floor.</p>
        <p><span className="font-semibold text-gray-700 dark:text-gray-300">DRTG Δ</span> = Off-court defensive rating − on-court defensive rating (sign-flipped so positive = better defense on). Positive means the defense holds opponents to fewer points per 100 when he&rsquo;s on.</p>
        <p><span className="font-semibold text-gray-700 dark:text-gray-300">Marginal Net Rating</span> = On/Off Net − Team Net Rating. Compares the player&rsquo;s swing to the team&rsquo;s baseline season performance.</p>
        <p><span className="font-semibold text-gray-700 dark:text-gray-300">Confidence tiers:</span> High ≥ 800 on-court min / Medium 400–800 / Low 200–400 / Insufficient &lt; 200. The border style of the classification badge mirrors this tier.</p>
        <p><span className="font-semibold text-gray-700 dark:text-gray-300">Impact classification:</span> Two-Way Elite (ORTG Δ &gt; 3 and DRTG Δ &gt; 3) · Offensive Engine (ORTG &gt; 3, DRTG &lt; 1) · Defensive Anchor (DRTG &gt; 3, ORTG &lt; 1) · Liability (both &lt; −2) · Neutral otherwise. Threshold of ±3 pts/100 represents a meaningful single-player swing.</p>
        <p><span className="font-semibold text-gray-700 dark:text-gray-300">External metrics</span> (RAPM, EPM, PIPM) are imported from public datasets and are never platform-original. They use opponent-adjusted regression and serve as a cross-check on raw on/off.</p>
        <p className="italic">Caveats: bench-unit stagger, opponent shot-selection timing, garbage-time minutes, and lineup partner quality all move raw on/off. Pair this panel with lineup context and usage data before drawing conclusions.</p>
      </div>
    </details>
  );
}
