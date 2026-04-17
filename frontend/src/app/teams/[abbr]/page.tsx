"use client";

import Image from "next/image";
import Link from "next/link";
import { useMemo, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import {
  useTeamAvailability,
  useTeamPrepQueue,
  useTeamRoster,
  useTeamAnalytics,
  useTeamFocusLevers,
  useTeamIntelligence,
  useTeamRotationReport,
  useTeamSplits,
  useLineupImpactReport,
  usePlayTypeEVReport,
  useMatchupFlagsReport,
  useFollowThroughReport,
} from "@/hooks/usePlayerStats";
import AvailabilitySummaryCard from "@/components/AvailabilitySummaryCard";
import TeamAnalyticsPanel from "@/components/TeamAnalyticsPanel";
import TeamDefenseShotLab from "@/components/TeamDefenseShotLab";
import TeamIntelligencePanel from "@/components/TeamIntelligencePanel";
import TeamPrepQueuePanel from "@/components/TeamPrepQueuePanel";
import TeamRotationIntelligencePanel from "@/components/TeamRotationIntelligencePanel";
import TeamLineupsPanel from "@/components/TeamLineupsPanel";
import TeamDecisionToolsPanel from "@/components/TeamDecisionToolsPanel";
import TeamSplitsPanel from "@/components/TeamSplitsPanel";
import type { TeamPrepQueueItem, TeamRosterPlayer } from "@/lib/types";

const DEFAULT_SEASON = "2024-25";

function formatValue(value: number | null | undefined, digits = 1) {
  return value == null ? "-" : value.toFixed(digits);
}

function coverageTone(status: "none" | "partial" | "ready") {
  if (status === "ready") return "bip-success";
  if (status === "partial") return "bip-pill";
  return "bg-[var(--surface-alt)] text-[var(--muted)]";
}

type Tab = "decision" | "prep" | "intelligence" | "roster" | "analytics" | "splits" | "lineups";

export default function TeamDetailPage() {
  const params = useParams<{ abbr: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const teamAbbreviation = params.abbr?.toUpperCase() ?? null;
  const activeTabParam = searchParams.get("tab");
  const seasonParam = searchParams.get("season")?.toUpperCase() ?? null;
  const opponentParam = searchParams.get("opponent")?.toUpperCase() ?? null;
  const sourceSurfaceParam = searchParams.get("source_surface");
  const sourceLabelParam = searchParams.get("source_label");
  const reasonParam = searchParams.get("reason");
  const [selectedTab, setSelectedTab] = useState<Tab>("intelligence");
  const [selectedSeason, setSelectedSeason] = useState<string>("");
  const activeTab =
    (activeTabParam && (["decision", "prep", "intelligence", "roster", "analytics", "splits", "lineups"] as Tab[]).includes(activeTabParam as Tab)
      ? (activeTabParam as Tab)
      : selectedTab);

  const { data: roster, error } = useTeamRoster(teamAbbreviation);
  const availableSeasons = useMemo(() => {
    const seasons = Array.from(
      new Set(
        (roster?.players ?? [])
          .map((player) => player.season)
          .filter((season): season is string => Boolean(season))
      )
    );
    return seasons.sort((a, b) => b.localeCompare(a));
  }, [roster]);
  const effectiveSeason =
    (selectedSeason && availableSeasons.includes(selectedSeason) ? selectedSeason : null) ??
    (seasonParam && availableSeasons.includes(seasonParam) ? seasonParam : null) ??
    availableSeasons[0] ??
    DEFAULT_SEASON;

  const {
    data: intelligence,
    isLoading: intelligenceLoading,
    error: intelligenceError,
  } = useTeamIntelligence(
    activeTab === "intelligence" || activeTab === "decision" ? teamAbbreviation : null,
    effectiveSeason
  );
  const {
    data: prepQueue,
    isLoading: prepLoading,
    error: prepError,
  } = useTeamPrepQueue(
    activeTab === "prep" || activeTab === "decision" ? teamAbbreviation : null,
    activeTab === "prep" || activeTab === "decision" ? effectiveSeason : null,
    10
  );
  const {
    data: rotationReport,
    isLoading: rotationLoading,
    error: rotationError,
  } = useTeamRotationReport(
    activeTab === "intelligence" || activeTab === "decision" ? teamAbbreviation : null,
    effectiveSeason
  );
  const {
    data: currentAnalytics,
    isLoading: analyticsLoading,
    error: analyticsError,
  } = useTeamAnalytics(teamAbbreviation, effectiveSeason);
  const {
    data: teamSplits,
    isLoading: splitsLoading,
    error: splitsError,
  } = useTeamSplits(
    activeTab === "splits" || activeTab === "prep" ? teamAbbreviation : null,
    activeTab === "splits" || activeTab === "prep" ? effectiveSeason : null
  );
  const {
    data: availability,
    isLoading: availabilityLoading,
    error: availabilityError,
  } = useTeamAvailability(
    activeTab === "roster" ? teamAbbreviation : null,
    activeTab === "roster" ? effectiveSeason : null
  );
  const effectiveSeasonIndex = availableSeasons.indexOf(effectiveSeason);
  const priorSeason =
    effectiveSeasonIndex >= 0 && effectiveSeasonIndex < availableSeasons.length - 1
      ? availableSeasons[effectiveSeasonIndex + 1]
      : null;
  const { data: priorAnalytics } = useTeamAnalytics(teamAbbreviation, priorSeason);
  const currentPath = teamAbbreviation ? `/teams/${teamAbbreviation}` : "/teams";

  const opponentOptions = useMemo(() => {
    const seen = new Set<string>();
    const options: { value: string; label: string }[] = [];
    (prepQueue?.items ?? []).forEach((item) => {
      if (!item.opponent_abbreviation || seen.has(item.opponent_abbreviation)) return;
      seen.add(item.opponent_abbreviation);
      options.push({
        value: item.opponent_abbreviation,
        label: `${item.opponent_abbreviation} · ${item.opponent_name ?? "Upcoming opponent"}`,
      });
    });
    (intelligence?.recent_games ?? []).forEach((game) => {
      if (!game.opponent_abbreviation || seen.has(game.opponent_abbreviation)) return;
      seen.add(game.opponent_abbreviation);
      options.push({
        value: game.opponent_abbreviation,
        label: `${game.opponent_abbreviation} · recent opponent`,
      });
    });
    return options;
  }, [intelligence?.recent_games, prepQueue?.items]);

  const selectedOpponent =
    opponentParam && opponentOptions.some((option) => option.value === opponentParam)
      ? opponentParam
      : opponentOptions[0]?.value ?? opponentParam ?? null;

  const { data: focusLevers } = useTeamFocusLevers(
    activeTab === "intelligence" || activeTab === "decision" ? teamAbbreviation : null,
    effectiveSeason,
    activeTab === "decision" ? selectedOpponent : null
  );

  const selectedPrepItem = useMemo<TeamPrepQueueItem | null>(
    () =>
      (prepQueue?.items ?? []).find((item) => item.opponent_abbreviation === selectedOpponent) ?? null,
    [prepQueue?.items, selectedOpponent]
  );

  const { data: lineupImpact } = useLineupImpactReport(
    activeTab === "decision" ? teamAbbreviation : null,
    activeTab === "decision" ? effectiveSeason : null,
    activeTab === "decision" ? selectedOpponent : null,
    10,
    25
  );
  const { data: playTypeEV } = usePlayTypeEVReport(
    activeTab === "decision" ? teamAbbreviation : null,
    activeTab === "decision" ? effectiveSeason : null,
    activeTab === "decision" ? selectedOpponent : null,
    10
  );
  const { data: matchupFlags } = useMatchupFlagsReport(
    activeTab === "decision" ? teamAbbreviation : null,
    activeTab === "decision" ? selectedOpponent : null,
    activeTab === "decision" ? effectiveSeason : null
  );
  const decisionReason =
    reasonParam ??
    selectedPrepItem?.first_adjustment_label ??
    focusLevers?.focus_levers?.[0]?.title ??
    "opponent-aware follow-through";
  const { data: followThrough } = useFollowThroughReport(
    activeTab === "decision" && teamAbbreviation
      ? {
          source_type: "decision",
          source_id: `${teamAbbreviation}:${selectedOpponent ?? "none"}:${selectedPrepItem?.game_id ?? "decision"}`,
          team: teamAbbreviation,
          opponent: selectedOpponent ?? undefined,
          player_ids: lineupImpact?.recommended_rotation?.[0]?.player_ids ?? [],
          lineup_key: lineupImpact?.recommended_rotation?.[0]?.lineup_key ?? undefined,
          season: effectiveSeason,
          window: 8,
          context: {
            source_surface: sourceSurfaceParam ?? "team-decision",
            source_label: sourceLabelParam ?? `Decision vs ${selectedOpponent ?? teamAbbreviation}`,
            reason: decisionReason,
            return_to: `${currentPath}?tab=decision&season=${effectiveSeason}${selectedOpponent ? `&opponent=${selectedOpponent}` : ""}`,
            linkage_quality: "timeline",
          },
        }
      : null
  );

  const sortedPlayers = useMemo(
    () =>
      [...(roster?.players ?? [])].sort(
        (a, b) => (b.pts_pg ?? -1) - (a.pts_pg ?? -1)
      ),
    [roster]
  );

  const leaders = useMemo(() => {
    if (!roster) return [];

    const getLeader = (
      label: string,
      selector: (player: TeamRosterPlayer) => number | null | undefined,
      digits = 1
    ) => {
      const player = [...roster.players]
        .filter((entry) => selector(entry) != null)
        .sort((a, b) => (selector(b) ?? -Infinity) - (selector(a) ?? -Infinity))[0];

      return {
        label,
        player,
        value: player ? formatValue(selector(player), digits) : "-",
      };
    };

    return [
      getLeader("Scoring leader", (player) => player.pts_pg),
      getLeader("Top playmaker", (player) => player.ast_pg),
      getLeader("Best BPM", (player) => player.bpm),
      getLeader("Best PER", (player) => player.per),
    ];
  }, [roster]);

  const syncCoverage =
    roster && roster.players.length > 0
      ? Math.round((roster.synced_count / roster.players.length) * 100)
      : 0;
  const pbpCoverage = intelligence?.pbp_coverage ?? null;
  const pbpCoveragePct =
    pbpCoverage && pbpCoverage.eligible_games > 0
      ? Math.round((pbpCoverage.synced_games / pbpCoverage.eligible_games) * 100)
      : 0;
  const teamTrendCards =
    currentAnalytics && priorAnalytics
      ? [
          {
            label: "Net Rating YoY",
            value: currentAnalytics.net_rating,
            delta:
              currentAnalytics.net_rating != null && priorAnalytics.net_rating != null
                ? currentAnalytics.net_rating - priorAnalytics.net_rating
                : null,
          },
          {
            label: "PTS YoY",
            value: currentAnalytics.pts_pg,
            delta:
              currentAnalytics.pts_pg != null && priorAnalytics.pts_pg != null
                ? currentAnalytics.pts_pg - priorAnalytics.pts_pg
                : null,
          },
          {
            label: "AST YoY",
            value: currentAnalytics.ast_pg,
            delta:
              currentAnalytics.ast_pg != null && priorAnalytics.ast_pg != null
                ? currentAnalytics.ast_pg - priorAnalytics.ast_pg
                : null,
          },
        ]
      : [];

  if (error) {
    return (
      <div className="bip-panel mx-auto max-w-6xl py-16 text-center rounded-[2rem]">
        <h1 className="bip-display text-3xl font-bold text-[var(--foreground)]">
          Team not available
        </h1>
        <p className="mt-4 text-[var(--muted)]">
          This team has not been synced yet, or the backend could not return it.
        </p>
        <Link
          href="/teams"
          className="bip-btn-primary mt-6 inline-flex rounded-full px-5 py-2 text-sm font-medium"
        >
          Browse synced teams
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <div className="space-y-3">
        <Link
          href="/teams"
          className="inline-flex items-center gap-1 text-sm text-[var(--muted)] bip-link"
        >
          ← Back to Teams
        </Link>

        {!roster ? (
          <div className="space-y-3 animate-pulse">
            <div className="h-6 w-24 rounded-full bg-gray-200 dark:bg-gray-800" />
            <div className="h-12 w-80 rounded-2xl bg-gray-200 dark:bg-gray-800" />
            <div className="h-5 w-full max-w-2xl rounded-xl bg-gray-200 dark:bg-gray-800" />
          </div>
        ) : (
          <div className="bip-panel-strong rounded-[2rem] p-8">
            <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <p className="bip-kicker">
                  {roster.abbreviation}
                </p>
                <h1 className="bip-display mt-3 text-5xl font-bold text-[var(--foreground)]">
                  {roster.name}
                </h1>
                <p className="mt-3 max-w-2xl text-[var(--muted)]">
                  Team analytics, roster, and individual player profiles.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <div className="rounded-2xl bip-metric p-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                    Active roster
                  </div>
                  <div className="mt-2 text-3xl font-semibold text-[var(--foreground)]">
                    {roster.players.length}
                  </div>
                </div>
                <div className="rounded-2xl bip-metric p-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                    Synced
                  </div>
                  <div className="mt-2 text-3xl font-semibold text-[var(--foreground)]">
                    {roster.synced_count}
                  </div>
                </div>
                <div className="rounded-2xl bip-accent-card p-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-[var(--accent)]">
                    Roster coverage
                  </div>
                  <div className="mt-2 text-3xl font-semibold text-[var(--accent-strong)]">
                    {syncCoverage}%
                  </div>
                </div>
                <div className="rounded-2xl bip-metric p-4">
                  <div className="flex items-center justify-between gap-2">
                    <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                      PBP status
                    </div>
                    {pbpCoverage ? (
                      <span
                        className={`rounded-full px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] ${coverageTone(pbpCoverage.status)}`}
                      >
                        {pbpCoverage.status}
                      </span>
                    ) : null}
                  </div>
                  <div className="mt-2 text-3xl font-semibold text-[var(--foreground)]">
                    {pbpCoverage ? `${pbpCoveragePct}%` : intelligenceLoading ? "…" : "—"}
                  </div>
                  <div className="mt-2 text-sm text-[var(--muted)]">
                    {pbpCoverage
                      ? `${pbpCoverage.synced_games}/${pbpCoverage.eligible_games} games tracked`
                      : "Open the intelligence tab to load derived team coverage."}
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-6 flex flex-wrap items-center gap-3">
              <div className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--muted)]">
                Season Focus
              </div>
              <select
                value={effectiveSeason}
                onChange={(e) => {
                  const nextSeason = e.target.value;
                  setSelectedSeason(nextSeason);
                  const params = new URLSearchParams(searchParams.toString());
                  params.set("season", nextSeason);
                  router.replace(`${currentPath}?${params.toString()}`);
                }}
                className="bip-input rounded-xl px-3 py-2 text-sm"
              >
                {availableSeasons.length > 0 ? (
                  availableSeasons.map((season) => (
                    <option key={season} value={season}>
                      {season}
                    </option>
                  ))
                ) : (
                  <option value={DEFAULT_SEASON}>{DEFAULT_SEASON}</option>
                )}
              </select>
              <p className="text-sm text-[var(--muted)]">
                Defaults to the latest synced roster season so intelligence panels open on real local data.
              </p>
            </div>

            <div className="mt-6 flex flex-wrap items-center gap-3">
              <Link
                href="/coverage"
                className="bip-btn-secondary inline-flex rounded-full px-4 py-2 text-sm font-medium"
              >
                {effectiveSeason >= "2024-25" ? "Open coverage board" : "Open coverage board (modern seasons)"}
              </Link>
              <button
                type="button"
                onClick={() => {
                  const params = new URLSearchParams(searchParams.toString());
                  params.set("tab", "intelligence");
                  params.set("season", effectiveSeason);
                  router.replace(`${currentPath}?${params.toString()}`);
                }}
                className="bip-btn-primary inline-flex rounded-full px-4 py-2 text-sm font-medium"
              >
                View sync intelligence
              </button>
              {pbpCoverage ? (
                <div className="text-sm text-[var(--muted)]">
                  {pbpCoverage.status === "ready"
                    ? "This team is fully ready for lineup and on/off analysis."
                    : effectiveSeason >= "2024-25"
                    ? `${pbpCoverage.eligible_games - pbpCoverage.synced_games} games still need play-by-play sync for full team intelligence.`
                    : "Historical seasons use legacy-plus-derived support in Sprint 16, so partial coverage here is an accepted scope limit unless validation shows a real product bug."}
                </div>
              ) : null}
            </div>

            {teamTrendCards.length > 0 && (
              <div className="mt-6 grid gap-3 md:grid-cols-3">
                {teamTrendCards.map((card) => (
                  <div
                    key={card.label}
                    className="rounded-2xl bip-metric p-4"
                  >
                    <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                      {card.label}
                    </div>
                    <div className="mt-2 flex items-end justify-between gap-3">
                      <div className="text-2xl font-bold tabular-nums text-[var(--foreground)]">
                        {formatValue(card.value)}
                      </div>
                      <div
                        className={`text-sm font-semibold tabular-nums ${
                          card.delta == null
                            ? "text-[var(--muted)]"
                            : card.delta >= 0
                            ? "text-[var(--success-ink)]"
                            : "text-[var(--danger-ink)]"
                        }`}
                      >
                        {card.delta == null
                          ? "—"
                          : `${card.delta >= 0 ? "+" : ""}${card.delta.toFixed(1)}`}
                      </div>
                    </div>
                    <div className="mt-1 text-xs text-[var(--muted)]">
                      vs {priorSeason}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Tab bar */}
      <div className="flex rounded-xl overflow-hidden border border-gray-200 dark:border-gray-700 w-fit text-sm">
        {(["decision", "prep", "intelligence", "roster", "analytics", "splits", "lineups"] as Tab[]).map((tab) => (
          <button
            key={tab}
            onClick={() => {
              setSelectedTab(tab);
              const params = new URLSearchParams(searchParams.toString());
              params.set("tab", tab);
              params.set("season", effectiveSeason);
              if (selectedOpponent) {
                params.set("opponent", selectedOpponent);
              }
              router.replace(`${currentPath}?${params.toString()}`);
            }}
            className={`px-5 py-2 capitalize transition-colors ${
              activeTab === tab
                ? "bip-toggle-active"
                : "bip-toggle"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {activeTab === "decision" && roster && intelligence && (
        <section>
          <TeamDecisionToolsPanel
            teamAbbreviation={teamAbbreviation ?? roster.abbreviation}
            season={effectiveSeason}
            selectedOpponent={selectedOpponent}
            opponentOptions={opponentOptions}
            onSelectOpponent={(nextOpponent) => {
              const params = new URLSearchParams(searchParams.toString());
              params.set("tab", "decision");
              params.set("season", effectiveSeason);
              params.set("opponent", nextOpponent);
              router.replace(`${currentPath}?${params.toString()}`);
            }}
            intelligence={intelligence}
            currentAnalytics={currentAnalytics ?? null}
            priorAnalytics={priorAnalytics ?? null}
            focusLevers={focusLevers ?? null}
            prepItem={selectedPrepItem}
            lineupImpact={lineupImpact ?? null}
            playTypeEV={playTypeEV ?? null}
            matchupFlags={matchupFlags ?? null}
            followThrough={followThrough ?? null}
          />
        </section>
      )}

      {activeTab === "prep" && (
        <section>
          {prepLoading && (
            <div className="space-y-4 animate-pulse">
              <div className="h-40 rounded-[2rem] bg-gray-200 dark:bg-gray-700" />
              <div className="grid gap-4 xl:grid-cols-2">
                {[1, 2].map((item) => (
                  <div key={item} className="h-72 rounded-[2rem] bg-gray-200 dark:bg-gray-700" />
                ))}
              </div>
            </div>
          )}
          {prepError && (
            <div className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 text-center text-gray-500 dark:text-gray-400">
              Could not load the prep queue for {effectiveSeason}. The rest of the team room is still available.
            </div>
          )}
          {prepQueue && !prepLoading && <TeamPrepQueuePanel queue={prepQueue} splits={teamSplits ?? null} />}
        </section>
      )}

      {activeTab === "intelligence" && (
        <section>
          {intelligenceLoading && (
            <div className="space-y-4 animate-pulse">
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                {[1, 2, 3, 4].map((item) => (
                  <div key={item} className="h-32 rounded-3xl bg-gray-200 dark:bg-gray-700" />
                ))}
              </div>
              <div className="h-[36rem] rounded-[2rem] bg-gray-200 dark:bg-gray-700" />
              <div className="grid gap-6 xl:grid-cols-[1.05fr,0.95fr]">
                <div className="h-96 rounded-[2rem] bg-gray-200 dark:bg-gray-700" />
                <div className="h-96 rounded-[2rem] bg-gray-200 dark:bg-gray-700" />
              </div>
            </div>
          )}
          {rotationLoading && !intelligenceLoading && (
            <div className="mb-6 h-[36rem] animate-pulse rounded-[2rem] bg-gray-200 dark:bg-gray-700" />
          )}
          {rotationError && (
            <div className="mb-6 rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 text-center text-gray-500 dark:text-gray-400">
              Could not load rotation intelligence for {effectiveSeason}. The base team context is still available below.
            </div>
          )}
          {intelligenceError && (
            <div className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 text-center text-gray-500 dark:text-gray-400">
              Could not load team intelligence for {effectiveSeason}. Some of this view depends on synced play-by-play and current standings data.
            </div>
          )}
          {rotationReport && !rotationLoading && (
            <div className="mb-6">
              <TeamRotationIntelligencePanel
                report={rotationReport}
                teamAbbreviation={teamAbbreviation ?? roster?.abbreviation ?? undefined}
                season={effectiveSeason}
                returnHref={`${currentPath}?tab=decision`}
              />
            </div>
          )}
          {intelligence && !intelligenceLoading && (
            <div className="space-y-6">
              <TeamIntelligencePanel
                intelligence={intelligence}
                currentAnalytics={currentAnalytics ?? null}
                priorAnalytics={priorAnalytics ?? null}
                season={effectiveSeason}
                focusLevers={focusLevers ?? null}
              />
              {roster ? (
                <TeamDefenseShotLab
                  teamId={roster.team_id}
                  teamAbbreviation={roster.abbreviation}
                  seasons={availableSeasons.length > 0 ? availableSeasons : [effectiveSeason]}
                  defaultSeason={effectiveSeason}
                />
              ) : null}
            </div>
          )}
        </section>
      )}

      {/* Analytics tab */}
      {activeTab === "analytics" && (
        <section>
          {analyticsLoading && (
            <div className="space-y-4 animate-pulse">
              <div className="h-8 w-48 rounded-full bg-gray-200 dark:bg-gray-700" />
              <div className="grid grid-cols-4 gap-3">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="h-24 rounded-2xl bg-gray-200 dark:bg-gray-700" />
                ))}
              </div>
              <div className="h-48 rounded-2xl bg-gray-200 dark:bg-gray-700" />
            </div>
          )}
          {analyticsError && (
            <div className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 text-center text-gray-500 dark:text-gray-400">
              Could not load team analytics for {effectiveSeason}. The NBA API may be temporarily unavailable.
            </div>
          )}
          {currentAnalytics && !analyticsLoading && (
            <div className="space-y-6">
              <TeamAnalyticsPanel analytics={currentAnalytics} />
              {roster ? (
                <TeamDefenseShotLab
                  teamId={roster.team_id}
                  teamAbbreviation={roster.abbreviation}
                  seasons={availableSeasons.length > 0 ? availableSeasons : [effectiveSeason]}
                  defaultSeason={effectiveSeason}
                />
              ) : null}
            </div>
          )}
        </section>
      )}

      {/* Splits tab */}
      {activeTab === "splits" && (
        <section>
          {splitsLoading && (
            <div className="space-y-4 animate-pulse">
              <div className="h-40 rounded-[2rem] bg-gray-200 dark:bg-gray-700" />
              <div className="h-64 rounded-[1.8rem] bg-gray-200 dark:bg-gray-700" />
            </div>
          )}
          {splitsError && (
            <div className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 text-center text-gray-500 dark:text-gray-400">
              No split data for {effectiveSeason} yet. Splits are populated by the daily official sync — check back after the next sync run.
            </div>
          )}
          {teamSplits && !splitsLoading && (
            <TeamSplitsPanel splits={teamSplits} />
          )}
        </section>
      )}

      {/* Lineups tab */}
      {activeTab === "lineups" && roster && (
        <TeamLineupsPanel teamId={roster.team_id} season={effectiveSeason} />
      )}

      {/* Roster tab */}
      {activeTab === "roster" && roster && (
        <>
          {availabilityLoading && (
            <section className="mb-4 rounded-[1.8rem] border border-[var(--border)] bg-[var(--surface)] p-6">
              <div className="animate-pulse space-y-4">
                <div className="h-4 w-32 rounded bg-[var(--surface-alt)]" />
                <div className="h-8 w-64 rounded bg-[var(--surface-alt)]" />
                <div className="h-4 w-full rounded bg-[var(--surface-alt)]" />
                <div className="grid gap-3 md:grid-cols-3">
                  {[1, 2, 3].map((item) => (
                    <div key={item} className="h-28 rounded-2xl bg-[var(--surface-alt)]" />
                  ))}
                </div>
              </div>
            </section>
          )}
          {availabilityError && (
            <section className="mb-4 rounded-[1.8rem] border border-[var(--border)] bg-[var(--surface)] p-6 text-sm leading-6 text-[var(--muted-strong)]">
              Could not load the latest roster availability for {effectiveSeason}. The roster board below is still available.
            </section>
          )}
          {availability && !availabilityLoading && (
            <section className="mb-4">
              <AvailabilitySummaryCard availability={availability} />
            </section>
          )}

          <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            {leaders.map((leader) => (
              <div
                key={leader.label}
                className="rounded-3xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5"
              >
                <div className="text-xs font-medium uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400">
                  {leader.label}
                </div>
                <div className="mt-4 text-lg font-semibold text-gray-900 dark:text-gray-100">
                  {leader.player?.full_name ?? "No synced data yet"}
                </div>
                <div className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  {leader.player?.position || "Add more player syncs to unlock"}
                </div>
                <div className="mt-6 text-3xl font-bold text-blue-600 dark:text-blue-300">
                  {leader.value}
                </div>
              </div>
            ))}
          </section>

          <section className="rounded-[2rem] border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 overflow-hidden">
            <div className="flex flex-col gap-2 border-b border-gray-200 dark:border-gray-800 px-6 py-5 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                  Roster Board
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Sorted by points per game using the latest synced regular-season stats.
                </p>
              </div>
              <Link
                href="/player-stats"
                className="text-sm text-blue-500 hover:text-blue-600 transition-colors"
              >
                Cross-team player stats →
              </Link>
            </div>

            <div className="divide-y divide-gray-200 dark:divide-gray-800">
              {sortedPlayers.map((player) => (
                <Link
                  key={player.player_id}
                  href={`/players/${player.player_id}`}
                  className="block px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-800/70 transition-colors"
                >
                  <div className="flex flex-col gap-4 lg:grid lg:grid-cols-[minmax(0,1.4fr)_repeat(4,minmax(64px,0.6fr))] lg:items-center lg:gap-3">
                    <div className="flex min-w-0 items-center gap-3">
                      <div className="relative h-14 w-14 overflow-hidden rounded-2xl bg-gray-100 dark:bg-gray-800">
                        {player.headshot_url ? (
                          <Image
                            src={player.headshot_url}
                            alt={player.full_name}
                            fill
                            className="object-cover object-top"
                          />
                        ) : null}
                      </div>
                      <div className="min-w-0">
                        <div className="truncate font-semibold text-gray-900 dark:text-gray-100">
                          {player.full_name}
                        </div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">
                          {player.position || "N/A"}{player.jersey ? ` · #${player.jersey}` : ""}
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                      <div className="rounded-2xl bg-gray-50 dark:bg-gray-800/80 px-3 py-2 text-right">
                        <div className="text-xs uppercase tracking-[0.18em] text-gray-400">
                          PTS
                        </div>
                        <div className="font-semibold text-gray-900 dark:text-gray-100">
                          {formatValue(player.pts_pg)}
                        </div>
                      </div>
                      <div className="rounded-2xl bg-gray-50 dark:bg-gray-800/80 px-3 py-2 text-right">
                        <div className="text-xs uppercase tracking-[0.18em] text-gray-400">
                          REB
                        </div>
                        <div className="font-semibold text-gray-900 dark:text-gray-100">
                          {formatValue(player.reb_pg)}
                        </div>
                      </div>
                      <div className="rounded-2xl bg-gray-50 dark:bg-gray-800/80 px-3 py-2 text-right">
                        <div className="text-xs uppercase tracking-[0.18em] text-gray-400">
                          AST
                        </div>
                        <div className="font-semibold text-gray-900 dark:text-gray-100">
                          {formatValue(player.ast_pg)}
                        </div>
                      </div>
                      <div className="rounded-2xl bg-gray-50 dark:bg-gray-800/80 px-3 py-2 text-right">
                        <div className="text-xs uppercase tracking-[0.18em] text-gray-400">
                          BPM
                        </div>
                        <div className="font-semibold text-gray-900 dark:text-gray-100">
                          {formatValue(player.bpm)}
                        </div>
                      </div>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
