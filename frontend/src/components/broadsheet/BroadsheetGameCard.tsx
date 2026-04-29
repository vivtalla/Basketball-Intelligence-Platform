"use client";

import Link from "next/link";
import type { PlayoffSeriesGameWithMatchup } from "@/lib/types";

/**
 * Sprint 77 (Stream B / EB1): Newsprint-styled playoff game card.
 *
 * Renders one of three visual states based on the game's payload:
 *   - LIVE   → both scores present, no winner_team_id → pulsing red dot +
 *              "LIVE" kicker + WP bar split forest/danger + score-large.
 *   - FINAL  → winner_team_id present → "FINAL" kicker + score-large +
 *              winner highlighted in forest.
 *   - SCHEDULED → no scores → tipoff/network kicker + score-blank ("—").
 *
 * Always rendered: kicker line, two team rows (logo glyph, abbr, name,
 * record, score), and an italic storyline footer if `headline_storyline`
 * is provided by the backend.
 */

const TIME_FORMATTER = new Intl.DateTimeFormat("en-US", {
  hour: "numeric",
  minute: "2-digit",
  timeZone: "America/Los_Angeles",
  timeZoneName: "short",
});

interface State {
  kind: "live" | "final" | "scheduled";
  kicker: string;
}

function deriveState(game: PlayoffSeriesGameWithMatchup): State {
  const gameNum = game.series_game_num != null ? `Game ${game.series_game_num}` : null;
  if (game.winner_team_id != null) {
    return {
      kind: "final",
      kicker: ["Final", gameNum].filter(Boolean).join(" · "),
    };
  }
  if (game.home_pts != null && game.away_pts != null) {
    return {
      kind: "live",
      kicker: ["Live", gameNum].filter(Boolean).join(" · "),
    };
  }
  // Scheduled — prefer the real CDN-sourced tipoff_utc when present.
  let tipoff = "Tipoff TBD";
  if (game.tipoff_utc) {
    const parsed = new Date(game.tipoff_utc);
    if (!Number.isNaN(parsed.getTime())) {
      tipoff = TIME_FORMATTER.format(parsed);
    }
  } else if (game.game_date) {
    const parsed = new Date(`${game.game_date}T19:00:00Z`);
    if (!Number.isNaN(parsed.getTime())) {
      tipoff = TIME_FORMATTER.format(parsed);
    }
  }
  const network = game.broadcaster ?? null;
  const parts = [tipoff, gameNum, network].filter(Boolean) as string[];
  return {
    kind: "scheduled",
    kicker: parts.join(" · "),
  };
}

function recordLine(
  abbr: string | null,
  isTopSeed: boolean,
  game: PlayoffSeriesGameWithMatchup
): string | null {
  if (!abbr) return null;
  const top = game.top_wins ?? 0;
  const bot = game.bottom_wins ?? 0;
  if (isTopSeed) return `Series ${top}-${bot}`;
  return `Series ${bot}-${top}`;
}

/** Compute a single live-game WP estimate from the score margin. */
function liveWinProbability(home: number, away: number): number {
  // Score-margin → WP via a mild logistic. Conservative slope so lopsided
  // games go ~85/15 not 99/1. This is a UI-only proxy — not used for any
  // analytical decisions.
  const margin = home - away;
  const wp = 1 / (1 + Math.exp(-margin / 8));
  return Math.max(0.05, Math.min(0.95, wp));
}

export interface BroadsheetGameCardProps {
  game: PlayoffSeriesGameWithMatchup;
}

export default function BroadsheetGameCard({ game }: BroadsheetGameCardProps) {
  const state = deriveState(game);
  const awayAbbr = game.away_team_abbr ?? "TBD";
  const homeAbbr = game.home_team_abbr ?? "TBD";
  // The "top seed" of the series is the higher-seed team; use the abbr
  // labels on the game row to figure out which side they sit on.
  const homeIsTopSeed =
    game.top_seed_team_abbr != null &&
    homeAbbr.toUpperCase() === game.top_seed_team_abbr.toUpperCase();
  const awayIsTopSeed =
    game.top_seed_team_abbr != null &&
    awayAbbr.toUpperCase() === game.top_seed_team_abbr.toUpperCase();

  const homeRecord = recordLine(game.home_team_abbr, homeIsTopSeed, game);
  const awayRecord = recordLine(game.away_team_abbr, awayIsTopSeed, game);

  const homePts = game.home_pts;
  const awayPts = game.away_pts;
  const homeWins =
    homePts != null && awayPts != null && homePts > awayPts;
  const awayWins =
    homePts != null && awayPts != null && awayPts > homePts;

  // Live WP bar — only computed for the LIVE state.
  const liveWP =
    state.kind === "live" && homePts != null && awayPts != null
      ? liveWinProbability(homePts, awayPts)
      : null;

  return (
    <>
      <style>{`
        @keyframes cv-broadsheet-live-pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.4; transform: scale(0.85); }
        }
        .cv-broadsheet-live-dot {
          animation: cv-broadsheet-live-pulse 1.4s ease-in-out infinite;
        }
      `}</style>
      <Link
      href={`/games/${encodeURIComponent(game.game_id)}`}
      className="block bip-panel rounded-2xl overflow-hidden hover:-translate-y-0.5 transition-transform focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
      style={{
        background: "rgba(255,249,241,0.6)",
        borderColor: "var(--border)",
      }}
    >
      <div className="px-5 py-4 space-y-3">
        {/* ── Kicker row ─────────────────────────────────────────────── */}
        <div className="flex items-center justify-between gap-3">
          <p
            className="flex items-center gap-2"
            style={{
              fontFamily: "var(--font-geist-mono)",
              fontSize: 11,
              letterSpacing: "0.16em",
              textTransform: "uppercase",
              color:
                state.kind === "live"
                  ? "var(--danger-ink)"
                  : "var(--muted)",
            }}
          >
            {state.kind === "live" && (
              <span
                className="cv-broadsheet-live-dot"
                aria-hidden
                style={{
                  display: "inline-block",
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: "#e85b3c",
                }}
              />
            )}
            {state.kicker}
          </p>
          {game.round != null && (
            <span
              style={{
                fontFamily: "var(--font-geist-mono)",
                fontSize: 10,
                letterSpacing: "0.14em",
                textTransform: "uppercase",
                color: "var(--muted)",
              }}
            >
              R{game.round}
            </span>
          )}
        </div>

        {/* ── Away row ───────────────────────────────────────────────── */}
        <TeamRow
          abbr={awayAbbr}
          record={awayRecord}
          score={awayPts}
          isWinner={awayWins}
          state={state.kind}
        />

        {/* ── Home row ───────────────────────────────────────────────── */}
        <TeamRow
          abbr={homeAbbr}
          record={homeRecord}
          score={homePts}
          isWinner={homeWins}
          state={state.kind}
        />

        {/* ── Live WP bar ────────────────────────────────────────────── */}
        {liveWP != null && (
          <div className="pt-1">
            <div
              className="h-1.5 w-full rounded-full overflow-hidden flex"
              style={{ background: "var(--surface-alt)" }}
              aria-label={`Live win probability: ${homeAbbr} ${Math.round(liveWP * 100)}%`}
            >
              <div
                style={{
                  width: `${Math.round(liveWP * 100)}%`,
                  background: "var(--accent)",
                }}
              />
              <div
                style={{
                  width: `${100 - Math.round(liveWP * 100)}%`,
                  background: "var(--danger-ink)",
                }}
              />
            </div>
            <div
              className="mt-1 flex items-center justify-between"
              style={{
                fontFamily: "var(--font-geist-mono)",
                fontSize: 10,
                letterSpacing: "0.1em",
                color: "var(--muted)",
              }}
            >
              <span>
                {homeAbbr} {Math.round(liveWP * 100)}%
              </span>
              <span>
                {awayAbbr} {100 - Math.round(liveWP * 100)}%
              </span>
            </div>
          </div>
        )}

        {/* ── Italic storyline footer ────────────────────────────────── */}
        {game.headline_storyline ? (
          <p
            className="pt-1 text-sm italic text-[var(--muted)]"
            style={{
              fontFamily: "var(--font-display)",
              lineHeight: 1.5,
            }}
          >
            {game.headline_storyline}
          </p>
        ) : null}
      </div>
    </Link>
    </>
  );
}

function TeamRow({
  abbr,
  record,
  score,
  isWinner,
  state,
}: {
  abbr: string;
  record: string | null;
  score: number | null;
  isWinner: boolean;
  state: State["kind"];
}) {
  // Score-large for live + final games. Score-blank ("—") for scheduled.
  const showScore = state === "live" || state === "final";
  return (
    <div className="flex items-center gap-3">
      {/* Logo glyph (placeholder square — matches DailyPlayoffSlate). */}
      <span
        aria-hidden
        className="inline-block w-7 h-7 rounded-md border border-[var(--border)]"
        style={{ background: "var(--surface-alt)" }}
      />
      <div className="flex-1 min-w-0">
        <p
          className="text-sm font-semibold text-[var(--foreground)] truncate"
          style={{ fontFamily: "var(--font-display)" }}
        >
          {abbr}
        </p>
        {record && (
          <p
            className="text-[11px] text-[var(--muted)]"
            style={{
              fontFamily: "var(--font-geist-mono)",
              letterSpacing: "0.06em",
            }}
          >
            {record}
          </p>
        )}
      </div>
      <div className="shrink-0 text-right">
        {showScore ? (
          <p
            className="tabular-nums font-bold"
            style={{
              fontFamily: "var(--font-display)",
              fontSize: 24,
              lineHeight: 1,
              color: isWinner ? "var(--accent)" : "var(--foreground)",
            }}
          >
            {score ?? 0}
          </p>
        ) : (
          <p
            className="tabular-nums text-[var(--muted)]"
            style={{
              fontFamily: "var(--font-display)",
              fontSize: 24,
              lineHeight: 1,
            }}
          >
            —
          </p>
        )}
      </div>
    </div>
  );
}
