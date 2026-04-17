"use client";

import Link from "next/link";
import { Fragment, type ReactNode, useMemo, useState } from "react";
import { useStandings, useStandingsHistory } from "@/hooks/usePlayerStats";
import type { StandingsEntry, StandingsHistoryEntry } from "@/lib/types";
import StandingsBumpChart from "@/components/StandingsBumpChart";

const DEFAULT_SEASON = "2025-26";
type StandingsStatGroup =
  | "records"
  | "offense"
  | "defense"
  | "shooting"
  | "advanced"
  | "rankings";

// Clinch indicator labels
const CLINCH_LABELS: Record<string, { label: string; color: string }> = {
  x: { label: "x", color: "text-emerald-600 dark:text-emerald-400" },
  y: { label: "y", color: "text-[var(--accent)]" },
  z: { label: "z", color: "text-[var(--signal-ink)]" },
  e: { label: "e", color: "text-red-400 dark:text-red-500" },
  pi: { label: "pi", color: "text-[var(--signal)]" },
};

function StreakBadge({ streak }: { streak: string }) {
  if (!streak) return null;
  const isWin = streak.startsWith("W");
  return (
    <span
      className={`text-xs font-semibold tabular-nums ${
        isWin
          ? "text-emerald-600 dark:text-emerald-400"
          : "text-red-500 dark:text-red-400"
      }`}
    >
      {streak}
    </span>
  );
}

function DiffCell({ diff }: { diff: number | null }) {
  if (diff == null) return <span className="text-[var(--muted)]">—</span>;
  const color =
    diff > 0
      ? "text-emerald-600 dark:text-emerald-400"
      : diff < 0
      ? "text-red-500 dark:text-red-400"
      : "text-[var(--muted)]";
  return (
    <span className={`font-medium tabular-nums ${color}`}>
      {diff > 0 ? "+" : ""}
      {diff.toFixed(1)}
    </span>
  );
}

type StandingsColumn = {
  key: string;
  label: string;
  description: string;
  align?: "left" | "right";
  minWidth?: number;
  sortDefault?: "asc" | "desc";
  sortValue?: (entry: StandingsEntry) => number | string | null | undefined;
  render: (
    entry: StandingsEntry,
    context: {
      historyMap: Record<number, StandingsHistoryEntry>;
      clinch: { label: string; color: string } | null;
    }
  ) => ReactNode;
};

type StandingsSort = {
  key: string;
  direction: "asc" | "desc";
};

const STAT_GROUPS: { key: StandingsStatGroup; label: string; description: string }[] = [
  {
    key: "records",
    label: "Records",
    description: "Record, last 10, home/away, streak, and trend",
  },
  {
    key: "offense",
    label: "Offense",
    description: "Box-score production and scoring margin",
  },
  {
    key: "defense",
    label: "Defense",
    description: "Defensive rating, opponent scoring, stocks, and possession control",
  },
  {
    key: "shooting",
    label: "Shooting",
    description: "Accuracy and shot-quality efficiency",
  },
  {
    key: "advanced",
    label: "Advanced",
    description: "Ratings, pace, possession rates, and impact",
  },
  {
    key: "rankings",
    label: "Rankings",
    description: "League ranks for major advanced indicators",
  },
];

const TEAM_ABBR_BY_NAME: Record<string, string> = {
  Hawks: "ATL",
  Celtics: "BOS",
  Nets: "BKN",
  Hornets: "CHA",
  Bulls: "CHI",
  Cavaliers: "CLE",
  Mavericks: "DAL",
  Nuggets: "DEN",
  Pistons: "DET",
  Warriors: "GSW",
  Rockets: "HOU",
  Pacers: "IND",
  Clippers: "LAC",
  Lakers: "LAL",
  Grizzlies: "MEM",
  Heat: "MIA",
  Bucks: "MIL",
  Timberwolves: "MIN",
  Pelicans: "NOP",
  Knicks: "NYK",
  Thunder: "OKC",
  Magic: "ORL",
  "76ers": "PHI",
  Suns: "PHX",
  "Trail Blazers": "POR",
  Kings: "SAC",
  Spurs: "SAS",
  Raptors: "TOR",
  Jazz: "UTA",
  Wizards: "WAS",
};

function formatOne(value: number | null | undefined) {
  return value == null ? "—" : value.toFixed(1);
}

function formatPercent(value: number | null | undefined) {
  return value == null ? "—" : `${(value * 100).toFixed(1)}%`;
}

function formatRank(value: number | null | undefined) {
  return value == null ? "—" : `#${value}`;
}

function compareSortValues(
  a: number | string | null | undefined,
  b: number | string | null | undefined,
  direction: "asc" | "desc"
) {
  const aMissing = a == null || a === "";
  const bMissing = b == null || b === "";
  if (aMissing && bMissing) return 0;
  if (aMissing) return 1;
  if (bMissing) return -1;

  let result = 0;
  if (typeof a === "string" || typeof b === "string") {
    result = String(a).localeCompare(String(b));
  } else {
    result = a - b;
  }
  return direction === "asc" ? result : -result;
}

function TeamCell({
  entry,
  clinch,
}: {
  entry: StandingsEntry;
  clinch: { label: string; color: string } | null;
}) {
  const name = `${entry.team_city} ${entry.team_name}`.trim();
  const compactName =
    entry.abbreviation ||
    TEAM_ABBR_BY_NAME[entry.team_name] ||
    TEAM_ABBR_BY_NAME[name] ||
    name;
  return (
    <div className="flex items-center justify-end gap-1.5">
      {entry.abbreviation ? (
        <Link
          href={`/teams/${entry.abbreviation}`}
          className="font-medium text-[var(--foreground)] transition-colors hover:text-[var(--accent)]"
          title={name}
        >
          {compactName}
        </Link>
      ) : (
        <span className="font-medium text-[var(--foreground)]" title={name}>{compactName}</span>
      )}
      {clinch && (
        <span
          className={`text-[10px] font-bold ${clinch.color}`}
          title={`Clinch: ${entry.clinch_indicator}`}
        >
          -{clinch.label}
        </span>
      )}
    </div>
  );
}

function TrendCell({
  entry,
}: {
  entry: StandingsEntry;
}) {
  const trend = entry.recent_trend;
  if (!trend || trend.games.length === 0) {
    const streakIsWin = entry.current_streak.startsWith("W");
    return (
      <div className="flex items-center justify-end gap-1.5 text-[11px] font-semibold">
        <span className="tabular-nums text-[var(--foreground)]">{entry.l10 || "—"}</span>
        {entry.current_streak && (
          <span
            className={
              streakIsWin
                ? "tabular-nums text-emerald-600 dark:text-emerald-400"
                : "tabular-nums text-red-500 dark:text-red-400"
            }
          >
            {entry.current_streak}
          </span>
        )}
      </div>
    );
  }

  const width = 58;
  const height = 22;
  const pad = 2;
  const margins = trend.games.map((game) => game.margin);
  const maxAbs = Math.max(1, ...margins.map((margin) => Math.abs(margin)));
  const zeroY = height / 2;
  const points = margins.map((margin, index) => {
    const x = pad + (index / Math.max(1, margins.length - 1)) * (width - pad * 2);
    const y = zeroY - (margin / maxAbs) * (height / 2 - pad);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const latest = trend.games[trend.games.length - 1];
  const avgMargin = trend.avg_margin;
  const positive = avgMargin >= 0;
  const title = `Last 10 ${trend.last_10_record}, avg margin ${
    avgMargin > 0 ? "+" : ""
  }${avgMargin.toFixed(1)}. Latest ${latest.is_home ? "vs" : "at"} ${
    latest.opponent_abbreviation ?? "opponent"
  }: ${latest.margin > 0 ? "+" : ""}${latest.margin}`;

  return (
    <div className="flex items-center justify-end gap-1.5" title={title}>
      <svg width={width} height={height} className="overflow-visible" aria-hidden="true">
        <line
          x1={pad}
          x2={width - pad}
          y1={zeroY}
          y2={zeroY}
          className="stroke-[var(--border)]"
          strokeWidth="1"
          strokeDasharray="2 2"
        />
        <polyline
          points={points.join(" ")}
          fill="none"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={
            positive
              ? "stroke-emerald-600 dark:stroke-emerald-400"
              : "stroke-red-500 dark:stroke-red-400"
          }
        />
        {trend.games.map((game, index) => {
          const x = pad + (index / Math.max(1, margins.length - 1)) * (width - pad * 2);
          const y = zeroY - (game.margin / maxAbs) * (height / 2 - pad);
          return (
            <circle
              key={`${game.date}-${index}`}
              cx={x}
              cy={y}
              r="1.7"
              className={game.won ? "fill-emerald-600 dark:fill-emerald-400" : "fill-red-500 dark:fill-red-400"}
            />
          );
        })}
      </svg>
      <span
        className={`min-w-[34px] text-right text-[11px] font-semibold tabular-nums ${
          positive ? "text-emerald-600 dark:text-emerald-400" : "text-red-500 dark:text-red-400"
        }`}
      >
        {avgMargin > 0 ? "+" : ""}
        {avgMargin.toFixed(1)}
      </span>
    </div>
  );
}

const BASE_COLUMNS: StandingsColumn[] = [
  {
    key: "rank",
    label: "#",
    description: "Conference seed.",
    minWidth: 34,
    sortDefault: "asc",
    sortValue: (entry) => entry.playoff_rank,
    render: (entry) => (
      <span className="text-xs tabular-nums text-[var(--muted)]">{entry.playoff_rank}</span>
    ),
  },
  {
    key: "team",
    label: "Team",
    description: "Team abbreviation. Hover the abbreviation for the full team name.",
    align: "left",
    minWidth: 62,
    sortDefault: "asc",
    sortValue: (entry) => entry.abbreviation,
    render: (entry, { clinch }) => <TeamCell entry={entry} clinch={clinch} />,
  },
];

const RECORD_COLUMN: StandingsColumn = {
  key: "record",
  label: "W-L",
  description: "Team win-loss record.",
  sortDefault: "desc",
  sortValue: (entry) => entry.win_pct,
  render: (entry) => (
    <span className="font-medium tabular-nums text-[var(--foreground)]">
      {entry.wins}-{entry.losses}
    </span>
  ),
};

const STANDINGS_COLUMNS: Record<StandingsStatGroup, StandingsColumn[]> = {
  records: [
    ...BASE_COLUMNS,
    {
      key: "wins",
      label: "W",
      description: "Wins.",
      sortDefault: "desc",
      sortValue: (entry) => entry.wins,
      render: (entry) => (
        <span className="font-medium tabular-nums text-[var(--foreground)]">{entry.wins}</span>
      ),
    },
    {
      key: "losses",
      label: "L",
      description: "Losses.",
      sortDefault: "asc",
      sortValue: (entry) => entry.losses,
      render: (entry) => <span className="tabular-nums text-[var(--muted)]">{entry.losses}</span>,
    },
    {
      key: "pct",
      label: "PCT",
      description: "Winning percentage.",
      sortDefault: "desc",
      sortValue: (entry) => entry.win_pct,
      render: (entry) => <span className="tabular-nums">{formatPercent(entry.win_pct)}</span>,
    },
    {
      key: "gb",
      label: "GB",
      description: "Games behind the conference leader.",
      sortDefault: "asc",
      sortValue: (entry) => entry.games_back,
      render: (entry) => (
        <span className="tabular-nums text-[var(--muted)]">
          {entry.games_back != null ? (entry.games_back === 0 ? "—" : entry.games_back.toFixed(1)) : "—"}
        </span>
      ),
    },
    {
      key: "l10",
      label: "L10",
      description: "Record over the last 10 final games.",
      sortDefault: "desc",
      sortValue: (entry) => entry.recent_trend?.games.filter((game) => game.won).length,
      render: (entry) => entry.l10 || "—",
    },
    {
      key: "home",
      label: "Home",
      description: "Home win-loss record from synced final games.",
      sortDefault: "desc",
      sortValue: (entry) => Number(entry.home_record.split("-")[0] ?? 0),
      render: (entry) => <span className="tabular-nums text-[var(--muted)]">{entry.home_record || "—"}</span>,
    },
    {
      key: "away",
      label: "Away",
      description: "Road win-loss record from synced final games.",
      sortDefault: "desc",
      sortValue: (entry) => Number(entry.road_record.split("-")[0] ?? 0),
      render: (entry) => <span className="tabular-nums text-[var(--muted)]">{entry.road_record || "—"}</span>,
    },
    {
      key: "strk",
      label: "Strk",
      description: "Current win or loss streak.",
      sortDefault: "desc",
      sortValue: (entry) => {
        if (!entry.current_streak) return null;
        const amount = Number(entry.current_streak.slice(1));
        return entry.current_streak.startsWith("W") ? amount : -amount;
      },
      render: (entry) => <StreakBadge streak={entry.current_streak} />,
    },
    {
      key: "trend",
      label: "Trend",
      description: "Last-10 point-margin momentum line with average margin label.",
      minWidth: 96,
      sortDefault: "desc",
      sortValue: (entry) => entry.recent_trend?.avg_margin,
      render: (entry) => <TrendCell entry={entry} />,
    },
  ],
  offense: [
    ...BASE_COLUMNS,
    RECORD_COLUMN,
    {
      key: "ortg",
      label: "ORTG",
      description: "Offensive rating: points scored per 100 possessions.",
      sortDefault: "desc",
      sortValue: (entry) => entry.off_rating,
      render: (entry) => formatOne(entry.off_rating),
    },
    {
      key: "pts",
      label: "PPG",
      description: "Points scored per game.",
      sortDefault: "desc",
      sortValue: (entry) => entry.pts_pg,
      render: (entry) => formatOne(entry.pts_pg),
    },
    {
      key: "reb",
      label: "REB",
      description: "Rebounds per game.",
      sortDefault: "desc",
      sortValue: (entry) => entry.reb_pg,
      render: (entry) => formatOne(entry.reb_pg),
    },
    {
      key: "ast",
      label: "AST",
      description: "Assists per game.",
      sortDefault: "desc",
      sortValue: (entry) => entry.ast_pg,
      render: (entry) => formatOne(entry.ast_pg),
    },
    {
      key: "tov",
      label: "TOV",
      description: "Turnovers per game.",
      sortDefault: "asc",
      sortValue: (entry) => entry.tov_pg,
      render: (entry) => formatOne(entry.tov_pg),
    },
    {
      key: "stl",
      label: "STL",
      description: "Steals per game.",
      sortDefault: "desc",
      sortValue: (entry) => entry.stl_pg,
      render: (entry) => formatOne(entry.stl_pg),
    },
    {
      key: "blk",
      label: "BLK",
      description: "Blocks per game.",
      sortDefault: "desc",
      sortValue: (entry) => entry.blk_pg,
      render: (entry) => formatOne(entry.blk_pg),
    },
    {
      key: "diff",
      label: "Diff",
      description: "Average scoring margin per game.",
      sortDefault: "desc",
      sortValue: (entry) => entry.diff_pts_pg,
      render: (entry) => <DiffCell diff={entry.diff_pts_pg} />,
    },
  ],
  defense: [
    ...BASE_COLUMNS,
    RECORD_COLUMN,
    {
      key: "opp-pts",
      label: "Opp PPG",
      description: "Opponent points per game, derived from team scoring and margin.",
      sortDefault: "asc",
      sortValue: (entry) => entry.opp_pts_pg,
      render: (entry) => formatOne(entry.opp_pts_pg),
    },
    {
      key: "drtg",
      label: "DRTG",
      description: "Defensive rating: points allowed per 100 possessions. Lower is better.",
      sortDefault: "asc",
      sortValue: (entry) => entry.def_rating,
      render: (entry) => formatOne(entry.def_rating),
    },
    {
      key: "dreb",
      label: "DREB%",
      description: "Share of available defensive rebounds secured.",
      sortDefault: "desc",
      sortValue: (entry) => entry.dreb_pct,
      render: (entry) => formatPercent(entry.dreb_pct),
    },
    {
      key: "stl",
      label: "STL",
      description: "Steals per game.",
      sortDefault: "desc",
      sortValue: (entry) => entry.stl_pg,
      render: (entry) => formatOne(entry.stl_pg),
    },
    {
      key: "blk",
      label: "BLK",
      description: "Blocks per game.",
      sortDefault: "desc",
      sortValue: (entry) => entry.blk_pg,
      render: (entry) => formatOne(entry.blk_pg),
    },
    {
      key: "tovpct",
      label: "TOV%",
      description: "Turnover percentage from official team dashboard context.",
      sortDefault: "asc",
      sortValue: (entry) => entry.tov_pct,
      render: (entry) => formatPercent(entry.tov_pct),
    },
    {
      key: "drtg-rank",
      label: "DRTG Rk",
      description: "League rank in defensive rating.",
      sortDefault: "asc",
      sortValue: (entry) => entry.def_rating_rank,
      render: (entry) => formatRank(entry.def_rating_rank),
    },
    {
      key: "diff",
      label: "Diff",
      description: "Average scoring margin per game.",
      sortDefault: "desc",
      sortValue: (entry) => entry.diff_pts_pg,
      render: (entry) => <DiffCell diff={entry.diff_pts_pg} />,
    },
  ],
  shooting: [
    ...BASE_COLUMNS,
    RECORD_COLUMN,
    {
      key: "fg",
      label: "FG%",
      description: "Field goal percentage.",
      sortDefault: "desc",
      sortValue: (entry) => entry.fg_pct,
      render: (entry) => formatPercent(entry.fg_pct),
    },
    {
      key: "fg3",
      label: "3P%",
      description: "Three-point percentage.",
      sortDefault: "desc",
      sortValue: (entry) => entry.fg3_pct,
      render: (entry) => formatPercent(entry.fg3_pct),
    },
    {
      key: "ft",
      label: "FT%",
      description: "Free throw percentage.",
      sortDefault: "desc",
      sortValue: (entry) => entry.ft_pct,
      render: (entry) => formatPercent(entry.ft_pct),
    },
    {
      key: "efg",
      label: "eFG%",
      description: "Effective field goal percentage, adjusting for added value of threes.",
      sortDefault: "desc",
      sortValue: (entry) => entry.efg_pct,
      render: (entry) => formatPercent(entry.efg_pct),
    },
    {
      key: "ts",
      label: "TS%",
      description: "True shooting percentage, incorporating twos, threes, and free throws.",
      sortDefault: "desc",
      sortValue: (entry) => entry.ts_pct,
      render: (entry) => formatPercent(entry.ts_pct),
    },
  ],
  advanced: [
    ...BASE_COLUMNS,
    RECORD_COLUMN,
    {
      key: "ortg",
      label: "ORTG",
      description: "Offensive rating: points scored per 100 possessions.",
      sortDefault: "desc",
      sortValue: (entry) => entry.off_rating,
      render: (entry) => formatOne(entry.off_rating),
    },
    {
      key: "drtg",
      label: "DRTG",
      description: "Defensive rating: points allowed per 100 possessions. Lower is better.",
      sortDefault: "asc",
      sortValue: (entry) => entry.def_rating,
      render: (entry) => formatOne(entry.def_rating),
    },
    {
      key: "net",
      label: "NET",
      description: "Net rating: offensive rating minus defensive rating.",
      sortDefault: "desc",
      sortValue: (entry) => entry.net_rating,
      render: (entry) => <DiffCell diff={entry.net_rating} />,
    },
    {
      key: "pace",
      label: "Pace",
      description: "Estimated possessions per 48 minutes.",
      sortDefault: "desc",
      sortValue: (entry) => entry.pace,
      render: (entry) => formatOne(entry.pace),
    },
    {
      key: "pie",
      label: "PIE",
      description: "Player Impact Estimate style team impact share.",
      sortDefault: "desc",
      sortValue: (entry) => entry.pie,
      render: (entry) => formatPercent(entry.pie),
    },
    {
      key: "oreb",
      label: "OREB%",
      description: "Share of available offensive rebounds secured.",
      sortDefault: "desc",
      sortValue: (entry) => entry.oreb_pct,
      render: (entry) => formatPercent(entry.oreb_pct),
    },
    {
      key: "dreb",
      label: "DREB%",
      description: "Share of available defensive rebounds secured.",
      sortDefault: "desc",
      sortValue: (entry) => entry.dreb_pct,
      render: (entry) => formatPercent(entry.dreb_pct),
    },
    {
      key: "tovpct",
      label: "TOV%",
      description: "Turnover percentage from official team dashboard context.",
      sortDefault: "asc",
      sortValue: (entry) => entry.tov_pct,
      render: (entry) => formatPercent(entry.tov_pct),
    },
    {
      key: "astpct",
      label: "AST%",
      description: "Assist percentage from official team dashboard context.",
      sortDefault: "desc",
      sortValue: (entry) => entry.ast_pct,
      render: (entry) => formatPercent(entry.ast_pct),
    },
  ],
  rankings: [
    ...BASE_COLUMNS,
    RECORD_COLUMN,
    {
      key: "ortg-rank",
      label: "ORTG Rk",
      description: "League rank in offensive rating. Lower rank is better.",
      sortDefault: "asc",
      sortValue: (entry) => entry.off_rating_rank,
      render: (entry) => formatRank(entry.off_rating_rank),
    },
    {
      key: "drtg-rank",
      label: "DRTG Rk",
      description: "League rank in defensive rating. Lower rank is better.",
      sortDefault: "asc",
      sortValue: (entry) => entry.def_rating_rank,
      render: (entry) => formatRank(entry.def_rating_rank),
    },
    {
      key: "net-rank",
      label: "NET Rk",
      description: "League rank in net rating. Lower rank is better.",
      sortDefault: "asc",
      sortValue: (entry) => entry.net_rating_rank,
      render: (entry) => formatRank(entry.net_rating_rank),
    },
    {
      key: "pace-rank",
      label: "Pace Rk",
      description: "League rank in pace. Lower rank means faster relative pace rank.",
      sortDefault: "asc",
      sortValue: (entry) => entry.pace_rank,
      render: (entry) => formatRank(entry.pace_rank),
    },
    {
      key: "efg-rank",
      label: "eFG Rk",
      description: "League rank in effective field goal percentage.",
      sortDefault: "asc",
      sortValue: (entry) => entry.efg_pct_rank,
      render: (entry) => formatRank(entry.efg_pct_rank),
    },
    {
      key: "ts-rank",
      label: "TS Rk",
      description: "League rank in true shooting percentage.",
      sortDefault: "asc",
      sortValue: (entry) => entry.ts_pct_rank,
      render: (entry) => formatRank(entry.ts_pct_rank),
    },
    {
      key: "oreb-rank",
      label: "OREB Rk",
      description: "League rank in offensive rebounding percentage.",
      sortDefault: "asc",
      sortValue: (entry) => entry.oreb_pct_rank,
      render: (entry) => formatRank(entry.oreb_pct_rank),
    },
    {
      key: "tov-rank",
      label: "TOV Rk",
      description: "League rank in turnover percentage.",
      sortDefault: "asc",
      sortValue: (entry) => entry.tov_pct_rank,
      render: (entry) => formatRank(entry.tov_pct_rank),
    },
  ],
};

function StandingsTable({
  entries,
  conference,
  historyMap,
  statGroup,
  sort,
  onSortChange,
}: {
  entries: StandingsEntry[];
  conference: string;
  historyMap: Record<number, StandingsHistoryEntry>;
  statGroup: StandingsStatGroup;
  sort: StandingsSort;
  onSortChange: (column: StandingsColumn) => void;
}) {
  const columns = STANDINGS_COLUMNS[statGroup];
  const sortColumn = columns.find((column) => column.key === sort.key) ?? columns[0];
  const sorted = entries
    .filter((e) => e.conference === conference)
    .sort((a, b) => {
      const sortResult = compareSortValues(
        sortColumn.sortValue ? sortColumn.sortValue(a) : a.playoff_rank,
        sortColumn.sortValue ? sortColumn.sortValue(b) : b.playoff_rank,
        sort.direction
      );
      return sortResult || a.playoff_rank - b.playoff_rank;
    });
  const tableMinWidth = Math.max(
    520,
    columns.reduce((total, column) => total + (column.minWidth ?? 56), 0)
  );
  const showSeedLines = sortColumn.key === "rank" && sort.direction === "asc";

  return (
    <div className="bip-table-shell overflow-hidden rounded-2xl">
      <div className="border-b border-[var(--border)] px-5 py-4">
        <h2 className="bip-display text-lg font-semibold text-[var(--foreground)]">
          {conference}ern Conference
        </h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm" style={{ minWidth: tableMinWidth }}>
          <thead>
            <tr className="bip-table-head border-b border-[var(--border)] text-xs uppercase tracking-[0.15em]">
              {columns.map((column) => (
                <th
                  key={column.key}
                  className={`px-1.5 py-3 ${column.align === "left" ? "text-left" : "text-right"}`}
                  style={{ minWidth: column.minWidth }}
                >
                  <button
                    type="button"
                    onClick={() => onSortChange(column)}
                    title={`${column.description} Click to sort by ${column.label}.`}
                    className={`group inline-flex items-center gap-1 transition-colors hover:text-[var(--accent)] ${
                      column.align === "left" ? "justify-start" : "justify-end"
                    } ${sortColumn.key === column.key ? "text-[var(--accent)]" : ""}`}
                  >
                    <span>{column.label}</span>
                    <span className="text-[9px] leading-none opacity-70">
                      {sortColumn.key === column.key
                        ? sort.direction === "asc"
                          ? "▲"
                          : "▼"
                        : "↕"}
                    </span>
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border)]">
            {sorted.map((entry, idx) => {
              const showPlayoffLine = showSeedLines && idx === 5;
              const showPlayInLine = showSeedLines && idx === 9;
              const clinch = entry.clinch_indicator
                ? CLINCH_LABELS[entry.clinch_indicator]
                : null;

              return (
                <Fragment key={entry.team_id}>
                  <tr
                    className={`transition-colors hover:bg-[rgba(216,228,221,0.26)] ${
                      showPlayoffLine
                        ? "border-b-2 border-[rgba(33,72,59,0.42)]"
                        : showPlayInLine
                        ? "border-b-2 border-dashed border-[rgba(111,101,90,0.45)]"
                        : ""
                    }`}
                  >
                    {columns.map((column) => (
                      <td
                        key={column.key}
                        className={`px-1.5 py-3 tabular-nums ${
                          column.align === "left" ? "text-left" : "text-right"
                        }`}
                      >
                        {column.render(entry, { historyMap, clinch })}
                      </td>
                    ))}
                  </tr>
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
      {/* Legend */}
      <div className="flex flex-wrap gap-4 border-t border-[var(--border)] px-5 py-3 text-[10px] text-[var(--muted)]">
        <span><span className="border-t-2 border-[var(--accent)] pr-1 font-bold text-[var(--accent)]">—</span> Playoff line (top 6)</span>
        <span><span className="border-t-2 border-dashed border-[var(--muted)] pr-1 font-bold">- -</span> Play-in line (7-10)</span>
        <span><span className="font-bold text-emerald-500">x</span> clinched playoff · <span className="font-bold text-[var(--accent)]">y</span> clinched division · <span className="font-bold text-red-400">e</span> eliminated</span>
      </div>
    </div>
  );
}

export default function StandingsPage() {
  const [season, setSeason] = useState(DEFAULT_SEASON);
  const [statGroup, setStatGroup] = useState<StandingsStatGroup>("records");
  const [sort, setSort] = useState<StandingsSort>({ key: "rank", direction: "asc" });
  const { data, isLoading, error } = useStandings(season);
  const { data: historyData } = useStandingsHistory(season, 30);

  const historyMap = useMemo<Record<number, StandingsHistoryEntry>>(() => {
    if (!historyData) return {};
    return Object.fromEntries(historyData.map((e) => [e.team_id, e]));
  }, [historyData]);
  const activeGroup = STAT_GROUPS.find((group) => group.key === statGroup) ?? STAT_GROUPS[0];

  function handleStatGroupChange(group: StandingsStatGroup) {
    setStatGroup(group);
    setSort({ key: "rank", direction: "asc" });
  }

  function handleSortChange(column: StandingsColumn) {
    setSort((current) => {
      if (current.key === column.key) {
        return {
          key: column.key,
          direction: current.direction === "asc" ? "desc" : "asc",
        };
      }
      return {
        key: column.key,
        direction: column.sortDefault ?? "desc",
      };
    });
  }

  return (
    <div className="relative left-1/2 w-screen -translate-x-1/2 space-y-8 px-2 sm:px-3 lg:px-4">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="bip-kicker mb-1">
            League
          </p>
          <h1 className="bip-display text-4xl font-semibold text-[var(--foreground)]">
            Standings
          </h1>
          <p className="mt-2 text-[var(--muted)]">
            Conference standings with record context, box-score production, shooting, advanced ratings, and ranks.
          </p>
        </div>
        <select
          value={season}
          onChange={(e) => setSeason(e.target.value)}
          className="bip-input rounded-xl px-3 py-2 text-sm"
        >
          {["2025-26", "2024-25", "2023-24", "2022-23", "2021-22", "2020-21"].map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-y border-[var(--border)] py-4">
        <div>
          <p className="bip-kicker mb-1">Table View</p>
          <p className="text-sm text-[var(--muted)]">{activeGroup.description}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {STAT_GROUPS.map((group) => {
            const active = group.key === statGroup;
            return (
              <button
                key={group.key}
                type="button"
                onClick={() => handleStatGroupChange(group.key)}
                className={`rounded-lg border px-3 py-2 text-xs font-semibold uppercase tracking-[0.12em] transition-colors ${
                  active
                    ? "border-[var(--accent)] bg-[var(--accent)] text-white"
                    : "border-[var(--border)] bg-[var(--surface)] text-[var(--muted)] hover:border-[var(--accent)] hover:text-[var(--foreground)]"
                }`}
              >
                {group.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Loading skeleton */}
      {isLoading && (
        <div className="space-y-6">
          {["East", "West"].map((conf) => (
            <div
              key={conf}
              className="bip-table-shell overflow-hidden rounded-2xl animate-pulse"
            >
              <div className="border-b border-[var(--border)] px-5 py-4">
                <div className="h-5 w-40 rounded bg-[var(--surface-alt)]" />
              </div>
              <div className="divide-y divide-[var(--border)]">
                {Array.from({ length: 15 }).map((_, i) => (
                  <div key={i} className="flex items-center gap-4 px-4 py-3">
                    <div className="h-3 w-4 rounded bg-[var(--surface-alt)]" />
                    <div className="h-3 w-36 rounded bg-[var(--surface-alt)]" />
                    <div className="flex-1" />
                    <div className="h-3 w-8 rounded bg-[var(--surface-alt)]" />
                    <div className="h-3 w-8 rounded bg-[var(--surface-alt)]" />
                    <div className="h-3 w-12 rounded bg-[var(--surface-alt)]" />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="bip-empty rounded-2xl p-8 text-center">
          Could not load standings for {season}. The NBA API may be temporarily unavailable.
        </div>
      )}

      {!isLoading && data && (
        <div className="grid grid-cols-[repeat(2,minmax(600px,1fr))] gap-3 overflow-x-auto pb-2">
          <StandingsTable
            entries={data}
            conference="East"
            historyMap={historyMap}
            statGroup={statGroup}
            sort={sort}
            onSortChange={handleSortChange}
          />
          <StandingsTable
            entries={data}
            conference="West"
            historyMap={historyMap}
            statGroup={statGroup}
            sort={sort}
            onSortChange={handleSortChange}
          />
        </div>
      )}

      {/* Standings bump charts — conference rank over last 30 days */}
      {!isLoading && historyData && historyData.length > 0 && (
        <div className="grid grid-cols-[repeat(2,minmax(600px,1fr))] gap-3 overflow-x-auto pb-2">
          <StandingsBumpChart historyData={historyData} conference="East" expanded />
          <StandingsBumpChart historyData={historyData} conference="West" expanded />
        </div>
      )}
    </div>
  );
}
