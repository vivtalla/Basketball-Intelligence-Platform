"use client";

import Image from "next/image";
import Link from "next/link";
import { useMvpRace } from "@/hooks/usePlayerStats";
import type { MvpCandidate } from "@/lib/types";

const SEASON = "2025-26";

function fmt(value: number | null | undefined, digits = 1): string {
  if (value == null || Number.isNaN(value)) return "-";
  return value.toFixed(digits);
}

function fmtSigned(value: number | null | undefined, digits = 1): string {
  if (value == null || Number.isNaN(value)) return "-";
  return `${value >= 0 ? "+" : ""}${value.toFixed(digits)}`;
}

function CandidateCard({ candidate, rank }: { candidate: MvpCandidate; rank: number }) {
  const isLeader = rank === 1;
  // Use pts_delta as a proxy for composite trend direction
  const delta = candidate.pts_delta;
  const deltaUp = delta == null ? null : delta >= 0;
  const eligibility = candidate.eligibility;
  const eligibilityTone =
    eligibility?.eligibility_status === "eligible"
      ? "var(--success-ink)"
      : eligibility?.eligibility_status === "ineligible"
        ? "var(--danger-ink)"
        : "var(--accent)";

  return (
    <Link
      href="/mvp"
      className="group bip-panel rounded-[1.85rem] p-5 hover:-translate-y-1 hover:border-[var(--accent)] hover:shadow-[0_24px_60px_rgba(33,72,59,0.16)] transition-all duration-220 block"
    >
      {/* Top row: name + avatar */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p
            className="bip-kicker mb-1.5"
            style={{ color: isLeader ? "var(--signal)" : "var(--muted)" }}
          >
            {isLeader ? "★ Leader" : `#${rank}`}
          </p>
          <h3
            className="bip-display font-semibold leading-tight truncate"
            style={{ fontSize: "1.15rem" }}
          >
            {candidate.player_name}
          </h3>
          <p
            className="mt-0.5"
            style={{
              fontFamily: "var(--font-geist-mono)",
              fontSize: 11,
              color: "var(--muted)",
              letterSpacing: "0.06em",
            }}
          >
            {candidate.team_abbreviation}
          </p>
          <p
            className="mt-1 tabular-nums"
            style={{
              fontFamily: "var(--font-geist-mono)",
              fontSize: 10,
              color: eligibilityTone,
            }}
          >
            {eligibility?.eligible_games ?? candidate.gp}/65 qualified · {eligibility?.eligibility_status ?? "unknown"}
          </p>
        </div>
        <div className="relative h-12 w-12 shrink-0 overflow-hidden rounded-full bg-[var(--surface-alt)] border border-[var(--border)]">
          {candidate.headshot_url && (
            <Image
              src={candidate.headshot_url}
              alt={candidate.player_name}
              fill
              className="object-cover object-top"
              unoptimized
            />
          )}
        </div>
      </div>

      {/* Divider + composite score */}
      <div className="mt-4 pt-3.5 border-t border-[var(--border)] flex items-end justify-between gap-2">
        <div>
          <span
            className="bip-display tabular-nums"
            style={{
              fontSize: "2.4rem",
              fontWeight: 700,
              lineHeight: 1,
              color: "var(--foreground)",
              fontVariantNumeric: "tabular-nums",
              letterSpacing: "-0.02em",
            }}
          >
            {fmt(candidate.composite_score)}
          </span>
          <p
            style={{
              fontFamily: "var(--font-geist-mono)",
              fontSize: 10,
              letterSpacing: "0.1em",
              color: "var(--muted)",
              marginTop: 4,
            }}
          >
            COMPOSITE
          </p>
        </div>

        {delta != null && (
          <span
            className="tabular-nums mb-1"
            style={{
              fontFamily: "var(--font-geist-mono)",
              fontSize: 12,
              color: deltaUp ? "var(--success-ink)" : "var(--danger-ink)",
              fontVariantNumeric: "tabular-nums",
            }}
          >
            {deltaUp ? "▲" : "▼"} {fmtSigned(delta)}
          </span>
        )}
      </div>

      {/* Stat chips */}
      <div className="mt-3 grid grid-cols-3 gap-1.5 text-center text-xs">
        <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] px-2 py-2">
          <p
            style={{
              fontFamily: "var(--font-geist-mono)",
              fontSize: 9,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: "var(--muted)",
            }}
          >
            PTS
          </p>
          <p className="mt-1 font-semibold tabular-nums">{fmt(candidate.pts_pg)}</p>
        </div>
        <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] px-2 py-2">
          <p
            style={{
              fontFamily: "var(--font-geist-mono)",
              fontSize: 9,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: "var(--muted)",
            }}
          >
            On/Off
          </p>
          <p className="mt-1 font-semibold tabular-nums">
            {candidate.on_off?.on_off_net == null
              ? "-"
              : `${candidate.on_off.on_off_net >= 0 ? "+" : ""}${fmt(candidate.on_off.on_off_net)}`}
          </p>
        </div>
        <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] px-2 py-2">
          <p
            style={{
              fontFamily: "var(--font-geist-mono)",
              fontSize: 9,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: "var(--muted)",
            }}
          >
            W-L
          </p>
          <p className="mt-1 font-semibold tabular-nums">
            {candidate.team_context?.wins != null && candidate.team_context.losses != null
              ? `${candidate.team_context.wins}-${candidate.team_context.losses}`
              : "-"}
          </p>
        </div>
      </div>
      <p className="mt-3 text-xs leading-5 text-[var(--muted)]">
        {candidate.opponent_context?.best_split
          ? `Best split: ${candidate.opponent_context.best_split}`
          : "Open the case map for availability, splits, and support context."}
      </p>
    </Link>
  );
}

function SkeletonCard() {
  return (
    <div className="bip-panel rounded-[1.85rem] p-5 animate-pulse">
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <div className="h-2.5 w-12 rounded bg-[var(--surface-alt)]" />
          <div className="h-4 w-32 rounded bg-[var(--surface-alt)]" />
        </div>
        <div className="h-12 w-12 rounded-full bg-[var(--surface-alt)]" />
      </div>
      <div className="mt-4 pt-3.5 border-t border-[var(--border)]">
        <div className="h-9 w-20 rounded bg-[var(--surface-alt)]" />
      </div>
    </div>
  );
}

export default function HomeMvpTeaser() {
  const { data, isLoading } = useMvpRace(SEASON, { top: 3, minGp: 20 });
  const candidates = data?.candidates ?? [];

  return (
    <section>
      <div className="mb-4 flex items-end justify-between gap-4">
        <div>
          <p className="bip-kicker mb-1.5">Award Case Lab</p>
          <h2 className="bip-display text-3xl font-semibold">
            MVP race, <span className="text-[var(--accent)]">live.</span>
          </h2>
        </div>
        <Link
          href="/mvp"
          className="bip-link shrink-0 flex items-center gap-1.5 text-sm font-medium"
        >
          Open workspace →
        </Link>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {isLoading &&
          Array.from({ length: 3 }).map((_, i) => <SkeletonCard key={i} />)}

        {!isLoading &&
          candidates.map((candidate) => (
            <CandidateCard
              key={candidate.player_id}
              candidate={candidate}
              rank={candidate.rank}
            />
          ))}
      </div>
    </section>
  );
}
