"use client";

import Link from "next/link";
import type { PreReadDeckResponse, TeamIntelligence, TeamRotationReport } from "@/lib/types";

interface ScoutingReportViewProps {
  teamAbbreviation: string;
  opponentAbbreviation: string;
  season: string;
  deck: PreReadDeckResponse;
  intelligence?: TeamIntelligence | null;
  rotationReport?: TeamRotationReport | null;
}

interface ScoutingGameCard {
  game_id: string;
  game_date: string | null;
  opponent_abbreviation: string | null;
  result: string;
  team_score: number | null;
  opponent_score: number | null;
  rotation_note: string;
  source: string;
}

function buildGameHref(
  teamAbbreviation: string,
  opponentAbbreviation: string,
  season: string,
  gameId: string,
  reason: string
) {
  const params = new URLSearchParams({
    source: "scouting-report",
    source_id: `${teamAbbreviation}:${opponentAbbreviation}:${gameId}`,
    team: teamAbbreviation,
    opponent: opponentAbbreviation,
    season,
    reason,
    return_to: `/pre-read?team=${teamAbbreviation}&opponent=${opponentAbbreviation}&season=${season}&mode=scouting`,
  });
  return `/games/${gameId}?${params.toString()}`;
}

export default function ScoutingReportView({
  teamAbbreviation,
  opponentAbbreviation,
  season,
  deck,
  intelligence,
  rotationReport,
}: ScoutingReportViewProps) {
  const topGames: ScoutingGameCard[] = [
    ...(rotationReport?.recommended_games ?? []).slice(0, 2).map((game) => ({
      ...game,
      source: "rotation report",
    })),
    ...(intelligence?.recent_games ?? []).slice(0, 1).map((game) => ({
      game_id: game.game_id,
      game_date: game.game_date,
      opponent_abbreviation: game.opponent_abbreviation,
      result: game.result.startsWith("W") ? "W" : "L",
      team_score: game.team_score,
      opponent_score: game.opponent_score,
      rotation_note: `Recent form against ${game.opponent_abbreviation ?? "the opponent"} is worth a film check.`,
      source: "recent form",
    })),
  ];

  return (
    <section className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2">
        <article className="rounded-[1.75rem] border border-[var(--border)] bg-[var(--surface)] p-6">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Top actions
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-[var(--foreground)]">
            What this staff should expect first
          </h2>
          <div className="mt-4 space-y-3">
            {deck.focus_levers.map((lever) => (
              <div
                key={`${lever.factor_id}-${lever.title}`}
                className="rounded-2xl border border-[var(--border)] bg-[rgba(255,255,255,0.72)] p-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="font-semibold text-[var(--foreground)]">{lever.title}</div>
                  <span className="rounded-full bg-[rgba(33,72,59,0.08)] px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--accent-strong)]">
                    {lever.impact_label}
                  </span>
                </div>
                <p className="mt-2 text-sm leading-6 text-[var(--muted-strong)]">
                  {lever.summary}
                </p>
              </div>
            ))}
          </div>
        </article>

        <article className="rounded-[1.75rem] border border-[var(--border)] bg-[var(--surface)] p-6">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Weak coverages
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-[var(--foreground)]">
            Opponent edges and pressure points
          </h2>
          <div className="mt-4 space-y-3">
            {deck.matchup_advantages.length ? (
              deck.matchup_advantages.map((advantage) => (
                <div
                  key={advantage}
                  className="rounded-2xl border border-[var(--border)] bg-[rgba(255,255,255,0.72)] p-4 text-sm leading-6 text-[var(--muted-strong)]"
                >
                  {advantage}
                </div>
              ))
            ) : (
              <div className="rounded-2xl border border-[var(--border)] px-4 py-4 text-sm text-[var(--muted-strong)]">
                No clear matchup edge surfaced from the current data.
              </div>
            )}
          </div>
        </article>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <article className="rounded-[1.75rem] border border-[var(--border)] bg-[var(--surface)] p-6">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Preferred rotation patterns
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-[var(--foreground)]">
            Which units and substitutions should matter
          </h2>
          <div className="mt-4 space-y-3">
            {rotationReport?.rotation_risers?.length ? (
              rotationReport.rotation_risers.slice(0, 3).map((row) => (
                <div
                  key={row.player_id}
                  className="rounded-2xl border border-[var(--border)] bg-[rgba(255,255,255,0.72)] p-4"
                >
                  <div className="font-semibold text-[var(--foreground)]">{row.player_name}</div>
                  <div className="mt-1 text-sm text-[var(--muted-strong)]">
                    Last 10: {row.avg_minutes_last_10?.toFixed(1) ?? "—"} min · Season: {row.avg_minutes_season?.toFixed(1) ?? "—"} min
                  </div>
                </div>
              ))
            ) : (
              <div className="rounded-2xl border border-[var(--border)] px-4 py-4 text-sm text-[var(--muted-strong)]">
                Rotation context is limited for this matchup, so keep this section directional.
              </div>
            )}
          </div>
        </article>

        <article className="rounded-[1.75rem] border border-[var(--border)] bg-[var(--surface)] p-6">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Recent shifts
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-[var(--foreground)]">
            Games worth opening in film or the explorer
          </h2>
          <div className="mt-4 space-y-3">
            {topGames.length ? (
              topGames.map((game) => (
                <Link
                  key={`${game.source}-${game.game_id}`}
                  href={buildGameHref(teamAbbreviation, opponentAbbreviation, season, game.game_id, game.rotation_note)}
                  className="block rounded-2xl border border-[var(--border)] bg-[rgba(255,255,255,0.72)] p-4 transition hover:border-[rgba(33,72,59,0.28)] hover:bg-[rgba(216,228,221,0.24)]"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                        {game.game_date ?? "Date unavailable"}
                      </div>
                      <div className="mt-1 text-lg font-semibold text-[var(--foreground)]">
                        {game.opponent_abbreviation ?? "Opponent TBD"}
                      </div>
                    </div>
                    <div className="text-right text-sm font-semibold text-[var(--accent-strong)]">
                      {game.result}
                    </div>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-[var(--muted-strong)]">
                    {game.rotation_note}
                  </p>
                </Link>
              ))
            ) : (
              <div className="rounded-2xl border border-[var(--border)] px-4 py-4 text-sm text-[var(--muted-strong)]">
                No recent shifts available yet for this season.
              </div>
            )}
          </div>
        </article>
      </div>

      <section className="grid gap-4 md:grid-cols-2">
        {deck.slides.map((slide) => (
          <article
            key={`${slide.eyebrow}-${slide.title}`}
            className="rounded-[1.75rem] border border-[var(--border)] bg-[var(--surface)] p-6 break-inside-avoid print:shadow-none"
          >
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
              {slide.eyebrow}
            </p>
            <h3 className="mt-3 text-2xl font-semibold text-[var(--foreground)]">
              {slide.title}
            </h3>
            <ul className="mt-5 space-y-3 text-sm leading-6 text-[var(--muted-strong)]">
              {slide.bullets.map((bullet) => (
                <li key={bullet}>{bullet}</li>
              ))}
            </ul>
          </article>
        ))}
      </section>
    </section>
  );
}
