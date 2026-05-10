"use client";

/**
 * Sprint 78 CF5 — Streaks & Milestones tracker page.
 *
 * Three sections, all read from `/api/milestones/*`:
 *
 *   - Active Streaks       — top-N league-wide active streaks
 *   - Approaching Milestones — closest career milestones
 *   - Signature Performances — top box-score lines from the most recent slate
 *
 * The page is a pure presentation layer — backend services compute the
 * ranking and snapshot tables, frontend renders. Each row deep-links to
 * the player profile so the streak chip there continues the narrative.
 */
import Link from "next/link";
import useSWR from "swr";

import {
  getActiveStreaks,
  getApproachingMilestones,
  getSignaturePerformances,
} from "@/lib/api";
import type {
  ActiveStreaksResponse,
  ApproachingMilestonesResponse,
  MilestoneSnapshotSummary,
  PlayerStreakSummary,
  SignaturePerformance,
  SignaturePerformancesResponse,
} from "@/lib/types";

const ACTIVE_STREAKS_LIMIT = 30;
const MILESTONES_LIMIT = 20;
const SIGNATURE_LIMIT = 10;
const REFRESH_MS = 5 * 60_000; // matches Sprint 77c story-rail cadence

function SectionHeader({
  kicker,
  title,
  blurb,
}: {
  kicker: string;
  title: string;
  blurb: string;
}) {
  return (
    <header className="mb-4">
      <p className="bip-kicker mb-1">{kicker}</p>
      <h2
        className="bip-display font-semibold text-[var(--foreground)]"
        style={{ fontSize: "1.4rem", letterSpacing: "-0.01em" }}
      >
        {title}
      </h2>
      <p
        className="mt-1 text-sm text-[var(--muted)]"
        style={{ fontFamily: "var(--font-display)" }}
      >
        {blurb}
      </p>
    </header>
  );
}

function StreakRow({ streak }: { streak: PlayerStreakSummary }) {
  return (
    <Link
      href={`/players/${streak.player_id}`}
      className="flex items-center justify-between gap-3 px-3 py-3 rounded-xl hover:bg-[var(--surface-alt)] transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-2">
          <span className="bip-display font-semibold text-[var(--foreground)] truncate">
            {streak.player_name}
          </span>
          {streak.team_abbreviation ? (
            <span
              className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]"
              style={{ fontFamily: "var(--font-geist-mono)" }}
            >
              {streak.team_abbreviation}
            </span>
          ) : null}
        </div>
        <div className="text-xs text-[var(--muted)] mt-0.5">
          {streak.length} straight {streak.streak_label}
        </div>
      </div>
      <div
        className="text-2xl font-bold tabular-nums text-[var(--accent-strong)]"
        style={{ fontFamily: "var(--font-display)" }}
      >
        {streak.length}
      </div>
    </Link>
  );
}

function MilestoneRow({ milestone }: { milestone: MilestoneSnapshotSummary }) {
  const remaining = milestone.points_remaining ?? 0;
  return (
    <Link
      href={`/players/${milestone.player_id}`}
      className="flex items-center justify-between gap-3 px-3 py-3 rounded-xl hover:bg-[var(--surface-alt)] transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-2">
          <span className="bip-display font-semibold text-[var(--foreground)] truncate">
            {milestone.player_name}
          </span>
          {milestone.team_abbreviation ? (
            <span
              className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]"
              style={{ fontFamily: "var(--font-geist-mono)" }}
            >
              {milestone.team_abbreviation}
            </span>
          ) : null}
        </div>
        <div className="text-xs text-[var(--muted)] mt-0.5">
          {Math.round(remaining).toLocaleString()} from {milestone.milestone_label}
        </div>
      </div>
      <div className="text-right">
        <div
          className="text-2xl font-bold tabular-nums text-[var(--accent-strong)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          {milestone.games_to_milestone ?? "—"}
        </div>
        <div className="text-[10px] uppercase tracking-[0.18em] text-[var(--muted)]">
          games
        </div>
      </div>
    </Link>
  );
}

function SignatureRow({ perf }: { perf: SignaturePerformance }) {
  // Render "top 8% of his career games" from a 92.0 percentile.
  const topPct = Math.max(0, Math.round(100 - perf.career_percentile));
  const tierLabel = perf.tier === "career" ? "career night" : "signature";
  return (
    <Link
      href={`/players/${perf.player_id}`}
      className="flex items-center justify-between gap-3 px-3 py-3 rounded-xl hover:bg-[var(--surface-alt)] transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-2">
          <span className="bip-display font-semibold text-[var(--foreground)] truncate">
            {perf.player_name}
          </span>
          {perf.team_abbreviation ? (
            <span
              className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]"
              style={{ fontFamily: "var(--font-geist-mono)" }}
            >
              {perf.team_abbreviation}
            </span>
          ) : null}
        </div>
        <div className="text-xs text-[var(--muted)] mt-0.5">
          {perf.line} · top {topPct}% · {tierLabel}
        </div>
      </div>
      <div
        className="text-2xl font-bold tabular-nums text-[var(--accent-strong)]"
        style={{ fontFamily: "var(--font-display)" }}
      >
        {perf.pts}
      </div>
    </Link>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <p
      className="px-3 py-6 text-sm italic text-[var(--muted)]"
      style={{ fontFamily: "var(--font-display)" }}
    >
      {message}
    </p>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-2 animate-pulse">
      {Array.from({ length: 4 }).map((_, i) => (
        <div
          key={i}
          className="rounded-xl"
          style={{
            height: 60,
            background: "rgba(255,249,241,0.4)",
          }}
        />
      ))}
    </div>
  );
}

export default function MilestonesPage() {
  const { data: streakData, isLoading: streaksLoading } = useSWR<ActiveStreaksResponse>(
    ["milestones-active-streaks", ACTIVE_STREAKS_LIMIT],
    () => getActiveStreaks(undefined, ACTIVE_STREAKS_LIMIT),
    { refreshInterval: REFRESH_MS, revalidateOnFocus: false }
  );

  const { data: milestoneData, isLoading: milestonesLoading } = useSWR<ApproachingMilestonesResponse>(
    ["milestones-approaching", MILESTONES_LIMIT],
    () => getApproachingMilestones(MILESTONES_LIMIT),
    { refreshInterval: REFRESH_MS, revalidateOnFocus: false }
  );

  const { data: signatureData, isLoading: signaturesLoading } =
    useSWR<SignaturePerformancesResponse>(
      ["milestones-signature", SIGNATURE_LIMIT],
      () => getSignaturePerformances(undefined, SIGNATURE_LIMIT),
      { refreshInterval: REFRESH_MS, revalidateOnFocus: false }
    );

  const streaks = streakData?.streaks ?? [];
  const milestones = milestoneData?.milestones ?? [];
  const performances = signatureData?.performances ?? [];
  const signatureDate = signatureData?.date;

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <div className="mb-8">
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm text-[var(--muted)] bip-link"
        >
          ← Back to Home
        </Link>
      </div>

      <header className="mb-8">
        <p className="bip-kicker mb-2">CourtVue Numbers Desk</p>
        <h1
          className="bip-display font-bold text-[var(--foreground)]"
          style={{ fontSize: "2.25rem", letterSpacing: "-0.02em" }}
        >
          Streaks & Milestones
        </h1>
        <p
          className="mt-2 text-base text-[var(--muted)] max-w-2xl"
          style={{ fontFamily: "var(--font-display)" }}
        >
          The active hot streaks, career milestones on the horizon, and tonight&rsquo;s
          signature box-score lines &mdash; all auto-computed from the platform&rsquo;s
          game-log history. Refreshed nightly.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* ─── Active Streaks ────────────────────────────────────────── */}
        <section className="bip-panel rounded-2xl px-5 py-5">
          <SectionHeader
            kicker="Active Streaks"
            title="Hot streaks"
            blurb="Consecutive games meeting a narrative threshold &mdash; 30+ pts, double-doubles, triple-doubles, 50%+ FG, 5+ 3PM."
          />
          {streaksLoading ? (
            <LoadingSkeleton />
          ) : streaks.length === 0 ? (
            <EmptyState message="No active streaks &mdash; check back after tomorrow&rsquo;s slate." />
          ) : (
            <div className="space-y-1">
              {streaks.map((streak) => (
                <StreakRow
                  key={`${streak.player_id}-${streak.streak_type}`}
                  streak={streak}
                />
              ))}
            </div>
          )}
        </section>

        {/* ─── Approaching Milestones ───────────────────────────────── */}
        <section className="bip-panel rounded-2xl px-5 py-5">
          <SectionHeader
            kicker="Milestone Watch"
            title="Approaching milestones"
            blurb="Career-total thresholds within reach. Games-to-milestone is projected from this season&rsquo;s per-game pace."
          />
          {milestonesLoading ? (
            <LoadingSkeleton />
          ) : milestones.length === 0 ? (
            <EmptyState message="No active player is within range tonight." />
          ) : (
            <div className="space-y-1">
              {milestones.map((milestone) => (
                <MilestoneRow
                  key={`${milestone.player_id}-${milestone.milestone_key}`}
                  milestone={milestone}
                />
              ))}
            </div>
          )}
        </section>

        {/* ─── Signature Performances ──────────────────────────────── */}
        <section className="bip-panel rounded-2xl px-5 py-5">
          <SectionHeader
            kicker="Signature Performances"
            title={
              signatureDate
                ? `Tonight's best (${signatureDate})`
                : "Tonight's best"
            }
            blurb="Box-score lines that ranked in the top 10% of the player&rsquo;s career &mdash; tier &ldquo;career&rdquo; = top 5%."
          />
          {signaturesLoading ? (
            <LoadingSkeleton />
          ) : performances.length === 0 ? (
            <EmptyState message="No signature lines from the most recent slate." />
          ) : (
            <div className="space-y-1">
              {performances.map((perf) => (
                <SignatureRow key={`${perf.player_id}-${perf.game_id}`} perf={perf} />
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
