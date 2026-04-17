"use client";

import Image from "next/image";
import Link from "next/link";
import type { MvpRaceResponse, MvpCandidate } from "@/lib/types";

interface MvpRacePanelProps {
  data: MvpRaceResponse;
}

// ---------------------------------------------------------------------------
// Formatters
// ---------------------------------------------------------------------------

function fmt(value: number | null | undefined, digits = 1): string {
  if (value == null) return "—";
  return value.toFixed(digits);
}

function fmtPct(value: number | null | undefined): string {
  if (value == null) return "—";
  return (value * 100).toFixed(1) + "%";
}

function fmtDelta(value: number | null | undefined): string {
  if (value == null || Math.abs(value) < 1) return "";
  return (value >= 0 ? "+" : "") + value.toFixed(1);
}

function momentumLabel(m: MvpCandidate["momentum"]): string {
  if (m === "hot") return "Hot";
  if (m === "cold") return "Cold";
  return "";
}

function momentumClasses(m: MvpCandidate["momentum"]): string {
  if (m === "hot") return "bg-orange-100 text-orange-700 border border-orange-200";
  if (m === "cold") return "bg-blue-100 text-blue-700 border border-blue-200";
  return "";
}

function rankBadgeClasses(rank: number): string {
  if (rank === 1) return "text-yellow-600 font-bold";
  if (rank === 2) return "text-zinc-500 font-bold";
  if (rank === 3) return "text-amber-700 font-bold";
  return "text-[var(--muted)] font-semibold";
}

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

function SkeletonCard() {
  return (
    <div className="flex items-center gap-4 p-4 rounded-xl border border-[var(--border)] bg-[var(--surface)] animate-pulse">
      <div className="w-8 h-8 rounded bg-[var(--border)]" />
      <div className="w-12 h-12 rounded-full bg-[var(--border)]" />
      <div className="flex-1 space-y-2">
        <div className="h-3 w-32 rounded bg-[var(--border)]" />
        <div className="h-2 w-20 rounded bg-[var(--border)]" />
      </div>
      <div className="flex gap-3">
        {[0, 1, 2].map((i) => (
          <div key={i} className="space-y-1 text-right">
            <div className="h-2 w-8 rounded bg-[var(--border)]" />
            <div className="h-3 w-10 rounded bg-[var(--border)]" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function MvpRacePanelSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 5 }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Candidate card
// ---------------------------------------------------------------------------

function CandidateCard({ candidate, maxScore }: { candidate: MvpCandidate; maxScore: number }) {
  const barWidth = maxScore > 0 ? (candidate.composite_score / maxScore) * 100 : 0;
  const ptsDelta = fmtDelta(candidate.pts_delta);
  const rebDelta = fmtDelta(candidate.reb_delta);
  const astDelta = fmtDelta(candidate.ast_delta);
  const momentumTag = momentumLabel(candidate.momentum);

  return (
    <Link href={`/players/${candidate.player_id}`} className="block group">
      <div className="flex items-center gap-4 p-4 rounded-xl border border-[var(--border)] bg-[var(--surface)] hover:border-[var(--accent)] transition-colors">
        {/* Rank */}
        <div className={`w-7 text-center text-lg shrink-0 ${rankBadgeClasses(candidate.rank)}`}>
          {candidate.rank}
        </div>

        {/* Headshot */}
        <div className="shrink-0">
          {candidate.headshot_url ? (
            <Image
              src={candidate.headshot_url}
              alt={candidate.player_name}
              width={48}
              height={48}
              className="rounded-full object-cover bg-[var(--border)]"
              unoptimized
            />
          ) : (
            <div className="w-12 h-12 rounded-full bg-[var(--border)] flex items-center justify-center text-[var(--muted)] text-xs font-bold">
              {candidate.player_name.split(" ").map((n) => n[0]).join("").slice(0, 2)}
            </div>
          )}
        </div>

        {/* Name + score bar */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm truncate group-hover:text-[var(--accent)]">
              {candidate.player_name}
            </span>
            {momentumTag && (
              <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium shrink-0 ${momentumClasses(candidate.momentum)}`}>
                {momentumTag}
              </span>
            )}
          </div>
          <div className="text-[11px] text-[var(--muted)] mt-0.5">
            {candidate.team_abbreviation} &middot; {candidate.gp} GP
          </div>
          {/* Composite score bar */}
          <div className="mt-2 h-1.5 rounded-full bg-[var(--border)] overflow-hidden">
            <div
              className="h-full rounded-full bg-[var(--accent)]"
              style={{ width: `${barWidth.toFixed(1)}%` }}
            />
          </div>
        </div>

        {/* Stat chips */}
        <div className="hidden sm:flex items-center gap-4 shrink-0 text-right">
          <StatChip label="PTS" value={fmt(candidate.pts_pg)} delta={ptsDelta} />
          <StatChip label="REB" value={fmt(candidate.reb_pg)} delta={rebDelta} />
          <StatChip label="AST" value={fmt(candidate.ast_pg)} delta={astDelta} />
          <StatChip label="TS%" value={fmtPct(candidate.ts_pct)} />
          {candidate.bpm != null && (
            <StatChip
              label="BPM"
              value={(candidate.bpm >= 0 ? "+" : "") + fmt(candidate.bpm)}
              tone={candidate.bpm >= 3 ? "positive" : candidate.bpm <= 0 ? "negative" : "neutral"}
            />
          )}
        </div>
      </div>
    </Link>
  );
}

function StatChip({
  label,
  value,
  delta,
  tone,
}: {
  label: string;
  value: string;
  delta?: string;
  tone?: "positive" | "negative" | "neutral";
}) {
  const toneClass =
    tone === "positive"
      ? "text-[var(--success-ink)]"
      : tone === "negative"
      ? "text-[var(--danger-ink)]"
      : "text-[var(--foreground)]";

  return (
    <div>
      <div className="text-[10px] text-[var(--muted)] uppercase tracking-[0.12em]">{label}</div>
      <div className={`text-sm font-semibold ${toneClass}`}>
        {value}
        {delta && (
          <span
            className={`ml-1 text-[10px] font-normal ${delta.startsWith("+") ? "text-[var(--success-ink)]" : "text-[var(--danger-ink)]"}`}
          >
            {delta}
          </span>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main panel
// ---------------------------------------------------------------------------

export default function MvpRacePanel({ data }: MvpRacePanelProps) {
  if (data.candidates.length === 0) {
    return (
      <div className="text-center py-16 text-[var(--muted)]">
        <p className="text-sm">No MVP candidates found for {data.season}.</p>
        <p className="text-xs mt-1">Requires 20+ games played. Run a season stats sync to populate.</p>
      </div>
    );
  }

  const maxScore = data.candidates[0]?.composite_score ?? 100;

  return (
    <div className="space-y-3">
      {data.candidates.map((c) => (
        <CandidateCard key={c.player_id} candidate={c} maxScore={maxScore} />
      ))}
    </div>
  );
}
