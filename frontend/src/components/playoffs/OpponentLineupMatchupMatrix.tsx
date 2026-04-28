"use client";

import { useMemo } from "react";
import useSWR from "swr";
import { getLineupsForSeasonType, getTeamRoster } from "@/lib/api";
import type {
  LineupStatsResponse,
  LineupsResult,
  TeamRosterResponse,
} from "@/lib/types";

interface Props {
  team: string;
  opponent: string;
  season: string;
}

const MIN_POSS = 100;
const TOP_N = 5;

function lineupShortLabel(lineup: LineupStatsResponse): string {
  // Show last names only to fit cell width.
  return lineup.player_names
    .map((name) => {
      const parts = name.trim().split(/\s+/);
      return parts.length > 1 ? parts[parts.length - 1] : name;
    })
    .join(" / ");
}

function deltaCellColor(delta: number): { bg: string; fg: string } {
  if (Number.isNaN(delta)) return { bg: "var(--surface-alt)", fg: "var(--muted)" };
  if (delta > 1.5) {
    const intensity = Math.min(1, Math.abs(delta) / 20);
    return {
      bg: `rgba(33, 72, 59, ${0.12 + intensity * 0.55})`,
      fg: "var(--foreground)",
    };
  }
  if (delta < -1.5) {
    const intensity = Math.min(1, Math.abs(delta) / 20);
    return {
      bg: `rgba(167, 72, 74, ${0.12 + intensity * 0.55})`,
      fg: "var(--foreground)",
    };
  }
  return { bg: "var(--surface-alt)", fg: "var(--muted-strong)" };
}

function topLineups(result: LineupsResult | undefined, teamId: number | null): LineupStatsResponse[] {
  if (!result) return [];
  const filtered = result.lineups.filter((lineup) => {
    if (teamId != null && lineup.team_id !== teamId) return false;
    if ((lineup.possessions ?? 0) < MIN_POSS) return false;
    if (lineup.net_rating == null) return false;
    return true;
  });
  return filtered.slice(0, TOP_N);
}

export default function OpponentLineupMatchupMatrix({ team, opponent, season }: Props) {
  // Resolve team_id for both abbreviations via existing roster endpoint.
  const { data: teamRoster } = useSWR<TeamRosterResponse>(
    team ? ["team-roster", team] : null,
    () => getTeamRoster(team)
  );
  const { data: opponentRoster } = useSWR<TeamRosterResponse>(
    opponent ? ["team-roster", opponent] : null,
    () => getTeamRoster(opponent)
  );

  const teamId = teamRoster?.team_id ?? null;
  const opponentId = opponentRoster?.team_id ?? null;

  const { data: teamLineups, error: teamError } = useSWR<LineupsResult>(
    teamId != null && season ? ["lineups-playoff", season, teamId] : null,
    () => getLineupsForSeasonType(season, "Playoffs", teamId as number, 5, 25)
  );
  const { data: opponentLineups, error: oppError } = useSWR<LineupsResult>(
    opponentId != null && season ? ["lineups-playoff", season, opponentId] : null,
    () => getLineupsForSeasonType(season, "Playoffs", opponentId as number, 5, 25)
  );

  const teamRows = useMemo(() => topLineups(teamLineups, teamId), [teamLineups, teamId]);
  const opponentRows = useMemo(
    () => topLineups(opponentLineups, opponentId),
    [opponentLineups, opponentId]
  );

  const isLoading = !teamLineups || !opponentLineups || !teamRoster || !opponentRoster;
  const hasError = teamError || oppError;

  if (hasError) {
    return (
      <section className="bip-panel rounded-[1.8rem] p-6">
        <p className="bip-kicker">Opponent matchup matrix</p>
        <h3 className="bip-display mt-1 text-xl font-semibold text-[var(--foreground)]">
          {team} vs {opponent}
        </h3>
        <p className="mt-3 text-sm text-[var(--muted-strong)]">
          Could not load playoff lineup data.
        </p>
      </section>
    );
  }

  if (isLoading) {
    return (
      <section className="bip-panel rounded-[1.8rem] p-6">
        <p className="bip-kicker">Opponent matchup matrix</p>
        <h3 className="bip-display mt-1 text-xl font-semibold text-[var(--foreground)]">
          {team} vs {opponent}
        </h3>
        <div className="mt-4 h-[260px] animate-pulse rounded-lg bg-[var(--surface-alt)]" />
      </section>
    );
  }

  if (teamRows.length === 0 || opponentRows.length === 0) {
    return (
      <section className="bip-panel rounded-[1.8rem] p-6">
        <p className="bip-kicker">Opponent matchup matrix</p>
        <h3 className="bip-display mt-1 text-xl font-semibold text-[var(--foreground)]">
          {team} vs {opponent}
        </h3>
        <p className="mt-3 text-sm text-[var(--muted-strong)]">
          Insufficient playoff lineup samples — need 100+ possessions per cell.
        </p>
      </section>
    );
  }

  return (
    <section className="bip-panel rounded-[1.8rem] p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <p className="bip-kicker">Opponent matchup matrix</p>
          <h3 className="bip-display mt-1 text-xl font-semibold text-[var(--foreground)]">
            {team} vs {opponent} · top {TOP_N} playoff lineups
          </h3>
        </div>
        <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
          ≥ {MIN_POSS} poss · cell = ΔNet (team − opponent)
        </span>
      </div>

      <div className="mt-4 overflow-x-auto">
        <table className="min-w-full border-collapse text-xs">
          <thead>
            <tr>
              <th
                scope="col"
                className="px-2 py-2 text-left font-semibold text-[var(--muted)]"
              >
                {team} \\ {opponent}
              </th>
              {opponentRows.map((opp, i) => (
                <th
                  key={opp.lineup_key}
                  scope="col"
                  className="px-2 py-2 text-left font-semibold text-[var(--foreground)]"
                  title={lineupShortLabel(opp)}
                >
                  <div className="font-mono text-[10px] tracking-wider text-[var(--muted)]">
                    OPP{i + 1}
                  </div>
                  <div className="max-w-[160px] truncate font-semibold">{lineupShortLabel(opp)}</div>
                  <div className="font-mono text-[10px] text-[var(--muted)]">
                    Net {opp.net_rating != null ? opp.net_rating.toFixed(1) : "—"} · {opp.possessions ?? 0}p
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {teamRows.map((row, i) => (
              <tr key={row.lineup_key}>
                <th
                  scope="row"
                  className="px-2 py-2 text-left align-top font-semibold text-[var(--foreground)]"
                  title={lineupShortLabel(row)}
                >
                  <div className="font-mono text-[10px] tracking-wider text-[var(--muted)]">
                    OWN{i + 1}
                  </div>
                  <div className="max-w-[160px] truncate font-semibold">{lineupShortLabel(row)}</div>
                  <div className="font-mono text-[10px] text-[var(--muted)]">
                    Net {row.net_rating != null ? row.net_rating.toFixed(1) : "—"} · {row.possessions ?? 0}p
                  </div>
                </th>
                {opponentRows.map((opp) => {
                  const ownNet = row.net_rating;
                  const oppNet = opp.net_rating;
                  if (ownNet == null || oppNet == null) {
                    return (
                      <td
                        key={opp.lineup_key}
                        className="border border-[var(--border)] px-2 py-3 text-center text-[var(--muted)]"
                      >
                        —
                      </td>
                    );
                  }
                  const delta = ownNet - oppNet;
                  const { bg, fg } = deltaCellColor(delta);
                  return (
                    <td
                      key={opp.lineup_key}
                      className="border border-[var(--border)] px-2 py-3 text-center font-semibold tabular-nums"
                      style={{ background: bg, color: fg }}
                      title={`${lineupShortLabel(row)} (Net ${ownNet.toFixed(1)}) vs ${lineupShortLabel(opp)} (Net ${oppNet.toFixed(1)})`}
                    >
                      {delta > 0 ? "+" : ""}
                      {delta.toFixed(1)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="mt-3 text-[11px] leading-5 text-[var(--muted-strong)]">
        Cells compare each lineup&apos;s standalone playoff net rating; positive
        forest-green favors {team}, terracotta favors {opponent}. Shared-possession
        net deltas would be a follow-on once `/api/advanced/lineup-matchups` ships.
      </p>
    </section>
  );
}
