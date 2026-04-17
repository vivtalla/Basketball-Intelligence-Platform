"use client";

import { Suspense } from "react";
import { useState, useEffect } from "react";
import { getAvailableSeasons } from "@/lib/api";
import { useMvpRace } from "@/hooks/usePlayerStats";
import MvpRacePanel, { MvpRacePanelSkeleton } from "@/components/MvpRacePanel";

function MvpContent({ season }: { season: string }) {
  const { data, isLoading, error } = useMvpRace(season);

  if (isLoading) return <MvpRacePanelSkeleton />;

  if (error) {
    return (
      <div className="text-center py-16 text-[var(--muted)]">
        <p className="text-sm">Could not load MVP race data.</p>
        <p className="text-xs mt-1 text-[var(--danger-ink)]">{String(error?.message ?? error)}</p>
      </div>
    );
  }

  if (!data) return <MvpRacePanelSkeleton />;

  return <MvpRacePanel data={data} />;
}

export default function MvpPage() {
  const [seasons, setSeasons] = useState<string[]>([]);
  const [season, setSeason] = useState<string | null>(null);

  useEffect(() => {
    getAvailableSeasons()
      .then((s) => {
        setSeasons(s);
        if (s.length > 0) setSeason(s[0]);
      })
      .catch(() => {});
  }, []);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end gap-4">
        <div>
          <h1 className="bip-display text-3xl font-bold tracking-tight">MVP Race</h1>
          <p className="text-sm text-[var(--muted)] mt-1">
            Top candidates ranked by composite score across scoring, rebounding, playmaking, efficiency, and impact.
          </p>
        </div>

        {/* Season selector */}
        {seasons.length > 0 && (
          <div className="sm:ml-auto shrink-0">
            <select
              value={season ?? ""}
              onChange={(e) => setSeason(e.target.value)}
              className="text-sm border border-[var(--border)] rounded-lg px-3 py-1.5 bg-[var(--surface)] text-[var(--foreground)]"
            >
              {seasons.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Race board */}
      {season ? (
        <Suspense fallback={<MvpRacePanelSkeleton />}>
          <MvpContent season={season} />
        </Suspense>
      ) : (
        <MvpRacePanelSkeleton />
      )}

      {/* Footnotes */}
      <div className="text-[11px] text-[var(--muted)] space-y-1 border-t border-[var(--border)] pt-4">
        <p>
          Composite score: 30% PTS/G + 15% REB/G + 15% AST/G + 20% TS% + 20% BPM &mdash; each pillar z-score normalized across the candidate pool. Requires 20+ games played.
        </p>
        <p>
          BPM (Box Plus/Minus) is a Basketball Reference estimate. Momentum arrows reflect last-10 games vs. season average.
        </p>
      </div>
    </div>
  );
}
