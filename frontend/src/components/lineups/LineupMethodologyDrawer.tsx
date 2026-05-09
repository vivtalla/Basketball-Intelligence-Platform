"use client";

export default function LineupMethodologyDrawer() {
  return (
    <details className="rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60">
      <summary className="cursor-pointer select-none px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300">
        Methodology
      </summary>
      <div className="px-3 pb-3 pt-1 space-y-2 text-[10px] text-gray-500 dark:text-gray-400 leading-relaxed">
        <p><span className="font-semibold text-gray-700 dark:text-gray-300">Net Rating</span> = points scored per 100 possessions minus points allowed. Positive means the lineup outscores opponents while on the floor.</p>
        <p><span className="font-semibold text-gray-700 dark:text-gray-300">vs Team Baseline</span> = lineup net rating minus the team&rsquo;s season-average net rating. A lineup at +8 on a +7 team is above average; on a +10 team it&rsquo;s below average.</p>
        <p><span className="font-semibold text-gray-700 dark:text-gray-300">Shrunk Net Rating</span> uses Bayesian shrinkage toward the team baseline: <code>nr × (poss / (poss + 150)) + team_baseline × (150 / (poss + 150))</code>. Small samples shrink strongly toward the mean; large samples trust the observed number.</p>
        <p><span className="font-semibold text-gray-700 dark:text-gray-300">Confidence tiers:</span> High ≥ 200 possessions / Medium 80–200 / Low &lt; 80. Ratings below 80 possessions are especially noisy.</p>
        <p><span className="font-semibold text-gray-700 dark:text-gray-300">Archetype classification:</span> Elite (net vs team ≥ +5) · Offensive Wall (ORTG &gt; team ORTG + 4, weak defense) · Defensive Wall (DRTG &lt; team DRTG − 4, weak offense) · Negative (net vs team ≤ −4) · Balanced (everything else).</p>
        <p><span className="font-semibold text-gray-700 dark:text-gray-300">What-If Studio</span> finds the closest lineup in the database by player overlap. If no exact 5-man match exists, partial matches show the most overlapping lineups. Player removal impact shows the average net rating of qualifying lineups when that player is absent.</p>
        <p><span className="font-semibold text-gray-700 dark:text-gray-300">2-man / 3-man combinations</span> are aggregated from 5-man lineup data. Net rating is the possession-weighted average across all 5-man lineups that include that sub-group. Minimum 50 combined possessions to surface.</p>
        <p className="italic">Caveats: lineup sample sizes are much smaller than player on/off. Bench-unit stagger, opponent quality, and garbage time all affect raw ratings. Always check the possession count before drawing conclusions.</p>
      </div>
    </details>
  );
}
