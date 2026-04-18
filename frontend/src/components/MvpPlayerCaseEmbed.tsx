"use client";

import Link from "next/link";
import { useMvpCandidateCase } from "@/hooks/usePlayerStats";

function fmt(value?: number | null) {
  return value == null ? "-" : value.toFixed(1);
}

export default function MvpPlayerCaseEmbed({ playerId, season }: { playerId: number; season: string | null }) {
  const { data, error, isLoading } = useMvpCandidateCase(playerId, season, { minGp: 20, profile: "balanced" });
  if (!season || error || (!isLoading && !data)) return null;
  if (isLoading) {
    return <div className="h-28 animate-pulse rounded-lg bg-[var(--surface-alt)]" />;
  }
  const candidate = data?.candidate;
  if (!candidate) return null;
  return (
    <section className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="bip-kicker">MVP case</p>
          <h2 className="mt-1 text-xl font-semibold text-[var(--foreground)]">
            #{candidate.award_case_rank ?? candidate.rank} Award Case
          </h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Basketball Value {fmt(candidate.basketball_value_score)} | Confidence {candidate.confidence?.overall ?? "-"} | {candidate.eligibility?.eligibility_status ?? "unknown"}
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs text-[var(--muted)]">Award Case</p>
          <p className="text-2xl font-bold text-[var(--accent)]">{fmt(candidate.award_case_score)}</p>
        </div>
      </div>
      <ul className="mt-3 space-y-1 text-sm leading-6 text-[var(--muted)]">
        {(candidate.case_summary ?? []).slice(0, 3).map((item) => <li key={item}>- {item}</li>)}
      </ul>
      <Link href="/mvp" className="mt-3 inline-flex rounded-lg border border-[var(--border)] px-3 py-2 text-xs font-semibold text-[var(--foreground)]">
        Open full MVP room
      </Link>
    </section>
  );
}
