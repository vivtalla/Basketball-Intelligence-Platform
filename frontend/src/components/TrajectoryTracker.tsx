"use client";

import Link from "next/link";
import { useState } from "react";
import { useTrajectory, useTrajectorySeries, useLineupContext } from "@/hooks/useTrajectory";
import type { TrajectoryPlayerRow } from "@/lib/types";
import { DriverBar } from "@/components/trajectory/DriverBar";
import { RollingSparklines } from "@/components/trajectory/RollingSparklines";
import { EvidenceGames } from "@/components/trajectory/EvidenceGames";
import { OnOffSwingCard } from "@/components/trajectory/OnOffSwingCard";
import { ClutchSplitCard } from "@/components/trajectory/ClutchSplitCard";
import { ShotQualityDeltaCard } from "@/components/trajectory/ShotQualityDeltaCard";
import { TrajectoryMethodologyDrawer } from "@/components/trajectory/TrajectoryMethodologyDrawer";

const TEAM_OPTIONS = [
  "ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DAL", "DEN", "DET", "GSW",
  "HOU", "IND", "LAC", "LAL", "MEM", "MIA", "MIL", "MIN", "NOP", "NYK",
  "OKC", "ORL", "PHI", "PHX", "POR", "SAC", "SAS", "TOR", "UTA", "WAS",
];
const POSITION_OPTIONS = ["G", "F", "C", "PG", "SG", "SF", "PF"];

type ListMode = "breakout" | "decline";

interface TrajectoryTrackerProps {
  initialTeam?: string;
  pinnedPlayerId?: number | null;
  onPlayerPin?: (playerId: number | null) => void;
}

function labelTone(label: string) {
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

function getErrorMessage(error: unknown) {
  if (error instanceof Error) return error.message;
  return typeof error === "string" ? error : "Unable to load trajectory data right now.";
}

interface PlayerListRowProps {
  row: TrajectoryPlayerRow;
  isSelected: boolean;
  onSelect: () => void;
}

function PlayerListRow({ row, isSelected, onSelect }: PlayerListRowProps) {
  return (
    <button
      onClick={onSelect}
      className={`w-full rounded-2xl border p-3 text-left transition-all ${
        isSelected
          ? "border-[var(--accent-strong)] bg-[rgba(33,72,59,0.06)] shadow-sm"
          : "border-[var(--border)] bg-[var(--surface)] hover:border-[var(--border-strong)]"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold text-[var(--muted)]">#{row.rank}</span>
            <Link
              href={`/players/${row.player_id}`}
              onClick={(e) => e.stopPropagation()}
              className="truncate text-sm font-semibold text-[var(--foreground)] hover:underline"
            >
              {row.player_name}
            </Link>
          </div>
          <div className="mt-0.5 flex items-center gap-1.5">
            <span className="text-[10px] text-[var(--muted)]">{row.team}</span>
            {row.position && (
              <span className="text-[10px] text-[var(--muted)]">· {row.position}</span>
            )}
            {row.position_percentile !== null && (
              <span className="rounded-full bg-[var(--surface-alt)] px-1.5 py-0.5 text-[9px] font-semibold text-[var(--muted-strong)]">
                {Math.round(row.position_percentile)}p
              </span>
            )}
          </div>
        </div>
        <div className="shrink-0 text-right">
          <p className={`text-base font-bold tabular-nums ${scoreTone(row.trajectory_score)}`}>
            {row.trajectory_score > 0 ? "+" : ""}{row.trajectory_score.toFixed(2)}
          </p>
          <span
            className={`rounded-full px-2 py-0.5 text-[9px] font-semibold ${labelTone(row.trajectory_label)}`}
          >
            {row.trajectory_label}
          </span>
        </div>
      </div>
      {row.driver_contributions.length > 0 && (
        <div className="mt-2">
          <DriverBar contributions={row.driver_contributions.slice(0, 4)} compact />
        </div>
      )}
    </button>
  );
}

interface DetailPanelProps {
  row: TrajectoryPlayerRow;
  lastNGames: number;
}

function DetailPanel({ row, lastNGames }: DetailPanelProps) {
  const { data: series, isLoading: seriesLoading } = useTrajectorySeries(
    row.player_id,
    "2025-26",
    lastNGames
  );
  const { data: lineupCtx } = useLineupContext(row.player_id, "2025-26");

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <Link
            href={`/players/${row.player_id}`}
            className="text-2xl font-bold text-[var(--foreground)] hover:underline"
          >
            {row.player_name}
          </Link>
          <div className="mt-1 flex items-center gap-2">
            <span className="text-sm text-[var(--muted)]">{row.team}</span>
            {row.position && <span className="text-sm text-[var(--muted)]">· {row.position}</span>}
            {row.position_percentile !== null && (
              <span className="rounded-full bg-[var(--surface-alt)] px-2 py-0.5 text-[10px] font-semibold text-[var(--muted-strong)]">
                {Math.round(row.position_percentile)}th pct (by position)
              </span>
            )}
          </div>
        </div>
        <div className="shrink-0 text-right">
          <p className={`text-3xl font-bold tabular-nums ${scoreTone(row.trajectory_score)}`}>
            {row.trajectory_score > 0 ? "+" : ""}{row.trajectory_score.toFixed(2)}
          </p>
          <span
            className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${labelTone(row.trajectory_label)}`}
          >
            {row.trajectory_label}
          </span>
        </div>
      </div>

      {/* Narrative */}
      <p className="text-sm leading-relaxed text-[var(--muted-strong)]">{row.narrative}</p>

      {/* Context flags */}
      {row.context_flags.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {row.context_flags.map((flag) => (
            <span
              key={flag}
              className="rounded-full border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-1 text-[11px] font-medium text-[var(--muted-strong)]"
            >
              {flag}
            </span>
          ))}
        </div>
      )}

      {/* Rolling sparklines */}
      <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3">
        <p className="mb-3 text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">
          Rolling game log — {lastNGames}-game window
        </p>
        {seriesLoading ? (
          <div className="h-40 animate-pulse rounded-xl bg-[var(--surface-alt)]" />
        ) : series ? (
          <RollingSparklines series={series.series} lastNGames={lastNGames} />
        ) : (
          <p className="text-xs text-[var(--muted)]">Could not load game series.</p>
        )}
      </div>

      {/* Driver decomposition */}
      <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3">
        <p className="mb-3 text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">
          Driver decomposition — all signals
        </p>
        <DriverBar contributions={row.driver_contributions} />
      </div>

      {/* Evidence games */}
      {row.evidence_games.length > 0 && (
        <EvidenceGames games={row.evidence_games} teamAbbr={row.team} />
      )}

      {/* 2-col cards */}
      <div className="grid gap-3 sm:grid-cols-2">
        <OnOffSwingCard onOffContext={row.on_off_context} lineupContext={lineupCtx ?? null} />
        <ClutchSplitCard clutchContext={row.clutch_context} />
      </div>
      <ShotQualityDeltaCard row={row} />
    </div>
  );
}

export function TrajectoryTracker({
  initialTeam = "OKC",
  pinnedPlayerId = null,
  onPlayerPin,
}: TrajectoryTrackerProps) {
  const [lastNGames, setLastNGames] = useState(10);
  const [playerPool, setPlayerPool] = useState<"all" | "position_filter" | "team_filter">("all");
  const [minMinutes, setMinMinutes] = useState(20);
  const [teamAbbreviation, setTeamAbbreviation] = useState(initialTeam);
  const [position, setPosition] = useState("G");
  const [listMode, setListMode] = useState<ListMode>("breakout");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const effectivePlayerPool = pinnedPlayerId != null ? "team_filter" : playerPool;
  const effectiveTeamAbbreviation = pinnedPlayerId != null ? initialTeam : teamAbbreviation;

  // Pre-allocate hook slots at top level per CLAUDE.md rule.
  const { data, error, isLoading } = useTrajectory(
    "2025-26",
    lastNGames,
    effectivePlayerPool,
    minMinutes,
    effectivePlayerPool === "team_filter" ? effectiveTeamAbbreviation : undefined,
    effectivePlayerPool === "position_filter" ? position : undefined
  );

  const list = listMode === "breakout"
    ? (data?.breakout_leaders ?? [])
    : (data?.decline_watch ?? []);

  const selectedPlayerId = pinnedPlayerId ?? selectedId;
  const selectedRow =
    selectedPlayerId !== null
      ? list.find((r) => r.player_id === selectedPlayerId) ?? list[0] ?? null
      : list[0] ?? null;

  return (
    <div className="mx-auto max-w-7xl space-y-8">
      {/* Controls */}
      <section className="rounded-[2rem] border border-[var(--border-strong)] bg-[linear-gradient(135deg,rgba(248,244,232,0.98),rgba(239,232,214,0.96))] p-6 shadow-[0_24px_80px_rgba(47,43,36,0.08)] sm:p-7">
        <div className="flex flex-wrap items-end justify-between gap-5">
          <div className="max-w-3xl">
            <p className="bip-kicker mb-2">Decision Surface</p>
            <h1 className="bip-display text-4xl font-semibold text-[var(--foreground)]">
              CourtVue Labs Trajectory Tracker
            </h1>
            <p className="mt-3 text-sm leading-6 text-[var(--muted-strong)]">
              Multi-signal recent-window momentum — comparing the last N games against the earlier season baseline.
              Select a player to see rolling curves, driver decomposition, clutch splits, on/off swing, and game evidence.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Last N Games</span>
              <select
                value={lastNGames}
                onChange={(e) => setLastNGames(Number(e.target.value))}
                className="bip-input w-full rounded-2xl px-4 py-3 text-sm"
              >
                {[5, 10, 15, 20].map((n) => (
                  <option key={n} value={n}>{n} games</option>
                ))}
              </select>
            </label>

            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Min Min/Game</span>
              <select
                value={minMinutes}
                onChange={(e) => setMinMinutes(Number(e.target.value))}
                className="bip-input w-full rounded-2xl px-4 py-3 text-sm"
              >
                {[15, 20, 25, 30].map((n) => (
                  <option key={n} value={n}>{n} min</option>
                ))}
              </select>
            </label>

            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Player Pool</span>
              <select
                value={playerPool}
                onChange={(e) =>
                  setPlayerPool(e.target.value as "all" | "position_filter" | "team_filter")
                }
                className="bip-input w-full rounded-2xl px-4 py-3 text-sm"
              >
                <option value="all">All players</option>
                <option value="position_filter">By position</option>
                <option value="team_filter">By team</option>
              </select>
            </label>

            {playerPool === "position_filter" && (
              <label className="space-y-2">
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Position</span>
                <select
                  value={position}
                  onChange={(e) => setPosition(e.target.value)}
                  className="bip-input w-full rounded-2xl px-4 py-3 text-sm"
                >
                  {POSITION_OPTIONS.map((p) => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </label>
            )}

            {playerPool === "team_filter" && (
              <label className="space-y-2">
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Team</span>
                <select
                  value={teamAbbreviation}
                  onChange={(e) => setTeamAbbreviation(e.target.value)}
                  className="bip-input w-full rounded-2xl px-4 py-3 text-sm"
                >
                  {TEAM_OPTIONS.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </label>
            )}
          </div>
        </div>
      </section>

      {/* List/Detail mode toggle */}
      <div className="flex items-center gap-3">
        <div className="flex overflow-hidden rounded-xl border border-[var(--border)] text-sm">
          <button
            onClick={() => setListMode("breakout")}
            className={`px-5 py-2 transition-colors ${
              listMode === "breakout" ? "bip-toggle-active" : "bip-toggle"
            }`}
          >
            Breakout Leaders
          </button>
          <button
            onClick={() => setListMode("decline")}
            className={`px-5 py-2 transition-colors ${
              listMode === "decline" ? "bip-toggle-active" : "bip-toggle"
            }`}
          >
            Decline Watch
          </button>
        </div>
        {data && (
          <p className="text-xs text-[var(--muted)]">
            {data.window} · {list.length} players
          </p>
        )}
        <div className="ml-auto w-full max-w-md">
          <TrajectoryMethodologyDrawer />
        </div>
      </div>

      {/* Main two-column layout */}
      {isLoading ? (
        <div className="grid gap-6 lg:grid-cols-[380px_1fr]">
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-24 animate-pulse rounded-2xl bg-[var(--surface-alt)]" />
            ))}
          </div>
          <div className="h-[600px] animate-pulse rounded-2xl bg-[var(--surface-alt)]" />
        </div>
      ) : error ? (
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 text-sm text-[var(--danger-ink)]">
          {getErrorMessage(error)}
        </div>
      ) : !data || list.length === 0 ? (
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-8 text-center text-sm text-[var(--muted)]">
          No players qualified for this window. Try a smaller window or lower the minutes threshold.
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[380px_1fr]">
          {/* Left: ranked list */}
          <div className="space-y-2">
            {list.map((row) => (
              <PlayerListRow
                key={row.player_id}
                row={row}
                isSelected={
                  selectedRow !== null && row.player_id === selectedRow.player_id
                }
                onSelect={() => {
                  setSelectedId(row.player_id);
                  onPlayerPin?.(row.player_id);
                }}
              />
            ))}
            {data.warnings.map((w) => (
              <p key={w} className="text-[11px] text-[var(--muted)]">⚠ {w}</p>
            ))}
          </div>

          {/* Right: detail panel */}
          <div className="rounded-[2rem] border border-[var(--border)] bg-[var(--surface)] p-6">
            {selectedRow ? (
              <DetailPanel row={selectedRow} lastNGames={lastNGames} />
            ) : (
              <div className="flex h-64 items-center justify-center text-sm text-[var(--muted)]">
                Select a player to see the detail breakdown.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Exclusions */}
      {data && data.excluded_players.length > 0 && (
        <details className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4">
          <summary className="cursor-pointer text-xs font-semibold text-[var(--muted)]">
            {data.excluded_players.length} players excluded — click to expand
          </summary>
          <ul className="mt-3 space-y-1">
            {data.excluded_players.map((entry) => (
              <li key={entry} className="text-xs text-[var(--muted)]">
                {entry}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
