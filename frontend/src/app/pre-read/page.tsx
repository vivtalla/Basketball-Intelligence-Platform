"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { usePreReadDeck, useTeamIntelligence, useTeamRotationReport, useTeams } from "@/hooks/usePlayerStats";
import AvailabilitySummaryCard from "@/components/AvailabilitySummaryCard";
import ScoutingReportView from "@/components/ScoutingReportView";

const SEASONS = ["2025-26", "2024-25", "2023-24", "2022-23"];
type ViewMode = "briefing" | "scouting";

function PreReadPageInner() {
  const searchParams = useSearchParams();
  const rawMode = searchParams.get("mode");

  const [team, setTeam] = useState(searchParams.get("team")?.toUpperCase() ?? "OKC");
  const [opponent, setOpponent] = useState(searchParams.get("opponent")?.toUpperCase() ?? "BOS");
  const [season, setSeason] = useState(searchParams.get("season") ?? "2024-25");
  const [mode, setMode] = useState<ViewMode>(rawMode === "scouting" ? "scouting" : "briefing");
  const { data: teams } = useTeams();
  const { data, isLoading } = usePreReadDeck(team, opponent, season);
  const { data: teamIntelligence } = useTeamIntelligence(team, season);
  const { data: rotationReport } = useTeamRotationReport(team, season);
  const nextGame = data?.team_availability.next_game ?? null;

  return (
    <div className="mx-auto max-w-6xl space-y-8 print:space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="bip-kicker">Pregame Briefing</p>
          <h1 className="bip-display mt-3 text-4xl font-semibold text-[var(--foreground)]">
            Game-Day Pre-Read
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--muted-strong)]">
            A short printable deck for game-day coaching: focus levers, matchup edges, tactical adjustments, and a scouting mode that keeps the next game readable in one place.
          </p>
        </div>
        <button
          type="button"
          onClick={() => window.print()}
          className="bip-btn-primary rounded-full px-4 py-2 text-sm font-medium"
        >
          Print deck
        </button>
      </div>

      <section className="flex rounded-xl overflow-hidden border border-[var(--border)] w-fit text-sm">
        <button
          type="button"
          onClick={() => setMode("briefing")}
          className={`px-5 py-2 transition-colors ${mode === "briefing" ? "bip-toggle-active" : "bip-toggle"}`}
        >
          Briefing
        </button>
        <button
          type="button"
          onClick={() => setMode("scouting")}
          className={`px-5 py-2 transition-colors ${mode === "scouting" ? "bip-toggle-active" : "bip-toggle"}`}
        >
          Scouting Report
        </button>
      </section>

      <section className="bip-panel rounded-[1.8rem] p-6 print:hidden">
        <div className="grid gap-4 md:grid-cols-3">
          <label className="space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Team</span>
            <select value={team} onChange={(event) => setTeam(event.target.value)} className="bip-input w-full rounded-2xl px-4 py-3 text-sm">
              {(teams ?? []).map((entry) => (
                <option key={entry.abbreviation} value={entry.abbreviation}>
                  {entry.abbreviation} · {entry.name}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Opponent</span>
            <select value={opponent} onChange={(event) => setOpponent(event.target.value)} className="bip-input w-full rounded-2xl px-4 py-3 text-sm">
              {(teams ?? []).map((entry) => (
                <option key={entry.abbreviation} value={entry.abbreviation}>
                  {entry.abbreviation} · {entry.name}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Season</span>
            <select value={season} onChange={(event) => setSeason(event.target.value)} className="bip-input w-full rounded-2xl px-4 py-3 text-sm">
              {SEASONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
        </div>
      </section>

      {data ? (
        <section className="grid gap-4 lg:grid-cols-2">
          <AvailabilitySummaryCard availability={data.team_availability} compact />
          <AvailabilitySummaryCard availability={data.opponent_availability} compact />
        </section>
      ) : null}

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="h-64 animate-pulse rounded-[1.75rem] bg-[var(--surface-alt)]" />
          ))}
        </div>
      ) : data ? (
        mode === "briefing" ? (
          <>
            <div className="grid gap-4 md:grid-cols-2">
              {data.slides.map((slide) => (
                <article key={`${slide.eyebrow}-${slide.title}`} className="rounded-[1.8rem] border border-[var(--border)] bg-[var(--surface)] p-6 break-inside-avoid print:shadow-none">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                    {slide.eyebrow}
                  </p>
                  <h2 className="mt-3 text-2xl font-semibold text-[var(--foreground)]">
                    {slide.title}
                  </h2>
                  <ul className="mt-5 space-y-3 text-sm leading-6 text-[var(--muted-strong)]">
                    {slide.bullets.map((bullet) => (
                      <li key={bullet}>{bullet}</li>
                    ))}
                  </ul>
                </article>
              ))}
            </div>

            <section className="rounded-[1.8rem] border border-[var(--border)] bg-[var(--surface)] p-6 print:hidden">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Follow-through</p>
              {nextGame ? (
                <p className="mt-3 text-sm leading-6 text-[var(--muted-strong)]">
                  Next synced game: {nextGame.is_home ? "vs" : "at"} {nextGame.opponent_abbreviation ?? nextGame.opponent_name ?? "Opponent TBD"} on {nextGame.game_date ?? "TBD"}.
                </p>
              ) : null}
              <div className="mt-4 flex flex-wrap gap-3">
                <Link href={`/teams/${team}?tab=decision`} className="bip-btn-primary rounded-full px-4 py-2 text-sm font-medium">
                  Open team decision tools
                </Link>
                <Link href={`/teams/${team}?tab=roster`} className="rounded-full border border-[var(--border-strong)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]">
                  Open availability board
                </Link>
                <Link href={`/compare?mode=teams&team_a=${team}&team_b=${opponent}&season=${season}&return_to=${encodeURIComponent(`/pre-read?team=${team}&opponent=${opponent}&season=${season}&mode=${mode}`)}`} className="rounded-full border border-[var(--border-strong)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]">
                  Open comparison sandbox
                </Link>
              </div>
            </section>
          </>
        ) : (
          <ScoutingReportView
            teamAbbreviation={team}
            opponentAbbreviation={opponent}
            season={season}
            deck={data}
            intelligence={teamIntelligence ?? null}
            rotationReport={rotationReport ?? null}
          />
        )
      ) : null}
    </div>
  );
}

export default function PreReadPage() {
  return (
    <Suspense>
      <PreReadPageInner />
    </Suspense>
  );
}
