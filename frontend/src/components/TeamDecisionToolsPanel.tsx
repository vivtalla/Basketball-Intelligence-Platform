"use client";

import Link from "next/link";
import type {
  TeamAnalytics,
  TeamFocusLeversReport,
  TeamIntelligence,
  TeamRotationReport,
} from "@/lib/types";

interface TeamDecisionToolsPanelProps {
  teamAbbreviation: string;
  season: string;
  intelligence: TeamIntelligence;
  currentAnalytics?: TeamAnalytics | null;
  priorAnalytics?: TeamAnalytics | null;
  focusLevers?: TeamFocusLeversReport | null;
  rotationReport?: TeamRotationReport | null;
}

interface FollowThroughGame {
  game_id: string;
  game_date: string | null;
  opponent_abbreviation: string | null;
  result: string;
  team_score: number | null;
  opponent_score: number | null;
  rotation_note: string;
}

function fmt(value: number | null | undefined, digits = 1) {
  return value == null ? "—" : value.toFixed(digits);
}

function pct(value: number | null | undefined, digits = 1) {
  return value == null ? "—" : `${(value * 100).toFixed(digits)}%`;
}

function signed(value: number | null | undefined, digits = 1) {
  if (value == null) return "—";
  return `${value > 0 ? "+" : ""}${value.toFixed(digits)}`;
}

function buildGameHref(
  teamAbbreviation: string,
  season: string,
  gameId: string,
  reason: string
) {
  const params = new URLSearchParams({
    source: "team-decision",
    source_id: `${teamAbbreviation}:${gameId}`,
    team: teamAbbreviation,
    season,
    reason,
    return_to: `/teams/${teamAbbreviation}?tab=decision`,
  });
  return `/games/${gameId}?${params.toString()}`;
}

function styleLabel(currentAnalytics?: TeamAnalytics | null, priorAnalytics?: TeamAnalytics | null) {
  if (!currentAnalytics) return "Style unknown";
  const pace = currentAnalytics.pace ?? 0;
  const ts = currentAnalytics.ts_pct ?? 0;
  const efg = currentAnalytics.efg_pct ?? 0;
  const tov = currentAnalytics.tov_pct ?? 0;
  const oreb = currentAnalytics.oreb_pct ?? 0;
  const paceDelta = currentAnalytics.pace != null && priorAnalytics?.pace != null ? currentAnalytics.pace - priorAnalytics.pace : null;
  const shotTag = (ts + efg) / 2 >= 0.56 ? "efficient shot profile" : "mixed shot profile";
  const paceTag = pace >= 99 ? "fast pace" : pace <= 96 ? "controlled pace" : "balanced pace";
  const securityTag = tov <= 0.13 ? "clean ball security" : "turnover watch";
  const glassTag = oreb >= 0.29 ? "pressure on the glass" : "modest glass profile";
  const drift = paceDelta == null ? "" : paceDelta >= 0 ? "with recent pace lift" : "with recent pace slowdown";
  return `${paceTag}, ${shotTag}, ${securityTag}, ${glassTag}${drift ? `, ${drift}` : ""}`;
}

export default function TeamDecisionToolsPanel({
  teamAbbreviation,
  season,
  intelligence,
  currentAnalytics = null,
  priorAnalytics = null,
  focusLevers = null,
  rotationReport = null,
}: TeamDecisionToolsPanelProps) {
  const bestLineup = intelligence.best_lineups[0] ?? null;
  const worstLineup = intelligence.worst_lineups[0] ?? null;
  const recentGame = intelligence.recent_games[0] ?? null;
  const followThroughGames: FollowThroughGame[] = rotationReport?.recommended_games?.length
    ? rotationReport.recommended_games
    : intelligence.recent_games.slice(0, 3).map((game) => ({
        game_id: game.game_id,
        game_date: game.game_date,
        opponent_abbreviation: game.opponent_abbreviation,
        result: game.result.startsWith("W") ? "W" : "L",
        team_score: game.team_score,
        opponent_score: game.opponent_score,
        rotation_note: `Review ${game.result.toLowerCase()} against ${game.opponent_abbreviation ?? "the opponent"} for rotation context.`,
      }));

  const lineupDelta =
    bestLineup?.net_rating != null && worstLineup?.net_rating != null
      ? bestLineup.net_rating - worstLineup.net_rating
      : null;
  const lineupNarrative =
    bestLineup && worstLineup
      ? `Best lineup ${fmt(bestLineup.net_rating)} net vs worst lineup ${fmt(worstLineup.net_rating)} net.`
      : "Not enough lineup data to compare the best and worst unit yet.";

  const styleNarrative = styleLabel(currentAnalytics, priorAnalytics);

  const factorHighlights = [
    currentAnalytics?.net_rating != null && priorAnalytics?.net_rating != null
      ? `Net rating ${signed(currentAnalytics.net_rating - priorAnalytics.net_rating)} vs prior season.`
      : "Net rating is available as a baseline, but prior comparison is missing.",
    currentAnalytics?.pace != null && priorAnalytics?.pace != null
      ? `Pace ${signed(currentAnalytics.pace - priorAnalytics.pace, 1)} vs prior season.`
      : `Pace baseline: ${fmt(currentAnalytics?.pace)}.`,
    currentAnalytics?.tov_pct != null && priorAnalytics?.tov_pct != null
      ? `Turnover rate ${signed((currentAnalytics.tov_pct - priorAnalytics.tov_pct) * 100, 1)} pts vs prior season.`
      : `Turnover profile is ${pct(currentAnalytics?.tov_pct)} of possessions.`,
  ];

  return (
    <section className="bip-panel-strong rounded-[2rem] p-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="bip-kicker">Decision Tools</p>
          <h2 className="bip-display mt-3 text-3xl font-semibold text-[var(--foreground)]">
            What should we do with this team now?
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--muted)]">
            CourtVue Labs uses lineup, style, and recent-form signals to give coaches a plain-language decision surface, not a black box.
          </p>
        </div>
        <div className="rounded-full border border-[var(--border)] bg-[rgba(255,255,255,0.72)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted-strong)]">
          {teamAbbreviation} · {season}
        </div>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-2">
        <article className="bip-panel rounded-[1.5rem] p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Lineup expected points
          </p>
          <h3 className="mt-2 text-2xl font-semibold text-[var(--foreground)]">
            Rotation leverage from the best and worst units
          </h3>
          <p className="mt-3 text-sm leading-6 text-[var(--muted-strong)]">
            {lineupNarrative} The gap is a directional guide for minute redistribution, not a fake precision forecast.
          </p>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <div className="rounded-2xl bip-metric p-4">
              <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">Best net</div>
              <div className="mt-2 text-2xl font-semibold text-[var(--accent-strong)]">
                {fmt(bestLineup?.net_rating)}
              </div>
              <div className="mt-1 text-sm text-[var(--muted)]">
                {fmt(bestLineup?.minutes)} min · {bestLineup?.possessions ?? "—"} poss
              </div>
            </div>
            <div className="rounded-2xl bip-metric p-4">
              <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">Worst net</div>
              <div className="mt-2 text-2xl font-semibold text-[var(--danger-ink)]">
                {fmt(worstLineup?.net_rating)}
              </div>
              <div className="mt-1 text-sm text-[var(--muted)]">
                {fmt(worstLineup?.minutes)} min · {worstLineup?.possessions ?? "—"} poss
              </div>
            </div>
            <div className="rounded-2xl bip-accent-card p-4">
              <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--accent)]">Observed swing</div>
              <div className="mt-2 text-2xl font-semibold text-[var(--accent-strong)]">
                {lineupDelta == null ? "—" : signed(lineupDelta)}
              </div>
              <div className="mt-1 text-sm text-[var(--muted)]">
                Use this as the first pass on minute redistribution
              </div>
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-3">
            <Link
              href={`/teams/${teamAbbreviation}?tab=lineups`}
              className="rounded-full border border-[var(--border-strong)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]"
            >
              Open lineups tab
            </Link>
            <Link
              href={`/compare?mode=styles&team_a=${teamAbbreviation}&team_b=${recentGame?.opponent_abbreviation ?? teamAbbreviation}&season=${season}`}
              className="rounded-full border border-[var(--border-strong)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]"
            >
              Open style compare
            </Link>
          </div>
          <div className="mt-4 space-y-2 rounded-2xl border border-[var(--border)] bg-[rgba(255,255,255,0.72)] p-4">
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
              Factor snapshot
            </div>
            <ul className="space-y-1 text-sm leading-6 text-[var(--muted-strong)]">
              {factorHighlights.map((highlight) => (
                <li key={highlight}>• {highlight}</li>
              ))}
            </ul>
          </div>
        </article>

        <article className="bip-panel rounded-[1.5rem] p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Pace and style
          </p>
          <h3 className="mt-2 text-2xl font-semibold text-[var(--foreground)]">
            {styleNarrative}
          </h3>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl bip-metric p-4">
              <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">Pace</div>
              <div className="mt-2 text-2xl font-semibold text-[var(--foreground)]">
                {fmt(currentAnalytics?.pace)}
              </div>
              <div className="mt-1 text-sm text-[var(--muted)]">
                {priorAnalytics?.pace != null ? `vs ${fmt(priorAnalytics.pace)}` : "Season baseline"}
              </div>
            </div>
            <div className="rounded-2xl bip-metric p-4">
              <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">TS%</div>
              <div className="mt-2 text-2xl font-semibold text-[var(--foreground)]">
                {pct(currentAnalytics?.ts_pct)}
              </div>
              <div className="mt-1 text-sm text-[var(--muted)]">
                {priorAnalytics?.ts_pct != null ? `vs ${pct(priorAnalytics.ts_pct)}` : "Season baseline"}
              </div>
            </div>
            <div className="rounded-2xl bip-metric p-4">
              <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">eFG%</div>
              <div className="mt-2 text-2xl font-semibold text-[var(--foreground)]">
                {pct(currentAnalytics?.efg_pct)}
              </div>
              <div className="mt-1 text-sm text-[var(--muted)]">
                {priorAnalytics?.efg_pct != null ? `vs ${pct(priorAnalytics.efg_pct)}` : "Season baseline"}
              </div>
            </div>
            <div className="rounded-2xl bip-metric p-4">
              <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">Turnovers</div>
              <div className="mt-2 text-2xl font-semibold text-[var(--foreground)]">
                {pct(currentAnalytics?.tov_pct)}
              </div>
              <div className="mt-1 text-sm text-[var(--muted)]">
                {priorAnalytics?.tov_pct != null ? `vs ${pct(priorAnalytics.tov_pct)}` : "Season baseline"}
              </div>
            </div>
          </div>
        </article>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[1fr,0.9fr]">
        <article className="bip-panel rounded-[1.5rem] p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Matchup pressure
          </p>
          <h3 className="mt-2 text-2xl font-semibold text-[var(--foreground)]">
            Plain-language levers the staff can act on
          </h3>
          <div className="mt-4 grid gap-3">
            {focusLevers?.focus_levers?.length ? (
              focusLevers.focus_levers.slice(0, 3).map((lever) => (
                <div
                  key={`${lever.factor_id}-${lever.title}`}
                  className="rounded-2xl border border-[var(--border)] bg-[rgba(255,255,255,0.68)] p-4"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="font-semibold text-[var(--foreground)]">{lever.title}</div>
                    <span className="rounded-full bg-[rgba(33,72,59,0.08)] px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--accent-strong)]">
                      {lever.impact_label}
                    </span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-[var(--muted-strong)]">
                    {lever.summary}
                  </p>
                </div>
              ))
            ) : (
              <div className="rounded-2xl border border-[var(--border)] px-4 py-4 text-sm text-[var(--muted-strong)]">
                No focus levers are available yet. Load the team intelligence tab to pull the latest four-factor summary.
              </div>
            )}
          </div>
        </article>

        <article className="bip-panel rounded-[1.5rem] p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Game follow-through
          </p>
          <h3 className="mt-2 text-2xl font-semibold text-[var(--foreground)]">
            Jump straight to the most useful game tape
          </h3>
          <div className="mt-4 space-y-3">
              {followThroughGames.length ? (
                followThroughGames.slice(0, 3).map((game) => (
                <Link
                  key={game.game_id}
                  href={buildGameHref(teamAbbreviation, season, game.game_id, game.rotation_note)}
                  className="block rounded-2xl border border-[var(--border)] bg-[rgba(255,255,255,0.68)] p-4 transition hover:border-[rgba(33,72,59,0.28)] hover:bg-[rgba(216,228,221,0.24)]"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                        {game.game_date ?? "Date unavailable"}
                      </div>
                      <div className="mt-1 text-lg font-semibold text-[var(--foreground)]">
                        {game.opponent_abbreviation ?? "Opponent TBD"}
                      </div>
                    </div>
                    <div className="text-right text-sm font-semibold text-[var(--accent-strong)]">
                      {game.result ?? "W"}
                    </div>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-[var(--muted-strong)]">
                    {game.rotation_note}
                  </p>
                </Link>
              ))
            ) : (
              <div className="rounded-2xl border border-[var(--border)] px-4 py-4 text-sm text-[var(--muted-strong)]">
                No follow-through games are available yet for this season.
              </div>
            )}
          </div>
          {recentGame ? (
            <div className="mt-4 text-sm text-[var(--muted)]">
              Latest game context: {recentGame.opponent_abbreviation ?? "Unknown opponent"} · {recentGame.result}
            </div>
          ) : null}
        </article>
      </div>
    </section>
  );
}
