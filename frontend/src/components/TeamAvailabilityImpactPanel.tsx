"use client";

/**
 * TeamAvailabilityImpactPanel — Sprint 78 FO5
 *
 * Mounts on the team page roster tab below the existing
 * AvailabilitySummaryCard. Shows the projected net-rating swing and
 * rotation re-organization implied by the team's currently-sidelined
 * players.
 */

import { useState } from "react";
import useSWR from "swr";

import { getTeamAvailabilityImpact } from "@/lib/api";
import type {
  PlayerAvailabilityProjection,
  RotationReplacement,
  TeamAvailabilityImpact,
} from "@/lib/types";

interface Props {
  teamAbbreviation: string;
  season: string;
}

function formatPts(value: number | null | undefined): string {
  if (value == null) return "—";
  return value.toFixed(1);
}

function formatNetRatingDelta(value: number | null | undefined): string {
  if (value == null) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}`;
}

function tagToneForDelta(value: number | null | undefined): string {
  if (value == null) return "text-[var(--muted)]";
  if (value > 0.5) return "text-[var(--success-ink)]";
  if (value < -0.5) return "text-[var(--danger-ink)]";
  return "text-[var(--muted)]";
}

function durationLabel(player: PlayerAvailabilityProjection): string | null {
  const est = player.expected_duration;
  if (!est) return null;
  if (est.is_fallback) {
    return `Prior: ~${est.median_games}g (${est.body_part})`;
  }
  return `Median ${est.median_games}g · IQR ${est.p25_games}–${est.p75_games}`;
}

function ReplacementRow({ rep }: { rep: RotationReplacement }) {
  return (
    <li className="rounded-2xl border border-[var(--border)] bg-[var(--surface-alt)] px-4 py-3 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="font-semibold text-[var(--foreground)]">
            {rep.out_player_name}
            <span className="text-[var(--muted)]"> → </span>
            {rep.replacement_player_name ?? "Distributed across roster"}
          </div>
          <div className="text-xs text-[var(--muted)]">{rep.note}</div>
        </div>
        {rep.additional_minutes ? (
          <span className="rounded-full bg-[var(--surface)] px-3 py-1 text-xs font-semibold text-[var(--foreground)]">
            +{rep.additional_minutes.toFixed(1)} mpg
          </span>
        ) : null}
      </div>
    </li>
  );
}

export default function TeamAvailabilityImpactPanel({
  teamAbbreviation,
  season,
}: Props) {
  const [methodologyOpen, setMethodologyOpen] = useState(false);
  const { data, isLoading, error } = useSWR<TeamAvailabilityImpact>(
    teamAbbreviation && season ? ["team-availability-impact", teamAbbreviation, season] : null,
    () => getTeamAvailabilityImpact(teamAbbreviation, season)
  );

  if (isLoading) {
    return (
      <section className="rounded-[1.8rem] border border-[var(--border)] bg-[var(--surface)] p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-4 w-48 rounded bg-[var(--surface-alt)]" />
          <div className="h-8 w-72 rounded bg-[var(--surface-alt)]" />
          <div className="grid gap-3 md:grid-cols-3">
            <div className="h-24 rounded-2xl bg-[var(--surface-alt)]" />
            <div className="h-24 rounded-2xl bg-[var(--surface-alt)]" />
            <div className="h-24 rounded-2xl bg-[var(--surface-alt)]" />
          </div>
        </div>
      </section>
    );
  }

  if (error || !data) return null;

  if (data.out_count === 0 && data.questionable_count === 0) {
    return (
      <section className="rounded-[1.8rem] border border-[var(--border)] bg-[var(--surface)] p-6 text-sm text-[var(--muted-strong)]">
        Full availability — no rotation impact projection needed for {data.abbreviation}.
      </section>
    );
  }

  return (
    <section className="rounded-[1.8rem] border border-[var(--border)] bg-[var(--surface)] p-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="bip-kicker">Availability impact</p>
          <h3 className="bip-display mt-2 text-2xl font-semibold text-[var(--foreground)]">
            Projected rotation under current absences
          </h3>
          <p className="mt-1 text-sm text-[var(--muted)]">{data.summary}</p>
        </div>
        <button
          type="button"
          onClick={() => setMethodologyOpen((open) => !open)}
          className="bip-btn-secondary inline-flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold"
          aria-label="Methodology"
          aria-expanded={methodologyOpen}
        >
          ⓘ
        </button>
      </div>

      {methodologyOpen ? (
        <div className="mt-4 rounded-2xl border border-dashed border-[var(--border)] bg-[var(--surface-alt)] p-4 text-xs leading-5 text-[var(--muted-strong)]">
          <p className="font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Methodology
          </p>
          <p className="mt-2">
            Net-rating delta sums each sidelined player&apos;s on/off swing
            weighted by their share of the team&apos;s 240-minute game budget.
            The healthy net rating comes from the official team season
            dashboard. Duration estimates per player are pulled from the
            historical injury cohort and fall back to a hardcoded prior on
            small samples.
          </p>
          <p className="mt-2">
            Replacement assignment greedily picks the highest-impact
            available roster player (by season pts/bpm) for each absence —
            it&apos;s a directional cue, not a coach&apos;s rotation plan.
          </p>
        </div>
      ) : null}

      <div className="mt-5 grid gap-3 md:grid-cols-3">
        <div className="rounded-2xl bip-metric p-4">
          <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
            Net-rating delta
          </div>
          <div
            className={`mt-2 text-3xl font-bold tabular-nums ${tagToneForDelta(
              data.net_rating_delta
            )}`}
          >
            {formatNetRatingDelta(data.net_rating_delta)}
          </div>
          <div className="mt-1 text-xs text-[var(--muted)]">
            {data.healthy_net_rating != null
              ? `Healthy ${formatPts(data.healthy_net_rating)} → projected ${formatPts(
                  data.projected_net_rating
                )}`
              : "Healthy baseline unavailable"}
          </div>
        </div>
        <div className="rounded-2xl bip-metric p-4">
          <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
            Sidelined load
          </div>
          <div className="mt-2 text-3xl font-bold tabular-nums text-[var(--foreground)]">
            {data.sidelined_minutes_per_game.toFixed(0)} mpg
          </div>
          <div className="mt-1 text-xs text-[var(--muted)]">
            {data.sidelined_pts_per_game.toFixed(1)} ppg removed from rotation
          </div>
        </div>
        <div className="rounded-2xl bip-metric p-4">
          <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
            Status counts
          </div>
          <div className="mt-2 text-3xl font-bold tabular-nums text-[var(--foreground)]">
            {data.out_count} <span className="text-base font-normal text-[var(--muted)]">out</span>
          </div>
          <div className="mt-1 text-xs text-[var(--muted)]">
            {data.questionable_count} questionable / GTD
          </div>
        </div>
      </div>

      {data.sidelined_players.length > 0 ? (
        <div className="mt-6">
          <h4 className="text-sm font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Sidelined players
          </h4>
          <ul className="mt-3 space-y-2">
            {data.sidelined_players.map((player) => (
              <li
                key={player.player_id}
                className="rounded-2xl border border-[var(--border)] bg-[var(--surface-alt)] px-4 py-3 text-sm"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <div className="font-semibold text-[var(--foreground)]">
                      {player.player_name}{" "}
                      <span className="text-xs text-[var(--muted)]">
                        · {player.position || "—"} · {player.injury_status}
                      </span>
                    </div>
                    <div className="text-xs text-[var(--muted)]">
                      {player.detail || player.injury_type || "Injury detail unavailable"}
                      {durationLabel(player) ? ` · ${durationLabel(player)}` : ""}
                    </div>
                  </div>
                  <div className="text-right text-xs text-[var(--muted)]">
                    {player.season_pts_pg != null ? (
                      <div>
                        {formatPts(player.season_pts_pg)} ppg ·{" "}
                        {player.season_min_pg != null
                          ? `${formatPts(player.season_min_pg)} mpg`
                          : ""}
                      </div>
                    ) : null}
                    {player.on_off_net != null ? (
                      <div className="tabular-nums">
                        on/off {formatNetRatingDelta(player.on_off_net)}
                      </div>
                    ) : null}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {data.rotation_replacements.length > 0 ? (
        <div className="mt-6">
          <h4 className="text-sm font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Rotation replacements
          </h4>
          <ul className="mt-3 space-y-2">
            {data.rotation_replacements.map((rep) => (
              <ReplacementRow
                key={`${rep.out_player_id}-${rep.replacement_player_id ?? "none"}`}
                rep={rep}
              />
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
