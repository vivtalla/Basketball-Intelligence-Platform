"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { useRouter, useSearchParams } from "next/navigation";
import { usePlayerSearch } from "@/hooks/usePlayerSearch";
import {
  usePlayerProfile,
  usePlayerCareerStats,
  useTeamComparison,
  useTeamAnalytics,
  useLineups,
  useTeams,
} from "@/hooks/usePlayerStats";
import { useCompareAvailability } from "@/hooks/useCompareAvailability";
import CompareShotLab from "@/components/CompareShotLab";
import ComparisonView from "@/components/ComparisonView";
import TeamComparisonView from "@/components/TeamComparisonView";
import LineupComparisonView from "@/components/LineupComparisonView";
import StyleComparisonView from "@/components/StyleComparisonView";
import ChartStatusBadge from "@/components/ChartStatusBadge";
import PerformanceCalendar from "@/components/PerformanceCalendar";

interface PlayerSlotProps {
  slotLabel: string;
  selectedId: number | null;
  onSelect: (id: number) => void;
  onClear: () => void;
}

function PlayerSlot({ slotLabel, selectedId, onSelect, onClear }: PlayerSlotProps) {
  const { query, setQuery, results, isLoading } = usePlayerSearch();
  const [isFocused, setIsFocused] = useState(false);
  const { data: profile } = usePlayerProfile(selectedId);

  const showDropdown = isFocused && query.length >= 2;

  if (selectedId && profile) {
    return (
      <div className="bip-panel flex items-center gap-3 rounded-2xl p-4">
        <div className="relative h-14 w-14 shrink-0 overflow-hidden rounded-full border border-[var(--border)] bg-[var(--surface-alt)]">
          {profile.headshot_url ? (
            <Image
              src={profile.headshot_url}
              alt={profile.full_name}
              fill
              className="object-cover object-top"
              onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
            />
          ) : null}
        </div>
        <div className="min-w-0 flex-1">
          <div className="truncate font-semibold text-[var(--foreground)]">{profile.full_name}</div>
          <div className="text-xs text-[var(--muted)]">
            {profile.team_name || "Free Agent"} · {profile.position || "—"}
          </div>
        </div>
        <button onClick={onClear} className="bip-link shrink-0 text-xs">
          Change
        </button>
      </div>
    );
  }

  return (
    <div className="relative">
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setTimeout(() => setIsFocused(false), 200)}
          placeholder={`Search ${slotLabel}...`}
          className="bip-input w-full rounded-2xl px-4 py-4 pr-10 text-[var(--foreground)]"
        />
        {isLoading ? (
          <div className="absolute right-4 top-1/2 -translate-y-1/2">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-[var(--surface-alt)] border-t-[var(--accent)]" />
          </div>
        ) : null}
      </div>

      {showDropdown ? (
        <div className="bip-panel absolute left-0 right-0 top-full z-50 mt-1 overflow-hidden rounded-xl">
          {results.length === 0 && !isLoading ? (
            <div className="px-4 py-3 text-sm text-[var(--muted)]">No players found</div>
          ) : (
            results.slice(0, 6).map((player) => (
              <button
                key={player.id}
                onMouseDown={() => {
                  onSelect(player.id);
                  setQuery("");
                }}
                className="w-full px-4 py-3 text-left transition-colors hover:bg-[rgba(216,228,221,0.34)]"
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="font-medium text-[var(--foreground)]">{player.full_name}</span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs ${
                      player.is_active
                        ? "bip-success"
                        : "bg-[var(--surface-alt)] text-[var(--muted)]"
                    }`}
                  >
                    {player.is_active ? "Active" : "Retired"}
                  </span>
                </div>
              </button>
            ))
          )}
        </div>
      ) : null}
    </div>
  );
}

interface TeamSlotProps {
  slotLabel: string;
  selectedTeam: string;
  onSelect: (abbr: string) => void;
  teams: Array<{ abbreviation: string; name: string }>;
}

function TeamSlot({ slotLabel, selectedTeam, onSelect, teams }: TeamSlotProps) {
  return (
    <label className="space-y-2">
      <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
        {slotLabel}
      </span>
      <select
        value={selectedTeam}
        onChange={(event) => onSelect(event.target.value)}
        className="bip-input w-full rounded-2xl px-4 py-4 text-sm"
      >
        <option value="">Select team</option>
        {teams.map((team) => (
          <option key={team.abbreviation} value={team.abbreviation}>
            {team.abbreviation} · {team.name}
          </option>
        ))}
      </select>
    </label>
  );
}

function ComparePageInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const rawMode = searchParams.get("mode");
  const mode =
    rawMode === "teams" || rawMode === "lineups" || rawMode === "styles"
      ? rawMode
      : "players";

  const p1Id = searchParams.get("p1") ? Number(searchParams.get("p1")) : null;
  const p2Id = searchParams.get("p2") ? Number(searchParams.get("p2")) : null;
  const teamA = searchParams.get("team_a") ?? "";
  const teamB = searchParams.get("team_b") ?? "";
  const season = searchParams.get("season") ?? "2024-25";
  const lineupAParam = searchParams.get("lineup_a");
  const lineupBParam = searchParams.get("lineup_b");
  const sourceType = searchParams.get("source_type");
  const sourceId = searchParams.get("source_id");
  const sourceReason = searchParams.get("reason");
  const returnTo = searchParams.get("return_to");
  const replayGameId = searchParams.get("replay_game_id");
  const replayFocusEventId = searchParams.get("replay_focus_event_id");
  const replayFocusActionNumber = searchParams.get("replay_focus_action_number");
  const replayLinkageQuality = searchParams.get("replay_linkage_quality");
  const replaySourceSurface = searchParams.get("replay_source_surface");
  const replaySourceLabel = searchParams.get("replay_source_label");
  const replayReason = searchParams.get("replay_reason");

  const { data: profile1, error: profile1Error } = usePlayerProfile(p1Id);
  const { data: career1, error: career1Error } = usePlayerCareerStats(p1Id);
  const { data: profile2, error: profile2Error } = usePlayerProfile(p2Id);
  const { data: career2, error: career2Error } = usePlayerCareerStats(p2Id);
  const { data: teams } = useTeams();
  const teamAInfo = teams?.find((team) => team.abbreviation === teamA) ?? null;
  const teamBInfo = teams?.find((team) => team.abbreviation === teamB) ?? null;
  const { data: analyticsA } = useTeamAnalytics(teamA || null, teamA ? season : null);
  const { data: analyticsB } = useTeamAnalytics(teamB || null, teamB ? season : null);
  const { data: lineupsA, isLoading: lineupsALoading } = useLineups(
    mode === "lineups" && teamAInfo ? season : null,
    teamAInfo?.team_id,
    5,
    12
  );
  const { data: lineupsB, isLoading: lineupsBLoading } = useLineups(
    mode === "lineups" && teamBInfo ? season : null,
    teamBInfo?.team_id,
    5,
    12
  );
  const { data: teamComparison, isLoading: teamComparisonLoading } = useTeamComparison(
    mode !== "players" && teamA ? teamA : null,
    mode !== "players" && teamB ? teamB : null,
    mode !== "players" ? season : null,
    {
      sourceType,
      sourceId,
      reason: sourceReason,
    }
  );
  const { data: compareAvailability } = useCompareAvailability(
    mode === "players" ? p1Id : null,
    mode === "players" ? p2Id : null
  );

  const compareSeasons =
    career1 && career2
      ? Array.from(
          new Set([
            ...career1.seasons.map((entry) => entry.season),
            ...career1.playoff_seasons.map((entry) => entry.season),
            ...career2.seasons.map((entry) => entry.season),
            ...career2.playoff_seasons.map((entry) => entry.season),
          ].filter(Boolean))
        ).sort((left, right) => right.localeCompare(left))
      : ["2025-26", "2024-25", "2023-24", "2022-23"];

  function updateParams(mutator: (params: URLSearchParams) => void) {
    const params = new URLSearchParams(searchParams.toString());
    mutator(params);
    router.push(`/compare?${params.toString()}`);
  }

  function selectPlayer(slot: 1 | 2, id: number) {
    updateParams((params) => {
      params.set(slot === 1 ? "p1" : "p2", String(id));
    });
  }

  function clearPlayer(slot: 1 | 2) {
    updateParams((params) => {
      params.delete(slot === 1 ? "p1" : "p2");
    });
  }

  function setMode(nextMode: "players" | "teams" | "lineups" | "styles") {
    updateParams((params) => {
      if (nextMode === "players") {
        params.delete("mode");
        params.delete("team_a");
        params.delete("team_b");
        params.delete("lineup_a");
        params.delete("lineup_b");
      } else {
        params.set("mode", nextMode);
        if (!params.get("season")) params.set("season", "2024-25");
      }
    });
  }

  function selectTeam(slot: "team_a" | "team_b", abbr: string) {
    updateParams((params) => {
      params.set("mode", mode === "players" ? "teams" : mode);
      params.set(slot, abbr);
      if (!params.get("season")) params.set("season", "2024-25");
    });
  }

  function selectSeason(nextSeason: string) {
    updateParams((params) => {
      if (mode === "players") {
        params.delete("mode");
      } else {
        params.set("mode", mode);
      }
      params.set("season", nextSeason);
    });
  }

  function selectLineup(slot: "lineup_a" | "lineup_b", lineupKey: string) {
    updateParams((params) => {
      params.set("mode", "lineups");
      params.set(slot, lineupKey);
      if (!params.get("season")) params.set("season", "2024-25");
    });
  }

  const bothSelected = Boolean(p1Id && p2Id);
  const comparisonError =
    profile1Error || career1Error || profile2Error || career2Error;
  const playerAReady = Boolean(
    profile1 &&
      career1 &&
      profile1.data_status !== "missing" &&
      career1.data_status !== "missing"
  );
  const playerBReady = Boolean(
    profile2 &&
      career2 &&
      profile2.data_status !== "missing" &&
      career2.data_status !== "missing"
  );
  const bothReady = playerAReady && playerBReady;
  const loadingComparison =
    bothSelected &&
    !comparisonError &&
    (!profile1 || !profile2 || !career1 || !career2);
  const staleComparison =
    bothSelected &&
    (profile1?.data_status === "stale" ||
      profile2?.data_status === "stale" ||
      career1?.data_status === "stale" ||
      career2?.data_status === "stale");
  const replayHref = (() => {
    if (!replayGameId) return null;
    const params = new URLSearchParams();
    params.set("source", replaySourceSurface ?? sourceType ?? "compare");
    if (replaySourceSurface) params.set("source_surface", replaySourceSurface);
    if (sourceId) params.set("source_id", sourceId);
    if (replaySourceLabel) params.set("source_label", replaySourceLabel);
    if (replayReason) params.set("reason", replayReason);
    if (replayLinkageQuality) params.set("linkage_quality", replayLinkageQuality);
    if (replayFocusEventId) params.set("focus_event_id", replayFocusEventId);
    if (replayFocusActionNumber) params.set("focus_action_number", replayFocusActionNumber);
    params.set("return_to", `/compare?${searchParams.toString()}`);
    return `/games/${replayGameId}?${params.toString()}`;
  })();

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-6">
        <Link href="/" className="bip-link inline-flex items-center gap-1 text-sm">
          ← Back to Home
        </Link>
      </div>

      <div className="bip-panel-strong mb-8 rounded-[2rem] p-8">
        <p className="bip-kicker">Compare</p>
        <h1 className="bip-display mt-3 text-3xl font-semibold text-[var(--foreground)]">
          {mode === "teams"
            ? "Comparison Sandbox"
            : mode === "lineups"
            ? "Lineup Comparison Sandbox"
            : mode === "styles"
            ? "Style Comparison Sandbox"
            : "Compare Players"}
        </h1>
        <p className="mt-2 text-[var(--muted)]">
          {mode === "teams"
            ? "Switch from player scouting to team-vs-team edges in one coach-friendly sandbox."
            : mode === "lineups"
            ? "Compare the rotation shapes of two lineups without leaving the sandbox."
            : mode === "styles"
            ? "Compare pace, shot quality, turnover pressure, and glass control across two teams."
            : "Search for two players to compare their stats side by side."}
        </p>
        <div className="mt-5 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => window.print()}
            className="rounded-full border border-[var(--border-strong)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]"
          >
            Print compare view
          </button>
          {replayHref ? (
            <Link
              href={replayHref}
              className="bip-btn-primary rounded-full px-4 py-2 text-sm font-medium"
            >
              Open replay evidence
            </Link>
          ) : null}
          {returnTo ? (
            <Link
              href={returnTo}
              className="rounded-full border border-[var(--border)] px-4 py-2 text-sm font-medium text-[var(--muted-strong)] transition hover:bg-[rgba(255,255,255,0.72)]"
            >
              Return to source
            </Link>
          ) : null}
        </div>
        {sourceType ? (
          <div className="mt-5 rounded-2xl border border-[var(--border)] bg-[rgba(255,255,255,0.72)] px-4 py-4 text-sm leading-6 text-[var(--muted-strong)]">
            This compare view was launched from <span className="font-semibold text-[var(--foreground)]">{sourceType.replaceAll("-", " ")}</span>
            {sourceReason ? ` with the prompt "${sourceReason.replaceAll("+", " ")}".` : "."}
          </div>
        ) : null}
        {replayReason ? (
          <div className="mt-4 rounded-2xl border border-[rgba(33,72,59,0.16)] bg-[rgba(216,228,221,0.22)] px-4 py-4 text-sm leading-6 text-[var(--muted-strong)]">
            Replay continuity is attached to this compare session: {replayReason}
            {replayLinkageQuality ? ` The handoff stays labeled as ${replayLinkageQuality}.` : ""}
          </div>
        ) : null}
      </div>

      <div className="mb-8 flex w-fit overflow-hidden rounded-xl border border-[var(--border)] text-sm">
        <button
          onClick={() => setMode("players")}
          className={`px-5 py-2 transition-colors ${
            mode === "players"
              ? "bip-toggle-active"
              : "bip-toggle"
          }`}
        >
          Players
        </button>
        <button
          onClick={() => setMode("teams")}
          className={`px-5 py-2 transition-colors ${
            mode === "teams"
              ? "bip-toggle-active"
              : "bip-toggle"
          }`}
        >
          Teams
        </button>
        <button
          onClick={() => setMode("lineups")}
          className={`px-5 py-2 transition-colors ${
            mode === "lineups"
              ? "bip-toggle-active"
              : "bip-toggle"
          }`}
        >
          Lineups
        </button>
        <button
          onClick={() => setMode("styles")}
          className={`px-5 py-2 transition-colors ${
            mode === "styles"
              ? "bip-toggle-active"
              : "bip-toggle"
          }`}
        >
          Styles
        </button>
      </div>

      {mode === "players" ? (
        <>
          <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <PlayerSlot
              slotLabel="Player 1"
              selectedId={p1Id}
              onSelect={(id) => selectPlayer(1, id)}
              onClear={() => clearPlayer(1)}
            />
            <PlayerSlot
              slotLabel="Player 2"
              selectedId={p2Id}
              onSelect={(id) => selectPlayer(2, id)}
              onClear={() => clearPlayer(2)}
            />
          </div>

          {loadingComparison && !bothReady ? (
            <div className="flex items-center justify-center gap-3 py-16 text-[var(--muted)]">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-[var(--accent)] border-t-transparent" />
              <span className="text-sm">Loading player data…</span>
            </div>
          ) : null}

          {!p1Id && !p2Id ? (
            <div className="bip-empty rounded-[2rem] py-16 text-center">
              <div className="mb-4 text-5xl">⚖️</div>
              <p className="text-lg font-medium text-[var(--foreground)]">Select two players to compare</p>
              <p className="mt-1 text-sm">Search above to get started</p>
            </div>
          ) : null}

          {(p1Id || p2Id) && !bothSelected && !loadingComparison ? (
            <div className="bip-empty rounded-[2rem] py-16 text-center">
              <div className="mb-4 text-5xl">🧭</div>
              <p className="text-lg font-medium text-[var(--foreground)]">Pick one more player</p>
              <p className="mt-1 text-sm">The comparison board opens after both player slots are filled.</p>
            </div>
          ) : null}

          {bothSelected && comparisonError ? (
            <div className="bip-panel rounded-[2rem] border border-[rgba(239,68,68,0.25)] bg-[rgba(127,29,29,0.06)] p-6 text-center">
              <p className="text-lg font-medium text-[var(--foreground)]">Unable to load one player comparison</p>
              <p className="mt-2 text-sm text-[var(--muted)]">
                One of the selected players did not return profile or career data. Try a different player or clear and reselect.
              </p>
            </div>
          ) : null}

          {bothSelected && !comparisonError && !loadingComparison && !bothReady ? (
            <div className="rounded-[2rem] border border-[rgba(25,52,42,0.12)] bg-[rgba(255,255,255,0.74)] p-6 text-center">
              <div className="flex justify-center gap-2">
                <ChartStatusBadge
                  status={
                    profile1?.data_status === "missing" || career1?.data_status === "missing" ||
                    profile2?.data_status === "missing" || career2?.data_status === "missing"
                      ? "missing"
                      : "stale"
                  }
                />
              </div>
              <p className="mt-3 text-lg font-medium text-[var(--foreground)]">
                Comparison is waiting on persisted player data
              </p>
              <p className="mt-2 text-sm text-[var(--muted)]">
                This page no longer rescues missing data live from the NBA API. If one player has not been synced yet, the compare board stays stable and waits for the queued refresh.
              </p>
            </div>
          ) : null}

          {bothReady ? (
            <>
              {staleComparison && (
                <div className="rounded-[1.5rem] border border-[rgba(194,122,44,0.2)] bg-[rgba(194,122,44,0.06)] px-5 py-4 text-sm text-[var(--muted-strong)]">
                  One or both player records are currently cached. The duel view is still usable while background refresh jobs catch up.
                </div>
              )}
              <ComparisonView
                playerA={{ profile: profile1!, career: career1! }}
                playerB={{ profile: profile2!, career: career2! }}
                availabilityA={compareAvailability?.player_a}
                availabilityB={compareAvailability?.player_b}
              />
              <CompareShotLab
                playerAId={profile1!.id}
                playerBId={profile2!.id}
                playerALabel={profile1!.full_name}
                playerBLabel={profile2!.full_name}
                season={season}
                seasons={compareSeasons}
                onSeasonChange={selectSeason}
              />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <PerformanceCalendar playerId={profile1!.id} season={season} />
                <PerformanceCalendar playerId={profile2!.id} season={season} />
              </div>
            </>
          ) : null}
        </>
      ) : mode === "teams" ? (
        <div className="space-y-8">
          <div className="grid gap-4 md:grid-cols-3">
            <TeamSlot
              slotLabel="Team A"
              selectedTeam={teamA}
              onSelect={(abbr) => selectTeam("team_a", abbr)}
              teams={teams ?? []}
            />
            <TeamSlot
              slotLabel="Team B"
              selectedTeam={teamB}
              onSelect={(abbr) => selectTeam("team_b", abbr)}
              teams={teams ?? []}
            />
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                Season
              </span>
              <select
                value={season}
                onChange={(event) => selectSeason(event.target.value)}
                className="bip-input w-full rounded-2xl px-4 py-4 text-sm"
              >
                {["2025-26", "2024-25", "2023-24", "2022-23"].map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {teamComparisonLoading ? (
            <div className="flex items-center justify-center gap-3 py-16 text-[var(--muted)]">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-[var(--accent)] border-t-transparent" />
              <span className="text-sm">Loading team comparison…</span>
            </div>
          ) : teamComparison ? (
            <TeamComparisonView comparison={teamComparison} />
          ) : (
            <div className="bip-empty rounded-[2rem] py-16 text-center">
              <div className="mb-4 text-5xl">🏀</div>
              <p className="text-lg font-medium text-[var(--foreground)]">Select two teams to open the sandbox</p>
              <p className="mt-1 text-sm">Compare efficiency, pace, rebounding, and turnover edges in one frame.</p>
            </div>
          )}
        </div>
      ) : mode === "lineups" ? (
        <div className="space-y-8">
          <div className="grid gap-4 md:grid-cols-3">
            <TeamSlot
              slotLabel="Team A"
              selectedTeam={teamA}
              onSelect={(abbr) => selectTeam("team_a", abbr)}
              teams={teams ?? []}
            />
            <TeamSlot
              slotLabel="Team B"
              selectedTeam={teamB}
              onSelect={(abbr) => selectTeam("team_b", abbr)}
              teams={teams ?? []}
            />
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                Season
              </span>
              <select
                value={season}
                onChange={(event) => selectSeason(event.target.value)}
                className="bip-input w-full rounded-2xl px-4 py-4 text-sm"
              >
                {["2025-26", "2024-25", "2023-24", "2022-23"].map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {lineupsALoading || lineupsBLoading ? (
            <div className="flex items-center justify-center gap-3 py-16 text-[var(--muted)]">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-[var(--accent)] border-t-transparent" />
              <span className="text-sm">Loading lineup comparison…</span>
            </div>
          ) : teamAInfo && teamBInfo ? (
            <LineupComparisonView
              teamAAbbr={teamA}
              teamBAbbr={teamB}
              teamAName={teamAInfo.name}
              teamBName={teamBInfo.name}
              season={season}
              teamALineups={lineupsA?.lineups ?? []}
              teamBLineups={lineupsB?.lineups ?? []}
              selectedLineupA={lineupAParam ?? lineupsA?.lineups[0]?.lineup_key ?? null}
              selectedLineupB={lineupBParam ?? lineupsB?.lineups[0]?.lineup_key ?? null}
              onSelectLineupA={(lineupKey) => selectLineup("lineup_a", lineupKey)}
              onSelectLineupB={(lineupKey) => selectLineup("lineup_b", lineupKey)}
            />
          ) : (
            <div className="bip-empty rounded-[2rem] py-16 text-center">
              <div className="mb-4 text-5xl">🧩</div>
              <p className="text-lg font-medium text-[var(--foreground)]">Select two teams to compare lineups</p>
              <p className="mt-1 text-sm">Lineup compare uses the team tables already synced in the warehouse.</p>
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-8">
          <div className="grid gap-4 md:grid-cols-3">
            <TeamSlot
              slotLabel="Team A"
              selectedTeam={teamA}
              onSelect={(abbr) => selectTeam("team_a", abbr)}
              teams={teams ?? []}
            />
            <TeamSlot
              slotLabel="Team B"
              selectedTeam={teamB}
              onSelect={(abbr) => selectTeam("team_b", abbr)}
              teams={teams ?? []}
            />
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                Season
              </span>
              <select
                value={season}
                onChange={(event) => selectSeason(event.target.value)}
                className="bip-input w-full rounded-2xl px-4 py-4 text-sm"
              >
                {["2025-26", "2024-25", "2023-24", "2022-23"].map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {teamComparisonLoading ? (
            <div className="flex items-center justify-center gap-3 py-16 text-[var(--muted)]">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-[var(--accent)] border-t-transparent" />
              <span className="text-sm">Loading style comparison…</span>
            </div>
          ) : teamAInfo && teamBInfo ? (
            <StyleComparisonView
              teamAAbbr={teamA}
              teamBAbbr={teamB}
              teamAName={teamAInfo.name}
              teamBName={teamBInfo.name}
              season={season}
              analyticsA={analyticsA ?? null}
              analyticsB={analyticsB ?? null}
              comparison={teamComparison}
            />
          ) : (
            <div className="bip-empty rounded-[2rem] py-16 text-center">
              <div className="mb-4 text-5xl">🧭</div>
              <p className="text-lg font-medium text-[var(--foreground)]">Select two teams to compare styles</p>
              <p className="mt-1 text-sm">Style compare uses pace, shot quality, turnover pressure, and glass control.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ComparePage() {
  return (
    <Suspense>
      <ComparePageInner />
    </Suspense>
  );
}
