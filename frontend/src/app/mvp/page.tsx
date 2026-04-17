"use client";

import { Suspense, useEffect, useState } from "react";
import { getAvailableSeasons } from "@/lib/api";
import { useMvpRace } from "@/hooks/usePlayerStats";
import MvpRacePanel, { MvpRacePanelSkeleton } from "@/components/MvpRacePanel";

const POSITION_OPTIONS = [
  { label: "All positions", value: "" },
  { label: "Guards", value: "G" },
  { label: "Forwards", value: "F" },
  { label: "Centers", value: "C" },
];

const PILLAR_METHODS = [
  {
    label: "Production",
    weight: "25%",
    formula: "z(PTS/G), z(REB/G), z(AST/G)",
  },
  {
    label: "Efficiency",
    weight: "20%",
    formula: "z(TS%), z(eFG%), z(usage-adjusted TS)",
  },
  {
    label: "Impact",
    weight: "25%",
    formula: "z(BPM), z(VORP), z(WS), z(on/off net)",
  },
  {
    label: "Team Context",
    weight: "15%",
    formula: "z(team win%), z(team net rating)",
  },
  {
    label: "Momentum",
    weight: "10%",
    formula: "last-10 PTS/REB/AST and TS trend vs season baseline",
  },
  {
    label: "Play Style",
    weight: "5%",
    formula: "capped PBP-derived style EV proxy",
  },
];

function MvpContent({
  season,
  top,
  position,
}: {
  season: string;
  top: number;
  position: string | null;
}) {
  const { data, isLoading, error } = useMvpRace(season, { top, minGp: 20, position });

  if (isLoading) return <MvpRacePanelSkeleton />;

  if (error) {
    return (
      <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] py-16 text-center text-[var(--muted)]">
        <p className="text-sm">Could not load MVP race data.</p>
        <p className="mt-1 text-xs text-[var(--danger-ink)]">{String(error?.message ?? error)}</p>
      </div>
    );
  }

  if (!data) return <MvpRacePanelSkeleton />;

  return <MvpRacePanel data={data} />;
}

export default function MvpPage() {
  const [seasons, setSeasons] = useState<string[]>([]);
  const [season, setSeason] = useState<string | null>(null);
  const [top, setTop] = useState(10);
  const [position, setPosition] = useState<string>("");

  useEffect(() => {
    getAvailableSeasons()
      .then((availableSeasons) => {
        setSeasons(availableSeasons);
        if (availableSeasons.length > 0) setSeason(availableSeasons[0]);
      })
      .catch(() => {});
  }, []);

  return (
    <div className="space-y-7">
      <header className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="bip-kicker">Award case lab</p>
            <h1 className="bip-display mt-2 text-3xl font-bold tracking-tight text-[var(--foreground)]">MVP Race</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--muted)]">
              Production, efficiency, team context, on/off lift, eligibility, opponent context, support burden, recent form, and transparent play-style proxies in one case workspace.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <label className="text-xs text-[var(--muted)]">
              Season
              <select
                value={season ?? ""}
                onChange={(event) => setSeason(event.target.value)}
                className="mt-1 w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--foreground)]"
              >
                {seasons.map((availableSeason) => (
                  <option key={availableSeason} value={availableSeason}>
                    {availableSeason}
                  </option>
                ))}
              </select>
            </label>

            <label className="text-xs text-[var(--muted)]">
              Candidates
              <select
                value={top}
                onChange={(event) => setTop(Number(event.target.value))}
                className="mt-1 w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--foreground)]"
              >
                {[5, 10, 15, 20, 25].map((value) => (
                  <option key={value} value={value}>
                    Top {value}
                  </option>
                ))}
              </select>
            </label>

            <label className="text-xs text-[var(--muted)]">
              Position
              <select
                value={position}
                onChange={(event) => setPosition(event.target.value)}
                className="mt-1 w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--foreground)]"
              >
                {POSITION_OPTIONS.map((option) => (
                  <option key={option.value || "all"} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>
      </header>

      {season ? (
        <Suspense fallback={<MvpRacePanelSkeleton />}>
          <MvpContent season={season} top={top} position={position || null} />
        </Suspense>
      ) : (
        <MvpRacePanelSkeleton />
      )}

      <section className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5">
        <div className="grid gap-5 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
          <div>
            <p className="text-xs font-semibold uppercase text-[var(--accent)]">Methodology</p>
            <h2 className="bip-display mt-1 text-2xl font-semibold text-[var(--foreground)]">How the MVP score is built</h2>
            <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
              This is an explainable case index, not an official prediction model. Every input is normalized against the current candidate pool with z-scores, then combined through the weighted pillars below. Missing data is treated neutrally and surfaced in coverage notes.
            </p>
            <p className="mt-3 rounded-lg border border-[rgba(176,70,70,0.28)] bg-[rgba(176,70,70,0.08)] p-3 text-sm leading-6 text-[var(--foreground)]">
              Important limitation: the current methodology is still very favorable to box-score and box-score-derived stats. Production, BPM, VORP, WS, TS, and eFG explain a lot of the score, but they are incomplete measures of defense, scheme load, spacing, matchup difficulty, teammate dependence, and possession-level creation.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            {PILLAR_METHODS.map((pillar) => (
              <div key={pillar.label} className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-[var(--foreground)]">{pillar.label}</p>
                  <span className="rounded border border-[var(--border)] px-2 py-1 text-[10px] font-semibold text-[var(--muted)]">
                    {pillar.weight}
                  </span>
                </div>
                <p className="mt-2 text-xs leading-5 text-[var(--muted)]">{pillar.formula}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-5 grid gap-3 md:grid-cols-3">
          <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-3 text-xs leading-5 text-[var(--muted)]">
            <span className="font-semibold text-[var(--foreground)]">Impact today:</span> BPM, VORP, WS, and on/off net. External impact metrics are shown only when imported locally.
          </div>
          <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-3 text-xs leading-5 text-[var(--muted)]">
            <span className="font-semibold text-[var(--foreground)]">Context today:</span> team success, opponent-quality splits, support burden, eligibility, and recent form are explanatory layers.
          </div>
          <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-3 text-xs leading-5 text-[var(--muted)]">
            <span className="font-semibold text-[var(--foreground)]">Next improvement:</span> persist official play-type, tracking, hustle, matchup, and external all-in-one metrics so box-score gravity does not dominate.
          </div>
        </div>
      </section>

      <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4 text-xs leading-6 text-[var(--muted)]">
        <p>
          Scoring profile `mvp_case_v1`: production 25%, efficiency 20%, impact 25%, team context 15%, momentum 10%, play style 5%.
          Each pillar is z-score normalized across the candidate pool and shown with coverage notes when the underlying data is partial. The case map places candidates by team-context and impact scores by default, sizes bubbles by minutes and availability, and colors recent momentum.
        </p>
        <p className="mt-2">
          Award eligibility is derived from regular-season game logs using the 65-game, 20-minute threshold with up to two 15-20 minute near-miss games. External metrics such as EPM, RAPTOR, LEBRON, DARKO, RAPM, and PIPM are optional imports; local BPM, VORP, WS, WS/48, and on/off remain the fallback impact layer.
        </p>
        <p className="mt-2">
          Play-style and pace values are inferred from parsed play-by-play descriptions and outcomes. They are directional proxies, not official Synergy labels.
        </p>
      </div>
    </div>
  );
}
