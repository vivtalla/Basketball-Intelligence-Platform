"use client";

import Link from "next/link";
import type {
  FollowThroughResponse,
  LineupImpactResponse,
  MatchupFlagsResponse,
  PlayTypeEVResponse,
  TeamAnalytics,
  TeamFocusLeversReport,
  TeamIntelligence,
  TeamPrepQueueItem,
} from "@/lib/types";

interface TeamDecisionToolsPanelProps {
  teamAbbreviation: string;
  season: string;
  selectedOpponent: string | null;
  opponentOptions: { value: string; label: string }[];
  onSelectOpponent: (opponent: string) => void;
  intelligence: TeamIntelligence;
  currentAnalytics?: TeamAnalytics | null;
  priorAnalytics?: TeamAnalytics | null;
  focusLevers?: TeamFocusLeversReport | null;
  prepItem?: TeamPrepQueueItem | null;
  lineupImpact?: LineupImpactResponse | null;
  playTypeEV?: PlayTypeEVResponse | null;
  matchupFlags?: MatchupFlagsResponse | null;
  followThrough?: FollowThroughResponse | null;
}

function fmt(value: number | null | undefined, digits = 1) {
  return value == null ? "—" : value.toFixed(digits);
}

function signed(value: number | null | undefined, digits = 1) {
  if (value == null) return "—";
  return `${value > 0 ? "+" : ""}${value.toFixed(digits)}`;
}

function styleLabel(currentAnalytics?: TeamAnalytics | null, priorAnalytics?: TeamAnalytics | null) {
  if (!currentAnalytics) return "Style baseline unavailable";
  const pace = currentAnalytics.pace ?? 0;
  const ts = currentAnalytics.ts_pct ?? 0;
  const efg = currentAnalytics.efg_pct ?? 0;
  const paceDelta = currentAnalytics.pace != null && priorAnalytics?.pace != null ? currentAnalytics.pace - priorAnalytics.pace : null;
  const shotTag = (ts + efg) / 2 >= 0.56 ? "efficient shot profile" : "mixed shot profile";
  const paceTag = pace >= 99 ? "fast pace" : pace <= 96 ? "controlled pace" : "balanced pace";
  const drift = paceDelta == null ? "" : paceDelta >= 0 ? "with recent pace lift" : "with recent pace slowdown";
  return `${paceTag}, ${shotTag}${drift ? `, ${drift}` : ""}`;
}

function buildCompareHref(teamAbbreviation: string, season: string, opponent: string | null, prepItem?: TeamPrepQueueItem | null) {
  if (prepItem?.compare_url) return prepItem.compare_url;
  if (!opponent) return `/compare?mode=teams&team_a=${teamAbbreviation}&team_b=${teamAbbreviation}&season=${season}`;
  const params = new URLSearchParams({
    mode: "teams",
    team_a: teamAbbreviation,
    team_b: opponent,
    season,
    source_type: "team-decision",
    source_id: `${teamAbbreviation}:${opponent}:${season}`,
    reason: prepItem?.first_adjustment_label ?? "decision follow-through",
    return_to: `/teams/${teamAbbreviation}?tab=decision&season=${season}&opponent=${opponent}`,
  });
  return `/compare?${params.toString()}`;
}

export default function TeamDecisionToolsPanel({
  teamAbbreviation,
  season,
  selectedOpponent,
  opponentOptions,
  onSelectOpponent,
  intelligence,
  currentAnalytics = null,
  priorAnalytics = null,
  focusLevers = null,
  prepItem = null,
  lineupImpact = null,
  playTypeEV = null,
  matchupFlags = null,
  followThrough = null,
}: TeamDecisionToolsPanelProps) {
  const styleNarrative = styleLabel(currentAnalytics, priorAnalytics);
  const topRecommendedLineup = lineupImpact?.recommended_rotation?.[0] ?? null;
  const topCurrentLineup = lineupImpact?.current_rotation?.[0] ?? null;
  const topActionFlag = playTypeEV?.overused_flags?.[0] ?? playTypeEV?.underused_flags?.[0] ?? null;
  const recentGame = intelligence.recent_games[0] ?? null;
  const followThroughGames = followThrough?.games ?? [];

  return (
    <section className="bip-panel-strong rounded-[2rem] p-6">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p className="bip-kicker">Decision Tools</p>
          <h2 className="bip-display mt-3 text-3xl font-semibold text-[var(--foreground)]">
            What should we emphasize for this opponent?
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--muted)]">
            This workspace combines prep context, lineup impact, matchup flags, and replay follow-through so the staff can move from recommendation to review without rebuilding the story.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="rounded-full border border-[var(--border)] bg-[rgba(255,255,255,0.72)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted-strong)]">
            {teamAbbreviation} · {season}
          </div>
          <select
            value={selectedOpponent ?? ""}
            onChange={(event) => onSelectOpponent(event.target.value)}
            className="bip-input min-w-[14rem] rounded-full px-4 py-2 text-sm"
          >
            {opponentOptions.length ? (
              opponentOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))
            ) : (
              <option value="">Choose opponent</option>
            )}
          </select>
        </div>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[1.15fr,0.85fr]">
        <article className="bip-panel rounded-[1.5rem] p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            First emphasis
          </p>
          <h3 className="mt-2 text-2xl font-semibold text-[var(--foreground)]">
            {prepItem?.first_adjustment_label ?? focusLevers?.focus_levers?.[0]?.title ?? "Select an opponent to load a coaching prompt"}
          </h3>
          <p className="mt-3 text-sm leading-6 text-[var(--muted-strong)]">
            {prepItem?.first_adjustment_summary ??
              focusLevers?.focus_levers?.[0]?.summary ??
              "Once an opponent context is selected, this view will recommend the first lever to press and where to go next to review it."}
          </p>
          {prepItem?.first_adjustment_rationale || prepItem?.urgency_rationale ? (
            <div className="mt-4 rounded-2xl border border-[var(--border)] bg-[rgba(255,255,255,0.72)] p-4 text-sm leading-6 text-[var(--muted-strong)]">
              <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                Why now
              </div>
              <p className="mt-2">
                {prepItem?.urgency_rationale ?? "Prep urgency is stable."}
              </p>
              {prepItem?.first_adjustment_rationale ? (
                <p className="mt-2">{prepItem.first_adjustment_rationale}</p>
              ) : null}
            </div>
          ) : null}
          <div className="mt-4 flex flex-wrap gap-3">
            <Link
              href={prepItem?.pre_read_url ?? `/pre-read?team=${teamAbbreviation}&opponent=${selectedOpponent ?? teamAbbreviation}&season=${season}`}
              className="bip-btn-primary rounded-full px-4 py-2 text-sm font-medium"
            >
              Open pre-read
            </Link>
            <Link
              href={buildCompareHref(teamAbbreviation, season, selectedOpponent, prepItem)}
              className="bip-btn-secondary rounded-full px-4 py-2 text-sm font-medium"
            >
              Open comparison sandbox
            </Link>
            {prepItem?.scouting_url ? (
              <Link
                href={prepItem.scouting_url}
                className="rounded-full border border-[var(--border-strong)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]"
              >
                Open scouting mode
              </Link>
            ) : null}
          </div>
        </article>

        <article className="bip-panel rounded-[1.5rem] p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Opponent frame
          </p>
          <h3 className="mt-2 text-2xl font-semibold text-[var(--foreground)]">
            {selectedOpponent ? `${selectedOpponent} changes the read` : "Choose the matchup lens"}
          </h3>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl bip-metric p-4">
              <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">Style</div>
              <div className="mt-2 text-sm font-semibold text-[var(--foreground)]">{styleNarrative}</div>
            </div>
            <div className="rounded-2xl bip-metric p-4">
              <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">Best edge</div>
              <div className="mt-2 text-sm font-semibold text-[var(--foreground)]">
                {prepItem?.best_edge_label ?? "Still calibrating"}
              </div>
              <div className="mt-1 text-sm text-[var(--muted)]">
                {prepItem?.best_edge_rationale ?? prepItem?.best_edge_summary ?? "No clean edge has cleared the confidence bar yet."}
              </div>
            </div>
            <div className="rounded-2xl bip-metric p-4">
              <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">Pace</div>
              <div className="mt-2 text-2xl font-semibold text-[var(--foreground)]">{fmt(currentAnalytics?.pace)}</div>
              <div className="mt-1 text-sm text-[var(--muted)]">
                {priorAnalytics?.pace != null ? `vs ${fmt(priorAnalytics.pace)}` : "Season baseline"}
              </div>
            </div>
            <div className="rounded-2xl bip-metric p-4">
              <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">Net rating</div>
              <div className="mt-2 text-2xl font-semibold text-[var(--foreground)]">{fmt(currentAnalytics?.net_rating)}</div>
              <div className="mt-1 text-sm text-[var(--muted)]">
                {currentAnalytics?.net_rating != null && priorAnalytics?.net_rating != null
                  ? `${signed(currentAnalytics.net_rating - priorAnalytics.net_rating)} vs prior year`
                  : "Directional baseline only"}
              </div>
            </div>
          </div>
        </article>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-2">
        <article className="bip-panel rounded-[1.5rem] p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Lineup impact
          </p>
          <h3 className="mt-2 text-2xl font-semibold text-[var(--foreground)]">
            Minute pressure with opponent context
          </h3>
          <p className="mt-3 text-sm leading-6 text-[var(--muted-strong)]">
            {lineupImpact?.impact_summary ??
              "Lineup impact will populate once the opponent-aware report is available. This stays directional rather than pretending to know the exact rotation answer."}
          </p>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <div className="rounded-2xl bip-metric p-4">
              <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">Recommended unit</div>
              <div className="mt-2 text-sm font-semibold text-[var(--foreground)]">
                {topRecommendedLineup ? topRecommendedLineup.player_names.slice(0, 3).join(" · ") : "—"}
              </div>
              <div className="mt-1 text-sm text-[var(--muted)]">
                {topRecommendedLineup ? `${fmt(topRecommendedLineup.expected_points_per_game)} pts/game · ${topRecommendedLineup.confidence} confidence` : "Waiting on lineup read"}
              </div>
            </div>
            <div className="rounded-2xl bip-metric p-4">
              <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">Current anchor</div>
              <div className="mt-2 text-sm font-semibold text-[var(--foreground)]">
                {topCurrentLineup ? topCurrentLineup.player_names.slice(0, 3).join(" · ") : "—"}
              </div>
              <div className="mt-1 text-sm text-[var(--muted)]">
                {topCurrentLineup ? `${fmt(topCurrentLineup.minutes)} min · ${topCurrentLineup.possessions ?? "—"} poss` : "Waiting on current rotation"}
              </div>
            </div>
            <div className="rounded-2xl bip-accent-card p-4">
              <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--accent)]">Warnings</div>
              <div className="mt-2 text-sm font-semibold text-[var(--accent-strong)]">
                {lineupImpact?.warnings?.[0] ?? "Opponent-aware read active"}
              </div>
            </div>
          </div>
          {topRecommendedLineup?.evidence?.length ? (
            <div className="mt-4 rounded-2xl border border-[var(--border)] bg-[rgba(255,255,255,0.72)] p-4 text-sm leading-6 text-[var(--muted-strong)]">
              <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Evidence</div>
              <ul className="mt-2 space-y-1">
                {topRecommendedLineup.evidence.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </article>

        <article className="bip-panel rounded-[1.5rem] p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Matchup flags
          </p>
          <h3 className="mt-2 text-2xl font-semibold text-[var(--foreground)]">
            Where the matchup should actually bend
          </h3>
          <div className="mt-4 space-y-3">
            {matchupFlags?.flags?.length ? (
              matchupFlags.flags.slice(0, 3).map((flag) => (
                <div key={flag.flag_id} className="rounded-2xl border border-[var(--border)] bg-[rgba(255,255,255,0.68)] p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="font-semibold text-[var(--foreground)]">{flag.title}</div>
                    <span className="rounded-full bg-[rgba(33,72,59,0.08)] px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--accent-strong)]">
                      {flag.severity} · {flag.confidence}
                    </span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-[var(--muted-strong)]">{flag.summary}</p>
                  {flag.evidence[0] ? (
                    <p className="mt-2 text-xs uppercase tracking-[0.14em] text-[var(--muted)]">
                      {flag.evidence[0].label}: {fmt(flag.evidence[0].team_value, 2)} vs {fmt(flag.evidence[0].opponent_value, 2)}
                    </p>
                  ) : null}
                </div>
              ))
            ) : (
              <div className="rounded-2xl border border-[var(--border)] px-4 py-4 text-sm text-[var(--muted-strong)]">
                No clean matchup flags cleared the threshold yet for this opponent.
              </div>
            )}
          </div>
          {topActionFlag ? (
            <div className="mt-4 rounded-2xl border border-[var(--border)] bg-[rgba(255,255,255,0.72)] p-4">
              <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                Action-family pressure
              </div>
              <div className="mt-2 text-sm font-semibold text-[var(--foreground)]">{topActionFlag.label}</div>
              <p className="mt-1 text-sm leading-6 text-[var(--muted-strong)]">{topActionFlag.reason}</p>
            </div>
          ) : null}
        </article>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[1fr,0.92fr]">
        <article className="bip-panel rounded-[1.5rem] p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Focus levers
          </p>
          <h3 className="mt-2 text-2xl font-semibold text-[var(--foreground)]">
            Coherent coaching levers, not disconnected modules
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
                  <p className="mt-2 text-sm leading-6 text-[var(--muted-strong)]">{lever.summary}</p>
                  {lever.projected_impact ? (
                    <p className="mt-2 text-sm leading-6 text-[var(--muted)]">{lever.projected_impact}</p>
                  ) : null}
                  {lever.coaching_prompt ? (
                    <p className="mt-2 text-xs uppercase tracking-[0.14em] text-[var(--muted)]">
                      Prompt: {lever.coaching_prompt}
                    </p>
                  ) : null}
                </div>
              ))
            ) : (
              <div className="rounded-2xl border border-[var(--border)] px-4 py-4 text-sm text-[var(--muted-strong)]">
                No focus levers are available yet. Once the matchup context is present, this panel will align prep, compare, and replay around the same story.
              </div>
            )}
          </div>
        </article>

        <article className="bip-panel rounded-[1.5rem] p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Follow-through games
          </p>
          <h3 className="mt-2 text-2xl font-semibold text-[var(--foreground)]">
            Review the most relevant recent sequences next
          </h3>
          <div className="mt-4 space-y-3">
            {followThroughGames.length ? (
              followThroughGames.slice(0, 4).map((game) => (
                <Link
                  key={game.game_id}
                  href={game.deep_link_url}
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
                    <div className="rounded-full bg-[rgba(33,72,59,0.08)] px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--accent-strong)]">
                      {game.result ?? "Review"}
                    </div>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-[var(--muted-strong)]">{game.why_this_game}</p>
                  {game.supporting_metrics.length ? (
                    <p className="mt-2 text-xs uppercase tracking-[0.14em] text-[var(--muted)]">
                      {game.supporting_metrics.join(" · ")}
                    </p>
                  ) : null}
                </Link>
              ))
            ) : (
              <div className="rounded-2xl border border-[var(--border)] px-4 py-4 text-sm text-[var(--muted-strong)]">
                No follow-through games are available yet for this opponent. The fallback is still to use recent games, but this sprint keeps the recommendation bounded rather than pretending to know more.
              </div>
            )}
          </div>
          {recentGame ? (
            <div className="mt-4 text-sm text-[var(--muted)]">
              Latest team result: {recentGame.opponent_abbreviation ?? "Unknown opponent"} · {recentGame.result}
            </div>
          ) : null}
        </article>
      </div>
    </section>
  );
}
