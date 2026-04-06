"use client";

import { Suspense, useState, useTransition } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { createPreReadSnapshot } from "@/lib/api";
import {
  usePreReadDeck,
  usePreReadSnapshot,
  usePreReadSnapshots,
  useTeamIntelligence,
  useTeamRotationReport,
  useTeams,
} from "@/hooks/usePlayerStats";
import AvailabilitySummaryCard from "@/components/AvailabilitySummaryCard";
import ScoutingReportView from "@/components/ScoutingReportView";

const SEASONS = ["2025-26", "2024-25", "2023-24", "2022-23"];
type ViewMode = "briefing" | "scouting";

function PreReadPageInner() {
  const searchParams = useSearchParams();
  const rawMode = searchParams.get("mode");
  const snapshotId = searchParams.get("snapshot_id");

  const [team, setTeam] = useState(searchParams.get("team")?.toUpperCase() ?? "OKC");
  const [opponent, setOpponent] = useState(searchParams.get("opponent")?.toUpperCase() ?? "BOS");
  const [season, setSeason] = useState(searchParams.get("season") ?? "2024-25");
  const [mode, setMode] = useState<ViewMode>(rawMode === "scouting" ? "scouting" : "briefing");
  const [snapshotMessage, setSnapshotMessage] = useState<string | null>(null);
  const [isSaving, startSaving] = useTransition();
  const { data: teams } = useTeams();
  const { data: snapshot } = usePreReadSnapshot(snapshotId);
  const activeTeam = snapshot?.context.team_abbreviation ?? team;
  const activeOpponent = snapshot?.context.opponent_abbreviation ?? opponent;
  const activeSeason = snapshot?.context.season ?? season;
  const { data, isLoading } = usePreReadDeck(activeTeam, activeOpponent, activeSeason, snapshotId);
  const { data: recentSnapshots } = usePreReadSnapshots(activeTeam, activeOpponent, activeSeason, 6);
  const { data: teamIntelligence } = useTeamIntelligence(activeTeam, activeSeason);
  const { data: rotationReport } = useTeamRotationReport(activeTeam, activeSeason);
  const nextGame = data?.team_availability.next_game ?? null;

  function handleSaveSnapshot(sourceView: "pre-read-briefing" | "pre-read-scouting") {
    startSaving(async () => {
      try {
        const response = await createPreReadSnapshot({
          team: activeTeam,
          opponent: activeOpponent,
          season: activeSeason,
          game_id: data?.prep_context?.prep_item?.game_id ?? undefined,
          source_view: sourceView,
          source_snapshot_id: snapshotId ?? undefined,
          context: {
            mode,
          },
        });
        setSnapshotMessage(`Saved snapshot ${response.snapshot_id.slice(0, 8)}. Share: ${response.share_url}`);
      } catch {
        setSnapshotMessage("Snapshot save failed.");
      }
    });
  }

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

      {data?.snapshot ? (
        <div className="rounded-[1.5rem] border border-[rgba(33,72,59,0.18)] bg-[rgba(216,228,221,0.28)] px-5 py-4 text-sm text-[var(--muted-strong)]">
          Frozen snapshot: {data.snapshot.snapshot_id.slice(0, 8)} · created {new Date(data.snapshot.created_at).toLocaleString()}
        </div>
      ) : null}

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
        <div className="mt-4 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => handleSaveSnapshot(mode === "scouting" ? "pre-read-scouting" : "pre-read-briefing")}
            className="rounded-full border border-[var(--border-strong)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]"
          >
            {isSaving ? "Saving snapshot..." : "Save frozen snapshot"}
          </button>
          {snapshotMessage ? <div className="text-sm text-[var(--muted-strong)]">{snapshotMessage}</div> : null}
        </div>
        {recentSnapshots?.items?.length ? (
          <div className="mt-5 space-y-2">
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Recent snapshots</div>
            <div className="flex flex-wrap gap-2">
              {recentSnapshots.items.map((item) => (
                <Link
                  key={item.snapshot_id}
                  href={item.share_url}
                  className="rounded-full border border-[var(--border)] bg-white/80 px-3 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-[var(--muted-strong)] transition hover:border-[rgba(33,72,59,0.24)]"
                >
                  {item.snapshot_id.slice(0, 8)} · {item.created_at.slice(0, 10)}
                </Link>
              ))}
            </div>
          </div>
        ) : null}
      </section>

      {data ? (
        <section className="grid gap-4 lg:grid-cols-2">
          <AvailabilitySummaryCard availability={data.team_availability} compact />
          <AvailabilitySummaryCard availability={data.opponent_availability} compact />
        </section>
      ) : null}

      {data?.prep_context ? (
        <section className="rounded-[1.5rem] border border-[var(--border)] bg-[rgba(255,255,255,0.72)] p-5 text-sm leading-6 text-[var(--muted-strong)]">
          <div className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Prep context</div>
          <div className="mt-2 font-semibold text-[var(--foreground)]">
            {data.prep_context.first_adjustment_label ?? data.prep_context.best_edge_label ?? data.prep_context.headline ?? "Prep context loaded"}
          </div>
          {data.prep_context.urgency_rationale ? (
            <p className="mt-2">{data.prep_context.urgency_rationale}</p>
          ) : null}
          {data.prep_context.first_adjustment_rationale ? (
            <p className="mt-2">{data.prep_context.first_adjustment_rationale}</p>
          ) : null}
        </section>
      ) : null}

      {data?.warnings?.length ? (
        <section className="rounded-[1.5rem] border border-[var(--border)] bg-[var(--surface)] p-5 text-sm leading-6 text-[var(--muted-strong)]">
          <div className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Readiness</div>
          <div className="mt-2">
            {data.data_status} via {data.canonical_source}
          </div>
          <ul className="mt-3 space-y-2">
            {data.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
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
                <Link href={data.launch_links.follow_through_url} className="bip-btn-primary rounded-full px-4 py-2 text-sm font-medium">
                  Open team decision tools
                </Link>
                <Link href={`/teams/${activeTeam}?tab=roster`} className="rounded-full border border-[var(--border-strong)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]">
                  Open availability board
                </Link>
                <Link href={`/compare?mode=teams&team_a=${activeTeam}&team_b=${activeOpponent}&season=${activeSeason}&return_to=${encodeURIComponent(`/pre-read?team=${activeTeam}&opponent=${activeOpponent}&season=${activeSeason}&mode=${mode}`)}`} className="rounded-full border border-[var(--border-strong)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]">
                  Open comparison sandbox
                </Link>
                <Link href={data.launch_links.follow_through_url} className="rounded-full border border-[var(--border-strong)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]">
                  Open follow-through
                </Link>
              </div>
            </section>
          </>
        ) : (
          <ScoutingReportView
            teamAbbreviation={activeTeam}
            opponentAbbreviation={activeOpponent}
            season={activeSeason}
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
