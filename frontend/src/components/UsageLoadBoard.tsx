"use client";

import Link from "next/link";
import type { UsageEfficiencyPlayerRow } from "@/lib/types";

interface UsageLoadBoardProps {
  featureMore: UsageEfficiencyPlayerRow[];
  reduceLoad: UsageEfficiencyPlayerRow[];
}

function fmtPct(value: number | null | undefined) {
  return value == null ? "—" : `${(value * 100).toFixed(1)}%`;
}

function fmtNum(value: number | null | undefined, digits = 1) {
  return value == null ? "—" : value.toFixed(digits);
}

function loadBarTone(direction: "more" | "less") {
  return direction === "more"
    ? "bg-[rgba(33,72,59,0.12)] text-[var(--accent-strong)]"
    : "bg-[rgba(159,63,49,0.12)] text-[var(--danger-ink)]";
}

function recommendationLabel(row: UsageEfficiencyPlayerRow, direction: "more" | "less") {
  if (direction === "more") {
    return row.ast_pg != null && row.ast_pg >= 4
      ? "efficient creator on light burden"
      : "efficient scorer on light burden";
  }
  return row.tov_pg != null && row.tov_pg >= 2.5
    ? "high burden with turnover drag"
    : "high burden with weak scoring return";
}

function recommendationStrength(
  row: UsageEfficiencyPlayerRow,
  direction: "more" | "less"
) {
  const raw =
    direction === "more"
      ? (row.efficiency_score ?? 0) - (row.burden_score ?? 0)
      : (row.burden_score ?? 0) - (row.efficiency_score ?? 0);
  return Math.max(8, Math.min(100, raw * 2.4));
}

function signalValue(row: UsageEfficiencyPlayerRow, direction: "more" | "less") {
  return direction === "more"
    ? Math.max(0, (row.efficiency_score ?? 0) - (row.burden_score ?? 0))
    : Math.max(0, (row.burden_score ?? 0) - (row.efficiency_score ?? 0));
}

function laneFormula(direction: "more" | "less") {
  return direction === "more"
    ? "Signal = Efficiency score - Burden score"
    : "Signal = Burden score - Efficiency score";
}

function burdenFormula() {
  return "Burden score = Player USG% - Pool average USG%";
}

function efficiencyFormula() {
  return "Efficiency score = (Player TS% - Pool average TS%) x 100";
}

function RecommendationLane({
  title,
  subtitle,
  direction,
  rows,
}: {
  title: string;
  subtitle: string;
  direction: "more" | "less";
  rows: UsageEfficiencyPlayerRow[];
}) {
  return (
    <section className="rounded-[1.75rem] border border-[var(--border)] bg-[var(--surface)]">
      <div className="border-b border-[var(--border)] px-5 py-4">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
          {direction === "more" ? "Feature More" : "Reduce Load"}
        </p>
        <h2 className="mt-1 text-2xl font-semibold text-[var(--foreground)]">{title}</h2>
        <p className="mt-2 text-sm text-[var(--muted-strong)]">{subtitle}</p>
        <div className="mt-3 inline-flex rounded-full border border-[rgba(25,52,42,0.12)] bg-[rgba(255,255,255,0.76)] px-3 py-1.5 text-[11px] font-medium text-[var(--foreground)]">
          {laneFormula(direction)}
        </div>
      </div>

      <div className="space-y-4 p-5">
        {rows.length ? (
          rows.map((row, index) => {
            const strength = recommendationStrength(row, direction);
            const signal = signalValue(row, direction);
            return (
              <article
                key={`${row.player_id}-${row.team_abbreviation}-${direction}`}
                className="rounded-[1.25rem] border border-[var(--border)] bg-[rgba(255,255,255,0.72)] p-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
                      Priority {index + 1}
                    </div>
                    <div className="mt-1 text-lg font-semibold text-[var(--foreground)]">
                      <Link href={`/players/${row.player_id}`} className="bip-link">
                        {row.player_name}
                      </Link>{" "}
                      <span className="text-sm font-medium text-[var(--muted-strong)]">
                        {row.team_abbreviation}
                      </span>
                    </div>
                    <div className="mt-2 text-sm text-[var(--muted-strong)]">
                      {recommendationLabel(row, direction)}
                    </div>
                  </div>

                  <div className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] ${loadBarTone(direction)}`}>
                    {direction === "more" ? "increase role" : "ease role"}
                  </div>
                </div>

                <div
                  className="mt-4"
                  title={
                    direction === "more"
                      ? `Recommendation strength: ${signal.toFixed(1)}. Higher means efficiency is outpacing burden by a wider margin.`
                      : `Recommendation strength: ${signal.toFixed(1)}. Higher means burden is outpacing efficiency by a wider margin.`
                  }
                >
                  <div className="rounded-xl px-1 py-2">
                    <div className="h-2 overflow-hidden rounded-full bg-[var(--surface-alt)]">
                      <div
                        className={`h-full rounded-full ${direction === "more" ? "bg-[var(--accent)]" : "bg-[var(--danger-ink)]"}`}
                        style={{ width: `${strength}%` }}
                      />
                    </div>
                  </div>
                </div>

                <div className="mt-4 grid gap-3 sm:grid-cols-7 text-sm text-[var(--muted-strong)]">
                  <div title={`Usage rate: ${fmtNum(row.usg_pct)}. Higher means the player finishes more possessions.`}>
                    <div className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">Usage</div>
                    <div className="mt-1 font-semibold text-[var(--foreground)]">{fmtNum(row.usg_pct)}</div>
                  </div>
                  <div title={`True shooting: ${fmtPct(row.ts_pct)}. This is the main efficiency read for scoring return.`}>
                    <div className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">TS%</div>
                    <div className="mt-1 font-semibold text-[var(--foreground)]">{fmtPct(row.ts_pct)}</div>
                  </div>
                  <div title={`Offensive rating: ${fmtNum(row.off_rating)}. Points produced per 100 possessions while this player is on the floor.`}>
                    <div className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">ORTG</div>
                    <div className="mt-1 font-semibold text-[var(--foreground)]">{fmtNum(row.off_rating)}</div>
                  </div>
                  <div title={`Minutes per game: ${fmtNum(row.minutes_pg)}. Bigger minute loads make the recommendation more important.`}>
                    <div className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">Minutes</div>
                    <div className="mt-1 font-semibold text-[var(--foreground)]">{fmtNum(row.minutes_pg)}</div>
                  </div>
                  <div
                    title={`Burden score: ${fmtNum(row.burden_score)}. Formula: ${burdenFormula()}. Positive means above-average burden for this filtered player pool.`}
                  >
                    <div className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">Burden</div>
                    <div className="mt-1 font-semibold text-[var(--foreground)]">{fmtNum(row.burden_score)}</div>
                  </div>
                  <div
                    title={`Efficiency score: ${fmtNum(row.efficiency_score)}. Formula: ${efficiencyFormula()}. Positive means above-average TS% for this filtered player pool, shown in percentage points.`}
                  >
                    <div className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">Efficiency</div>
                    <div className="mt-1 font-semibold text-[var(--foreground)]">{fmtNum(row.efficiency_score)}</div>
                  </div>
                  <div
                    title={
                      direction === "more"
                        ? `Signal: +${signal.toFixed(1)}. Efficiency score is ahead of burden score by this amount.`
                        : `Signal: +${signal.toFixed(1)}. Burden score is ahead of efficiency score by this amount.`
                    }
                  >
                    <div className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">Signal</div>
                    <div className="mt-1 font-semibold text-[var(--foreground)]">
                      +{signal.toFixed(1)}
                    </div>
                  </div>
                </div>
              </article>
            );
          })
        ) : (
          <div className="rounded-[1.25rem] border border-[var(--border)] px-5 py-8 text-sm text-[var(--muted-strong)]">
            No players crossed the current threshold for this recommendation lane.
          </div>
        )}
      </div>
    </section>
  );
}

export default function UsageLoadBoard({
  featureMore,
  reduceLoad,
}: UsageLoadBoardProps) {
  return (
    <div className="space-y-6">
      <section className="rounded-[1.75rem] border border-[var(--border)] bg-[linear-gradient(145deg,rgba(247,243,232,0.92),rgba(228,236,232,0.94))] p-5">
        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
          Read This Fast
        </p>
        <h2 className="mt-1 text-2xl font-semibold text-[var(--foreground)]">
          Who should get more and who should get less?
        </h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--muted-strong)]">
          Each card gives the recommendation first, then the evidence. The line shows recommendation strength, the{" "}
          <span className="font-semibold text-[var(--foreground)]">Signal</span> shows the exact gap driving that
          recommendation, and the{" "}
          <span className="font-semibold text-[var(--foreground)]">Burden</span> /{" "}
          <span className="font-semibold text-[var(--foreground)]">Efficiency</span> scores show which side of the
          decision is winning for that player relative to the current filtered player pool.
        </p>
        <details className="mt-4 max-w-3xl rounded-2xl border border-[rgba(25,52,42,0.12)] bg-[rgba(255,255,255,0.66)] px-4 py-3 text-sm text-[var(--muted-strong)]">
          <summary className="cursor-pointer list-none font-medium text-[var(--foreground)]">
            How these scores are calculated
          </summary>
          <div className="mt-3 space-y-2">
            <p>
              <strong>Burden score</strong> compares the player&apos;s usage rate to the current filtered pool average.
            </p>
            <p className="font-mono text-[12px] text-[var(--foreground)]">
              <span className="font-semibold">{burdenFormula()}</span>
            </p>
            <p>
              <strong>Efficiency score</strong> compares the player&apos;s true shooting to the current filtered pool average, shown in percentage points.
            </p>
            <p className="font-mono text-[12px] text-[var(--foreground)]">
              <span className="font-semibold">{efficiencyFormula()}</span>
            </p>
            <p>
              <strong>Signal</strong> is the gap between those two scores.
            </p>
            <p className="font-mono text-[12px] text-[var(--foreground)]">
              Feature More: <span className="font-semibold">Efficiency score - Burden score</span>
            </p>
            <p className="font-mono text-[12px] text-[var(--foreground)]">
              Reduce Load: <span className="font-semibold">Burden score - Efficiency score</span>
            </p>
          </div>
        </details>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <div className="rounded-2xl border border-[rgba(33,72,59,0.12)] bg-[rgba(255,255,255,0.68)] p-4 text-sm text-[var(--muted-strong)]">
            <div className="font-semibold text-[var(--accent-strong)]">Feature more</div>
            <div className="mt-1">Low burden, strong efficiency, clean offensive return.</div>
          </div>
          <div className="rounded-2xl border border-[rgba(181,145,78,0.14)] bg-[rgba(255,255,255,0.68)] p-4 text-sm text-[var(--muted-strong)]">
            <div className="font-semibold text-[rgb(123,93,42)]">Center lane</div>
            <div className="mt-1">Nothing urgent. These players are closer to role balance.</div>
          </div>
          <div className="rounded-2xl border border-[rgba(159,63,49,0.14)] bg-[rgba(255,255,255,0.68)] p-4 text-sm text-[var(--muted-strong)]">
            <div className="font-semibold text-[var(--danger-ink)]">Reduce load</div>
            <div className="mt-1">Heavy burden without enough efficiency payoff.</div>
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-2">
        <RecommendationLane
          title="Best Feature-More Candidates"
          subtitle="These are the clearest cases for giving a player a little more offensive responsibility."
          direction="more"
          rows={featureMore}
        />
        <RecommendationLane
          title="Biggest Reduce-Load Candidates"
          subtitle="These are the clearest cases where the current offensive burden looks too expensive."
          direction="less"
          rows={reduceLoad}
        />
      </div>
    </div>
  );
}
