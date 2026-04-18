"use client";

import { Suspense, useEffect, useState } from "react";
import { getAvailableSeasons } from "@/lib/api";
import { useMvpRace, useMvpSensitivity } from "@/hooks/usePlayerStats";
import MvpRacePanel, { MvpRacePanelSkeleton } from "@/components/MvpRacePanel";
import MvpSensitivitySlope from "@/components/MvpSensitivitySlope";

const POSITION_OPTIONS = [
  { label: "All positions", value: "" },
  { label: "Guards", value: "G" },
  { label: "Forwards", value: "F" },
  { label: "Centers", value: "C" },
];

const PROFILES = [
  {
    key: "box_first",
    label: "Box-First",
    blurb: "Classic MVP index — production, efficiency, BPM/VORP/WS, team context.",
    weights: "Production 25% · Efficiency 20% · Impact 25% · Team 15% · Momentum 10% · Style 5%",
  },
  {
    key: "balanced",
    label: "Balanced",
    blurb: "Default. Blends box totals with multi-metric impact consensus and clutch signal.",
    weights: "Prod 18 · Eff 15 · Box-Impact 15 · Impact Consensus 20 · Clutch 10 · Team 12 · Momentum 7 · Style 3",
  },
  {
    key: "impact_consensus",
    label: "Impact-Consensus",
    blurb: "Leans on EPM/LEBRON/RAPTOR/PIPM/DARKO consensus + clutch; tempers box-total reliance.",
    weights: "Impact Consensus 35 · Clutch 15 · Eff 15 · Team 15 · Prod 10 · Style 5 · Momentum 5",
  },
] as const;

function MvpContent({
  season,
  top,
  position,
  profile,
}: {
  season: string;
  top: number;
  position: string | null;
  profile: string;
}) {
  const { data, isLoading, error } = useMvpRace(season, {
    top,
    minGp: 20,
    position,
    profile,
  });

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

function SensitivitySection({ season }: { season: string }) {
  const { data, isLoading } = useMvpSensitivity(season, { top: 10 });
  return <MvpSensitivitySlope data={data} isLoading={isLoading} />;
}

export default function MvpPage() {
  const [seasons, setSeasons] = useState<string[]>([]);
  const [season, setSeason] = useState<string | null>(null);
  const [top, setTop] = useState(10);
  const [position, setPosition] = useState<string>("");
  const [profile, setProfile] = useState<string>("balanced");

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
              Multiple transparent scoring profiles, a multi-metric impact consensus, clutch/leverage context,
              opponent-adjusted splits, eligibility, support burden, and signature-game evidence in one case workspace.
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

        <div className="mt-5 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-[var(--accent)]">Scoring Profile</p>
              <p className="mt-1 text-xs text-[var(--muted)]">
                Each profile publishes its weights. None is tuned to favor a specific player — toggle to see how the ranking shifts.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {PROFILES.map((p) => {
                const active = p.key === profile;
                return (
                  <button
                    key={p.key}
                    type="button"
                    onClick={() => setProfile(p.key)}
                    title={p.weights}
                    className={`rounded-full border px-4 py-1.5 text-xs font-semibold transition ${
                      active
                        ? "border-[var(--accent)] bg-[var(--accent)] text-white"
                        : "border-[var(--border)] bg-[var(--surface)] text-[var(--foreground)] hover:border-[var(--accent)]"
                    }`}
                  >
                    {p.label}
                  </button>
                );
              })}
            </div>
          </div>
          <p className="mt-3 text-xs text-[var(--muted)]">
            <span className="font-semibold text-[var(--foreground)]">
              {PROFILES.find((p) => p.key === profile)?.label}:
            </span>{" "}
            {PROFILES.find((p) => p.key === profile)?.blurb}
          </p>
          <p className="mt-1 text-[10px] text-[var(--muted)]">
            Weights: {PROFILES.find((p) => p.key === profile)?.weights}
          </p>
        </div>
      </header>

      {season ? <SensitivitySection season={season} /> : null}

      {season ? (
        <Suspense fallback={<MvpRacePanelSkeleton />}>
          <MvpContent season={season} top={top} position={position || null} profile={profile} />
        </Suspense>
      ) : (
        <MvpRacePanelSkeleton />
      )}

      <section className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5">
        <p className="text-xs font-semibold uppercase text-[var(--accent)]">Methodology</p>
        <h2 className="bip-display mt-1 text-2xl font-semibold text-[var(--foreground)]">How the MVP case engine works</h2>
        <p className="mt-3 max-w-4xl text-sm leading-6 text-[var(--muted)]">
          We publish three transparent scoring profiles and let you compare them. The Balanced default blends traditional
          box-score pillars with a multi-metric Impact Consensus (EPM, LEBRON, RAPTOR, PIPM, DARKO, RAPM, BPM, WS/48) and a
          confidence-gated Clutch signal. The Impact-Consensus profile leans further on consensus impact metrics and
          de-emphasizes raw box totals. Box-First preserves the original Sprint 48 weights for continuity. Every external
          metric is shown with its source and as-of date; metrics that aren&apos;t loaded locally are simply labeled
          &quot;coverage n/8&quot; instead of being silently imputed.
        </p>
        <div className="mt-5 grid gap-3 md:grid-cols-3">
          {PROFILES.map((p) => (
            <div key={p.key} className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-3">
              <p className="text-sm font-semibold text-[var(--foreground)]">{p.label}</p>
              <p className="mt-1 text-xs leading-5 text-[var(--muted)]">{p.blurb}</p>
              <p className="mt-2 text-[10px] leading-4 text-[var(--muted)]">{p.weights}</p>
            </div>
          ))}
        </div>
        <div className="mt-5 grid gap-3 md:grid-cols-3">
          <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-3 text-xs leading-5 text-[var(--muted)]">
            <span className="font-semibold text-[var(--foreground)]">Consensus over any one metric:</span> when impact metrics
            disagree we surface the disagreement (σ) rather than picking a winner.
          </div>
          <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-3 text-xs leading-5 text-[var(--muted)]">
            <span className="font-semibold text-[var(--foreground)]">Confidence gating:</span> clutch stats under ~100 possessions
            and opponent splits with &lt; 4 games per bucket render dimmed with a warning icon, not hidden.
          </div>
          <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-3 text-xs leading-5 text-[var(--muted)]">
            <span className="font-semibold text-[var(--foreground)]">Attribution:</span> every external metric is labeled with
            source and as-of date. Gravity continues to distinguish official NBA rows from CourtVue proxy values.
          </div>
        </div>
      </section>
    </div>
  );
}
