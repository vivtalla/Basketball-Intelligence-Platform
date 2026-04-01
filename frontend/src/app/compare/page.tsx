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
import ComparisonView from "@/components/ComparisonView";
import TeamComparisonView from "@/components/TeamComparisonView";
import LineupComparisonView from "@/components/LineupComparisonView";
import StyleComparisonView from "@/components/StyleComparisonView";

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
    mode !== "players" ? season : null
  );

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
        params.delete("season");
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
      params.set("mode", mode === "players" ? "teams" : mode);
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
  const bothReady = Boolean(profile1 && career1 && profile2 && career2);
  const loadingComparison =
    bothSelected &&
    !comparisonError &&
    (!profile1 || !profile2 || !career1 || !career2);

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

          {bothReady ? (
            <ComparisonView
              playerA={{ profile: profile1!, career: career1! }}
              playerB={{ profile: profile2!, career: career2! }}
            />
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
