"use client";

import useSWR from "swr";
import Link from "next/link";
import { getPlayoffsToday } from "@/lib/api";
import type {
  PlayoffSeriesGameWithMatchup,
  PlayoffTodayResponse,
} from "@/lib/types";

/**
 * Sprint 77 (Stream B / EB1): Hero "above-the-fold" newsprint cover.
 *
 * Two-column layout:
 *   - Left: kicker → big serif headline → italic lede → 3 stat pills.
 *   - Right: parchment "From the desk" pull-quote box.
 *
 * The headline + lede are derived from the highest-priority playoff game on
 * today's slate (live > final > tipoff). When no slate is available we render
 * a graceful evergreen broadsheet cover.
 */

interface HeroPick {
  kicker: string;
  headline: string;
  lede: string;
  pills: string[];
}

function pickHero(games: readonly PlayoffSeriesGameWithMatchup[]): HeroPick {
  // 1. Live game (both scores, no winner).
  const live = games.find(
    (g) =>
      g.home_pts != null &&
      g.away_pts != null &&
      g.winner_team_id == null
  );
  if (live) {
    const story = live.headline_storyline ??
      `${live.away_team_abbr ?? "TBD"} vs ${live.home_team_abbr ?? "TBD"} — live tonight.`;
    return {
      kicker: `Live · Game ${live.series_game_num ?? "?"}`,
      headline: `${live.away_team_abbr ?? "TBD"} at ${live.home_team_abbr ?? "TBD"}, on the floor.`,
      lede: story,
      pills: [
        `Series ${live.top_wins ?? 0}-${live.bottom_wins ?? 0}`,
        `Round ${live.round ?? "?"}`,
        "Live",
      ],
    };
  }

  // 2. Most recent FINAL.
  const final = games.find((g) => g.winner_team_id != null);
  if (final) {
    const story = final.headline_storyline ??
      `${final.away_team_abbr ?? "TBD"} vs ${final.home_team_abbr ?? "TBD"} — wrapped tonight.`;
    return {
      kicker: `Final · Game ${final.series_game_num ?? "?"}`,
      headline: `${final.away_team_abbr ?? "TBD"} ${final.away_pts ?? 0} — ${final.home_team_abbr ?? "TBD"} ${final.home_pts ?? 0}.`,
      lede: story,
      pills: [
        `Series ${final.top_wins ?? 0}-${final.bottom_wins ?? 0}`,
        `Round ${final.round ?? "?"}`,
        "Final",
      ],
    };
  }

  // 3. Next scheduled tipoff.
  const next = games[0];
  if (next) {
    const story = next.headline_storyline ??
      `Tip-off tonight in the ${next.away_team_abbr ?? "TBD"}-${next.home_team_abbr ?? "TBD"} series.`;
    return {
      kicker: `Tonight · Game ${next.series_game_num ?? "?"}`,
      headline: `${next.away_team_abbr ?? "TBD"} at ${next.home_team_abbr ?? "TBD"}, tonight.`,
      lede: story,
      pills: [
        `Series ${next.top_wins ?? 0}-${next.bottom_wins ?? 0}`,
        `Round ${next.round ?? "?"}`,
        "Scheduled",
      ],
    };
  }

  // 4. Evergreen fallback — no slate today.
  return {
    kicker: "Today's edition",
    headline: "The bracket holds — and the math is restless.",
    lede:
      "No tip-off tonight, but the storylines keep moving. Read the desk for what's still in play.",
    pills: ["Bracket", "Series tracker", "Narrative leaders"],
  };
}

export default function BroadsheetHero() {
  const { data } = useSWR<PlayoffTodayResponse>(
    ["broadsheet-hero-today"],
    () => getPlayoffsToday(),
    { refreshInterval: 60_000, revalidateOnFocus: true }
  );

  const games = data?.games ?? [];
  const pick = pickHero(games);

  return (
    <section className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-6">
      {/* ── Left: headline + lede + stat pills ───────────────────────── */}
      <div
        className="bip-panel rounded-[1.85rem] px-7 py-8"
        style={{
          background: "rgba(255,249,241,0.6)",
        }}
      >
        <p className="bip-kicker mb-4">{pick.kicker}</p>
        <h2
          className="bip-display font-bold text-[var(--foreground)]"
          style={{
            fontSize: "clamp(2rem, 4.4vw, 3.6rem)",
            letterSpacing: "-0.025em",
            lineHeight: 1.05,
          }}
        >
          {pick.headline}
        </h2>
        <p
          className="mt-5 italic text-[var(--muted)]"
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "clamp(1rem, 1.4vw, 1.2rem)",
            lineHeight: 1.55,
          }}
        >
          {pick.lede}
        </p>
        <div className="mt-6 flex flex-wrap items-center gap-2">
          {pick.pills.map((pill) => (
            <span
              key={pill}
              className="bip-pill"
              style={{
                fontSize: 11,
                fontFamily: "var(--font-geist-mono)",
                letterSpacing: "0.1em",
                textTransform: "uppercase",
                padding: "0.35rem 0.8rem",
              }}
            >
              {pill}
            </span>
          ))}
        </div>
        <Link
          href="/bracket"
          className="mt-6 inline-flex items-center text-sm font-medium bip-link"
        >
          Open the playoff command center →
        </Link>
      </div>

      {/* ── Right: From-the-desk pull-quote ──────────────────────────── */}
      <aside
        className="bip-panel rounded-[1.85rem] px-6 py-7 flex flex-col"
        style={{
          background:
            "linear-gradient(180deg, rgba(234,219,183,0.55) 0%, rgba(255,249,241,0.85) 100%)",
          borderColor: "rgba(180,137,61,0.28)",
        }}
      >
        <p className="bip-kicker mb-3">From the desk</p>
        <blockquote
          className="text-[var(--foreground)]"
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "1.05rem",
            lineHeight: 1.55,
          }}
        >
          <span
            aria-hidden
            className="block text-[var(--signal)]"
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "3rem",
              lineHeight: 0.6,
              marginBottom: "0.4rem",
            }}
          >
            &ldquo;
          </span>
          <em>
            Possession-by-possession truth still beats the box score.
            Read the matchups, not the noise.
          </em>
        </blockquote>
        <p
          className="mt-4 text-xs"
          style={{
            fontFamily: "var(--font-geist-mono)",
            letterSpacing: "0.14em",
            textTransform: "uppercase",
            color: "var(--muted)",
          }}
        >
          — The Editors
        </p>
      </aside>
    </section>
  );
}
