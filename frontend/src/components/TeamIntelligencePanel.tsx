import Link from "next/link";
import type {
  LineupStatsResponse,
  TeamAnalytics,
  TeamFocusLeversReport,
  TeamImpactLeader,
  TeamIntelligence,
} from "@/lib/types";

interface TeamIntelligencePanelProps {
  intelligence: TeamIntelligence;
  currentAnalytics?: TeamAnalytics | null;
  priorAnalytics?: TeamAnalytics | null;
  season?: string | null;
  focusLevers?: TeamFocusLeversReport | null;
}

function fmt(value: number | null | undefined, digits = 1) {
  return value == null ? "—" : value.toFixed(digits);
}

function signed(value: number | null | undefined, digits = 1) {
  if (value == null) return "—";
  return `${value > 0 ? "+" : ""}${value.toFixed(digits)}`;
}

function coverageTone(status: TeamIntelligence["pbp_coverage"]["status"]) {
  if (status === "ready") return "bip-success";
  if (status === "partial") return "bip-pill";
  return "bg-[var(--surface-alt)] text-[var(--muted)]";
}

function coveragePct(numerator: number, denominator: number) {
  if (!denominator) return 0;
  return Math.round((numerator / denominator) * 100);
}

function isWarehouseTargetSeason(season: string | null | undefined) {
  if (!season) return false;
  const startYear = Number(season.slice(0, 4));
  if (Number.isNaN(startYear)) return false;
  return startYear >= 2024;
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
    <div className="bip-panel rounded-3xl p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="text-sm font-semibold text-[var(--foreground)]">
            {lineup.player_names.join(" · ")}
          </div>
          <div className="mt-2 text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
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
      className="bip-panel flex items-center justify-between gap-4 rounded-3xl p-4 transition-colors hover:border-[rgba(33,72,59,0.28)] hover:bg-[rgba(216,228,221,0.24)]"
    >
      <div className="min-w-0">
        <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
          Impact #{rank}
        </div>
        <div className="mt-1 truncate text-base font-semibold text-[var(--foreground)]">
          {leader.player_name}
        </div>
        <div className="mt-1 text-sm text-[var(--muted)]">
          {fmt(leader.pts_pg)} PPG · BPM {signed(leader.bpm)}
        </div>
      </div>
      <div className="text-right">
        <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
          On/Off
        </div>
        <div className="mt-1 text-xl font-bold tabular-nums text-emerald-600 dark:text-emerald-300">
          {signed(leader.on_off_net)}
        </div>
        <div className="text-xs text-[var(--muted)]">
          {fmt(leader.on_minutes, 0)} min
        </div>
      </div>
    </Link>
  );
}

export default function TeamIntelligencePanel({
  intelligence,
  currentAnalytics = null,
  priorAnalytics = null,
  season = null,
  focusLevers = null,
}: TeamIntelligencePanelProps) {
  const effectiveSeason = season ?? intelligence.season;
  const warehouseTargetSeason = isWarehouseTargetSeason(effectiveSeason);
  const coverage = intelligence.pbp_coverage;
  const gameCoveragePct = coveragePct(coverage.synced_games, coverage.eligible_games);
  const playerCoverageTarget = Math.max(intelligence.impact_leaders.length, coverage.players_with_on_off);
  const playerCoveragePct = coveragePct(
    coverage.players_with_on_off + coverage.players_with_scoring_splits,
    Math.max(1, playerCoverageTarget + coverage.players_with_scoring_splits)
  );
  const nextStep =
    coverage.status === "ready"
      ? "Coverage is complete. Use lineups and impact leaders to evaluate rotation decisions."
      : coverage.status === "partial"
      ? warehouseTargetSeason
        ? `${coverage.eligible_games - coverage.synced_games} games are still missing from local play-by-play. Finish the season sync, then revisit lineup and on/off sections.`
        : `${coverage.eligible_games - coverage.synced_games} tracked games are still missing derived coverage. Historical seasons rely on legacy-plus-derived support, so use this page as directional context rather than waiting for full warehouse sync.`
      : warehouseTargetSeason
      ? "This team has no meaningful play-by-play coverage yet. Start from the coverage dashboard and run a season sync before trusting derived insights."
      : "This historical season is using legacy-plus-derived support. If key team signals still look empty after validation, log it as a product gap instead of assuming a warehouse sync is required.";
  const yoySignals = currentAnalytics && priorAnalytics
    ? [
        {
          label: "Net rating",
          delta:
            currentAnalytics.net_rating != null && priorAnalytics.net_rating != null
              ? currentAnalytics.net_rating - priorAnalytics.net_rating
              : null,
        },
        {
          label: "Points scored",
          delta:
            currentAnalytics.pts_pg != null && priorAnalytics.pts_pg != null
              ? currentAnalytics.pts_pg - priorAnalytics.pts_pg
              : null,
        },
        {
          label: "Assist rate",
          delta:
            currentAnalytics.ast_pct != null && priorAnalytics.ast_pct != null
              ? (currentAnalytics.ast_pct - priorAnalytics.ast_pct) * 100
              : null,
        },
      ]
    : [];

  return (
    <div className="space-y-6">
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="bip-panel rounded-3xl p-5">
          <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
            Standings
          </div>
          <div className="mt-3 text-3xl font-bold text-[var(--foreground)]">
            {intelligence.wins ?? "—"}-{intelligence.losses ?? "—"}
          </div>
          <div className="mt-2 text-sm text-[var(--muted)]">
            {intelligence.conference ?? "Conference"} · Rank {intelligence.playoff_rank ?? "—"}
          </div>
        </div>

        <div className="bip-panel rounded-3xl p-5">
          <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
            Recent Form
          </div>
          <div className="mt-3 text-3xl font-bold text-[var(--foreground)]">
            {intelligence.recent_record ?? intelligence.l10 ?? "—"}
          </div>
          <div className="mt-2 text-sm text-[var(--muted)]">
            Avg margin {signed(intelligence.recent_avg_margin)} · {intelligence.current_streak ?? "No streak"}
          </div>
        </div>

        <div className="bip-panel rounded-3xl p-5">
          <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
            Point Profile
          </div>
          <div className="mt-3 text-3xl font-bold text-[var(--foreground)]">
            {fmt(intelligence.pts_pg)}
          </div>
          <div className="mt-2 text-sm text-[var(--muted)]">
            Allowed {fmt(intelligence.opp_pts_pg)} · Diff {signed(intelligence.diff_pts_pg)}
          </div>
        </div>

        <div className="bip-panel rounded-3xl p-5">
          <div className="flex items-center justify-between gap-3">
            <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
              PBP Coverage
            </div>
            <span className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${coverageTone(coverage.status)}`}>
              {coverage.status}
            </span>
          </div>
          <div className="mt-3 text-3xl font-bold text-[var(--foreground)]">
            {coverage.synced_games}/{coverage.eligible_games}
          </div>
          <div className="mt-2 text-sm text-[var(--muted)]">
            {coverage.players_with_on_off} on/off · {coverage.players_with_scoring_splits} split-ready
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.05fr,0.95fr]">
        <div className="bip-panel-strong rounded-[2rem] p-6">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="bip-display text-2xl font-semibold text-[var(--foreground)]">
                Sync Readiness
              </h2>
              <p className="mt-1 text-sm text-[var(--muted)]">
                A quick read on how safe it is to trust team-level derived metrics for this season.
              </p>
            </div>
            <span className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${coverageTone(coverage.status)}`}>
              {coverage.status}
            </span>
          </div>

          <div className="mt-5 space-y-4">
            <div>
              <div className="flex items-center justify-between gap-3 text-sm text-[var(--muted)]">
                <span>Game coverage</span>
                <span className="font-semibold text-[var(--foreground)]">
                  {coverage.synced_games}/{coverage.eligible_games} games
                </span>
              </div>
              <div className="mt-2 h-3 overflow-hidden rounded-full bg-[var(--surface-alt)]">
                <div
                  className="h-full rounded-full bg-[var(--accent)] transition-all"
                  style={{ width: `${gameCoveragePct}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between gap-3 text-sm text-[var(--muted)]">
                <span>Derived player signals</span>
                <span className="font-semibold text-[var(--foreground)]">
                  {coverage.players_with_on_off} on/off · {coverage.players_with_scoring_splits} scoring
                </span>
              </div>
              <div className="mt-2 h-3 overflow-hidden rounded-full bg-[var(--surface-alt)]">
                <div
                  className="h-full rounded-full bg-emerald-500 transition-all"
                  style={{ width: `${playerCoveragePct}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        <div className="bip-panel-strong rounded-[2rem] p-6">
          <h2 className="bip-display text-2xl font-semibold text-[var(--foreground)]">
            Next Move
          </h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Suggested operations step based on current local team coverage.
          </p>
          <div className="bip-metric mt-5 rounded-3xl p-5">
            <div className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--muted)]">
              Recommendation
            </div>
            <div className="mt-3 text-base leading-7 text-[var(--foreground)]">
              {nextStep}
            </div>
            <div className="mt-4 text-sm text-[var(--muted)]">
              {coverage.status === "ready"
                ? "Best lineups and impact leaders now have enough support to drive analysis."
                : warehouseTargetSeason
                ? "Run more sync work from the coverage board, then use this page to validate lineup and impact changes."
                : "Historical seasons are not full warehouse targets in Sprint 16, so use this page to confirm native and derived signals rather than expecting full coverage-board parity."}
            </div>
          </div>
        </div>
      </section>

      {yoySignals.length > 0 && (
        <section className="bip-panel-strong rounded-[2rem] p-6">
          <div className="flex items-end justify-between gap-4">
            <div>
              <h2 className="bip-display text-2xl font-semibold text-[var(--foreground)]">
                Year-over-Year Signals
              </h2>
              <p className="mt-1 text-sm text-[var(--muted)]">
                Quick deltas against the previous tracked season to show where this team is moving.
              </p>
            </div>
            <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
              vs {priorAnalytics?.season}
            </div>
          </div>
          <div className="mt-5 grid gap-3 md:grid-cols-3">
            {yoySignals.map((signal) => (
              <div
                key={signal.label}
                className="bip-metric rounded-3xl p-4"
              >
                <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">
                  {signal.label}
                </div>
                <div
                  className={`mt-3 text-3xl font-bold tabular-nums ${
                    signal.delta == null
                      ? "text-gray-400 dark:text-gray-500"
                      : signal.delta >= 0
                      ? "text-emerald-600 dark:text-emerald-300"
                      : "text-red-500 dark:text-red-300"
                  }`}
                >
                  {signal.delta == null
                    ? "—"
                    : `${signal.delta >= 0 ? "+" : ""}${signal.delta.toFixed(1)}`}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {focusLevers && focusLevers.focus_levers.length > 0 ? (
        <section className="bip-panel-strong rounded-[2rem] p-6">
          <div className="flex items-end justify-between gap-4">
            <div>
              <h2 className="bip-display text-2xl font-semibold text-[var(--foreground)]">
                Focus Levers
              </h2>
              <p className="mt-1 text-sm text-[var(--muted)]">
                Four-factor decision cues that show where the clearest coachable edge or leak lives.
              </p>
            </div>
            <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
              {focusLevers.season}
            </div>
          </div>
          <div className="mt-5 grid gap-4 xl:grid-cols-[1.05fr,0.95fr]">
            <div className="space-y-3">
              {focusLevers.focus_levers.map((lever) => (
                <div key={`${lever.factor_id}-${lever.title}`} className="bip-panel rounded-3xl p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-sm font-semibold text-[var(--foreground)]">{lever.title}</div>
                    <span className="rounded-full bg-[rgba(33,72,59,0.08)] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--accent-strong)]">
                      {lever.impact_label}
                    </span>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-[var(--muted-strong)]">
                    {lever.summary}
                  </p>
                </div>
              ))}
            </div>
            <div className="space-y-3">
              {focusLevers.factor_rows.map((row) => (
                <div key={row.factor_id} className="bip-panel rounded-3xl p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                        {row.label}
                      </div>
                      <div className="mt-2 text-2xl font-semibold text-[var(--foreground)]">
                        {fmt(row.team_value, row.factor_id === "shooting" || row.factor_id === "free_throws" ? 3 : 1)}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                        League
                      </div>
                      <div className="mt-2 text-lg font-semibold text-[var(--muted-strong)]">
                        {fmt(row.league_reference, row.factor_id === "shooting" || row.factor_id === "free_throws" ? 3 : 1)}
                      </div>
                    </div>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-[var(--muted-strong)]">
                    {row.note}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[1.05fr,0.95fr]">
        <section className="bip-panel-strong rounded-[2rem] p-6">
          <div className="flex items-end justify-between gap-4">
            <div>
              <h2 className="bip-display text-2xl font-semibold text-[var(--foreground)]">
                Impact Leaders
              </h2>
              <p className="mt-1 text-sm text-[var(--muted)]">
                Best on/off differentials among current roster players with synced play-by-play.
              </p>
            </div>
          </div>
          <div className="mt-5 space-y-3">
            {intelligence.impact_leaders.length === 0 ? (
              <div className="bip-empty rounded-3xl p-6 text-sm">
                {warehouseTargetSeason
                  ? "No team impact leaders yet. Sync more play-by-play to unlock this section."
                  : "No team impact leaders are available yet for this historical season. If this blocks analysis, log it in the Sprint 16 validation matrix rather than treating it as a mandatory warehouse task."}
              </div>
            ) : (
              intelligence.impact_leaders.map((leader, index) => (
                <LeaderRow key={leader.player_id} leader={leader} rank={index + 1} />
              ))
            )}
          </div>
        </section>

        <section className="bip-panel-strong rounded-[2rem] p-6">
          <div>
            <h2 className="bip-display text-2xl font-semibold text-[var(--foreground)]">
              Recent Games
            </h2>
            <p className="mt-1 text-sm text-[var(--muted)]">
              Latest completed team games with direct links into the Game Explorer.
            </p>
          </div>
          <div className="mt-5 space-y-3">
            {intelligence.recent_games.length === 0 ? (
              <div className="bip-empty rounded-3xl p-6 text-sm">
                No recent games are stored for this season yet.
              </div>
            ) : (
              intelligence.recent_games.map((game) => (
                <Link
                  key={game.game_id}
                  href={`/games/${game.game_id}`}
                  className="bip-panel flex items-center justify-between gap-4 rounded-3xl p-4 transition-colors hover:border-[rgba(33,72,59,0.28)] hover:bg-[rgba(216,228,221,0.24)]"
                >
                  <div>
                    <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                      {game.game_date ?? "Date unavailable"}
                    </div>
                    <div className="mt-1 text-base font-semibold text-[var(--foreground)]">
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
                    <div className="mt-1 text-base font-semibold tabular-nums text-[var(--foreground)]">
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
        <section className="bip-panel-strong rounded-[2rem] p-6">
          <h2 className="bip-display text-2xl font-semibold text-[var(--foreground)]">
            Best Lineups
          </h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Top five-man combinations with at least 20 tracked possessions.
          </p>
          <div className="mt-5 space-y-3">
            {intelligence.best_lineups.length === 0 ? (
              <div className="bip-empty rounded-3xl p-6 text-sm">
                No high-confidence lineup data yet for this team.
              </div>
            ) : (
              intelligence.best_lineups.map((lineup) => (
                <LineupMiniCard key={lineup.lineup_key} lineup={lineup} tone="good" />
              ))
            )}
          </div>
        </section>

        <section className="bip-panel-strong rounded-[2rem] p-6">
          <h2 className="bip-display text-2xl font-semibold text-[var(--foreground)]">
            Pressure Points
          </h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Lowest-performing tracked lineups, useful for rotation and bench context.
          </p>
          <div className="mt-5 space-y-3">
            {intelligence.worst_lineups.length === 0 ? (
              <div className="bip-empty rounded-3xl p-6 text-sm">
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
