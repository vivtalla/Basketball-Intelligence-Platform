"use client";

import { useState } from "react";
import type { MvpTimelinePlayer, MvpTimelineResponse } from "@/lib/types";

const COLORS = ["#285037", "#8a5a1f", "#2f6f89", "#7f332b", "#5b6b35", "#4b6078", "#8a4f62", "#3e6b59"];

function fmtScore(value?: number | null) {
  return value == null ? "-" : value.toFixed(1);
}

function fmtPct(value?: number | null) {
  return value == null ? "-" : `${(value * 100).toFixed(1)}%`;
}

function fmtRankDelta(value?: number | null) {
  if (value == null) return "New";
  if (value === 0) return "Steady";
  return value > 0 ? `Up ${value}` : `Down ${Math.abs(value)}`;
}

function dateLabel(value?: string | null) {
  if (!value) return "";
  const date = new Date(`${value}T00:00:00`);
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function RankPathChart({
  players,
  activePlayerId,
  onActivePlayerChange,
  colorForPlayer,
}: {
  players: MvpTimelinePlayer[];
  activePlayerId: number | null;
  onActivePlayerChange: (playerId: number | null) => void;
  colorForPlayer: (playerId: number) => string;
}) {
  const chartPlayers = players.filter((player) => player.series.length > 1);
  if (chartPlayers.length === 0) return null;

  const dates = Array.from(new Set(chartPlayers.flatMap((player) => player.series.map((point) => point.date)))).sort();
  const maxRank = Math.max(...chartPlayers.flatMap((player) => player.series.map((point) => point.rank)), 8);
  const width = 1060;
  const height = 300;
  const leftPad = 44;
  const rightPad = 240;
  const topPad = 24;
  const bottomPad = 42;
  const innerWidth = width - leftPad - rightPad;
  const innerHeight = height - topPad - bottomPad;

  function xFor(date: string) {
    const index = dates.indexOf(date);
    return leftPad + (index / Math.max(dates.length - 1, 1)) * innerWidth;
  }

  function yFor(rank: number) {
    return topPad + ((rank - 1) / Math.max(maxRank - 1, 1)) * innerHeight;
  }

  const activePlayer = chartPlayers.find((player) => player.player_id === activePlayerId) ?? chartPlayers[0];
  const activeLatest = activePlayer?.series[activePlayer.series.length - 1] ?? null;
  const labelRows = chartPlayers
    .map((player) => {
      const latest = player.series[player.series.length - 1];
      return {
        playerId: player.player_id,
        targetY: yFor(latest.rank),
        y: yFor(latest.rank),
      };
    })
    .sort((a, b) => a.targetY - b.targetY);
  const labelGap = 18;
  const minLabelY = topPad + 6;
  const maxLabelY = height - bottomPad - 8;

  labelRows.forEach((row, index) => {
    const previous = labelRows[index - 1];
    row.y = Math.max(minLabelY, row.targetY, previous ? previous.y + labelGap : minLabelY);
  });

  for (let index = labelRows.length - 1; index >= 0; index -= 1) {
    const next = labelRows[index + 1];
    labelRows[index].y = Math.min(labelRows[index].y, next ? next.y - labelGap : maxLabelY);
  }

  labelRows.forEach((row, index) => {
    const previous = labelRows[index - 1];
    row.y = Math.max(minLabelY, previous ? previous.y + labelGap : row.y);
  });

  const labelYByPlayerId = new Map(labelRows.map((row) => [row.playerId, row.y]));

  return (
    <div className="overflow-x-auto" onMouseLeave={() => onActivePlayerChange(null)}>
      <svg viewBox={`0 0 ${width} ${height}`} className="min-w-[920px]">
        {[1, Math.ceil(maxRank / 2), maxRank].map((rank) => (
          <g key={rank}>
            <line x1={leftPad} x2={width - rightPad} y1={yFor(rank)} y2={yFor(rank)} stroke="var(--border)" strokeDasharray="4 6" />
            <text x={12} y={yFor(rank) + 4} className="fill-[var(--muted)] text-[11px]">#{rank}</text>
          </g>
        ))}
        {dates.map((date, index) => (
          index % 2 === 0 || index === dates.length - 1 ? (
            <text key={date} x={xFor(date)} y={height - 12} textAnchor="middle" className="fill-[var(--muted)] text-[10px]">
              {dateLabel(date)}
            </text>
          ) : null
        ))}
        {chartPlayers.map((player) => {
          const color = colorForPlayer(player.player_id);
          const isActive = activePlayerId === null || activePlayerId === player.player_id;
          const isDimmed = activePlayerId !== null && activePlayerId !== player.player_id;
          const points = player.series.map((point) => `${xFor(point.date).toFixed(1)},${yFor(point.rank).toFixed(1)}`);
          const latest = player.series[player.series.length - 1];
          const latestY = yFor(latest.rank);
          const labelY = labelYByPlayerId.get(player.player_id) ?? latestY;
          return (
            <g
              key={player.player_id}
              onMouseEnter={() => onActivePlayerChange(player.player_id)}
              onFocus={() => onActivePlayerChange(player.player_id)}
              tabIndex={0}
              role="button"
              aria-label={`Highlight ${player.player_name}`}
            >
              <polyline points={points.join(" ")} fill="none" stroke="transparent" strokeWidth="16" strokeLinecap="round" strokeLinejoin="round" />
              <polyline
                points={points.join(" ")}
                fill="none"
                stroke={color}
                strokeWidth={isActive ? "4" : "2.5"}
                strokeLinecap="round"
                strokeLinejoin="round"
                opacity={isDimmed ? 0.2 : 1}
              />
              {player.series.map((point) => (
                <circle
                  key={`${player.player_id}-${point.date}`}
                  cx={xFor(point.date)}
                  cy={yFor(point.rank)}
                  r={isActive ? 4 : 3}
                  fill={color}
                  opacity={isDimmed ? 0.2 : 1}
                />
              ))}
              <line
                x1={width - rightPad + 4}
                x2={width - rightPad + 20}
                y1={latestY}
                y2={labelY}
                stroke={color}
                strokeWidth="1.5"
                opacity={isDimmed ? 0.2 : 0.75}
              />
              <circle cx={width - rightPad + 22} cy={labelY} r="3" fill={color} opacity={isDimmed ? 0.25 : 1} />
              <text
                x={width - rightPad + 30}
                y={labelY + 4}
                className="fill-[var(--foreground)] text-[11px] font-semibold"
                opacity={isDimmed ? 0.35 : 1}
              >
                #{latest.rank} {player.player_name}
              </text>
            </g>
          );
        })}
        {activePlayer && activeLatest ? (
          <g pointerEvents="none">
            <rect
              x={Math.min(xFor(activeLatest.date) + 10, width - rightPad - 220)}
              y={Math.max(yFor(activeLatest.rank) - 58, 8)}
              width="210"
              height="48"
              rx="6"
              fill="var(--surface)"
              stroke="var(--border)"
            />
            <text x={Math.min(xFor(activeLatest.date) + 22, width - rightPad - 208)} y={Math.max(yFor(activeLatest.rank) - 36, 30)} className="fill-[var(--foreground)] text-[12px] font-semibold">
              {activePlayer.player_name}
            </text>
            <text x={Math.min(xFor(activeLatest.date) + 22, width - rightPad - 208)} y={Math.max(yFor(activeLatest.rank) - 18, 48)} className="fill-[var(--muted)] text-[11px]">
              #{activeLatest.rank} · {dateLabel(activeLatest.date)} · Score {fmtScore(activeLatest.score)}
            </text>
          </g>
        ) : null}
      </svg>
    </div>
  );
}

function MovementCard({ player }: { player: MvpTimelinePlayer }) {
  const latest = player.series[player.series.length - 1];
  return (
    <article className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-[var(--foreground)]">
            #{player.current_rank} {player.player_name}
          </p>
          <p className="mt-1 text-xs text-[var(--muted)]">
            {player.team_abbreviation || "Team"} · {fmtRankDelta(player.rank_delta)} · Score {fmtScore(player.current_score)}
          </p>
        </div>
        <span className="shrink-0 rounded border border-[var(--border)] px-2 py-1 text-xs font-semibold text-[var(--foreground)]">
          {latest?.wins ?? "-"}-{latest?.losses ?? "-"}
        </span>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
        <div>
          <p className="text-[10px] uppercase text-[var(--muted)]">PTS</p>
          <p className="font-semibold text-[var(--foreground)]">{fmtScore(latest?.pts_pg)}</p>
        </div>
        <div>
          <p className="text-[10px] uppercase text-[var(--muted)]">AST</p>
          <p className="font-semibold text-[var(--foreground)]">{fmtScore(latest?.ast_pg)}</p>
        </div>
        <div>
          <p className="text-[10px] uppercase text-[var(--muted)]">TS</p>
          <p className="font-semibold text-[var(--foreground)]">{fmtPct(latest?.ts_pct)}</p>
        </div>
      </div>
      <ul className="mt-3 space-y-1 text-xs leading-5 text-[var(--muted)]">
        {player.reasons.slice(0, 3).map((reason) => (
          <li key={reason}>{reason}</li>
        ))}
      </ul>
    </article>
  );
}

export default function MvpTimelineStrip({
  data,
  isLoading,
}: {
  data?: MvpTimelineResponse;
  isLoading?: boolean;
}) {
  const availablePlayers = data?.players ?? [];
  const playerKey = availablePlayers.map((player) => player.player_id).join("|");
  const defaultSelectedIds = availablePlayers.slice(0, 6).map((player) => player.player_id);
  const [selection, setSelection] = useState<{ key: string; ids: number[] }>({ key: "", ids: [] });
  const [activePlayerId, setActivePlayerId] = useState<number | null>(null);
  const selectedIds = selection.key === playerKey ? selection.ids : defaultSelectedIds;
  const selectedIdSet = new Set(selectedIds);
  const selectedPlayers = availablePlayers.filter((player) => selectedIdSet.has(player.player_id));
  const chartPlayers = selectedPlayers.length > 0 ? selectedPlayers : availablePlayers.slice(0, 1);

  function colorForPlayer(playerId: number) {
    const index = availablePlayers.findIndex((player) => player.player_id === playerId);
    return COLORS[(index >= 0 ? index : 0) % COLORS.length];
  }

  function togglePlayer(playerId: number) {
    setSelection((currentSelection) => {
      const current = currentSelection.key === playerKey ? currentSelection.ids : defaultSelectedIds;
      if (current.includes(playerId)) {
        return { key: playerKey, ids: current.filter((id) => id !== playerId) };
      }
      return { key: playerKey, ids: [...current, playerId] };
    });
    setActivePlayerId(playerId);
  }

  if (isLoading) {
    return (
      <section className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5">
        <div className="h-4 w-44 animate-pulse rounded bg-[var(--surface-alt)]" />
        <div className="mt-4 h-72 animate-pulse rounded-lg bg-[var(--surface-alt)]" />
      </section>
    );
  }

  if (!data || data.snapshot_count < 2 || data.players.length === 0) {
    return (
      <section className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5">
        <p className="text-xs font-semibold uppercase text-[var(--accent)]">Voter Timeline</p>
        <h2 className="bip-display mt-1 text-2xl font-semibold text-[var(--foreground)]">The race needs a longer runway</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--muted)]">
          {data?.coverage_note ?? "Weekly MVP movement needs enough regular-season game logs to reconstruct multiple voting checkpoints."}
        </p>
      </section>
    );
  }

  const movers = data.biggest_movers.length > 0
    ? data.biggest_movers
    : data.players.filter((player) => player.rank_delta === 0).slice(0, 3).map((player) => ({
        player_id: player.player_id,
        player_name: player.player_name,
        team_abbreviation: player.team_abbreviation,
        current_rank: player.current_rank,
        previous_rank: player.previous_rank ?? player.current_rank,
        rank_delta: player.rank_delta ?? 0,
        score_delta: player.score_delta,
        reasons: player.reasons,
      }));

  return (
    <section className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase text-[var(--accent)]">Voter Timeline</p>
          <h2 className="bip-display mt-1 text-2xl font-semibold text-[var(--foreground)]">How the MVP room moved</h2>
          <p className="mt-2 max-w-4xl text-sm leading-6 text-[var(--muted)]">
            Weekly checkpoints from {dateLabel(data.horizon_start)} through {dateLabel(data.horizon_end)} reconstruct the award conversation from game logs.
          </p>
          <p className="mt-2 max-w-4xl text-xs leading-5 text-[var(--muted)]">
            Timeline points are a value-driven reconstruction, not a backfilled version of the full v3 model. They use only information available through each cutoff: production, TS%, availability, team W-L, and last-five momentum.
          </p>
        </div>
        <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-xs text-[var(--muted)]">
          {data.snapshot_count} weekly points · {data.profile.replace("_", " ")}
        </div>
      </div>

      <div className="mt-5 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3">
        <div className="mb-3 flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase text-[var(--muted)]">Shown on chart</p>
            <p className="mt-1 text-xs leading-5 text-[var(--muted)]">
              Hover a line or a name to identify the path. Choose fewer candidates when the room gets crowded.
            </p>
          </div>
          <div className="flex shrink-0 flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setSelection({ key: playerKey, ids: data.players.slice(0, 6).map((player) => player.player_id) })}
              className="rounded border border-[var(--border)] px-3 py-1.5 text-xs font-semibold text-[var(--foreground)] transition hover:border-[var(--accent)]"
            >
              Top 6
            </button>
            <button
              type="button"
              onClick={() => setSelection({ key: playerKey, ids: data.players.slice(0, 8).map((player) => player.player_id) })}
              className="rounded border border-[var(--border)] px-3 py-1.5 text-xs font-semibold text-[var(--foreground)] transition hover:border-[var(--accent)]"
            >
              Top 8
            </button>
          </div>
        </div>
        <div className="mb-4 flex flex-wrap gap-2">
          {data.players.slice(0, 12).map((player) => {
            const selected = selectedIdSet.has(player.player_id);
            return (
              <button
                key={player.player_id}
                type="button"
                onClick={() => togglePlayer(player.player_id)}
                onMouseEnter={() => setActivePlayerId(player.player_id)}
                onFocus={() => setActivePlayerId(player.player_id)}
                aria-pressed={selected}
                className={`flex max-w-full items-center gap-2 rounded border px-2.5 py-1.5 text-xs transition ${
                  selected
                    ? "border-[var(--accent)] bg-[var(--surface-alt)] text-[var(--foreground)]"
                    : "border-[var(--border)] text-[var(--muted)] hover:border-[var(--accent)] hover:text-[var(--foreground)]"
                }`}
              >
                <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: colorForPlayer(player.player_id) }} />
                <span className="shrink-0 font-semibold">#{player.current_rank}</span>
                <span className="truncate">{player.player_name}</span>
              </button>
            );
          })}
        </div>
        <RankPathChart
          players={chartPlayers}
          activePlayerId={activePlayerId}
          onActivePlayerChange={setActivePlayerId}
          colorForPlayer={colorForPlayer}
        />
      </div>

      <div className="mt-4">
        <p className="text-xs font-semibold uppercase text-[var(--muted)]">This week&apos;s movement</p>
        <p className="mt-1 text-xs leading-5 text-[var(--muted)]">
          Movement reasons are tagged by methodology facet, such as scoring load, efficiency, team value, availability, or entry into the race.
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          {movers.map((mover) => (
            <span key={mover.player_id} className="rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-xs text-[var(--foreground)]">
              {mover.player_name}: {fmtRankDelta(mover.rank_delta)}
            </span>
          ))}
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-4">
        {data.players.slice(0, 8).map((player) => (
          <MovementCard key={player.player_id} player={player} />
        ))}
      </div>

      <div className="mt-4 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3 text-xs leading-5 text-[var(--muted)]">
        <p className="font-semibold uppercase text-[var(--accent)]">Methodology</p>
        <p className="mt-1">{data.methodology}</p>
        <p className="mt-1">{data.coverage_note}</p>
      </div>
    </section>
  );
}
