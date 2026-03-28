"use client";

import Link from "next/link";
import type { LineupStatsResponse, TeamImpactLeader, TeamIntelligence } from "@/lib/types";

interface TeamIntelligencePanelProps {
  intelligence: TeamIntelligence;
}

function fmt(value: number | null | undefined, digits = 1) {
  return value == null ? "—" : value.toFixed(digits);
}

function signed(value: number | null | undefined, digits = 1) {
  if (value == null) return "—";
  return `${value > 0 ? "+" : ""}${value.toFixed(digits)}`;
}

function coverageTone(status: TeamIntelligence["pbp_coverage"]["status"]) {
  if (status === "ready") return "text-emerald-600 bg-emerald-50 dark:text-emerald-300 dark:bg-emerald-950/30";
  if (status === "partial") return "text-amber-600 bg-amber-50 dark:text-amber-300 dark:bg-amber-950/30";
  return "text-gray-500 bg-gray-100 dark:text-gray-300 dark:bg-gray-800";
}

function LineupMiniCard({
  lineup,
  tone,
}: {
  lineup: LineupStatsResponse;
  tone: "good" | "bad";
}) {
  const net = lineup.net_rating ?? 0;
  const netClass =
    tone === "good"
      ? "text-emerald-600 dark:text-emerald-300"
      : "text-red-500 dark:text-red-300";

  return (
    <div className="rounded-3xl border border-gray-200 p-4 dark:border-gray-800">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            {lineup.player_names.join(" · ")}
          </div>
          <div className="mt-2 text-xs uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400">
            {fmt(lineup.minutes)} min · {lineup.possessions ?? "—"} poss
          </div>
        </div>
        <div className={`text-lg font-bold tabular-nums ${netClass}`}>
          {net > 0 ? "+" : ""}
          {fmt(net)}
        </div>
      </div>
    </div>
  );
}

function LeaderRow({ leader, rank }: { leader: TeamImpactLeader; rank: number }) {
  return (
    <Link
      href={`/players/${leader.player_id}`}
      className="flex items-center justify-between gap-4 rounded-3xl border border-gray-200 p-4 transition-colors hover:border-blue-300 hover:bg-blue-50/50 dark:border-gray-800 dark:hover:border-blue-800 dark:hover:bg-blue-950/20"
    >
      <div className="min-w-0">
        <div className="text-xs uppercase tracking-[0.18em] text-gray-400 dark:text-gray-500">
          Impact #{rank}
        </div>
        <div className="mt-1 truncate text-base font-semibold text-gray-900 dark:text-gray-100">
          {leader.player_name}
        </div>
        <div className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          {fmt(leader.pts_pg)} PPG · BPM {signed(leader.bpm)}
        </div>
      </div>
      <div className="text-right">
        <div className="text-xs uppercase tracking-[0.18em] text-gray-400 dark:text-gray-500">
          On/Off
        </div>
        <div className="mt-1 text-xl font-bold tabular-nums text-emerald-600 dark:text-emerald-300">
          {signed(leader.on_off_net)}
        </div>
        <div className="text-xs text-gray-500 dark:text-gray-400">
          {fmt(leader.on_minutes, 0)} min
        </div>
      </div>
    </Link>
  );
}

export default function TeamIntelligencePanel({ intelligence }: TeamIntelligencePanelProps) {
  const coverage = intelligence.pbp_coverage;

  return (
    <div className="space-y-6">
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-3xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
          <div className="text-xs uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400">
            Standings
          </div>
          <div className="mt-3 text-3xl font-bold text-gray-900 dark:text-gray-100">
            {intelligence.wins ?? "—"}-{intelligence.losses ?? "—"}
          </div>
          <div className="mt-2 text-sm text-gray-500 dark:text-gray-400">
            {intelligence.conference ?? "Conference"} · Rank {intelligence.playoff_rank ?? "—"}
          </div>
        </div>

        <div className="rounded-3xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
          <div className="text-xs uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400">
            Recent Form
          </div>
          <div className="mt-3 text-3xl font-bold text-gray-900 dark:text-gray-100">
            {intelligence.recent_record ?? intelligence.l10 ?? "—"}
          </div>
          <div className="mt-2 text-sm text-gray-500 dark:text-gray-400">
            Avg margin {signed(intelligence.recent_avg_margin)} · {intelligence.current_streak ?? "No streak"}
          </div>
        </div>

        <div className="rounded-3xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
          <div className="text-xs uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400">
            Point Profile
          </div>
          <div className="mt-3 text-3xl font-bold text-gray-900 dark:text-gray-100">
            {fmt(intelligence.pts_pg)}
          </div>
          <div className="mt-2 text-sm text-gray-500 dark:text-gray-400">
            Allowed {fmt(intelligence.opp_pts_pg)} · Diff {signed(intelligence.diff_pts_pg)}
          </div>
        </div>

        <div className="rounded-3xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
          <div className="flex items-center justify-between gap-3">
            <div className="text-xs uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400">
              PBP Coverage
            </div>
            <span className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${coverageTone(coverage.status)}`}>
              {coverage.status}
            </span>
          </div>
          <div className="mt-3 text-3xl font-bold text-gray-900 dark:text-gray-100">
            {coverage.synced_games}/{coverage.eligible_games}
          </div>
          <div className="mt-2 text-sm text-gray-500 dark:text-gray-400">
            {coverage.players_with_on_off} on/off · {coverage.players_with_scoring_splits} split-ready
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.05fr,0.95fr]">
        <section className="rounded-[2rem] border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-900">
          <div className="flex items-end justify-between gap-4">
            <div>
              <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                Impact Leaders
              </h2>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                Best on/off differentials among current roster players with synced play-by-play.
              </p>
            </div>
          </div>
          <div className="mt-5 space-y-3">
            {intelligence.impact_leaders.length === 0 ? (
              <div className="rounded-3xl border border-dashed border-gray-200 p-6 text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
                No team impact leaders yet. Sync more play-by-play to unlock this section.
              </div>
            ) : (
              intelligence.impact_leaders.map((leader, index) => (
                <LeaderRow key={leader.player_id} leader={leader} rank={index + 1} />
              ))
            )}
          </div>
        </section>

        <section className="rounded-[2rem] border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-900">
          <div>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
              Recent Games
            </h2>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Latest completed team games with direct links into the Game Explorer.
            </p>
          </div>
          <div className="mt-5 space-y-3">
            {intelligence.recent_games.length === 0 ? (
              <div className="rounded-3xl border border-dashed border-gray-200 p-6 text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
                No recent games are stored for this season yet.
              </div>
            ) : (
              intelligence.recent_games.map((game) => (
                <Link
                  key={game.game_id}
                  href={`/games/${game.game_id}`}
                  className="flex items-center justify-between gap-4 rounded-3xl border border-gray-200 p-4 transition-colors hover:border-blue-300 hover:bg-blue-50/50 dark:border-gray-800 dark:hover:border-blue-800 dark:hover:bg-blue-950/20"
                >
                  <div>
                    <div className="text-xs uppercase tracking-[0.18em] text-gray-400 dark:text-gray-500">
                      {game.game_date ?? "Date unavailable"}
                    </div>
                    <div className="mt-1 text-base font-semibold text-gray-900 dark:text-gray-100">
                      {game.is_home ? "vs" : "at"} {game.opponent_abbreviation ?? "TBD"}
                    </div>
                  </div>
                  <div className="text-right">
                    <div
                      className={`text-sm font-semibold ${
                        game.result === "W"
                          ? "text-emerald-600 dark:text-emerald-300"
                          : game.result === "L"
                          ? "text-red-500 dark:text-red-300"
                          : "text-gray-500 dark:text-gray-400"
                      }`}
                    >
                      {game.result}
                    </div>
                    <div className="mt-1 text-base font-semibold tabular-nums text-gray-900 dark:text-gray-100">
                      {game.team_score ?? "—"}-{game.opponent_score ?? "—"}
                    </div>
                  </div>
                </Link>
              ))
            )}
          </div>
        </section>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-[2rem] border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-900">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
            Best Lineups
          </h2>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Top five-man combinations with at least 20 tracked possessions.
          </p>
          <div className="mt-5 space-y-3">
            {intelligence.best_lineups.length === 0 ? (
              <div className="rounded-3xl border border-dashed border-gray-200 p-6 text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
                No high-confidence lineup data yet for this team.
              </div>
            ) : (
              intelligence.best_lineups.map((lineup) => (
                <LineupMiniCard key={lineup.lineup_key} lineup={lineup} tone="good" />
              ))
            )}
          </div>
        </section>

        <section className="rounded-[2rem] border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-900">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
            Pressure Points
          </h2>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Lowest-performing tracked lineups, useful for rotation and bench context.
          </p>
          <div className="mt-5 space-y-3">
            {intelligence.worst_lineups.length === 0 ? (
              <div className="rounded-3xl border border-dashed border-gray-200 p-6 text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
                No weak lineup samples are available yet.
              </div>
            ) : (
              intelligence.worst_lineups.map((lineup) => (
                <LineupMiniCard key={lineup.lineup_key} lineup={lineup} tone="bad" />
              ))
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
