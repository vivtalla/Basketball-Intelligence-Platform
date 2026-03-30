import Link from "next/link";
import type { TeamImpactLeader, TeamRotationGame, TeamRotationPlayerRow, TeamRotationReport } from "@/lib/types";

interface TeamRotationIntelligencePanelProps {
  report: TeamRotationReport;
}

function fmt(value: number | null | undefined, digits = 1) {
  return value == null ? "—" : value.toFixed(digits);
}

function signed(value: number | null | undefined, digits = 1) {
  if (value == null) return "—";
  return `${value > 0 ? "+" : ""}${value.toFixed(digits)}`;
}

function statusTone(status: TeamRotationReport["status"]) {
  if (status === "ready") {
    return "bip-success";
  }
  return "bip-pill";
}

function stabilityTone(stability: TeamRotationReport["starter_stability"]) {
  if (stability === "stable") return "text-emerald-600 dark:text-emerald-300";
  if (stability === "mixed") return "text-amber-600 dark:text-amber-300";
  return "text-red-500 dark:text-red-300";
}

function PlayerDeltaRow({
  player,
  label,
}: {
  player: TeamRotationPlayerRow;
  label: string;
}) {
  return (
    <Link
      href={`/players/${player.player_id}`}
      className="bip-panel flex items-center justify-between gap-4 rounded-3xl p-4 transition-colors hover:border-[rgba(33,72,59,0.28)] hover:bg-[rgba(216,228,221,0.24)]"
    >
      <div className="min-w-0">
        <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
          {label}
        </div>
        <div className="mt-1 truncate text-base font-semibold text-[var(--foreground)]">
          {player.player_name}
        </div>
        <div className="mt-1 text-sm text-[var(--muted)]">
          Last 10: {fmt(player.avg_minutes_last_10)} min · Season: {fmt(player.avg_minutes_season)} min
        </div>
      </div>
      <div className="text-right">
        <div
          className={`text-xl font-bold tabular-nums ${
            (player.minutes_delta ?? 0) >= 0
              ? "text-emerald-600 dark:text-emerald-300"
              : "text-red-500 dark:text-red-300"
          }`}
        >
          {signed(player.minutes_delta)}
        </div>
        <div className="text-xs text-[var(--muted)]">
          {player.starts_last_10} starts
        </div>
      </div>
    </Link>
  );
}

function StarterRow({ player }: { player: TeamRotationPlayerRow }) {
  return (
    <Link
      href={`/players/${player.player_id}`}
      className="bip-panel grid gap-3 rounded-3xl p-4 transition-colors hover:border-[rgba(33,72,59,0.28)] hover:bg-[rgba(216,228,221,0.24)] md:grid-cols-[minmax(0,1.2fr)_repeat(3,minmax(88px,0.6fr))]"
    >
      <div className="min-w-0">
        <div className="truncate text-base font-semibold text-[var(--foreground)]">
          {player.player_name}
        </div>
        <div className="mt-1 text-sm text-[var(--muted)]">
          {player.is_primary_starter ? "Primary recent starter" : "Recent starter mix"}
        </div>
      </div>
      <div className="bip-metric rounded-2xl px-3 py-2 text-right">
        <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">Starts</div>
        <div className="mt-1 font-semibold text-[var(--foreground)]">{player.starts_last_10}</div>
      </div>
      <div className="bip-metric rounded-2xl px-3 py-2 text-right">
        <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">Recent Min</div>
        <div className="mt-1 font-semibold text-[var(--foreground)]">{fmt(player.avg_minutes_last_10)}</div>
      </div>
      <div className="bip-metric rounded-2xl px-3 py-2 text-right">
        <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">Delta</div>
        <div
          className={`mt-1 font-semibold ${
            (player.minutes_delta ?? 0) >= 0
              ? "text-emerald-600 dark:text-emerald-300"
              : "text-red-500 dark:text-red-300"
          }`}
        >
          {signed(player.minutes_delta)}
        </div>
      </div>
    </Link>
  );
}

function AnchorRow({ anchor, rank }: { anchor: TeamImpactLeader; rank: number }) {
  return (
    <Link
      href={`/players/${anchor.player_id}`}
      className="bip-panel flex items-center justify-between gap-4 rounded-3xl p-4 transition-colors hover:border-[rgba(33,72,59,0.28)] hover:bg-[rgba(216,228,221,0.24)]"
    >
      <div className="min-w-0">
        <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
          Anchor #{rank}
        </div>
        <div className="mt-1 truncate text-base font-semibold text-[var(--foreground)]">
          {anchor.player_name}
        </div>
        <div className="mt-1 text-sm text-[var(--muted)]">
          BPM {signed(anchor.bpm)} · {fmt(anchor.pts_pg)} PPG
        </div>
      </div>
      <div className="text-right">
        <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
          On/Off
        </div>
        <div className="mt-1 text-xl font-bold tabular-nums text-emerald-600 dark:text-emerald-300">
          {signed(anchor.on_off_net)}
        </div>
        <div className="text-xs text-[var(--muted)]">
          {fmt(anchor.on_minutes, 0)} min
        </div>
      </div>
    </Link>
  );
}

function ReviewGameCard({ game }: { game: TeamRotationGame }) {
  return (
    <Link
      href={`/games/${game.game_id}`}
      className="bip-panel block rounded-3xl p-4 transition-colors hover:border-[rgba(33,72,59,0.28)] hover:bg-[rgba(216,228,221,0.24)]"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
            {game.game_date ?? "Date unavailable"}
          </div>
          <div className="mt-1 text-lg font-semibold text-[var(--foreground)]">
            {game.opponent_abbreviation ?? "TBD"}
          </div>
        </div>
        <div className="text-right">
          <div
            className={`text-sm font-semibold ${
              game.result === "W"
                ? "text-emerald-600 dark:text-emerald-300"
                : "text-red-500 dark:text-red-300"
            }`}
          >
            {game.result}
          </div>
          <div className="mt-1 text-base font-semibold tabular-nums text-[var(--foreground)]">
            {game.team_score ?? "—"}-{game.opponent_score ?? "—"}
          </div>
        </div>
      </div>
      <p className="mt-3 text-sm leading-6 text-[var(--foreground)]">
        {game.rotation_note}
      </p>
    </Link>
  );
}

export default function TeamRotationIntelligencePanel({
  report,
}: TeamRotationIntelligencePanelProps) {
  const largestRiser = report.rotation_risers[0] ?? null;
  const largestFaller = report.rotation_fallers[0] ?? null;
  const topMinuteLeader = report.minute_load_leaders[0] ?? null;

  return (
    <section className="bip-panel-strong rounded-[2rem] p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="bip-kicker">
            Rotation Intelligence
          </div>
          <h2 className="bip-display mt-3 text-3xl font-semibold text-[var(--foreground)]">
            Decision support for who is driving this team now
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--muted)]">
            Compare the last {report.window_games || 10} completed games with the season baseline, then jump straight into the most revealing game tape.
          </p>
        </div>
        <span className={`w-fit rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${statusTone(report.status)}`}>
          {report.status}
        </span>
      </div>

      {report.status === "limited" ? (
        <div className="bip-empty mt-6 rounded-3xl p-6 text-sm leading-6">
          This rotation report is available for warehouse-backed modern seasons only.
        </div>
      ) : (
        <div className="mt-6 space-y-6">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <div className="bip-metric rounded-3xl p-5">
              <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                Rotation status
              </div>
              <div className="mt-3 text-3xl font-bold text-[var(--foreground)]">
                {report.status}
              </div>
              <div className="mt-2 text-sm text-[var(--muted)]">
                {report.window_games}-game window · {topMinuteLeader?.player_name ?? "No leader yet"}
              </div>
            </div>
            <div className="bip-metric rounded-3xl p-5">
              <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                Starter stability
              </div>
              <div className={`mt-3 text-3xl font-bold capitalize ${stabilityTone(report.starter_stability)}`}>
                {report.starter_stability}
              </div>
              <div className="mt-2 text-sm text-[var(--muted)]">
                Unique starters across the last {report.window_games} games
              </div>
            </div>
            <div className="bip-metric rounded-3xl p-5">
              <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                Largest riser
              </div>
              <div className="mt-3 text-xl font-semibold text-[var(--foreground)]">
                {largestRiser?.player_name ?? "—"}
              </div>
              <div className="mt-2 text-sm text-emerald-600 dark:text-emerald-300">
                {largestRiser ? `${signed(largestRiser.minutes_delta)} min` : "No recent riser"}
              </div>
            </div>
            <div className="bip-metric rounded-3xl p-5">
              <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                Largest faller
              </div>
              <div className="mt-3 text-xl font-semibold text-[var(--foreground)]">
                {largestFaller?.player_name ?? "—"}
              </div>
              <div className="mt-2 text-sm text-red-500 dark:text-red-300">
                {largestFaller ? `${signed(largestFaller.minutes_delta)} min` : "No recent faller"}
              </div>
            </div>
          </div>

          <div className="grid gap-6 xl:grid-cols-[1.1fr,0.9fr]">
            <div className="space-y-6">
              <div>
                <div className="flex items-end justify-between gap-4">
                  <div>
                    <h3 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                      Recent Starters
                    </h3>
                    <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                      Sorted by starts in the last {report.window_games} completed games, then recent minutes.
                    </p>
                  </div>
                </div>
                <div className="mt-5 space-y-3">
                  {report.recent_starters.length === 0 ? (
                    <div className="rounded-3xl border border-dashed border-gray-200 p-6 text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
                      No recent starter data is available yet.
                    </div>
                  ) : (
                    report.recent_starters.map((player) => (
                      <StarterRow key={player.player_id} player={player} />
                    ))
                  )}
                </div>
              </div>

              <div className="grid gap-6 lg:grid-cols-2">
                <div>
                  <h3 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                    Who&apos;s Gaining Minutes
                  </h3>
                  <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                    Biggest positive shifts versus season usage.
                  </p>
                  <div className="mt-5 space-y-3">
                    {report.rotation_risers.length === 0 ? (
                      <div className="rounded-3xl border border-dashed border-gray-200 p-6 text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
                        No clear risers in this recent sample.
                      </div>
                    ) : (
                      report.rotation_risers.map((player) => (
                        <PlayerDeltaRow key={player.player_id} player={player} label="Riser" />
                      ))
                    )}
                  </div>
                </div>
                <div>
                  <h3 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                    Who&apos;s Losing Minutes
                  </h3>
                  <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                    Biggest negative shifts versus season usage.
                  </p>
                  <div className="mt-5 space-y-3">
                    {report.rotation_fallers.length === 0 ? (
                      <div className="rounded-3xl border border-dashed border-gray-200 p-6 text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
                        No clear fallers in this recent sample.
                      </div>
                    ) : (
                      report.rotation_fallers.map((player) => (
                        <PlayerDeltaRow key={player.player_id} player={player} label="Faller" />
                      ))
                    )}
                  </div>
                </div>
              </div>
            </div>

            <div className="space-y-6">
              <div>
                <h3 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                  Impact Anchors
                </h3>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  Rotation context tied back to the players most associated with team performance.
                </p>
                <div className="mt-5 space-y-3">
                  {report.on_off_anchors.length === 0 ? (
                    <div className="rounded-3xl border border-dashed border-gray-200 p-6 text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
                      No on/off anchors are available for this sample yet.
                    </div>
                  ) : (
                    report.on_off_anchors.map((anchor, index) => (
                      <AnchorRow key={anchor.player_id} anchor={anchor} rank={index + 1} />
                    ))
                  )}
                </div>
              </div>

              <div>
                <h3 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                  Games To Review Next
                </h3>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  Recent matchups with the biggest minute redistribution or most unusual starter combinations.
                </p>
                <div className="mt-5 space-y-3">
                  {report.recommended_games.length === 0 ? (
                    <div className="rounded-3xl border border-dashed border-gray-200 p-6 text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
                      No recent completed games are available to review yet.
                    </div>
                  ) : (
                    report.recommended_games.map((game) => (
                      <ReviewGameCard key={game.game_id} game={game} />
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
