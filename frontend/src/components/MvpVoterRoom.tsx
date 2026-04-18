"use client";

import { useMemo, useState } from "react";
import { useMvpVoterRoom } from "@/hooks/usePlayerStats";
import type { MvpCandidate } from "@/lib/types";

function fmt(value?: number | null, digits = 1) {
  return value == null ? "-" : value.toFixed(digits);
}

export default function MvpVoterRoom({
  season,
  candidates,
}: {
  season: string;
  candidates: MvpCandidate[];
}) {
  const defaultIds = useMemo(
    () => candidates.slice(0, 2).map((candidate) => candidate.player_id),
    [candidates]
  );
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const effectiveSelectedIds = selectedIds.length ? selectedIds : defaultIds;

  const { data, isLoading } = useMvpVoterRoom(season, effectiveSelectedIds, { minGp: 20 });
  function toggleCandidate(playerId: number) {
    setSelectedIds((current) => {
      const base = current.length ? current : defaultIds;
      if (base.includes(playerId)) return base.filter((id) => id !== playerId);
      if (base.length >= 3) return [base[1], base[2], playerId].filter(Boolean);
      return [...base, playerId];
    });
  }

  return (
    <section className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="bip-kicker">Voter Room</p>
          <h2 className="bip-display mt-1 text-2xl font-semibold text-[var(--foreground)]">Case comparison, not a ballot simulator</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--muted)]">
            Compare two or three MVP cases across Basketball Value, Award Case, availability, team framing, confidence, clutch evidence, and momentum.
          </p>
        </div>
        <div className="flex max-w-xl flex-wrap gap-2">
          {candidates.slice(0, 10).map((candidate) => {
            const selected = effectiveSelectedIds.includes(candidate.player_id);
            return (
              <button
                key={candidate.player_id}
                type="button"
                onClick={() => toggleCandidate(candidate.player_id)}
                className={`rounded-lg border px-3 py-2 text-xs font-semibold transition-colors ${
                  selected
                    ? "border-[var(--accent)] bg-[var(--accent)] text-white"
                    : "border-[var(--border)] bg-[var(--surface-alt)] text-[var(--foreground)]"
                }`}
              >
                #{candidate.rank} {candidate.player_name.split(" ").slice(-1)[0]}
              </button>
            );
          })}
        </div>
      </div>

      {isLoading && <div className="mt-5 rounded-lg bg-[var(--surface-alt)] p-5 text-sm text-[var(--muted)]">Loading Voter Room...</div>}

      {data && (
        <div className="mt-5 space-y-5">
          <div className="grid gap-3 lg:grid-cols-3">
            {data.candidates.map((candidate) => (
              <article key={candidate.player_id} className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">{candidate.team_abbreviation}</p>
                    <h3 className="mt-1 text-lg font-semibold text-[var(--foreground)]">{candidate.player_name}</h3>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-[var(--muted)]">Award Case</p>
                    <p className="text-xl font-bold text-[var(--accent)]">{fmt(candidate.award_case_score)}</p>
                  </div>
                </div>
                <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
                  <div><p className="text-[var(--muted)]">Award rank</p><p className="font-semibold">#{candidate.award_case_rank ?? "-"}</p></div>
                  <div><p className="text-[var(--muted)]">Value rank</p><p className="font-semibold">#{candidate.basketball_value_rank ?? "-"}</p></div>
                  <div><p className="text-[var(--muted)]">Confidence</p><p className="font-semibold">{candidate.confidence?.overall ?? "-"}</p></div>
                </div>
                <ul className="mt-3 space-y-2 text-xs leading-5 text-[var(--muted)]">
                  {candidate.evidence.slice(0, 3).map((item) => <li key={item}>- {item}</li>)}
                </ul>
              </article>
            ))}
          </div>

          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {data.categories.map((category) => (
              <div key={category.key} className="rounded-lg border border-[var(--border)] p-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">{category.label}</p>
                <p className="mt-1 text-sm font-semibold text-[var(--foreground)]">{category.winner_name ?? "No clear edge"}</p>
                <p className="mt-1 text-xs leading-5 text-[var(--muted)]">{category.summary}</p>
              </div>
            ))}
          </div>

          <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-[var(--accent)]">Room read</p>
            <ul className="mt-2 space-y-1 text-sm text-[var(--muted)]">
              {data.ballot_summary.map((item) => <li key={item}>{item}</li>)}
              {data.warnings.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </div>
        </div>
      )}
    </section>
  );
}
