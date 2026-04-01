"use client";

import Link from "next/link";
import { useState } from "react";
import type { TeamAnalytics } from "@/lib/types";

interface WhatIfPanelProps {
  teamAbbreviation: string;
  season: string;
  currentAnalytics?: TeamAnalytics | null;
  priorAnalytics?: TeamAnalytics | null;
}

type ScenarioKey = "turnovers" | "pace" | "threes" | "glass" | "shot_quality";

interface ScenarioCard {
  key: ScenarioKey;
  title: string;
  subtitle: string;
  direction: "upside" | "watch" | "mixed";
}

function fmt(value: number | null | undefined, digits = 1) {
  return value == null ? "—" : value.toFixed(digits);
}

function pct(value: number | null | undefined, digits = 1) {
  return value == null ? "—" : `${(value * 100).toFixed(digits)}%`;
}

function scenarioText(
  key: ScenarioKey,
  current: TeamAnalytics | null | undefined,
  prior: TeamAnalytics | null | undefined
) {
  switch (key) {
    case "turnovers": {
      const currentValue = current?.tov_pct;
      const priorValue = prior?.tov_pct;
      const delta = currentValue != null && priorValue != null ? currentValue - priorValue : null;
      return {
        confidence: currentValue != null ? "high" : "low",
        direction: delta == null ? "mixed" : delta > 0 ? "upside" : "watch",
        summary:
          currentValue != null
            ? `Current turnover rate sits at ${pct(currentValue)}. Cleaning that up would recover possessions and make every other lever easier to see.`
            : "Turnover context is not fully populated yet, so the scenario stays directional only.",
        support: priorValue != null ? `Prior season: ${pct(priorValue)}.` : "No prior season comparison.",
      };
    }
    case "pace": {
      const currentValue = current?.pace;
      const priorValue = prior?.pace;
      const delta = currentValue != null && priorValue != null ? currentValue - priorValue : null;
      return {
        confidence: currentValue != null ? "medium" : "low",
        direction: delta == null ? "mixed" : delta >= 0 ? "watch" : "upside",
        summary:
          currentValue != null
            ? `Current pace is ${fmt(currentValue)}. Slowing or speeding it up should be tested against the team's current efficiency shape rather than assumed.`
            : "Pace is not fully available yet, so this stays as a directional coaching prompt.",
        support: priorValue != null ? `Prior season: ${fmt(priorValue)}.` : "No prior season comparison.",
      };
    }
    case "threes": {
      const currentValue = current?.fg3_pct;
      const priorValue = prior?.fg3_pct;
      const delta = currentValue != null && priorValue != null ? currentValue - priorValue : null;
      return {
        confidence: currentValue != null ? "medium" : "low",
        direction: delta == null ? "mixed" : delta >= 0 ? "upside" : "watch",
        summary:
          currentValue != null
            ? `Three-point accuracy is ${pct(currentValue)}. If this team can raise volume without losing shot quality, that is a plausible upside lever.`
            : "Three-point context is incomplete, so the lever remains qualitative.",
        support: priorValue != null ? `Prior season: ${pct(priorValue)}.` : "No prior season comparison.",
      };
    }
    case "glass": {
      const currentValue = current?.oreb_pct;
      const priorValue = prior?.oreb_pct;
      const delta = currentValue != null && priorValue != null ? currentValue - priorValue : null;
      return {
        confidence: currentValue != null ? "medium" : "low",
        direction: delta == null ? "mixed" : delta >= 0 ? "upside" : "watch",
        summary:
          currentValue != null
            ? `Offensive rebounding is ${pct(currentValue)}. Extra possessions are one of the cleanest non-tracking levers to test in game planning.`
            : "Glass control is not fully populated yet, so keep the lever directional.",
        support: priorValue != null ? `Prior season: ${pct(priorValue)}.` : "No prior season comparison.",
      };
    }
    case "shot_quality":
    default: {
      const currentValue = current?.ts_pct;
      const priorValue = prior?.ts_pct;
      const delta = currentValue != null && priorValue != null ? currentValue - priorValue : null;
      return {
        confidence: currentValue != null ? "high" : "low",
        direction: delta == null ? "mixed" : delta >= 0 ? "upside" : "watch",
        summary:
          currentValue != null
            ? `True shooting is ${pct(currentValue)}. If the team is already creating clean looks, this is the most stable efficiency lever to protect.`
            : "Shot-quality data is incomplete, so the scenario stays directional.",
        support: priorValue != null ? `Prior season: ${pct(priorValue)}.` : "No prior season comparison.",
      };
    }
  }
}

export default function WhatIfPanel({
  teamAbbreviation,
  season,
  currentAnalytics,
  priorAnalytics,
}: WhatIfPanelProps) {
  const cards: ScenarioCard[] = [
    {
      key: "turnovers",
      title: "Reduce turnovers",
      subtitle: "Protect possessions and stabilize the offense.",
      direction: "upside",
    },
    {
      key: "pace",
      title: "Change pace",
      subtitle: "Test a faster or slower game shape.",
      direction: "mixed",
    },
    {
      key: "threes",
      title: "Raise 3PA rate",
      subtitle: "Lean into spacing and shot-making.",
      direction: "upside",
    },
    {
      key: "glass",
      title: "Increase offensive rebounding",
      subtitle: "Create second-chance possessions.",
      direction: "upside",
    },
    {
      key: "shot_quality",
      title: "Protect shot quality",
      subtitle: "Keep the best looks stable before adding volume.",
      direction: "watch",
    },
  ];

  const [selected, setSelected] = useState<ScenarioKey>("turnovers");
  const insight = scenarioText(selected, currentAnalytics, priorAnalytics);

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
          <div className="bip-kicker">What-If</div>
          <h2 className="bip-display mt-3 text-3xl font-semibold text-[var(--foreground)]">
            Directional coaching levers for {teamAbbreviation}
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--muted)]">
            These scenarios are intentionally bounded and explainable. They are not a black-box prediction, just a useful first test of what to emphasize next.
          </p>
        </div>
        <Link
          href={`/compare?mode=styles&team_a=${teamAbbreviation}&team_b=${teamAbbreviation}&season=${season}`}
          className="rounded-full border border-[var(--border-strong)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]"
        >
          Open style compare
        </Link>
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
              {card.direction}
            </div>
            <div className="mt-2 text-lg font-semibold text-[var(--foreground)]">
              {card.title}
            </div>
            <p className="mt-2 text-sm leading-6 text-[var(--muted-strong)]">
              {card.subtitle}
            </p>
          </button>
        ))}
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-[1.05fr,0.95fr]">
        <article className="rounded-[1.5rem] border border-[var(--border)] bg-[rgba(255,255,255,0.72)] p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Selected scenario
          </p>
          <h3 className="mt-2 text-2xl font-semibold text-[var(--foreground)]">
            {cards.find((card) => card.key === selected)?.title}
          </h3>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <div className="rounded-2xl bip-metric p-4">
              <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">Confidence</div>
              <div className="mt-2 text-2xl font-semibold text-[var(--foreground)]">{insight.confidence}</div>
            </div>
            <div className="rounded-2xl bip-metric p-4">
              <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">Direction</div>
              <div className="mt-2 text-2xl font-semibold capitalize text-[var(--foreground)]">{insight.direction}</div>
            </div>
            <div className="rounded-2xl bip-accent-card p-4">
              <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--accent)]">Context</div>
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
          <p className="mt-4 text-sm leading-6 text-[var(--muted-strong)]">
            {insight.summary}
          </p>
          <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
            {insight.support}
          </p>
        </article>

        <article className="rounded-[1.5rem] border border-[var(--border)] bg-[rgba(255,255,255,0.72)] p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Coach note
          </p>
          <div className="mt-2 space-y-3 text-sm leading-6 text-[var(--muted-strong)]">
            <p>
              This tab is intentionally heuristic and explainable. It is meant to help an analyst decide what to test first, not to simulate the whole game.
            </p>
            <p>
              If the scenario feels promising, use the team decision tools or compare view to inspect the underlying lineup and style context before presenting it to staff.
            </p>
          </div>
          <div className="mt-4 flex flex-wrap gap-3">
            <Link
              href={`/teams/${teamAbbreviation}?tab=decision`}
              className="rounded-full border border-[var(--border-strong)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]"
            >
              Back to decision tools
            </Link>
            <Link
              href={`/insights?tab=trajectory&team=${teamAbbreviation}&season=${season}`}
              className="rounded-full border border-[var(--border-strong)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]"
            >
              Open trajectory tracker
            </Link>
          </div>
        </article>
      </div>
    </section>
  );
}
