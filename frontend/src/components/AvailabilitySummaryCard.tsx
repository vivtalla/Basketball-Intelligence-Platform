"use client";

import type { TeamAvailabilityPlayer, TeamAvailabilityResponse } from "@/lib/types";

interface AvailabilitySummaryCardProps {
  availability: TeamAvailabilityResponse;
  compact?: boolean;
}

function formatDate(value: string | null) {
  if (!value) return "Date TBD";
  const dateOnlyMatch = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  const parsed = dateOnlyMatch
    ? new Date(Number(dateOnlyMatch[1]), Number(dateOnlyMatch[2]) - 1, Number(dateOnlyMatch[3]))
    : new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

function toneClass(status: TeamAvailabilityResponse["overall_status"]) {
  if (status === "healthy") return "bg-[rgba(47,109,74,0.12)] text-[var(--success-ink)]";
  if (status === "shorthanded") return "bg-[rgba(165,72,54,0.12)] text-[var(--danger-ink)]";
  if (status === "monitor") return "bg-[rgba(181,145,78,0.14)] text-[var(--foreground)]";
  return "bg-[var(--surface-alt)] text-[var(--muted-strong)]";
}

function playerLine(player: TeamAvailabilityPlayer) {
  const details = [
    player.injury_status,
    player.return_date ? `Return ${formatDate(player.return_date)}` : null,
    player.impact_label,
  ].filter(Boolean);
  return `${player.player_name}${player.position ? ` · ${player.position}` : ""}${details.length ? ` · ${details.join(" · ")}` : ""}`;
}

function PlayerSection({
  label,
  players,
  emptyLabel,
  compact,
}: {
  label: string;
  players: TeamAvailabilityPlayer[];
  emptyLabel: string;
  compact: boolean;
}) {
  const visible = compact ? players.slice(0, 2) : players.slice(0, 4);

  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[rgba(255,255,255,0.68)] p-4">
      <div className="flex items-center justify-between gap-3">
        <div className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
          {label}
        </div>
        <div className="text-sm font-semibold text-[var(--foreground)]">{players.length}</div>
      </div>
      <div className="mt-3 space-y-2 text-sm leading-6 text-[var(--muted-strong)]">
        {visible.length ? (
          visible.map((player) => (
            <div key={`${label}-${player.player_id}`}>{playerLine(player)}</div>
          ))
        ) : (
          <div>{emptyLabel}</div>
        )}
      </div>
    </div>
  );
}

export default function AvailabilitySummaryCard({
  availability,
  compact = false,
}: AvailabilitySummaryCardProps) {
  const nextGame = availability.next_game;

  return (
    <article className="rounded-[1.8rem] border border-[var(--border)] bg-[var(--surface)] p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            {availability.abbreviation}
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-[var(--foreground)]">
            Roster availability
          </h2>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--muted-strong)]">
            {availability.summary}
          </p>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${toneClass(availability.overall_status)}`}>
          {availability.overall_status}
        </span>
      </div>

      <div className="mt-4 flex flex-wrap gap-3 text-sm">
        <span className="rounded-full bg-[var(--surface-alt)] px-3 py-1 text-[var(--muted-strong)]">
          Available: {availability.available_count}
        </span>
        <span className="rounded-full bg-[rgba(165,72,54,0.12)] px-3 py-1 text-[var(--danger-ink)]">
          Out: {availability.unavailable_count}
        </span>
        <span className="rounded-full bg-[rgba(181,145,78,0.14)] px-3 py-1 text-[var(--foreground)]">
          Questionable: {availability.questionable_count}
        </span>
        <span className="rounded-full bg-[rgba(33,72,59,0.08)] px-3 py-1 text-[var(--accent-strong)]">
          Probable: {availability.probable_count}
        </span>
      </div>

      <div className="mt-4 rounded-2xl border border-[var(--border)] bg-[rgba(216,228,221,0.22)] px-4 py-3">
        <div className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
          Next game
        </div>
        <div className="mt-2 text-sm leading-6 text-[var(--foreground)]">
          {nextGame ? (
            <>
              {nextGame.is_home ? "vs" : "at"} {nextGame.opponent_abbreviation ?? nextGame.opponent_name ?? "Opponent TBD"} · {formatDate(nextGame.game_date)} · {nextGame.status}
            </>
          ) : (
            "No upcoming game is currently on the synced schedule."
          )}
        </div>
      </div>

      <div className={`mt-5 grid gap-4 ${compact ? "md:grid-cols-2" : "xl:grid-cols-3"}`}>
        <PlayerSection
          label="Out"
          players={availability.unavailable_players}
          emptyLabel="No current outs."
          compact={compact}
        />
        <PlayerSection
          label="Questionable"
          players={availability.questionable_players}
          emptyLabel="No questionable or doubtful players."
          compact={compact}
        />
        {!compact && (
          <PlayerSection
            label="Probable"
            players={availability.probable_players}
            emptyLabel="No probable tags."
            compact={compact}
          />
        )}
      </div>
    </article>
  );
}
