"use client";

import Link from "next/link";
import { useState } from "react";
import { useTrajectory } from "@/hooks/useTrajectory";

const TEAM_OPTIONS = [
  "ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DAL", "DEN", "DET", "GSW",
  "HOU", "IND", "LAC", "LAL", "MEM", "MIA", "MIL", "MIN", "NOP", "NYK",
  "OKC", "ORL", "PHI", "PHX", "POR", "SAC", "SAS", "TOR", "UTA", "WAS",
];
const POSITION_OPTIONS = ["G", "F", "C", "PG", "SG", "SF", "PF"];

function tone(label: string) {
  if (label === "Breaking Out" || label === "Quietly Rising") {
    return "text-[var(--accent-strong)] bg-[rgba(33,72,59,0.08)]";
  }
  if (label === "Collapsing" || label === "Slumping") {
    return "text-[var(--danger-ink)] bg-[var(--danger-soft)]";
  }
  return "text-[var(--muted-strong)] bg-[rgba(111,101,90,0.12)]";
}

function scoreTone(score: number) {
  if (score >= 0.5) return "text-[var(--accent-strong)]";
  if (score <= -0.5) return "text-[var(--danger-ink)]";
  return "text-[var(--foreground)]";
}

function formatDelta(key: string, value: number) {
  const signed = `${value > 0 ? "+" : ""}${value.toFixed(2)}`;
  if (key === "ts_pct") return `${signed} TS%`;
  if (key === "usg_pct") return `${signed} USG`;
  if (key === "tov_pct") return `${signed} TOV%`;
  if (key === "plus_minus") return `${signed} +/-`;
  return `${signed} ${key.toUpperCase()}`;
}

function getErrorMessage(error: unknown) {
  if (error instanceof Error) return error.message;
  return typeof error === "string" ? error : "Unable to load trajectory data right now.";
}

export function TrajectoryTracker() {
  const [lastNGames, setLastNGames] = useState(10);
  const [playerPool, setPlayerPool] = useState<"all" | "position_filter" | "team_filter">("all");
  const [minMinutes, setMinMinutes] = useState(20);
  const [teamAbbreviation, setTeamAbbreviation] = useState("OKC");
  const [position, setPosition] = useState("G");
  const { data, error, isLoading } = useTrajectory(
    "2025-26",
    lastNGames,
    playerPool,
    minMinutes,
    playerPool === "team_filter" ? teamAbbreviation : undefined,
    playerPool === "position_filter" ? position : undefined
  );

  return (
    <div className="mx-auto max-w-7xl space-y-8">
      <section className="rounded-[2rem] border border-[var(--border-strong)] bg-[linear-gradient(135deg,rgba(248,244,232,0.98),rgba(239,232,214,0.96))] p-6 shadow-[0_24px_80px_rgba(47,43,36,0.08)] sm:p-7">
        <div className="flex flex-wrap items-end justify-between gap-5">
          <div className="max-w-3xl">
            <p className="bip-kicker mb-2">Decision Surface</p>
            <h1 className="bip-display text-4xl font-semibold text-[var(--foreground)]">
              CourtVue Labs Trajectory Tracker
            </h1>
            <p className="mt-3 text-sm leading-6 text-[var(--muted-strong)]">
              Track who is breaking out or slipping in the 2025-26 season by comparing the last N games against the earlier season baseline, not the full-season average blur.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                Last N Games
              </span>
              <select
                value={lastNGames}
                onChange={(event) => setLastNGames(Number(event.target.value))}
                className="bip-input w-full rounded-2xl px-4 py-3 text-sm"
              >
                {[5, 7, 10, 12, 15].map((option) => (
                  <option key={option} value={option}>
                    Last {option}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                Player Pool
              </span>
              <select
                value={playerPool}
                onChange={(event) =>
                  setPlayerPool(event.target.value as "all" | "position_filter" | "team_filter")
                }
                className="bip-input w-full rounded-2xl px-4 py-3 text-sm"
              >
                <option value="all">All Players</option>
                <option value="team_filter">Team Filter</option>
                <option value="position_filter">Position Filter</option>
              </select>
            </label>
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                Min MPG
              </span>
              <input
                type="number"
                min="0"
                step="1"
                value={minMinutes}
                onChange={(event) => setMinMinutes(Number(event.target.value) || 0)}
                className="bip-input w-full rounded-2xl px-4 py-3 text-sm"
              />
            </label>
            {playerPool === "team_filter" ? (
              <label className="space-y-2">
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                  Team
                </span>
                <select
                  value={teamAbbreviation}
                  onChange={(event) => setTeamAbbreviation(event.target.value)}
                  className="bip-input w-full rounded-2xl px-4 py-3 text-sm"
                >
                  {TEAM_OPTIONS.map((team) => (
                    <option key={team} value={team}>
                      {team}
                    </option>
                  ))}
                </select>
              </label>
            ) : playerPool === "position_filter" ? (
              <label className="space-y-2">
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                  Position
                </span>
                <select
                  value={position}
                  onChange={(event) => setPosition(event.target.value)}
                  className="bip-input w-full rounded-2xl px-4 py-3 text-sm"
                >
                  {POSITION_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>
            ) : (
              <div className="rounded-2xl border border-[var(--border)] bg-[rgba(255,255,255,0.6)] px-4 py-3 text-sm text-[var(--muted-strong)]">
                CourtVue Labs excludes the selected window from the baseline, so the tracker stays focused on recency instead of full-season smoothing.
              </div>
            )}
          </div>
        </div>
      </section>

      {error ? (
        <div className="rounded-[1.5rem] border border-[rgba(140,58,42,0.24)] bg-[var(--danger-soft)] px-5 py-4 text-sm text-[var(--danger-ink)]">
          {getErrorMessage(error)}
        </div>
      ) : null}

      {data?.warnings?.length ? (
        <div className="rounded-[1.5rem] border border-[rgba(161,119,55,0.24)] bg-[rgba(181,145,78,0.08)] px-5 py-4">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Warnings
          </p>
          <ul className="mt-3 space-y-2 text-sm text-[var(--muted-strong)]">
            {data.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-2">
        <section className="rounded-[1.75rem] border border-[var(--border)] bg-[var(--surface)]">
          <div className="border-b border-[var(--border)] px-5 py-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
              {data?.window ?? "Recent Window"}
            </p>
            <h2 className="mt-1 text-2xl font-semibold text-[var(--foreground)]">
              Breakout Leaders
            </h2>
          </div>
          <div className="space-y-4 p-5">
            {isLoading ? (
              Array.from({ length: 5 }).map((_, index) => (
                <div key={index} className="animate-pulse rounded-[1.25rem] border border-[var(--border)] p-4">
                  <div className="h-4 w-32 rounded bg-[var(--surface-alt)]" />
                  <div className="mt-3 h-3 w-full rounded bg-[var(--surface-alt)]" />
                  <div className="mt-2 h-3 w-2/3 rounded bg-[var(--surface-alt)]" />
                </div>
              ))
            ) : data?.breakout_leaders?.length ? (
              data.breakout_leaders.map((row) => (
                <article key={`${row.rank}-${row.player_name}`} className="rounded-[1.25rem] border border-[var(--border)] bg-[rgba(255,255,255,0.7)] p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                          #{row.rank}
                        </span>
                        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.14em] ${tone(row.trajectory_label)}`}>
                          {row.trajectory_label}
                        </span>
                      </div>
                      <h3 className="mt-2 text-lg font-semibold text-[var(--foreground)]">
                        {row.player_name} <span className="text-sm font-medium text-[var(--muted-strong)]">{row.team}</span>
                      </h3>
                    </div>
                    <div className={`text-right text-lg font-semibold tabular-nums ${scoreTone(row.trajectory_score)}`}>
                      {row.trajectory_score > 0 ? "+" : ""}
                      {row.trajectory_score.toFixed(2)}
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {Object.entries(row.key_stat_deltas).map(([key, value]) => (
                      <span key={`${row.player_name}-${key}`} className="rounded-full border border-[var(--border)] bg-[rgba(244,238,223,0.75)] px-2.5 py-1 text-xs text-[var(--muted-strong)]">
                        {formatDelta(key, value)}
                      </span>
                    ))}
                  </div>
                  <p className="mt-3 text-sm leading-6 text-[var(--muted-strong)]">{row.narrative}</p>
                  {row.context_flags.length ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {row.context_flags.map((flag) => (
                        <span key={`${row.player_name}-${flag}`} className="rounded-full bg-[rgba(33,72,59,0.08)] px-2.5 py-1 text-xs font-medium text-[var(--accent-strong)]">
                          {flag}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </article>
              ))
            ) : (
              <div className="rounded-[1.25rem] border border-[var(--border)] px-5 py-8 text-sm text-[var(--muted-strong)]">
                No breakout leaders matched this window and pool.
              </div>
            )}
          </div>
        </section>

        <section className="rounded-[1.75rem] border border-[var(--border)] bg-[var(--surface)]">
          <div className="border-b border-[var(--border)] px-5 py-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
              {data?.window ?? "Recent Window"}
            </p>
            <h2 className="mt-1 text-2xl font-semibold text-[var(--foreground)]">
              Decline Watch
            </h2>
          </div>
          <div className="space-y-4 p-5">
            {isLoading ? (
              Array.from({ length: 5 }).map((_, index) => (
                <div key={index} className="animate-pulse rounded-[1.25rem] border border-[var(--border)] p-4">
                  <div className="h-4 w-32 rounded bg-[var(--surface-alt)]" />
                  <div className="mt-3 h-3 w-full rounded bg-[var(--surface-alt)]" />
                  <div className="mt-2 h-3 w-2/3 rounded bg-[var(--surface-alt)]" />
                </div>
              ))
            ) : data?.decline_watch?.length ? (
              data.decline_watch.map((row) => (
                <article key={`${row.rank}-${row.player_name}`} className="rounded-[1.25rem] border border-[var(--border)] bg-[rgba(255,255,255,0.7)] p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                          #{row.rank}
                        </span>
                        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.14em] ${tone(row.trajectory_label)}`}>
                          {row.trajectory_label}
                        </span>
                      </div>
                      <h3 className="mt-2 text-lg font-semibold text-[var(--foreground)]">
                        {row.player_name} <span className="text-sm font-medium text-[var(--muted-strong)]">{row.team}</span>
                      </h3>
                    </div>
                    <div className={`text-right text-lg font-semibold tabular-nums ${scoreTone(row.trajectory_score)}`}>
                      {row.trajectory_score.toFixed(2)}
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {Object.entries(row.key_stat_deltas).map(([key, value]) => (
                      <span key={`${row.player_name}-${key}`} className="rounded-full border border-[var(--border)] bg-[rgba(244,238,223,0.75)] px-2.5 py-1 text-xs text-[var(--muted-strong)]">
                        {formatDelta(key, value)}
                      </span>
                    ))}
                  </div>
                  <p className="mt-3 text-sm leading-6 text-[var(--muted-strong)]">{row.narrative}</p>
                  {row.context_flags.length ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {row.context_flags.map((flag) => (
                        <span key={`${row.player_name}-${flag}`} className="rounded-full bg-[rgba(140,58,42,0.08)] px-2.5 py-1 text-xs font-medium text-[var(--danger-ink)]">
                          {flag}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </article>
              ))
            ) : (
              <div className="rounded-[1.25rem] border border-[var(--border)] px-5 py-8 text-sm text-[var(--muted-strong)]">
                No decline-watch players matched this window and pool.
              </div>
            )}
          </div>
        </section>
      </div>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
        <div className="rounded-[1.75rem] border border-[var(--border)] bg-[var(--surface)] p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Excluded Players
          </p>
          <div className="mt-4 space-y-2 text-sm text-[var(--muted-strong)]">
            {data?.excluded_players?.length ? (
              data.excluded_players.slice(0, 24).map((entry) => <div key={entry}>{entry}</div>)
            ) : (
              <div>No exclusions for the current filter set.</div>
            )}
          </div>
        </div>
        <div className="rounded-[1.75rem] border border-[var(--border)] bg-[var(--surface)] p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Analyst Follow-Through
          </p>
          <div className="mt-4 space-y-3 text-sm leading-6 text-[var(--muted-strong)]">
            <p>
              Use the highest-trajectory names to jump into player pages and compare the current trend against the new Player Trend Intelligence panel from Sprint 19.
            </p>
            <p>
              For team-level context, cross-check a riser against the Rotation Intelligence workflow on the team page to see whether the role change is tied to a wider lineup shift.
            </p>
            <Link href="/player-stats" className="inline-flex rounded-full border border-[var(--border-strong)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]">
              Open Player Stats Context
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
