"use client";

import { useState, useMemo } from "react";
import Image from "next/image";
import type { PlayerProfile, CareerStatsResponse, SeasonStats, PlayerAvailabilitySlot } from "@/lib/types";
import { usePlayerPercentiles } from "@/hooks/usePlayerStats";
import DualCareerArcChart from "./DualCareerArcChart";
import InjuryStatusBadge from "./InjuryStatusBadge";

interface PlayerData {
  profile: PlayerProfile;
  career: CareerStatsResponse;
}

interface ComparisonViewProps {
  playerA: PlayerData;
  playerB: PlayerData;
  availabilityA?: PlayerAvailabilitySlot | null;
  availabilityB?: PlayerAvailabilitySlot | null;
}

type ViewMode = "career" | "current" | "percentile" | "arc";

// ─── Stat row definitions ─────────────────────────────────────────────────────

interface StatRow {
  key: keyof SeasonStats;
  label: string;
  higherBetter: boolean;
  pct?: boolean;
  decimals?: number;
}

const TRADITIONAL_ROWS: StatRow[] = [
  { key: "pts_pg",  label: "Points Per Game",   higherBetter: true  },
  { key: "reb_pg",  label: "Rebounds Per Game",  higherBetter: true  },
  { key: "ast_pg",  label: "Assists Per Game",   higherBetter: true  },
  { key: "stl_pg",  label: "Steals Per Game",    higherBetter: true  },
  { key: "blk_pg",  label: "Blocks Per Game",    higherBetter: true  },
  { key: "tov_pg",  label: "Turnovers Per Game", higherBetter: false },
  { key: "min_pg",  label: "Minutes Per Game",   higherBetter: true  },
  { key: "fg_pct",  label: "FG%",                higherBetter: true,  pct: true },
  { key: "fg3_pct", label: "3P%",                higherBetter: true,  pct: true },
  { key: "ft_pct",  label: "FT%",                higherBetter: true,  pct: true },
  { key: "gp",      label: "Games Played",       higherBetter: true  },
];

const ADVANCED_ROWS: StatRow[] = [
  { key: "per",         label: "PER",             higherBetter: true              },
  { key: "bpm",         label: "BPM",             higherBetter: true              },
  { key: "ws",          label: "Win Shares",      higherBetter: true              },
  { key: "vorp",        label: "VORP",            higherBetter: true              },
  { key: "ts_pct",      label: "TS%",             higherBetter: true,  pct: true  },
  { key: "efg_pct",     label: "eFG%",            higherBetter: true,  pct: true  },
  { key: "usg_pct",     label: "USG%",            higherBetter: false             },
  { key: "off_rating",  label: "Offensive Rating", higherBetter: true             },
  { key: "def_rating",  label: "Defensive Rating", higherBetter: false            },
  { key: "net_rating",  label: "Net Rating",      higherBetter: true              },
  { key: "pie",         label: "PIE",             higherBetter: true,  pct: true  },
  { key: "darko",       label: "DARKO",           higherBetter: true,  decimals: 2},
  { key: "epm",         label: "EPM*",            higherBetter: true              },
  { key: "raptor",      label: "RAPTOR*",         higherBetter: true              },
  { key: "pipm",        label: "PIPM*",           higherBetter: true              },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatVal(val: number | null | undefined, row: StatRow): string {
  if (val == null) return "—";
  const v = row.pct ? val * 100 : val;
  const d = row.decimals ?? 1;
  return row.pct ? `${v.toFixed(d)}%` : v.toFixed(d);
}

function winner(
  valA: number | null | undefined,
  valB: number | null | undefined,
  higherBetter: boolean
): "A" | "B" | null {
  if (valA == null || valB == null) return null;
  if (valA === valB) return null;
  return higherBetter ? (valA > valB ? "A" : "B") : (valA < valB ? "A" : "B");
}

function pctileColor(pct: number): string {
  if (pct >= 80) return "#10b981"; // emerald
  if (pct >= 60) return "#21483b"; // forest
  if (pct >= 40) return "#b4893d"; // brass
  return "#ef4444";                // red
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function PlayerAvatar({
  profile,
  align,
  availability,
}: {
  profile: PlayerProfile;
  align: "left" | "right";
  availability?: PlayerAvailabilitySlot | null;
}) {
  return (
    <div className={`flex items-center gap-3 ${align === "right" ? "flex-row-reverse text-right" : ""}`}>
      <div className="relative h-16 w-16 shrink-0 overflow-hidden rounded-full border-2 border-[var(--border)] bg-[var(--surface-alt)]">
        {profile.headshot_url ? (
          <Image
            src={profile.headshot_url}
            alt={profile.full_name}
            fill
            className="object-cover object-top"
            onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
          />
        ) : null}
      </div>
      <div>
        <div className="leading-tight font-bold text-[var(--foreground)]">{profile.full_name}</div>
        <div className="mt-0.5 text-xs text-[var(--muted)]">
          {profile.team_name || "Free Agent"} · {profile.position || "—"}
        </div>
        {availability ? (
          <div className={`mt-1 ${align === "right" ? "flex justify-end" : ""}`}>
            <InjuryStatusBadge availability={availability} />
          </div>
        ) : null}
      </div>
    </div>
  );
}

function StatRowItem({
  row,
  statsA,
  statsB,
}: {
  row: StatRow;
  statsA: SeasonStats | null;
  statsB: SeasonStats | null;
}) {
  const valA = statsA ? (statsA[row.key] as number | null) : null;
  const valB = statsB ? (statsB[row.key] as number | null) : null;
  const w = winner(valA, valB, row.higherBetter);

  return (
    <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 border-b border-[var(--border)] py-2 last:border-0">
      <span
        className={`text-right font-semibold tabular-nums text-lg ${
          w === "A"
            ? "text-[var(--accent)]"
            : w === "B"
            ? "text-[var(--muted)]"
            : "text-[var(--foreground)]"
        }`}
      >
        {formatVal(valA, row)}
      </span>
      <span className="min-w-[120px] whitespace-nowrap px-2 text-center text-xs text-[var(--muted)]">
        {row.label}
      </span>
      <span
        className={`text-left font-semibold tabular-nums text-lg ${
          w === "B"
            ? "text-[var(--accent)]"
            : w === "A"
            ? "text-[var(--muted)]"
            : "text-[var(--foreground)]"
        }`}
      >
        {formatVal(valB, row)}
      </span>
    </div>
  );
}

function PercentileRowItem({
  row,
  pctA,
  pctB,
  statsA,
  statsB,
}: {
  row: StatRow;
  pctA: number | null;
  pctB: number | null;
  statsA: SeasonStats | null;
  statsB: SeasonStats | null;
}) {
  const valA = statsA ? (statsA[row.key] as number | null) : null;
  const valB = statsB ? (statsB[row.key] as number | null) : null;
  const hasPctA = pctA != null;
  const hasPctB = pctB != null;

  return (
    <div className="border-b border-[var(--border)] py-2.5 last:border-0">
      <div className="mb-1.5 text-center text-xs text-[var(--muted)]">{row.label}</div>
      <div className="space-y-1">
        {/* Player A bar */}
        <div className="flex items-center gap-2">
          <div className="relative h-5 flex-1 overflow-hidden rounded-full bg-[var(--surface-alt)]">
            {hasPctA && (
              <div
                className="h-full rounded-full transition-all"
                style={{ width: `${pctA}%`, backgroundColor: pctileColor(pctA) }}
              />
            )}
          </div>
          <span className="w-28 shrink-0 text-right text-xs tabular-nums text-[var(--muted)]">
            {hasPctA
              ? <span style={{ color: pctileColor(pctA!) }}>{Math.round(pctA!)}th pct</span>
              : null}{" "}
            <span className="text-[var(--muted)]">{formatVal(valA, row)}</span>
          </span>
        </div>
        {/* Player B bar */}
        <div className="flex items-center gap-2">
          <div className="relative h-5 flex-1 overflow-hidden rounded-full bg-[var(--surface-alt)]">
            {hasPctB && (
              <div
                className="h-full rounded-full transition-all"
                style={{ width: `${pctB}%`, backgroundColor: pctileColor(pctB) }}
              />
            )}
          </div>
          <span className="w-28 shrink-0 text-right text-xs tabular-nums text-[var(--muted)]">
            {hasPctB
              ? <span style={{ color: pctileColor(pctB!) }}>{Math.round(pctB!)}th pct</span>
              : null}{" "}
            <span className="text-[var(--muted)]">{formatVal(valB, row)}</span>
          </span>
        </div>
      </div>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function ComparisonView({ playerA, playerB, availabilityA, availabilityB }: ComparisonViewProps) {
  const [mode, setMode] = useState<ViewMode>("career");
  const [selectedSeason, setSelectedSeason] = useState<string>("");

  const availableSeasons = useMemo(() => {
    const all = new Set<string>();
    playerA.career.seasons.forEach((s) => all.add(s.season));
    playerB.career.seasons.forEach((s) => all.add(s.season));
    return Array.from(all).sort((a, b) => b.localeCompare(a));
  }, [playerA.career.seasons, playerB.career.seasons]);

  const effectiveCurrentSeason = selectedSeason || availableSeasons[0] || null;

  // For percentile context, always use the most recent season each player has
  const currentSeasonA = playerA.career.seasons[playerA.career.seasons.length - 1]?.season ?? null;
  const currentSeasonB = playerB.career.seasons[playerB.career.seasons.length - 1]?.season ?? null;

  const statsA: SeasonStats | null =
    mode === "career"
      ? playerA.career.career_totals
      : mode === "current"
      ? playerA.career.seasons.find((s) => s.season === effectiveCurrentSeason) ?? null
      : playerA.career.seasons[playerA.career.seasons.length - 1] ?? null;

  const statsB: SeasonStats | null =
    mode === "career"
      ? playerB.career.career_totals
      : mode === "current"
      ? playerB.career.seasons.find((s) => s.season === effectiveCurrentSeason) ?? null
      : playerB.career.seasons[playerB.career.seasons.length - 1] ?? null;
  // Use the more recent season for percentile context
  const pctSeason = currentSeasonA && currentSeasonB
    ? currentSeasonA >= currentSeasonB ? currentSeasonA : currentSeasonB
    : currentSeasonA ?? currentSeasonB;

  const { data: percA } = usePlayerPercentiles(
    mode === "percentile" ? playerA.profile.id : null,
    mode === "percentile" ? pctSeason : null
  );
  const { data: percB } = usePlayerPercentiles(
    mode === "percentile" ? playerB.profile.id : null,
    mode === "percentile" ? pctSeason : null
  );

  const pctStatsA = mode === "percentile"
    ? (playerA.career.seasons[playerA.career.seasons.length - 1] ?? null)
    : statsA;
  const pctStatsB = mode === "percentile"
    ? (playerB.career.seasons[playerB.career.seasons.length - 1] ?? null)
    : statsB;

  const seasonLabelA = mode === "career" ? "Career" : mode === "percentile" ? (currentSeasonA ?? "—") : (statsA?.season ?? "—");
  const seasonLabelB = mode === "career" ? "Career" : mode === "percentile" ? (currentSeasonB ?? "—") : (statsB?.season ?? "—");

  const getPct = (percs: typeof percA, key: string): number | null => {
    if (!percs) return null;
    const v = percs.percentiles[key];
    return v != null ? Math.round(v) : null;
  };

  return (
    <div className="space-y-6">
      {/* Player headers */}
      <div className="grid grid-cols-2 gap-4">
        <PlayerAvatar profile={playerA.profile} align="left" availability={availabilityA} />
        <PlayerAvatar profile={playerB.profile} align="right" availability={availabilityB} />
      </div>

      {/* Availability warning banner */}
      {(availabilityA || availabilityB) ? (
        <div className="rounded-xl border border-[rgba(234,179,8,0.25)] bg-[rgba(234,179,8,0.06)] px-4 py-3 text-sm text-[var(--foreground)]">
          <span className="font-medium text-[#ca8a04]">Availability note · </span>
          {availabilityA && availabilityB
            ? `${playerA.profile.full_name} and ${playerB.profile.full_name} are both currently listed as injured. Stats shown may not reflect current form.`
            : availabilityA
            ? `${playerA.profile.full_name} is currently listed as ${availabilityA.injury_status}${availabilityA.injury_type ? ` (${availabilityA.injury_type})` : ""}. Stats shown may not reflect current form.`
            : `${playerB.profile.full_name} is currently listed as ${availabilityB!.injury_status}${availabilityB?.injury_type ? ` (${availabilityB.injury_type})` : ""}. Stats shown may not reflect current form.`}
        </div>
      ) : null}

      {/* Mode toggle + season labels */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <span className="min-w-0 text-xs text-[var(--muted)]">{seasonLabelA}</span>
        <div className="flex shrink-0 overflow-hidden rounded-lg border border-[var(--border)] text-xs">
          {([
            { id: "career", label: "Career" },
            { id: "current", label: "Season" },
            { id: "percentile", label: "Percentile" },
            { id: "arc", label: "Arc" },
          ] as { id: ViewMode; label: string }[]).map((m) => (
            <button
              key={m.id}
              onClick={() => setMode(m.id)}
              className={`px-3 py-1.5 transition-colors ${
                mode === m.id
                  ? "bip-toggle-active"
                  : "bip-toggle"
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>
        <span className="min-w-0 text-right text-xs text-[var(--muted)]">{seasonLabelB}</span>
      </div>

      {/* Season selector (current mode only) */}
      {mode === "current" && availableSeasons.length > 1 && (
        <div className="flex justify-center">
          <select
            value={effectiveCurrentSeason ?? ""}
            onChange={(e) => setSelectedSeason(e.target.value)}
            className="bip-input rounded-lg px-3 py-1.5 text-xs"
          >
            {availableSeasons.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
      )}

      {/* Percentile mode */}
      {mode === "percentile" && (
        <>
          {/* Legend */}
          <div className="flex flex-wrap items-center gap-4 text-xs text-[var(--muted)]">
            <div className="flex items-center gap-1.5">
              <div className="h-2 w-12 overflow-hidden rounded-full bg-[var(--surface-alt)]">
                <div className="h-full w-1/2 rounded-full" style={{ backgroundColor: "#21483b" }} />
              </div>
              <span>{playerA.profile.full_name} (top bar)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="h-2 w-12 overflow-hidden rounded-full bg-[var(--surface-alt)]">
                <div className="h-full w-1/2 rounded-full" style={{ backgroundColor: "#b4893d" }} />
              </div>
              <span>{playerB.profile.full_name} (bottom bar)</span>
            </div>
            <div className="flex items-center gap-3 ml-auto">
              {[["≥80th", "#10b981"], ["60–79th", "#21483b"], ["40–59th", "#b4893d"], ["<40th", "#ef4444"]].map(([label, color]) => (
                <span key={label} className="flex items-center gap-1">
                  <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ backgroundColor: color }} />
                  {label}
                </span>
              ))}
            </div>
          </div>

          <div className="bip-panel rounded-2xl p-4">
            <h4 className="bip-kicker mb-3 text-xs">
              Traditional — {pctSeason}
            </h4>
            {TRADITIONAL_ROWS.filter(r => !["gp", "min_pg"].includes(r.key as string)).map((row) => (
              <PercentileRowItem
                key={row.key}
                row={row}
                pctA={getPct(percA, row.key as string)}
                pctB={getPct(percB, row.key as string)}
                statsA={pctStatsA}
                statsB={pctStatsB}
              />
            ))}
          </div>

          <div className="bip-panel rounded-2xl p-4">
            <h4 className="bip-kicker mb-3 text-xs">
              Advanced — {pctSeason}
            </h4>
            {ADVANCED_ROWS.filter(r => !["darko"].includes(r.key as string)).map((row) => (
              <PercentileRowItem
                key={row.key}
                row={row}
                pctA={getPct(percA, row.key as string)}
                pctB={getPct(percB, row.key as string)}
                statsA={pctStatsA}
                statsB={pctStatsB}
              />
            ))}
          </div>

          <p className="text-center text-xs text-[var(--muted)]">
            Percentiles computed among all players with ≥20 GP in {pctSeason}
          </p>
        </>
      )}

      {/* Arc mode */}
      {mode === "arc" && (
        <DualCareerArcChart
          playerA={{ name: playerA.profile.full_name, seasons: playerA.career.seasons, birthDate: playerA.profile.birth_date }}
          playerB={{ name: playerB.profile.full_name, seasons: playerB.career.seasons, birthDate: playerB.profile.birth_date }}
        />
      )}

      {/* Career / Current Season mode */}
      {mode !== "percentile" && mode !== "arc" && (
        <>
          <div className="bip-panel rounded-2xl p-4">
            <h4 className="bip-kicker mb-3 text-xs">
              Traditional
            </h4>
            {TRADITIONAL_ROWS.map((row) => (
              <StatRowItem key={row.key} row={row} statsA={statsA} statsB={statsB} />
            ))}
          </div>

          <div className="bip-panel rounded-2xl p-4">
            <h4 className="bip-kicker mb-3 text-xs">
              Advanced
            </h4>
            {ADVANCED_ROWS.map((row) => (
              <StatRowItem key={row.key} row={row} statsA={statsA} statsB={statsB} />
            ))}
          </div>

          <p className="text-center text-xs text-[var(--accent)]">
            Forest = better value
          </p>
          <p className="text-center text-xs text-[var(--muted)]">
            * External metric — not platform-original (EPM: Dunks & Threes · RAPTOR: FiveThirtyEight · PIPM: Basketball Index)
          </p>
        </>
      )}
    </div>
  );
}
