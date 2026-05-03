"use client";

import useSWR from "swr";
import { getTeamHustle } from "@/lib/api";
import type { TeamHustleResponse, TeamHustleStats } from "@/lib/types";

interface Props {
  teamAbbr: string;
  season: string;
  isPlayoff?: boolean;
}

interface StatTile {
  key: keyof TeamHustleStats;
  label: string;
  format: "int" | "float1";
}

const TILES: StatTile[] = [
  { key: "contested_shots", label: "Contested Shots", format: "int" },
  { key: "deflections", label: "Deflections", format: "int" },
  { key: "loose_balls_recovered", label: "Loose Balls", format: "int" },
  { key: "charges_drawn", label: "Charges Drawn", format: "int" },
  { key: "screen_assists", label: "Screen Assists", format: "int" },
  { key: "screen_assist_points", label: "Screen Ast Pts", format: "int" },
  { key: "box_outs", label: "Box Outs", format: "int" },
  { key: "gp", label: "GP", format: "int" },
];

function fmtCell(value: number | string | null, format: "int" | "float1"): string {
  if (value == null || value === "") return "—";
  if (typeof value === "string") return value;
  if (format === "int") return Math.round(value).toString();
  return value.toFixed(1);
}

function HustleSkeleton() {
  return (
    <div className="bip-panel-strong rounded-[2rem] p-6 animate-pulse space-y-4">
      <div className="h-4 w-32 rounded bg-[var(--surface-alt)]" />
      <div className="h-6 w-56 rounded bg-[var(--surface-alt)]" />
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-5">
        {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
          <div key={i} className="h-20 rounded-[1.2rem] bg-[var(--surface-alt)]" />
        ))}
      </div>
    </div>
  );
}

export default function TeamHustlePanel({ teamAbbr, season, isPlayoff = false }: Props) {
  const { data, isLoading, error } = useSWR<TeamHustleResponse>(
    teamAbbr && season ? `team-hustle-${teamAbbr}-${season}-${isPlayoff}` : null,
    () => getTeamHustle(teamAbbr, season, isPlayoff)
  );

  if (isLoading) return <HustleSkeleton />;

  if (error) {
    return (
      <div className="bip-panel rounded-[1.8rem] p-6 text-sm text-[var(--muted-strong)]">
        Hustle data unavailable for {season}.
      </div>
    );
  }

  const stats = data?.stats ?? null;
  if (!stats) {
    return (
      <div className="bip-panel rounded-[1.8rem] p-6 text-sm text-[var(--muted-strong)]">
        No hustle data available for {season}.
      </div>
    );
  }

  return (
    <section className="bip-panel-strong rounded-[2rem] p-6 space-y-5">
      <div>
        <p className="bip-kicker">Hustle</p>
        <h2
          className="bip-display mt-3 font-semibold text-[var(--foreground)]"
          style={{ fontSize: "1.6rem", lineHeight: 1.15, letterSpacing: "-0.02em" }}
        >
          Effort plays beyond the box score
        </h2>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-[var(--muted-strong)]">
          Official NBA hustle-stat aggregate for the {season} regular season. Totals across
          {stats.gp != null ? ` ${stats.gp} games` : ""}. Powered by{" "}
          <span className="font-medium">stats.nba.com</span>.
        </p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {TILES.map((tile) => (
          <div
            key={tile.key as string}
            className="rounded-[1.2rem] bg-[var(--surface-alt)] p-4 flex flex-col justify-between"
          >
            <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
              {tile.label}
            </p>
            <p className="mt-2 text-2xl font-semibold tabular-nums text-[var(--foreground)]">
              {fmtCell(stats[tile.key] as number | string | null, tile.format)}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
