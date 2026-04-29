"use client";

/**
 * Sprint 78 (CF4): Game Story Mode timeline.
 *
 * A *re-presentation* of existing game-detail data into a single ranked
 * narrative recap of the night. Combines:
 *   - WP swing events (entries on `data.win_probability` that carry a
 *     non-empty `event` label — the trajectory service flags these when
 *     a single possession produced a >=12pp WP swing)
 *   - Top possession-diary entries (already ranked by impact upstream
 *     in `possession_diary_service`)
 *   - Scoring events from `data.timeline` (every score-changing PBP row)
 *
 * Each moment receives a client-side narrative score:
 *
 *     score = |wp_delta| * 100 + (lead_impact_score ?? 0) * 0.5
 *
 * Top 10 moments render as broadsheet cards. Clicking a card scrolls
 * the page to the relevant downstream module via existing anchor IDs
 * (e.g. `#bs-wp`, `#bs-diary`).
 *
 * NO new backend service: this is a frontend-led narrative reorg of the
 * data the rest of the page already consumes.
 */

import { useMemo, useRef } from "react";
import type {
  GameDetailResponse,
  GameTimelinePoint,
  PossessionEntry,
  WinProbPoint,
} from "@/lib/types";

interface GameStoryTimelineProps {
  data: GameDetailResponse;
}

/**
 * Source family — used to colour the kicker chip and pick the anchor
 * the card scrolls to when clicked.
 */
type StorySource = "wp" | "diary" | "score";

interface StoryMoment {
  source: StorySource;
  quarter: number;
  /** Display string like "9:42" — already mm:ss formatted. */
  clock: string;
  /** Sortable seconds-from-tip; stable order tiebreaker. */
  seconds_elapsed: number;
  /** Headline string, data-driven from PBP / diary / WP descriptions. */
  description: string;
  /** Team abbreviation, when known. */
  team_abbreviation: string | null;
  /** Player name involved, when known. */
  player_name: string | null;
  /** Raw narrative score used for ranking; not displayed. */
  narrative_score: number;
  /** Display score line "104-101". */
  score_line: string | null;
  /** WP swing in percentage points (signed, +ve home), when applicable. */
  wp_delta_pp: number | null;
  /** Lead-impact score from the diary service, when applicable. */
  lead_impact_score: number | null;
  /** Anchor link to the downstream module the moment is sourced from. */
  anchor: string;
}

const SOURCE_LABEL: Record<StorySource, string> = {
  wp: "Win-prob swing",
  diary: "Key possession",
  score: "Scoring play",
};

const SOURCE_ANCHOR: Record<StorySource, string> = {
  wp: "#bs-wp",
  diary: "#bs-diary",
  score: "#bs-lead",
};

const MAX_MOMENTS = 10;

/**
 * Convert an NBA PBP clock string (`PT09M42.00S`) or already-formatted
 * `9:42` string into a stable seconds-elapsed-from-tip number. The
 * timeline has different formats across sources; this normalises.
 */
function clockToSecondsRemaining(clock: string | null): number | null {
  if (!clock) return null;
  // Already-formatted "M:SS" or "MM:SS"
  const direct = clock.match(/^(\d{1,2}):(\d{2})$/);
  if (direct) {
    const m = Number(direct[1]);
    const s = Number(direct[2]);
    if (Number.isFinite(m) && Number.isFinite(s)) return m * 60 + s;
  }
  // ISO-8601 duration "PT09M42.00S"
  const iso = clock.match(/^PT(\d+)M([\d.]+)S$/);
  if (iso) {
    const m = Number(iso[1]);
    const s = Number(iso[2]);
    if (Number.isFinite(m) && Number.isFinite(s)) return Math.round(m * 60 + s);
  }
  return null;
}

function periodLengthSec(period: number): number {
  return period > 4 ? 300 : 720; // OT periods are 5 minutes
}

/**
 * Seconds-from-tip for a given (period, secondsRemaining). Returns
 * Number.POSITIVE_INFINITY when the inputs are unparseable so callers
 * can drop those rows from sort tiebreakers.
 */
function secondsFromTip(period: number, secondsRemaining: number | null): number {
  if (secondsRemaining == null) return Number.POSITIVE_INFINITY;
  // Sum prior periods (regulation + any OT).
  let prior = 0;
  for (let p = 1; p < period; p += 1) {
    prior += periodLengthSec(p);
  }
  const len = periodLengthSec(period);
  return prior + (len - secondsRemaining);
}

function formatClock(secondsRemaining: number | null): string {
  if (secondsRemaining == null) return "—";
  const m = Math.floor(secondsRemaining / 60);
  const s = Math.floor(secondsRemaining % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function formatQuarter(q: number): string {
  if (q <= 0) return "—";
  if (q <= 4) return `Q${q}`;
  return `OT${q - 4}`;
}

function formatSwingPP(pp: number): string {
  const r = Math.round(pp);
  if (r > 0) return `+${r}pp`;
  if (r < 0) return `${r}pp`;
  return "0pp";
}

/**
 * Walk the WP series and return the swing events. The trajectory
 * service already labels `event` when a single possession produced a
 * >=12pp swing; we compute the delta against the previous point and
 * carry it through as the dominant ranking signal.
 */
function collectWpMoments(points: WinProbPoint[] | null | undefined): StoryMoment[] {
  if (!Array.isArray(points) || points.length === 0) return [];
  const moments: StoryMoment[] = [];
  let prev: WinProbPoint | null = null;
  for (const p of points) {
    if (prev != null && p.event) {
      const delta = (p.wp_home - prev.wp_home) * 100; // percentage points
      // Estimate quarter from seconds_elapsed (regulation = 4 * 720s).
      let elapsed = p.seconds_elapsed;
      let quarter = 1;
      let len = 720;
      while (elapsed > len && quarter < 8) {
        elapsed -= len;
        quarter += 1;
        len = quarter > 4 ? 300 : 720;
      }
      const remaining = Math.max(0, len - elapsed);
      moments.push({
        source: "wp",
        quarter,
        clock: formatClock(remaining),
        seconds_elapsed: p.seconds_elapsed,
        description: p.event,
        team_abbreviation: null,
        player_name: null,
        narrative_score: Math.abs(delta) * 100,
        score_line: `${p.score_home}-${p.score_away}`,
        wp_delta_pp: delta,
        lead_impact_score: null,
        anchor: SOURCE_ANCHOR.wp,
      });
    }
    prev = p;
  }
  return moments;
}

/**
 * Top-impact possessions. The diary is already sorted by impact
 * upstream, so we just translate the rows into the unified moment
 * shape. We carry `lead_swing` as a proxy lead-impact score (the
 * service does not surface its raw composite).
 */
function collectDiaryMoments(
  diary: PossessionEntry[] | null | undefined
): StoryMoment[] {
  if (!Array.isArray(diary) || diary.length === 0) return [];
  return diary.slice(0, 12).map<StoryMoment>((row) => {
    const remaining = clockToSecondsRemaining(row.time_remaining);
    const elapsed = secondsFromTip(row.quarter, remaining);
    const action = row.primary_action_type
      .split("_")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");
    const player = row.primary_player_name;
    const pts = row.points_scored;
    const description =
      pts > 0
        ? `${player} · ${action} (${pts} pt${pts === 1 ? "" : "s"})`
        : `${player} · ${action}`;
    return {
      source: "diary",
      quarter: row.quarter,
      clock: row.time_remaining,
      seconds_elapsed: Number.isFinite(elapsed) ? elapsed : 0,
      description,
      team_abbreviation: row.offense_team_abbr,
      player_name: row.primary_player_name,
      // Service does not surface a raw impact score — use |lead_swing|
      // as a stable proxy. Per spec: narrative = |wp_delta|*100 +
      // (lead_impact ?? 0) * 0.5. WP swings dominate; diary rows are
      // ranked among themselves by lead-swing magnitude.
      narrative_score: Math.abs(row.lead_swing) * 0.5,
      score_line: null,
      wp_delta_pp: null,
      lead_impact_score: Math.abs(row.lead_swing),
      anchor: SOURCE_ANCHOR.diary,
    };
  });
}

/**
 * Scoring plays from the timeline. The timeline already includes
 * only score-changing rows. We weight by the magnitude of the score
 * change, capped to keep them subordinate to WP swings.
 */
function collectScoreMoments(
  timeline: GameTimelinePoint[] | null | undefined
): StoryMoment[] {
  if (!Array.isArray(timeline) || timeline.length === 0) return [];
  let prevHome = 0;
  let prevAway = 0;
  const out: StoryMoment[] = [];
  for (const ev of timeline) {
    const remaining = clockToSecondsRemaining(ev.clock);
    const elapsed = secondsFromTip(ev.period, remaining);
    const homeDiff = ev.home_score - prevHome;
    const awayDiff = ev.away_score - prevAway;
    prevHome = ev.home_score;
    prevAway = ev.away_score;
    const delta = Math.max(homeDiff, awayDiff);
    if (delta <= 0) continue;
    // Light weight — these are the volume layer; signal layer is
    // WP swings + diary impact.
    const score = delta * 8;
    out.push({
      source: "score",
      quarter: ev.period,
      clock: formatClock(remaining),
      seconds_elapsed: Number.isFinite(elapsed) ? elapsed : 0,
      description: ev.description ?? "Score change",
      team_abbreviation: ev.scoring_team_abbreviation ?? null,
      player_name: null,
      narrative_score: score,
      score_line: `${ev.home_score}-${ev.away_score}`,
      wp_delta_pp: null,
      lead_impact_score: null,
      anchor: SOURCE_ANCHOR.score,
    });
  }
  return out;
}

function sourcePriority(s: StorySource): number {
  // WP swings are the cleanest narrative signal; diary next; raw scores last.
  if (s === "wp") return 3;
  if (s === "diary") return 2;
  return 1;
}

/**
 * De-dup near-coincident moments — when the WP swing event and the
 * scoring play that triggered it land at the same second, prefer the
 * WP row (richer signal). Two moments are "coincident" if they share
 * a quarter and the seconds_elapsed values are within 5 seconds.
 */
function dedupNearby(moments: StoryMoment[]): StoryMoment[] {
  const sorted = [...moments].sort((a, b) => b.narrative_score - a.narrative_score);
  const kept: StoryMoment[] = [];
  for (const m of sorted) {
    const collision = kept.find(
      (k) =>
        k.quarter === m.quarter &&
        Math.abs(k.seconds_elapsed - m.seconds_elapsed) <= 5 &&
        // Only kill the lower-priority source on collision.
        sourcePriority(k.source) >= sourcePriority(m.source)
    );
    if (!collision) kept.push(m);
  }
  return kept;
}

function MethodologyTooltip() {
  // Mirrors the NarrativeLeaders convention exactly — pure CSS
  // group-hover, no React state.
  return (
    <span
      className="group relative inline-flex items-center"
      tabIndex={0}
      aria-label="How the game story is ranked"
    >
      <span
        aria-hidden
        className="inline-flex items-center justify-center rounded-full border text-[11px] font-bold cursor-help transition-colors hover:bg-[var(--accent)] hover:text-[var(--accent-ink)] hover:border-[var(--accent)] group-focus:bg-[var(--accent)] group-focus:text-[var(--accent-ink)]"
        style={{
          width: 18,
          height: 18,
          borderColor: "var(--border-strong)",
          color: "var(--muted)",
          fontFamily: "var(--font-display)",
        }}
      >
        i
      </span>
      <span
        role="tooltip"
        className="absolute left-0 top-full mt-2 z-30 w-[320px] max-w-[calc(100vw-2rem)] p-4 rounded-xl border shadow-lg opacity-0 pointer-events-none translate-y-1 transition-all duration-150 group-hover:opacity-100 group-hover:pointer-events-auto group-hover:translate-y-0 group-focus:opacity-100 group-focus:pointer-events-auto group-focus:translate-y-0"
        style={{
          background: "var(--surface)",
          borderColor: "var(--border-strong)",
          boxShadow: "var(--shadow)",
        }}
      >
        <p className="bip-kicker mb-2" style={{ color: "var(--accent)" }}>
          Game Story · Methodology
        </p>
        <p
          className="text-[12px] leading-5 mb-3 text-[var(--foreground)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Re-ranks events from win-probability swings, the possession
          diary, and the scoring timeline into one narrative recap.
        </p>
        <pre
          className="text-[11px] leading-[1.55] mb-3 px-3 py-2 rounded-md whitespace-pre-wrap"
          style={{
            fontFamily: "var(--font-geist-mono)",
            background: "var(--surface-alt)",
            color: "var(--foreground)",
          }}
        >
{`narrative = |wp_delta| × 100
          + lead_impact × 0.5`}
        </pre>
        <ul
          className="text-[11px] leading-[1.5] space-y-1.5 text-[var(--muted)]"
          style={{
            fontFamily: "var(--font-geist-mono)",
            letterSpacing: "0.02em",
          }}
        >
          <li>· WP swings dominate; diary impact tunes the order.</li>
          <li>· Coincident events de-duped within ±5 sec.</li>
          <li>· Click a card to jump to its source module.</li>
        </ul>
      </span>
    </span>
  );
}

function MomentCard({
  moment,
  index,
}: {
  moment: StoryMoment;
  index: number;
}) {
  const swingLabel =
    moment.wp_delta_pp != null ? formatSwingPP(moment.wp_delta_pp) : null;
  return (
    <a
      href={moment.anchor}
      className="group relative flex w-[280px] shrink-0 snap-start flex-col gap-3 rounded-[1.4rem] border px-5 py-5 transition-all hover:-translate-y-0.5 hover:shadow-md focus:-translate-y-0.5 focus:shadow-md focus:outline-none"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border)",
      }}
    >
      <div className="flex items-center justify-between gap-2">
        <span
          className="rounded-full px-2 py-1 text-[10px] font-bold uppercase tabular-nums"
          style={{
            background: "var(--signal-soft)",
            color: "var(--signal-ink)",
            fontFamily: "var(--font-geist-mono)",
            letterSpacing: "0.16em",
          }}
        >
          {String(index + 1).padStart(2, "0")} · {SOURCE_LABEL[moment.source]}
        </span>
        <span
          className="text-[10px] uppercase tabular-nums"
          style={{
            fontFamily: "var(--font-geist-mono)",
            letterSpacing: "0.16em",
            color: "var(--muted)",
          }}
        >
          {formatQuarter(moment.quarter)} · {moment.clock}
        </span>
      </div>

      <p
        className="text-[15px] leading-snug font-semibold text-[var(--foreground)]"
        style={{
          fontFamily: "var(--font-display)",
          letterSpacing: "-0.005em",
        }}
      >
        {moment.description}
      </p>

      <div className="mt-auto flex flex-wrap items-center gap-2">
        {moment.team_abbreviation && (
          <span
            className="rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase"
            style={{
              background: "var(--accent-soft)",
              color: "var(--accent-strong)",
              fontFamily: "var(--font-geist-mono)",
              letterSpacing: "0.16em",
            }}
          >
            {moment.team_abbreviation}
          </span>
        )}
        {swingLabel && (
          <span
            className="rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tabular-nums"
            style={{
              background: "var(--success-soft)",
              color: "var(--success-ink)",
              fontFamily: "var(--font-geist-mono)",
              letterSpacing: "0.14em",
            }}
            title="Win probability swing"
          >
            {swingLabel}
          </span>
        )}
        {moment.score_line && (
          <span
            className="ml-auto text-[12px] tabular-nums"
            style={{
              fontFamily: "var(--font-display)",
              color: "var(--muted)",
            }}
          >
            {moment.score_line}
          </span>
        )}
      </div>

      <span
        aria-hidden
        className="pointer-events-none absolute inset-x-5 bottom-2 h-px opacity-0 transition-opacity group-hover:opacity-100 group-focus:opacity-100"
        style={{ background: "var(--accent)" }}
      />
    </a>
  );
}

export default function GameStoryTimeline({ data }: GameStoryTimelineProps) {
  const scrollerRef = useRef<HTMLDivElement | null>(null);

  const moments = useMemo<StoryMoment[]>(() => {
    const wp = collectWpMoments(data.win_probability);
    const diary = collectDiaryMoments(data.possession_diary);
    const score = collectScoreMoments(data.timeline);
    const all = [...wp, ...diary, ...score];
    if (all.length === 0) return [];
    const deduped = dedupNearby(all);
    return deduped
      .sort((a, b) => b.narrative_score - a.narrative_score)
      .slice(0, MAX_MOMENTS)
      .sort((a, b) => a.seconds_elapsed - b.seconds_elapsed);
  }, [data.win_probability, data.possession_diary, data.timeline]);

  if (moments.length === 0) {
    return null; // Quiet failure — pre-game / no PBP yet — keep page calm.
  }

  return (
    <section
      id="bs-story"
      className="bip-panel rounded-[1.85rem] px-6 py-7"
      style={{ background: "rgba(255,249,241,0.6)" }}
    >
      <header className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <p className="bip-kicker">Game Story · top moments</p>
            <MethodologyTooltip />
          </div>
          <h2
            className="bip-display mt-2 font-bold text-[var(--foreground)]"
            style={{
              fontSize: "clamp(1.6rem, 2.4vw, 2.1rem)",
              letterSpacing: "-0.02em",
            }}
          >
            How the game turned.
          </h2>
        </div>
        <span
          className="rounded-full px-3 py-1 text-[10px] font-semibold uppercase tabular-nums"
          style={{
            background: "var(--accent-soft)",
            color: "var(--accent-strong)",
            fontFamily: "var(--font-geist-mono)",
            letterSpacing: "0.18em",
          }}
        >
          {moments.length} moments
        </span>
      </header>

      <div
        ref={scrollerRef}
        className="-mx-6 flex snap-x snap-mandatory gap-3 overflow-x-auto px-6 pb-2"
        style={{ scrollPaddingInline: "1.5rem" }}
        aria-label="Top game moments timeline"
      >
        {moments.map((moment, idx) => (
          <MomentCard
            key={`${moment.source}-${moment.quarter}-${moment.seconds_elapsed}-${idx}`}
            moment={moment}
            index={idx}
          />
        ))}
      </div>
    </section>
  );
}
