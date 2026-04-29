"use client";

import { useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { useViewMode } from "@/hooks/useViewMode";
import { useSeasonPhase } from "@/hooks/useSeasonPhase";
import { getBracket, getPlayoffsToday } from "@/lib/api";
import type {
  PlayoffBracketResponse,
  PlayoffSeriesGameWithMatchup,
  PlayoffSeriesResponse,
  PlayoffTodayResponse,
} from "@/lib/types";
import BroadsheetMasthead from "@/components/broadsheet/BroadsheetMasthead";
import TodaysSlate from "@/components/broadsheet/TodaysSlate";
import SeriesTrackerStrip from "@/components/broadsheet/SeriesTrackerStrip";
import BracketStrip from "@/components/broadsheet/BracketStrip";
import NarrativeLeaders from "@/components/broadsheet/NarrativeLeaders";
import StoryRail from "@/components/broadsheet/StoryRail";
import { Kicker, Pill, Hardwood, Reveal, Stat } from "@/components/brand";

const ACTIVE_SEASON_FALLBACK = "2025-26";

const ROUND_LABELS: Record<number, string> = {
  1: "First Round",
  2: "Conference Semifinals",
  3: "Conference Finals",
  4: "NBA Finals",
};

const TODAY_FORMATTER = new Intl.DateTimeFormat("en-US", {
  month: "long",
  day: "numeric",
});

export default function PlayoffsPage() {
  const { viewMode } = useViewMode();
  const router = useRouter();

  // When the user switches mode away from playoff, hand off to the home page
  // which renders the correct variant based on viewMode.
  useEffect(() => {
    if (viewMode === "regular" || viewMode === "offseason") {
      router.replace("/");
    }
  }, [viewMode, router]);

  return (
    <div className="space-y-8">
      <BroadsheetMasthead />

      <Reveal>
        <PlayoffHero />
      </Reveal>

      <Reveal>
        <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-6">
          <TodaysSlate />
          <SeriesTrackerStrip />
        </div>
      </Reveal>

      <Reveal>
        <BracketStrip />
      </Reveal>

      <Reveal>
        <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-6">
          <NarrativeLeaders />
          <StoryRail />
        </div>
      </Reveal>

      <Reveal>
        <ByTheNumbers />
      </Reveal>

      <EndOfEdition />
    </div>
  );
}

// ─── Edition data hook ──────────────────────────────────────────────
// Compose a single derived snapshot of the playoff edition from the
// existing /bracket and /today endpoints. Components that follow read
// fields from this hook and never reach for hardcoded copy.
interface EditionSnapshot {
  round: number | null;
  roundLabel: string;
  gamesToday: number;
  matchupsToday: PlayoffSeriesGameWithMatchup[];
  broadcasters: string[];
  totalGamesPlayed: number;
  avgMarginPts: number | null;
  longestSeriesLabel: string | null;
}

function useEditionSnapshot(): EditionSnapshot {
  const { season } = useSeasonPhase();
  const seasonKey = season ?? ACTIVE_SEASON_FALLBACK;

  const { data: bracket } = useSWR<PlayoffBracketResponse>(
    ["playoff-edition-bracket", seasonKey],
    () => getBracket(seasonKey),
    { refreshInterval: 5 * 60_000 }
  );
  const { data: today } = useSWR<PlayoffTodayResponse>(
    ["playoff-edition-today"],
    () => getPlayoffsToday(),
    { refreshInterval: 60_000 }
  );

  return useMemo(() => {
    const allSeries: PlayoffSeriesResponse[] = bracket
      ? [
          ...(bracket.east ?? []),
          ...(bracket.west ?? []),
          ...(bracket.finals ? [bracket.finals] : []),
        ]
      : [];

    // Current round is the highest round number with at least one active series.
    // Falls back to the highest round present if all are closed.
    const activeRounds = allSeries
      .filter((s) => s.status === "active")
      .map((s) => s.round);
    const allRounds = allSeries.map((s) => s.round);
    const round =
      activeRounds.length > 0
        ? Math.max(...activeRounds)
        : allRounds.length > 0
          ? Math.max(...allRounds)
          : null;
    const roundLabel = round != null ? ROUND_LABELS[round] ?? `Round ${round}` : "Postseason";

    const matchupsToday = today?.games ?? [];
    const gamesToday = matchupsToday.length;

    const broadcasterSet = new Set<string>();
    for (const g of matchupsToday) {
      if (g.broadcaster) broadcasterSet.add(g.broadcaster);
    }
    const broadcasters = Array.from(broadcasterSet);

    // Aggregate completed-game stats across the postseason.
    const completedGames = allSeries.flatMap((s) =>
      (s.games ?? []).filter(
        (g) => g.home_pts != null && g.away_pts != null && g.winner_team_id != null
      )
    );
    const totalGamesPlayed = completedGames.length;
    const margins = completedGames.map((g) => Math.abs((g.home_pts ?? 0) - (g.away_pts ?? 0)));
    const avgMarginPts = margins.length > 0
      ? margins.reduce((a, b) => a + b, 0) / margins.length
      : null;

    // Longest series = most total games played in any single series.
    let longestSeriesLabel: string | null = null;
    let longestCount = 0;
    for (const s of allSeries) {
      const count = (s.games ?? []).filter(
        (g) => g.home_pts != null && g.away_pts != null
      ).length;
      if (count > longestCount && s.top_seed_team_abbr && s.bottom_seed_team_abbr) {
        longestCount = count;
        longestSeriesLabel = `${s.top_seed_team_abbr}-${s.bottom_seed_team_abbr} · ${count}`;
      }
    }

    return {
      round,
      roundLabel,
      gamesToday,
      matchupsToday,
      broadcasters,
      totalGamesPlayed,
      avgMarginPts,
      longestSeriesLabel,
    };
  }, [bracket, today]);
}

// ─── Hero — broadsheet headline + lede ─────────────────────────────
function PlayoffHero() {
  const edition = useEditionSnapshot();

  // Headline templates by game count — compiled rather than free-form so
  // it stays sensible at any volume.
  const headline = (() => {
    if (edition.gamesToday === 0) {
      return (
        <>
          A quiet night,{" "}
          <em className="not-italic" style={{ fontStyle: "italic", color: "var(--accent)" }}>
            but the bracket keeps writing
          </em>
          .
        </>
      );
    }
    if (edition.gamesToday === 1) {
      return (
        <>
          One game tonight,{" "}
          <em className="not-italic" style={{ fontStyle: "italic", color: "var(--accent)" }}>
            one series at the edge
          </em>
          .
        </>
      );
    }
    return (
      <>
        {edition.gamesToday} games tonight,{" "}
        <em className="not-italic" style={{ fontStyle: "italic", color: "var(--accent)" }}>
          the bracket in flux
        </em>
        .
      </>
    );
  })();

  // Subhead — list tonight's matchups in prose form.
  const subhead = (() => {
    if (edition.matchupsToday.length === 0) {
      return "No tip-offs scheduled today. Tomorrow's slate is one refresh away.";
    }
    const segments = edition.matchupsToday
      .map((g) => {
        const away = g.away_team_abbr ?? "TBD";
        const home = g.home_team_abbr ?? "TBD";
        return `${away} at ${home}`;
      });
    return segments.join(" · ") + ".";
  })();

  return (
    <section
      className="relative overflow-hidden rounded-[1.85rem] border border-[var(--border)] bg-[var(--surface)] px-8 py-12"
      style={{ boxShadow: "var(--shadow)" }}
    >
      <Hardwood opacity={0.075} tint="#a8753a" />
      <div className="relative grid grid-cols-1 lg:grid-cols-[1.6fr_1fr] gap-10 items-end">
        <div>
          <Kicker style={{ marginBottom: 14, display: "block" }}>
            {edition.roundLabel}
          </Kicker>
          <h1
            className="bip-display font-bold mb-5"
            style={{
              fontSize: "clamp(48px, 6.4vw, 78px)",
              letterSpacing: "-0.04em",
              lineHeight: 0.96,
              textWrap: "balance",
            }}
          >
            {headline}
          </h1>
          <p
            className="mb-5 text-[var(--muted)]"
            style={{
              fontFamily: "var(--font-display)",
              fontStyle: "italic",
              fontSize: 21,
              lineHeight: 1.45,
              maxWidth: 660,
            }}
          >
            {subhead}
          </p>
          <div className="flex flex-wrap gap-2.5">
            <Pill tone="accent">
              {edition.gamesToday === 1
                ? "1 game tonight"
                : `${edition.gamesToday} games tonight`}
            </Pill>
            <Pill tone="signal">
              {edition.totalGamesPlayed} games played · {edition.roundLabel}
            </Pill>
            {edition.broadcasters.length > 0 && (
              <Pill tone="default">
                Live · {edition.broadcasters.slice(0, 3).join(" · ")}
              </Pill>
            )}
          </div>
        </div>
        <aside
          className="pl-6 lg:border-l border-[var(--border)]"
          aria-label="Edition desk"
        >
          <div
            className="mb-2 text-[10px] font-bold uppercase text-[var(--muted)]"
            style={{
              fontFamily: "var(--font-geist-mono)",
              letterSpacing: "0.16em",
            }}
          >
            From the desk
          </div>
          {edition.matchupsToday.length > 0 ? (
            <ul className="space-y-2">
              {edition.matchupsToday.slice(0, 4).map((g) => {
                const away = g.away_team_abbr ?? "TBD";
                const home = g.home_team_abbr ?? "TBD";
                const isFinal = g.winner_team_id != null;
                const isLive =
                  !isFinal && g.home_pts != null && g.away_pts != null;
                let tag = "Scheduled";
                if (isFinal) tag = "Final";
                else if (isLive) tag = "Live";
                return (
                  <li
                    key={g.game_id}
                    className="flex items-baseline justify-between gap-3"
                  >
                    <span
                      className="text-[var(--foreground)]"
                      style={{
                        fontFamily: "var(--font-display)",
                        fontSize: 15,
                        letterSpacing: "-0.005em",
                      }}
                    >
                      {away} <span className="text-[var(--muted)]">at</span> {home}
                    </span>
                    <span
                      className="text-[10px] font-bold uppercase shrink-0"
                      style={{
                        fontFamily: "var(--font-geist-mono)",
                        letterSpacing: "0.14em",
                        color: tag === "Live" ? "var(--danger-ink)" : "var(--muted)",
                      }}
                    >
                      {tag}
                    </span>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p
              className="text-[var(--foreground)]"
              style={{
                fontFamily: "var(--font-display)",
                fontStyle: "italic",
                fontSize: 16,
                lineHeight: 1.55,
              }}
            >
              The presses rest tonight. Today&apos;s slate is empty;
              tomorrow&apos;s edition is already in proof.
            </p>
          )}
        </aside>
      </div>
    </section>
  );
}

// ─── By the Numbers — strip of four animated stats ──────────────────
function ByTheNumbers() {
  const edition = useEditionSnapshot();

  const todayLabel = useMemo(() => {
    return `Through ${TODAY_FORMATTER.format(new Date())}`;
  }, []);

  return (
    <section className="rounded-[1.85rem] border border-[var(--border)] bg-[var(--surface)] px-6 py-8 sm:px-8">
      <div className="mb-5 flex items-baseline justify-between">
        <div>
          <Kicker>By the numbers</Kicker>
          <h2
            className="bip-display mt-2 font-bold"
            style={{
              fontSize: 26,
              letterSpacing: "-0.025em",
            }}
          >
            The edition, in four lines.
          </h2>
        </div>
        <span
          className="text-[10.5px] font-bold uppercase text-[var(--muted)]"
          style={{
            fontFamily: "var(--font-geist-mono)",
            letterSpacing: "0.14em",
          }}
        >
          {todayLabel}
        </span>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Stat
          label="Playoff games"
          value={edition.totalGamesPlayed}
          decimals={0}
          animate
          tone="default"
        />
        <Stat
          label="Avg margin (pts)"
          value={edition.avgMarginPts ?? 0}
          decimals={1}
          animate
          tone="soft"
        />
        <Stat
          label="Games tonight"
          value={edition.gamesToday}
          decimals={0}
          animate
          tone="signal"
        />
        <Stat
          label="Longest series"
          value={edition.longestSeriesLabel ?? "—"}
          tone="default"
        />
      </div>
    </section>
  );
}

function EndOfEdition() {
  return (
    <div className="py-8 text-center">
      <span
        className="text-[10px] font-bold uppercase text-[var(--muted)]"
        style={{
          fontFamily: "var(--font-geist-mono)",
          letterSpacing: "0.18em",
        }}
      >
        — End of edition —
      </span>
    </div>
  );
}
