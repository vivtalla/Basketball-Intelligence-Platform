"use client";

import Link from "next/link";
import { useState } from "react";
import { useStyleXRay, useWhatIfScenario } from "@/hooks/usePlayerStats";
import type { TeamAnalytics } from "@/lib/types";

interface WhatIfPanelProps {
  teamAbbreviation: string;
  season: string;
  opponentAbbreviation?: string | null;
  currentAnalytics?: TeamAnalytics | null;
  priorAnalytics?: TeamAnalytics | null;
}

type ScenarioKey = "turnovers" | "pace" | "threes" | "glass" | "shot_quality";

interface ScenarioCard {
  key: ScenarioKey;
  title: string;
  subtitle: string;
  scenarioType: string;
  delta: number;
}

function fmt(value: number | null | undefined, digits = 1) {
  return value == null ? "—" : value.toFixed(digits);
}

function pct(value: number | null | undefined, digits = 1) {
  return value == null ? "—" : `${(value * 100).toFixed(digits)}%`;
}

export default function WhatIfPanel({
  teamAbbreviation,
  season,
  opponentAbbreviation,
  currentAnalytics,
  priorAnalytics,
}: WhatIfPanelProps) {
  const cards: ScenarioCard[] = [
    {
      key: "turnovers",
      title: "Reduce turnovers",
      subtitle: "Protect possessions and stabilize the offense.",
      scenarioType: "reduce_iso_proxy",
      delta: 2,
    },
    {
      key: "pace",
      title: "Change pace",
      subtitle: "Test a slower tempo against the current game shape.",
      scenarioType: "slow_pace",
      delta: 2,
    },
    {
      key: "threes",
      title: "Raise 3PA rate",
      subtitle: "Lean into spacing when the current shot diet can support it.",
      scenarioType: "raise_3pa_rate",
      delta: 0.03,
    },
    {
      key: "glass",
      title: "Increase offensive rebounding",
      subtitle: "Create a second-possession margin.",
      scenarioType: "increase_oreb",
      delta: 0.02,
    },
    {
      key: "shot_quality",
      title: "Protect shot quality",
      subtitle: "Shift toward cleaner assisted creation before forcing volume.",
      scenarioType: "increase_pnr_proxy",
      delta: 0.02,
    },
  ];

  const [selected, setSelected] = useState<ScenarioKey>("turnovers");
  const activeCard = cards.find((card) => card.key === selected) ?? cards[0];
  const scenarioPayload = {
    team: teamAbbreviation,
    season,
    scenario_type: activeCard.scenarioType,
    delta: activeCard.delta,
    opponent: opponentAbbreviation ?? undefined,
    context: {
      source_view: "insights-whatif",
    },
  };
  const { data: scenario, isLoading: scenarioLoading } = useWhatIfScenario(scenarioPayload);
  const { data: styleXRay } = useStyleXRay(teamAbbreviation, season, 10, opponentAbbreviation ?? undefined);

  if (!currentAnalytics) {
    return (
      <section className="bip-panel-strong rounded-[2rem] p-6">
        <div className="bip-kicker">What-If</div>
        <h2 className="bip-display mt-3 text-3xl font-semibold text-[var(--foreground)]">
          Test small tactical shifts for {teamAbbreviation}
        </h2>
        <div className="bip-empty mt-6 rounded-3xl p-6 text-sm leading-6">
          Select a team to run the coach-facing what-if prompts for {season}. The panel stays directional when the season comparison is sparse.
        </div>
      </section>
    );
  }

  return (
    <section className="bip-panel-strong rounded-[2rem] p-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="bip-kicker">What-If + Style X-Ray</div>
          <h2 className="bip-display mt-3 text-3xl font-semibold text-[var(--foreground)]">
            Decision workspace for {teamAbbreviation}
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--muted)]">
            Backend-driven scenario responses and style identity now share one workspace, so the recommendation, the why, and the next workflow stay in the same coaching thread.
          </p>
        </div>
        <div className="text-sm text-[var(--muted-strong)]">
          {opponentAbbreviation ? `Opponent context: ${opponentAbbreviation}` : "Team-only directional mode"}
        </div>
      </div>

      <div className="mt-6 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {cards.map((card) => (
          <button
            key={card.key}
            type="button"
            onClick={() => setSelected(card.key)}
            className={`rounded-[1.35rem] border p-4 text-left transition ${
              selected === card.key
                ? "border-[rgba(33,72,59,0.32)] bg-[rgba(216,228,221,0.32)]"
                : "border-[var(--border)] bg-[rgba(255,255,255,0.72)] hover:border-[rgba(33,72,59,0.2)]"
            }`}
          >
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
              {card.scenarioType.replaceAll("_", " ")}
            </div>
            <div className="mt-2 text-lg font-semibold text-[var(--foreground)]">{card.title}</div>
            <p className="mt-2 text-sm leading-6 text-[var(--muted-strong)]">{card.subtitle}</p>
          </button>
        ))}
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-[1.1fr,0.9fr]">
        <article className="rounded-[1.5rem] border border-[var(--border)] bg-[rgba(255,255,255,0.72)] p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Scenario response
          </p>
          <h3 className="mt-2 text-2xl font-semibold text-[var(--foreground)]">
            {scenario?.scenario_label ?? activeCard.title}
          </h3>
          {scenarioLoading ? (
            <div className="mt-4 h-48 animate-pulse rounded-3xl bg-[var(--surface-alt)]" />
          ) : (
            <>
              <div className="mt-4 grid gap-3 sm:grid-cols-4">
                <div className="rounded-2xl bip-metric p-4">
                  <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">Readiness</div>
                  <div className="mt-2 text-xl font-semibold capitalize text-[var(--foreground)]">{scenario?.data_status ?? "—"}</div>
                </div>
                <div className="rounded-2xl bip-metric p-4">
                  <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">Confidence</div>
                  <div className="mt-2 text-xl font-semibold capitalize text-[var(--foreground)]">{scenario?.confidence ?? "—"}</div>
                </div>
                <div className="rounded-2xl bip-metric p-4">
                  <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">Direction</div>
                  <div className="mt-2 text-xl font-semibold capitalize text-[var(--foreground)]">{scenario?.expected_direction ?? "—"}</div>
                </div>
                <div className="rounded-2xl bip-accent-card p-4">
                  <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--accent)]">Band</div>
                  <div className="mt-2 text-xl font-semibold text-[var(--accent-strong)]">
                    {scenario ? `${fmt(scenario.lower_bound, 2)} to ${fmt(scenario.upper_bound, 2)}` : "—"}
                  </div>
                </div>
              </div>

              <p className="mt-4 text-sm leading-6 text-[var(--muted-strong)]">
                {scenario?.summary ?? "Scenario response is loading."}
              </p>
              {scenario?.directional_note ? (
                <p className="mt-3 text-sm leading-6 text-[var(--muted)]">{scenario.directional_note}</p>
              ) : null}

              <div className="mt-5 grid gap-4 md:grid-cols-2">
                <div className="rounded-[1.35rem] border border-[var(--border)] bg-white/70 p-4">
                  <div className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Driver features</div>
                  <div className="mt-3 space-y-3">
                    {(scenario?.driver_features ?? []).map((feature) => (
                      <div key={feature.metric_id} className="rounded-2xl border border-[var(--border)] px-3 py-3">
                        <div className="font-semibold text-[var(--foreground)]">{feature.label}</div>
                        <div className="mt-1 text-sm text-[var(--muted-strong)]">
                          Team {fmt(feature.value, 2)} · League {fmt(feature.league_reference, 2)}
                        </div>
                        <div className="mt-1 text-sm leading-6 text-[var(--muted)]">{feature.note}</div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="rounded-[1.35rem] border border-[var(--border)] bg-white/70 p-4">
                  <div className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Comparable patterns</div>
                  <div className="mt-3 space-y-3">
                    {(scenario?.comparable_patterns ?? []).map((pattern) => (
                      <div key={`${pattern.team_abbreviation}-${pattern.season}`} className="rounded-2xl border border-[var(--border)] px-3 py-3">
                        <div className="font-semibold text-[var(--foreground)]">
                          {pattern.team_abbreviation} · {pattern.archetype ?? "Neighbor"}
                        </div>
                        <div className="mt-1 text-sm text-[var(--muted-strong)]">{pattern.summary}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="mt-5 flex flex-wrap gap-3">
                {scenario?.launch_links.prep_url ? (
                  <Link href={scenario.launch_links.prep_url} className="bip-btn-primary rounded-full px-4 py-2 text-sm font-medium">
                    Open prep
                  </Link>
                ) : null}
                <Link href={scenario?.launch_links.compare_url ?? `/compare?mode=styles&team_a=${teamAbbreviation}&team_b=${teamAbbreviation}&season=${season}`} className="rounded-full border border-[var(--border-strong)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]">
                  Open style compare
                </Link>
              </div>
            </>
          )}
        </article>

        <article className="rounded-[1.5rem] border border-[var(--border)] bg-[rgba(255,255,255,0.72)] p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Style implication
          </p>
          <h3 className="mt-2 text-2xl font-semibold text-[var(--foreground)]">
            {styleXRay?.archetype ?? scenario?.style_implication.archetype ?? "Style profile"}
          </h3>
          <p className="mt-3 text-sm leading-6 text-[var(--muted-strong)]">
            {scenario?.style_implication.label_reason ?? styleXRay?.label_reason ?? "Style identity will appear once team-game coverage is available."}
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl bip-metric p-4">
              <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">Stability</div>
              <div className="mt-2 text-2xl font-semibold capitalize text-[var(--foreground)]">
                {scenario?.style_implication.stability ?? styleXRay?.stability ?? "—"}
              </div>
            </div>
            <div className="rounded-2xl bip-accent-card p-4">
              <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--accent)]">Current context</div>
              <div className="mt-2 text-2xl font-semibold text-[var(--accent-strong)]">
                {selected === "turnovers"
                  ? pct(currentAnalytics.tov_pct)
                  : selected === "pace"
                  ? fmt(currentAnalytics.pace)
                  : selected === "threes"
                  ? pct(currentAnalytics.fg3_pct)
                  : selected === "glass"
                  ? pct(currentAnalytics.oreb_pct)
                  : pct(currentAnalytics.ts_pct)}
              </div>
            </div>
          </div>
          <div className="mt-4 rounded-[1.35rem] border border-[var(--border)] bg-white/70 p-4">
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Relevant contributors</div>
            <div className="mt-3 flex flex-wrap gap-2">
              {(scenario?.style_implication.relevant_contributors ?? styleXRay?.feature_contributors.map((item) => item.label).slice(0, 4) ?? []).map((item) => (
                <span key={item} className="rounded-full bg-[rgba(33,72,59,0.08)] px-3 py-1 text-xs font-semibold uppercase tracking-[0.12em] text-[var(--accent-strong)]">
                  {item}
                </span>
              ))}
            </div>
          </div>
          {styleXRay?.scenario_links?.length ? (
            <div className="mt-4 space-y-3">
              {styleXRay.scenario_links.slice(0, 3).map((link) => (
                <button
                  key={link.scenario_type}
                  type="button"
                  onClick={() => {
                    const matched = cards.find((card) => card.scenarioType === link.scenario_type);
                    if (matched) setSelected(matched.key);
                  }}
                  className="w-full rounded-2xl border border-[var(--border)] bg-white/70 p-4 text-left transition hover:border-[rgba(33,72,59,0.24)]"
                >
                  <div className="font-semibold text-[var(--foreground)]">{link.title}</div>
                  <div className="mt-1 text-sm leading-6 text-[var(--muted-strong)]">{link.rationale}</div>
                </button>
              ))}
            </div>
          ) : null}
          <div className="mt-4 text-sm text-[var(--muted)]">
            Prior season reference: {priorAnalytics ? pct(priorAnalytics.ts_pct) : "No prior season comparison."}
          </div>
        </article>
      </div>
    </section>
  );
}
