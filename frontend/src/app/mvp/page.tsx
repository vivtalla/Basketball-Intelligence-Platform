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
              Production, efficiency, team context, on/off lift, recent form, and transparent play-style proxies in one case board.
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

      <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4 text-xs leading-6 text-[var(--muted)]">
        <p>
          Scoring profile `mvp_case_v1`: production 25%, efficiency 20%, impact 25%, team context 15%, momentum 10%, play style 5%.
          Each pillar is z-score normalized across the candidate pool and shown with coverage notes when the underlying data is partial.
        </p>
        <p className="mt-2">
          Play-style values are inferred from parsed play-by-play descriptions and outcomes. They are directional proxies, not official Synergy labels.
        </p>
      </div>
    </div>
  );
}
