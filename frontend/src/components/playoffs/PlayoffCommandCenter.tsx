"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import useSWR from "swr";
import { ErrorPanel } from "@/components/ErrorPanel";
import { MethodologyEvidenceCard } from "@/components/methodology/MethodologyEvidenceCard";
import {
  getPlayoffSeriesIntelligence,
  getPlayoffsToday,
} from "@/lib/api";
import type {
  PlayoffBracketResponse,
  PlayoffLineupEntry,
  PlayoffMetricEdge,
  PlayoffSeriesGameWithMatchup,
  PlayoffSeriesIntelligenceResponse,
  PlayoffSeriesResponse,
  PlayoffShotDietEntry,
  PlayoffStarBurdenEntry,
  PlayoffTodayResponse,
} from "@/lib/types";
import SeriesWPSimulator from "./SeriesWPSimulator";

const ROUND_LABELS: Record<number, string> = {
  1: "First Round",
  2: "Conference Semifinals",
  3: "Conference Finals",
  4: "NBA Finals",
};

function flattenSeries(bracket: PlayoffBracketResponse): PlayoffSeriesResponse[] {
  return [
    ...bracket.east,
    ...bracket.west,
    ...(bracket.finals ? [bracket.finals] : []),
  ];
}

function seriesLabel(series: PlayoffSeriesResponse): string {
  const top =
    series.top_seed_team_abbr ??
    (series.top_seed != null ? `#${series.top_seed}` : "TBD");
  const bottom =
    series.bottom_seed_team_abbr ??
    (series.bottom_seed != null ? `#${series.bottom_seed}` : "TBD");
  return `${top} vs ${bottom}`;
}

function seriesState(series: PlayoffSeriesResponse): string {
  if (series.status === "closed") {
    const winner =
      series.top_wins > series.bottom_wins
        ? series.top_seed_team_abbr
        : series.bottom_seed_team_abbr;
    return `${winner ?? "Winner"} won ${Math.max(series.top_wins, series.bottom_wins)}-${Math.min(
      series.top_wins,
      series.bottom_wins
    )}`;
  }
  if (series.status === "scheduled") return "Tipoff TBD";
  if (series.top_wins === series.bottom_wins) return `Tied ${series.top_wins}-${series.bottom_wins}`;
  const leader =
    series.top_wins > series.bottom_wins
      ? series.top_seed_team_abbr
      : series.bottom_seed_team_abbr;
  return `${leader ?? "Leader"} leads ${Math.max(series.top_wins, series.bottom_wins)}-${Math.min(
    series.top_wins,
    series.bottom_wins
  )}`;
}

function formatValue(value: number | null | undefined, unit = "number"): string {
  if (value == null || Number.isNaN(value)) return "n/a";
  if (unit === "pct") return `${(value * 100).toFixed(1)}%`;
  if (unit === "rating") return `${value > 0 ? "+" : ""}${value.toFixed(1)}`;
  return value.toFixed(1);
}

function formatDelta(value: number | null | undefined, unit = "number"): string {
  if (value == null || Number.isNaN(value)) return "no baseline";
  const sign = value > 0 ? "+" : "";
  if (unit === "pct") return `${sign}${(value * 100).toFixed(1)} pp vs RS`;
  return `${sign}${value.toFixed(1)} vs RS`;
}

function todayGameLabel(game: PlayoffSeriesGameWithMatchup): string {
  const away = game.away_team_abbr ?? "TBD";
  const home = game.home_team_abbr ?? "TBD";
  const gameNum = game.series_game_num != null ? `G${game.series_game_num}` : "Game";
  if (game.home_pts != null && game.away_pts != null) {
    return `${away} ${game.away_pts}, ${home} ${game.home_pts} (${gameNum})`;
  }
  return `${away} at ${home} (${gameNum})`;
}

function StatusDot({ active }: { active: boolean }) {
  return (
    <span
      aria-hidden
      className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full"
      style={{ background: active ? "var(--signal)" : "var(--border)" }}
    />
  );
}

// Sprint 91 — small inline badge surfaced when the intelligence service had
// to fall back from playoff sample to regular-season rows. Renders nothing
// when the source is "playoffs" (or null/undefined for older rows).
function DataSourceBadge({ source }: { source: "playoffs" | "regular_season" | null | undefined }) {
  if (source !== "regular_season") return null;
  return (
    <span
      title="Showing regular-season baseline. Playoff series sample populates after Game 1."
      className="ml-2 inline-flex items-center rounded-full border border-[var(--border)] bg-[var(--surface-alt)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--muted)]"
    >
      Regular season
    </span>
  );
}

function SeriesRail({
  series,
  selectedSeriesId,
  onSelect,
}: {
  series: PlayoffSeriesResponse[];
  selectedSeriesId: string | null;
  onSelect: (seriesId: string) => void;
}) {
  return (
    <section className="bip-panel rounded-[1.8rem] p-4">
      <div className="mb-4">
        <p className="bip-kicker">Series board</p>
        <h2 className="bip-display mt-1 text-2xl font-semibold text-[var(--foreground)]">
          Pick the chessboard.
        </h2>
        {selectedSeriesId ? (
          <Link
            href={`/beta/playoff-series/${encodeURIComponent(selectedSeriesId)}`}
            className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-[var(--accent)] transition-colors hover:underline"
          >
            View per-game player stats →
          </Link>
        ) : null}
      </div>
      <div className="space-y-2">
        {series.map((item) => {
          const selected = item.series_id === selectedSeriesId;
          return (
            <button
              key={item.series_id}
              type="button"
              onClick={() => onSelect(item.series_id)}
              className={`w-full rounded-2xl border px-4 py-3 text-left transition ${
                selected
                  ? "border-[var(--accent)] bg-[rgba(33,72,59,0.08)]"
                  : "border-[var(--border)] bg-[var(--surface)] hover:border-[var(--accent)]"
              }`}
            >
              <div className="flex gap-3">
                <StatusDot active={item.status === "active"} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-3">
                    <p className="truncate text-sm font-semibold text-[var(--foreground)]">
                      {seriesLabel(item)}
                    </p>
                    <span className="rounded-full bg-[var(--surface-alt)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">
                      {ROUND_LABELS[item.round] ?? `R${item.round}`}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-[var(--muted)]">{seriesState(item)}</p>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}

function TodayStrip({ today }: { today: PlayoffTodayResponse | undefined }) {
  const games = today?.games ?? [];
  return (
    <section className="rounded-[1.4rem] border border-[var(--border)] bg-[var(--surface)] p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="bip-kicker">Today</p>
          <p className="mt-1 text-sm font-semibold text-[var(--foreground)]">
            {games.length ? `${games.length} playoff game${games.length === 1 ? "" : "s"}` : "No playoff games today"}
          </p>
        </div>
        {today?.date ? (
          <span className="font-mono text-[11px] text-[var(--muted)]">{today.date}</span>
        ) : null}
      </div>
      {games.length ? (
        <div className="mt-3 flex gap-2 overflow-x-auto pb-1">
          {games.map((game) => (
            <div
              key={game.game_id}
              className="min-w-[220px] rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-2"
            >
              <p className="text-xs font-semibold text-[var(--foreground)]">{todayGameLabel(game)}</p>
              <p className="mt-1 text-[11px] text-[var(--muted)]">
                {game.top_seed_team_abbr && game.bottom_seed_team_abbr
                  ? `${game.top_seed_team_abbr}-${game.bottom_seed_team_abbr} series`
                  : game.series_id ?? "Series TBD"}
              </p>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function PulsePanel({ data }: { data: PlayoffSeriesIntelligenceResponse }) {
  const pulse = data.pulse;
  return (
    <section className="bip-panel rounded-[1.8rem] p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="bip-kicker">Series Pulse</p>
          <h2 className="bip-display mt-1 text-3xl font-semibold text-[var(--foreground)]">
            {data.top_team.abbreviation ?? "Top"} {data.top_team.wins} - {data.bottom_team.wins}{" "}
            {data.bottom_team.abbreviation ?? "Bottom"}
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--muted-strong)]">
            {pulse.summary}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-4 lg:min-w-[420px]">
          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] p-3">
            <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">Next</p>
            <p className="mt-1 text-lg font-semibold text-[var(--foreground)]">
              {pulse.next_game_number ? `Game ${pulse.next_game_number}` : "Complete"}
            </p>
          </div>
          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] p-3">
            <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">Leverage</p>
            <p className="mt-1 text-lg font-semibold text-[var(--foreground)]">
              {pulse.is_elimination_game ? "Elim" : pulse.is_swing_game ? "Swing" : "Tactical"}
            </p>
          </div>
          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] p-3">
            <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">Games</p>
            <p className="mt-1 text-lg font-semibold text-[var(--foreground)]">{pulse.completed_games}</p>
          </div>
          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] p-3">
            <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">Reliability</p>
            <p className="mt-1 text-lg font-semibold capitalize text-[var(--foreground)]">
              {data.analysis_metadata?.confidence ?? "low"}
            </p>
          </div>
        </div>
      </div>
      {pulse.margin_by_game.length ? (
        <div className="mt-5 flex flex-wrap gap-2">
          {pulse.margin_by_game.map((game, index) => (
            <span
              key={`${game.game_num ?? index}-${game.winner_team_abbr ?? "tie"}`}
              className="rounded-full border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-1 text-xs text-[var(--muted-strong)]"
            >
              G{game.game_num ?? index + 1}: {game.winner_team_abbr ?? "TBD"} by {game.margin ?? "n/a"}
            </span>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function MetricCard({
  metric,
  topAbbr,
  bottomAbbr,
}: {
  metric: PlayoffMetricEdge;
  topAbbr: string;
  bottomAbbr: string;
}) {
  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-[var(--foreground)]">{metric.label}</p>
          <p className="mt-1 text-[11px] text-[var(--muted)]">
            Edge: {metric.edge_team_abbr ?? "even"}
            {metric.edge_amount != null ? ` by ${formatValue(metric.edge_amount, metric.unit)}` : ""}
          </p>
        </div>
        <span className="rounded-full bg-[var(--surface-alt)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">
          {metric.unit}
        </span>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3">
        <div>
          <p className="text-[11px] font-semibold text-[var(--muted)]">{topAbbr}</p>
          <p className="mt-1 text-xl font-semibold text-[var(--foreground)]">
            {formatValue(metric.top_value, metric.unit)}
          </p>
          <p className="mt-1 text-[11px] text-[var(--muted)]">{formatDelta(metric.top_delta_vs_regular, metric.unit)}</p>
        </div>
        <div>
          <p className="text-[11px] font-semibold text-[var(--muted)]">{bottomAbbr}</p>
          <p className="mt-1 text-xl font-semibold text-[var(--foreground)]">
            {formatValue(metric.bottom_value, metric.unit)}
          </p>
          <p className="mt-1 text-[11px] text-[var(--muted)]">{formatDelta(metric.bottom_delta_vs_regular, metric.unit)}</p>
        </div>
      </div>
    </div>
  );
}

function FourFactorsPanel({ data }: { data: PlayoffSeriesIntelligenceResponse }) {
  const topAbbr = data.top_team.abbreviation ?? "Top";
  const bottomAbbr = data.bottom_team.abbreviation ?? "Bottom";
  // Sprint 83c — surface the per-team "regular-season baseline" caveats so the
  // user knows when the four-factor cards are using a regular-season fallback.
  const baselineWarnings = (data.warnings ?? []).filter((w) =>
    w.toLowerCase().includes("regular-season baseline"),
  );
  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <p className="bip-kicker">Four Factors Edge</p>
          <h3 className="bip-display text-2xl font-semibold text-[var(--foreground)]">
            What is actually separating the series.
          </h3>
        </div>
        <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
          Playoff value + regular-season delta
        </span>
      </div>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {data.four_factors.map((metric) => (
          <MetricCard
            key={metric.key}
            metric={metric}
            topAbbr={topAbbr}
            bottomAbbr={bottomAbbr}
          />
        ))}
      </div>
      {baselineWarnings.map((warning, index) => (
        <p key={index} className="mt-3 text-[11px] italic leading-5 text-[var(--muted)]">
          {warning}
        </p>
      ))}
    </section>
  );
}

function StarTable({ stars }: { stars: PlayoffStarBurdenEntry[] }) {
  // If any row in the table came from a regular-season fallback, surface
  // a single header-level badge rather than tagging every row.
  const fallbackInUse = stars.some((s) => s.data_source === "regular_season");
  return (
    <section className="bip-panel rounded-[1.8rem] p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div className="flex items-baseline">
          <p className="bip-kicker">Star Burden</p>
          {fallbackInUse ? <DataSourceBadge source="regular_season" /> : null}
        </div>
        <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
          Usage sorted
        </span>
      </div>
      <h3 className="bip-display mt-1 text-2xl font-semibold text-[var(--foreground)]">
        Who is carrying creation.
      </h3>
      {fallbackInUse ? (
        <p className="mt-2 text-xs leading-5 text-[var(--muted)]">
          Series sample is too thin yet — showing each team&apos;s regular-season
          usage so the matchup is still readable. Updates to playoff numbers
          once Game 1 finalizes.
        </p>
      ) : null}
      {stars.length ? (
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="text-[11px] uppercase tracking-[0.12em] text-[var(--muted)]">
              <tr>
                <th className="py-2 pr-4">Player</th>
                <th className="py-2 pr-4">Team</th>
                <th className="py-2 pr-4">MPG</th>
                <th className="py-2 pr-4">USG</th>
                <th className="py-2 pr-4">PTS</th>
                <th className="py-2 pr-4">TS</th>
                <th className="py-2 pr-4">Scoring share</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {stars.slice(0, 8).map((star) => (
                <tr key={`${star.team_abbreviation}-${star.player_id}`}>
                  <td className="py-2 pr-4 font-semibold text-[var(--foreground)]">
                    {star.player_name}
                    {star.position_bucket ? (
                      <span className="ml-2 rounded-full bg-[var(--surface-alt)] px-2 py-0.5 text-[10px] text-[var(--muted)]">
                        {star.position_bucket}
                      </span>
                    ) : null}
                  </td>
                  <td className="py-2 pr-4 text-[var(--muted-strong)]">{star.team_abbreviation}</td>
                  <td className="py-2 pr-4 tabular-nums text-[var(--muted-strong)]">{formatValue(star.min_pg)}</td>
                  <td className="py-2 pr-4 tabular-nums text-[var(--muted-strong)]">{formatValue(star.usg_pct, "pct")}</td>
                  <td className="py-2 pr-4 tabular-nums text-[var(--muted-strong)]">{formatValue(star.pts_pg)}</td>
                  <td className="py-2 pr-4 tabular-nums text-[var(--muted-strong)]">{formatValue(star.ts_pct, "pct")}</td>
                  <td className="py-2 pr-4 tabular-nums text-[var(--muted-strong)]">
                    {formatValue(star.share_team_points, "pct")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="mt-4 text-sm text-[var(--muted)]">
          Player stats for this series will populate after Game 1 finalizes.
        </p>
      )}
    </section>
  );
}

function ShotDietCard({ diet }: { diet: PlayoffShotDietEntry }) {
  const rows: Array<[string, number | null]> = [
    ["Rim", diet.rim_frequency],
    ["Paint", diet.paint_frequency],
    ["3PAr", diet.par3],
    ["FTr", diet.ftr],
    ["Corner 3", diet.corner_three_frequency],
    ["Assisted FG", diet.assisted_fg_rate],
  ];
  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4">
      <p className="flex items-baseline text-sm font-semibold text-[var(--foreground)]">
        {diet.team_abbreviation}
        <DataSourceBadge source={diet.data_source} />
      </p>
      <div className="mt-3 grid grid-cols-2 gap-2">
        {rows.map(([label, value]) => (
          <div key={label} className="rounded-xl bg-[var(--surface-alt)] px-3 py-2">
            <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">{label}</p>
            <p className="mt-1 text-base font-semibold text-[var(--foreground)]">
              {formatValue(value, "pct")}
            </p>
          </div>
        ))}
      </div>
      {diet.notes.length ? (
        <p className="mt-3 text-xs leading-5 text-[var(--muted)]">{diet.notes[0]}</p>
      ) : null}
    </div>
  );
}

function ShotDietPanel({ data }: { data: PlayoffSeriesIntelligenceResponse }) {
  return (
    <section className="space-y-3">
      <div>
        <p className="bip-kicker">Shot Diet Pressure</p>
        <h3 className="bip-display text-2xl font-semibold text-[var(--foreground)]">
          How playoff defense is reshaping each team&apos;s shot selection.
        </h3>
        <p className="mt-2 max-w-3xl text-xs leading-5 text-[var(--muted)]">
          Rim and paint share track how often each team is attacking inside; 3PAr (3-point attempt rate) tracks perimeter spacing; FTr (free throw rate) tracks how often the offense is drawing fouls. Significant shifts from the regular-season baseline reveal which way the opponent&apos;s defense is bending the offense — e.g., a sudden 3PAr spike often means the defense is selling out to stop drives.
        </p>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {data.shot_diet.map((diet) => (
          <ShotDietCard key={diet.team_abbreviation} diet={diet} />
        ))}
      </div>
    </section>
  );
}

function LineupList({ title, lineups }: { title: string; lineups: PlayoffLineupEntry[] }) {
  return (
    <div>
      <p className="text-sm font-semibold text-[var(--foreground)]">{title}</p>
      <div className="mt-3 space-y-2">
        {lineups.length ? (
          lineups.map((lineup) => (
            <div key={`${lineup.label}-${lineup.lineup_key}`} className="rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-xs font-semibold text-[var(--foreground)]">
                  {lineup.team_abbreviation ?? "Team"} · {formatValue(lineup.net_rating, "rating")} net
                </p>
                <span className="font-mono text-[10px] text-[var(--muted)]">
                  {lineup.possessions ?? 0} poss
                </span>
              </div>
              <p className="mt-1 text-xs leading-5 text-[var(--muted)]">
                {lineup.player_names.length ? lineup.player_names.join(" / ") : lineup.lineup_key}
              </p>
            </div>
          ))
        ) : (
          <p className="rounded-xl bg-[var(--surface-alt)] p-3 text-xs text-[var(--muted)] leading-5">
            Lineup matchups appear once a 5-man unit has played enough together
            to read against. Usually that&apos;s after Game 2.
          </p>
        )}
      </div>
    </div>
  );
}

function LineupChessPanel({ data }: { data: PlayoffSeriesIntelligenceResponse }) {
  return (
    <section className="bip-panel rounded-[1.8rem] p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <p className="bip-kicker">Lineup Chess</p>
          <h3 className="bip-display mt-1 text-2xl font-semibold text-[var(--foreground)]">
            Groups to protect or pressure.
          </h3>
        </div>
        <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
          Descriptive lineup net
        </span>
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <LineupList title="Best logged groups" lineups={data.best_lineups} />
        <LineupList title="Pressure points" lineups={data.worst_lineups} />
      </div>
    </section>
  );
}

function TacticalEdgesPanel({ data }: { data: PlayoffSeriesIntelligenceResponse }) {
  return (
    <section className="grid gap-4 lg:grid-cols-2">
      <div className="bip-panel rounded-[1.8rem] p-6">
        <p className="bip-kicker">Tactical Edges</p>
        <h3 className="bip-display mt-1 text-2xl font-semibold text-[var(--foreground)]">
          What matters next.
        </h3>
        <div className="mt-4 space-y-3">
          {data.tactical_edges.map((edge) => (
            <div key={`${edge.edge_type}-${edge.title}`} className="rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] p-3">
              <p className="text-sm font-semibold text-[var(--foreground)]">{edge.title}</p>
              <p className="mt-1 text-xs leading-5 text-[var(--muted)]">{edge.summary}</p>
            </div>
          ))}
        </div>
      </div>
      <div className="bip-panel rounded-[1.8rem] p-6">
        <p className="bip-kicker">Adjustment Signals</p>
        <h3 className="bip-display mt-1 text-2xl font-semibold text-[var(--foreground)]">
          Coachable levers.
        </h3>
        <div className="mt-4 space-y-3">
          {data.adjustment_signals.length ? (
            data.adjustment_signals.map((signal) => (
              <div key={`${signal.title}-${signal.team_abbreviation ?? "series"}`} className="rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] p-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-[var(--foreground)]">{signal.title}</p>
                  <span className="rounded-full bg-[var(--surface)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">
                    {signal.confidence}
                  </span>
                </div>
                <p className="mt-1 text-xs leading-5 text-[var(--muted)]">{signal.summary}</p>
              </div>
            ))
          ) : (
            <p className="rounded-xl bg-[var(--surface-alt)] p-3 text-xs text-[var(--muted)]">
              No strong adjustment signal yet.
            </p>
          )}
        </div>
      </div>
    </section>
  );
}

function CoveragePanel({ data }: { data: PlayoffSeriesIntelligenceResponse }) {
  const coverage = data.data_coverage;
  const chips: Array<[string, boolean]> = [
    ["Team stats", coverage.playoff_team_stats],
    ["RS baseline", coverage.regular_team_baselines],
    ["Player stats", coverage.playoff_player_stats],
    ["Lineups", coverage.playoff_lineups],
    ["Shot splits", coverage.shot_profile_splits],
  ];
  return (
    <section className="rounded-[1.4rem] border border-[var(--border)] bg-[var(--surface)] p-4">
      <div className="flex flex-wrap gap-2">
        {chips.map(([label, ok]) => (
          <span
            key={label}
            className={`rounded-full border px-3 py-1 text-xs font-semibold ${
              ok
                ? "border-[rgba(33,72,59,0.25)] bg-[rgba(33,72,59,0.08)] text-[var(--accent)]"
                : "border-[var(--border)] bg-[var(--surface-alt)] text-[var(--muted)]"
            }`}
          >
            {label}: {ok ? "ready" : "thin"}
          </span>
        ))}
      </div>
      {data.warnings.length ? (
        <p className="mt-3 text-xs leading-5 text-[var(--muted)]">{data.warnings[0]}</p>
      ) : null}
    </section>
  );
}

function IntelligenceSkeleton() {
  return (
    <div className="space-y-4">
      <div className="h-48 animate-pulse rounded-[1.8rem] bg-[var(--surface-alt)]" />
      <div className="grid gap-3 md:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="h-28 animate-pulse rounded-2xl bg-[var(--surface-alt)]" />
        ))}
      </div>
    </div>
  );
}

function IntelligenceDetail({
  selectedSeriesId,
}: {
  selectedSeriesId: string | null;
}) {
  const { data, error, isLoading, mutate } = useSWR<PlayoffSeriesIntelligenceResponse>(
    selectedSeriesId ? ["playoff-series-intelligence", selectedSeriesId] : null,
    () => getPlayoffSeriesIntelligence(selectedSeriesId as string)
  );

  if (!selectedSeriesId) {
    return (
      <div className="bip-empty rounded-[1.8rem] p-8 text-center text-sm text-[var(--muted)]">
        No playoff series is available yet.
      </div>
    );
  }

  if (isLoading || (!data && !error)) return <IntelligenceSkeleton />;

  if (error || !data) {
    return (
      <div className="rounded-[1.8rem] p-2">
        <ErrorPanel
          message="Could not load series intelligence. Check your connection and try again."
          onRetry={() => mutate()}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PulsePanel data={data} />
      <CoveragePanel data={data} />
      <FourFactorsPanel data={data} />
      <TacticalEdgesPanel data={data} />
      <StarTable stars={data.star_burden} />
      <ShotDietPanel data={data} />
      <LineupChessPanel data={data} />
      <SeriesWPSimulator key={selectedSeriesId} defaultSeriesId={selectedSeriesId} />
      <MethodologyEvidenceCard
        domain="playoffs"
        metadata={data.analysis_metadata}
        title="Playoff Command Center reliability"
      />
    </div>
  );
}

export default function PlayoffCommandCenter({
  bracket,
  initialSeriesId,
}: {
  bracket: PlayoffBracketResponse;
  initialSeriesId?: string | null;
}) {
  const allSeries = useMemo(() => flattenSeries(bracket), [bracket]);
  const defaultSeriesId = useMemo(() => {
    // Sprint 83c — honor a deep-linked ?series_id=X when it matches a real
    // series in the bracket; otherwise fall back to the active/scheduled
    // auto-pick.
    if (initialSeriesId && allSeries.some((s) => s.series_id === initialSeriesId)) {
      return initialSeriesId;
    }
    // Sprint 91 — prefer the highest-round active series so the command
    // center surfaces R2/R3/Finals once they start instead of staying
    // pinned on a stale R1 entry.
    const byRoundDesc = [...allSeries].sort((a, b) => b.round - a.round);
    const active = byRoundDesc.find((s) => s.status === "active");
    const scheduled = byRoundDesc.find((s) => s.status === "scheduled");
    return active?.series_id ?? scheduled?.series_id ?? allSeries[0]?.series_id ?? null;
  }, [allSeries, initialSeriesId]);
  const [selectedSeriesId, setSelectedSeriesId] = useState<string | null>(null);
  const effectiveSeriesId = selectedSeriesId ?? defaultSeriesId;
  const { data: today } = useSWR<PlayoffTodayResponse>(
    ["playoff-command-center-today"],
    () => getPlayoffsToday()
  );

  return (
    <div className="space-y-6">
      <TodayStrip today={today} />
      <div className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
        <div className="xl:sticky xl:top-24 xl:self-start">
          <SeriesRail
            series={allSeries}
            selectedSeriesId={effectiveSeriesId}
            onSelect={setSelectedSeriesId}
          />
        </div>
        <IntelligenceDetail selectedSeriesId={effectiveSeriesId} />
      </div>
    </div>
  );
}
