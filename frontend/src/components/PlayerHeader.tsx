"use client";

import Image from "next/image";
import useSWR from "swr";
import type { PlayerProfile, SeasonStats } from "@/lib/types";
import { getPlayerInjuries } from "@/lib/api";
import StatCard from "./StatCard";
import { usePlayerPercentiles, useLeagueContext } from "@/hooks/usePlayerStats";
import { useFavorites } from "@/hooks/useFavorites";

interface PlayerHeaderProps {
  profile: PlayerProfile;
  currentSeason?: SeasonStats | null;
  priorSeason?: SeasonStats | null;
}

const PERCENTILE_LABELS: Record<string, string> = {
  pts_pg: "PPG",
  reb_pg: "RPG",
  ast_pg: "APG",
  ts_pct: "TS%",
  per: "PER",
  bpm: "BPM",
};

function pctColor(pct: number): string {
  if (pct >= 90) return "bip-success";
  if (pct >= 75) return "bg-[var(--accent-soft)] text-[var(--accent-strong)]";
  if (pct >= 50) return "bg-[var(--surface-alt)] text-[var(--muted)]";
  return "bip-danger";
}

function ordinal(n: number): string {
  if (n >= 11 && n <= 13) return `${n}th`;
  const s = ["th", "st", "nd", "rd"];
  return `${n}${s[n % 10] ?? "th"}`;
}

function deltaLabel(value: number, median: number): { text: string; cls: string } {
  const pct = median > 0 ? ((value - median) / median) * 100 : 0;
  const sign = pct >= 0 ? "+" : "";
  const text = `${sign}${pct.toFixed(0)}%`;
  if (pct >= 10) return { text, cls: "text-emerald-600 dark:text-emerald-400" };
  if (pct <= -10) return { text, cls: "text-red-500 dark:text-red-400" };
  return { text, cls: "text-gray-400 dark:text-gray-500" };
}

interface ContextRowProps {
  label: string;
  value: number;
  leagueMedian: number | null;
  posMedian: number | null;
  posGroup: string | null;
}

function ContextRow({ label, value, leagueMedian, posMedian, posGroup }: ContextRowProps) {
  if (leagueMedian == null) return null;
  const league = deltaLabel(value, leagueMedian);
  const pos = posMedian != null ? deltaLabel(value, posMedian) : null;
  return (
    <div className="text-xs text-gray-500 dark:text-gray-400 text-center">
      <span className="font-medium text-gray-700 dark:text-gray-300">{label}</span>
      <span className="mx-1 text-gray-300 dark:text-gray-600">·</span>
      <span className={league.cls}>Lg {league.text}</span>
      {pos && posGroup && (
        <>
          <span className="mx-1 text-gray-300 dark:text-gray-600">·</span>
          <span className={pos.cls}>{posGroup} {pos.text}</span>
        </>
      )}
    </div>
  );
}

export default function PlayerHeader({
  profile,
  currentSeason,
  priorSeason,
}: PlayerHeaderProps) {
  const { data: pctData } = usePlayerPercentiles(
    profile.id,
    currentSeason?.season ?? null
  );

  const { data: context } = useLeagueContext(
    currentSeason?.season ?? null,
    profile.position ?? undefined
  );

  const { isFavorite, toggleFavorite } = useFavorites();
  const starred = isFavorite(profile.id);

  const { data: injuryData } = useSWR(
    `injuries-${profile.id}`,
    () => getPlayerInjuries(profile.id)
  );
  const latestInjury = injuryData?.entries?.[0] ?? null;
  const showInjuryBadge =
    latestInjury?.injury_status === "Out" ||
    latestInjury?.injury_status === "Questionable" ||
    latestInjury?.injury_status === "Doubtful";

  const draftInfo =
    profile.draft_year && profile.draft_year !== "Undrafted"
      ? `${profile.draft_year} Round ${profile.draft_round}, Pick ${profile.draft_number}`
      : "Undrafted";

  const trendCards =
    currentSeason && priorSeason
      ? [
          {
            label: "PPG YoY",
            delta: currentSeason.pts_pg - priorSeason.pts_pg,
            value: currentSeason.pts_pg,
          },
          {
            label: "TS% YoY",
            delta:
              currentSeason.ts_pct != null && priorSeason.ts_pct != null
                ? currentSeason.ts_pct - priorSeason.ts_pct
                : null,
            value: currentSeason.ts_pct != null ? currentSeason.ts_pct * 100 : null,
            pct: true,
          },
          {
            label: "BPM YoY",
            delta:
              currentSeason.bpm != null && priorSeason.bpm != null
                ? currentSeason.bpm - priorSeason.bpm
                : null,
            value: currentSeason.bpm,
          },
        ]
      : [];

  return (
    <div className="bip-panel-strong rounded-[2rem] p-6 mb-6">
      <div className="flex flex-col gap-6">
        {trendCards.length > 0 && (
          <div className="grid gap-3 md:grid-cols-3">
            {trendCards.map((card) => {
              const delta = card.delta;
              const positive = delta != null ? delta >= 0 : null;
              return (
                <div
                  key={card.label}
                  className="rounded-2xl bip-metric p-4"
                >
                  <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                    {card.label}
                  </div>
                  <div className="mt-2 flex items-end justify-between gap-3">
                    <div className="text-2xl font-bold tabular-nums text-[var(--foreground)]">
                      {card.value == null
                        ? "—"
                        : card.pct
                        ? `${card.value.toFixed(1)}%`
                        : card.value.toFixed(1)}
                    </div>
                    <div
                      className={`text-sm font-semibold tabular-nums ${
                        delta == null
                          ? "text-[var(--muted)]"
                          : positive
                          ? "text-[var(--success-ink)]"
                          : "text-[var(--danger-ink)]"
                      }`}
                    >
                      {delta == null
                        ? "No prior season"
                        : `${positive ? "+" : ""}${card.pct ? (delta * 100).toFixed(1) : delta.toFixed(1)}`}
                    </div>
                  </div>
                  <div className="mt-1 text-xs text-[var(--muted)]">
                    vs {priorSeason?.season}
                  </div>
                </div>
              );
            })}
          </div>
        )}

      <div className="flex flex-col md:flex-row gap-6">
        {/* Headshot */}
        <div className="flex-shrink-0">
          <div className="relative w-40 h-40 rounded-2xl overflow-hidden bg-gray-100 dark:bg-gray-700">
            <Image
              src={
                profile.headshot_url ||
                "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect fill='%23374151' width='100' height='100'/%3E%3Ctext x='50' y='55' text-anchor='middle' fill='%239CA3AF' font-size='40'%3E%3F%3C/text%3E%3C/svg%3E"
              }
              alt={profile.full_name}
              fill
              className="object-cover"
              unoptimized
            />
          </div>
        </div>

        {/* Bio */}
        <div className="flex-grow">
          <div className="flex items-center gap-3 mb-2">
            <h1 className="bip-display text-4xl font-bold text-[var(--foreground)]">{profile.full_name}</h1>
            {profile.jersey && (
              <span className="text-2xl text-[var(--muted)]">#{profile.jersey}</span>
            )}
            {showInjuryBadge && latestInjury && (
              <span
                title={latestInjury.detail || latestInjury.injury_type || ""}
                className={`px-2 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wide ${
                  latestInjury.injury_status === "Out"
                    ? "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400"
                    : "bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-400"
                }`}
              >
                {latestInjury.injury_status}
              </span>
            )}
            {/* Star / watchlist button */}
            <button
              onClick={() =>
                toggleFavorite({
                  id: profile.id,
                  name: profile.full_name,
                  team: profile.team_abbreviation ?? profile.team_name ?? "",
                  headshot_url: profile.headshot_url ?? null,
                })
              }
              title={starred ? "Remove from My Players" : "Add to My Players"}
              className={`ml-1 transition-colors ${
                starred
                  ? "text-[var(--signal)] hover:text-[var(--signal-ink)]"
                  : "text-[var(--muted)] hover:text-[var(--signal)]"
              }`}
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill={starred ? "currentColor" : "none"}
                stroke="currentColor"
                strokeWidth={1.8}
                className="w-6 h-6"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M11.48 3.499a.562.562 0 0 1 1.04 0l2.125 5.111a.563.563 0 0 0 .475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 0 0-.182.557l1.285 5.385a.562.562 0 0 1-.84.61l-4.725-2.885a.562.562 0 0 0-.586 0L6.982 20.54a.562.562 0 0 1-.84-.61l1.285-5.386a.562.562 0 0 0-.182-.557l-4.204-3.602a.562.562 0 0 1 .321-.988l5.518-.442a.563.563 0 0 0 .475-.345L11.48 3.5Z"
                />
              </svg>
            </button>
          </div>

          <div className="flex flex-wrap gap-2 mb-4">
            <span className="px-3 py-1 rounded-full text-sm font-medium bg-[var(--accent-soft)] text-[var(--accent-strong)]">
              {profile.team_name || "Free Agent"}
            </span>
            {profile.position && (
              <span className="px-3 py-1 rounded-full text-sm bg-[var(--surface-alt)] text-[var(--muted)]">
                {profile.position}
              </span>
            )}
          </div>

          {/* Percentile badges */}
          {pctData && (
            <div className="flex flex-wrap gap-1.5 mb-4">
              {Object.entries(PERCENTILE_LABELS).map(([stat, label]) => {
                const pct = pctData.percentiles[stat];
                if (pct == null) return null;
                return (
                  <span
                    key={stat}
                    title={`${label}: ${ordinal(pct)} percentile vs players in ${pctData.season}`}
                    className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${pctColor(pct)}`}
                  >
                    {label}
                    <span className="font-semibold">{ordinal(pct)}</span>
                  </span>
                );
              })}
            </div>
          )}

          <div className="grid grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-2 text-sm text-[var(--muted)]">
            <div>
              <span className="text-gray-400">Height:</span>{" "}
              <span className="text-foreground">{profile.height}</span>
            </div>
            <div>
              <span className="text-gray-400">Weight:</span>{" "}
              <span className="text-foreground">{profile.weight} lbs</span>
            </div>
            <div>
              <span className="text-gray-400">Country:</span>{" "}
              <span className="text-foreground">{profile.country}</span>
            </div>
            <div>
              <span className="text-gray-400">Draft:</span>{" "}
              <span className="text-foreground">{draftInfo}</span>
            </div>
          </div>
        </div>

        {/* Quick Stats + context */}
        {currentSeason && (
          <div className="flex flex-col gap-2 flex-shrink-0">
            <div className="grid grid-cols-3 gap-3">
              <StatCard label="PPG" value={currentSeason.pts_pg} />
              <StatCard label="RPG" value={currentSeason.reb_pg} />
              <StatCard label="APG" value={currentSeason.ast_pg} />
            </div>
            {/* League / position context rows */}
            {context && (
              <div className="space-y-0.5">
                <ContextRow
                  label="PPG"
                  value={currentSeason.pts_pg}
                  leagueMedian={context.league_medians["pts_pg"] ?? null}
                  posMedian={context.position_medians["pts_pg"] ?? null}
                  posGroup={context.position_group}
                />
                <ContextRow
                  label="RPG"
                  value={currentSeason.reb_pg}
                  leagueMedian={context.league_medians["reb_pg"] ?? null}
                  posMedian={context.position_medians["reb_pg"] ?? null}
                  posGroup={context.position_group}
                />
                <ContextRow
                  label="APG"
                  value={currentSeason.ast_pg}
                  leagueMedian={context.league_medians["ast_pg"] ?? null}
                  posMedian={context.position_medians["ast_pg"] ?? null}
                  posGroup={context.position_group}
                />
              </div>
            )}
          </div>
        )}
      </div>
      </div>
    </div>
  );
}
