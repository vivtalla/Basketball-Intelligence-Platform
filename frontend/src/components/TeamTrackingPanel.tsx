"use client";

import { useState } from "react";
import useSWR from "swr";
import { getTeamTracking } from "@/lib/api";
import type { TeamTrackingResponse, TeamTrackingRow } from "@/lib/types";

interface Props {
  teamAbbr: string;
  season: string;
  isPlayoff?: boolean;
}

const FAMILY_ORDER = ["Shot Creation", "Passing", "Shot Defense"];

const FAMILY_LABELS: Record<string, string> = {
  "Shot Creation": "Shot Creation",
  "Passing": "Passing",
  "Shot Defense": "Shot Defense",
};

const SHOT_CREATION_COLUMNS: Array<{
  key: keyof TeamTrackingRow;
  label: string;
  format?: "int" | "float1";
}> = [
  { key: "gp", label: "GP", format: "int" },
  { key: "touches", label: "Touches", format: "float1" },
  { key: "front_court_touches", label: "FC Touch", format: "float1" },
  { key: "drives", label: "Drives", format: "float1" },
  { key: "time_of_possession", label: "Time Poss", format: "float1" },
  { key: "paint_touch_pts", label: "Paint Pts", format: "float1" },
  { key: "close_touch_pts", label: "Close Pts", format: "float1" },
  { key: "pull_up_fga", label: "Pull-Up FGA", format: "float1" },
  { key: "pull_up_pts", label: "Pull-Up Pts", format: "float1" },
  { key: "catch_shoot_fga", label: "C&S FGA", format: "float1" },
  { key: "catch_shoot_pts", label: "C&S Pts", format: "float1" },
];

const PASSING_COLUMNS: Array<{
  key: keyof TeamTrackingRow;
  label: string;
  format?: "int" | "float1";
}> = [
  { key: "gp", label: "GP", format: "int" },
  { key: "passes_made", label: "Passes Made", format: "float1" },
  { key: "passes_received", label: "Passes Rcvd", format: "float1" },
];

const SHOT_DEFENSE_COLUMNS: Array<{
  key: keyof TeamTrackingRow;
  label: string;
  format?: "int" | "float1";
}> = [
  { key: "gp", label: "GP", format: "int" },
];

const COLUMNS_BY_FAMILY: Record<
  string,
  Array<{ key: keyof TeamTrackingRow; label: string; format?: "int" | "float1" }>
> = {
  "Shot Creation": SHOT_CREATION_COLUMNS,
  "Passing": PASSING_COLUMNS,
  "Shot Defense": SHOT_DEFENSE_COLUMNS,
};

function fmtCell(value: number | string | null, format?: "int" | "float1"): string {
  if (value == null || value === "") return "—";
  if (typeof value === "string") return value;
  if (format === "int") return Math.round(value).toString();
  return value.toFixed(1);
}

function safeSetItem(key: string, value: string): void {
  // Defensive — Sprint 83 A7 lesson: localStorage throws in private mode.
  try {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(key, value);
    }
  } catch {
    // ignore — best-effort persistence
  }
}

function safeGetItem(key: string): string | null {
  try {
    if (typeof window !== "undefined") {
      return window.localStorage.getItem(key);
    }
  } catch {
    return null;
  }
  return null;
}

function TrackingSkeleton() {
  return (
    <div className="bip-panel-strong rounded-[2rem] p-6 animate-pulse space-y-4">
      <div className="h-4 w-32 rounded bg-[var(--surface-alt)]" />
      <div className="h-6 w-56 rounded bg-[var(--surface-alt)]" />
      <div className="flex gap-2 mt-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-8 w-32 rounded-full bg-[var(--surface-alt)]" />
        ))}
      </div>
      <div className="space-y-2 mt-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-8 rounded bg-[var(--surface-alt)]" />
        ))}
      </div>
    </div>
  );
}

function TrackingTable({
  rows,
  columns,
}: {
  rows: TeamTrackingRow[];
  columns: Array<{ key: keyof TeamTrackingRow; label: string; format?: "int" | "float1" }>;
}) {
  const thCls =
    "py-2 px-3 text-right text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)] whitespace-nowrap";
  const tdCls =
    "py-2.5 px-3 text-right tabular-nums text-sm text-[var(--muted-strong)] whitespace-nowrap";
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--border)]">
            <th className={thCls + " text-left pr-4"}>Split</th>
            {columns.map((col) => (
              <th key={col.key as string} className={thCls}>
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--border)]">
          {rows.map((row, idx) => (
            <tr
              key={`${row.split_key}-${idx}`}
              className="hover:bg-[rgba(255,255,255,0.4)] transition-colors"
            >
              <td className="py-2.5 px-3 text-left text-sm font-medium text-[var(--foreground)] whitespace-nowrap pr-4">
                {row.split_key}
              </td>
              {columns.map((col) => (
                <td key={col.key as string} className={tdCls}>
                  {fmtCell(row[col.key] as number | string | null, col.format)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const FAMILY_PREF_KEY = "cv-team-tracking-family";

export default function TeamTrackingPanel({ teamAbbr, season, isPlayoff = false }: Props) {
  const { data, isLoading, error } = useSWR<TeamTrackingResponse>(
    teamAbbr && season ? `team-tracking-${teamAbbr}-${season}-${isPlayoff}` : null,
    () => getTeamTracking(teamAbbr, season, isPlayoff)
  );

  const [activeFamily, setActiveFamily] = useState<string>(
    () => safeGetItem(FAMILY_PREF_KEY) || ""
  );

  if (isLoading) return <TrackingSkeleton />;

  if (error) {
    return (
      <div className="bip-panel rounded-[1.8rem] p-6 text-sm text-[var(--muted-strong)]">
        Team tracking data unavailable for {season}.
      </div>
    );
  }

  const families = data?.families ?? {};
  const presentFamilies = FAMILY_ORDER.filter((f) => (families[f]?.length ?? 0) > 0);

  if (presentFamilies.length === 0) {
    return (
      <div className="bip-panel rounded-[1.8rem] p-6 text-sm text-[var(--muted-strong)]">
        No team-tracking data available for {season}.
      </div>
    );
  }

  const displayedFamily =
    activeFamily && presentFamilies.includes(activeFamily) ? activeFamily : presentFamilies[0];
  const rows = families[displayedFamily] ?? [];
  const columns = COLUMNS_BY_FAMILY[displayedFamily] ?? SHOT_CREATION_COLUMNS;

  const handleFamilyChange = (family: string) => {
    setActiveFamily(family);
    safeSetItem(FAMILY_PREF_KEY, family);
  };

  return (
    <div className="space-y-6">
      <section className="bip-panel-strong rounded-[2rem] p-6">
        <p className="bip-kicker">Team Tracking</p>
        <h2
          className="bip-display mt-3 font-semibold text-[var(--foreground)]"
          style={{ fontSize: "1.6rem", lineHeight: 1.15, letterSpacing: "-0.02em" }}
        >
          On-court motion, passing & defended shots
        </h2>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-[var(--muted-strong)]">
          Official NBA team-tracking dashboards for {season}. Powered by{" "}
          <span className="font-medium">stats.nba.com</span>.
        </p>

        <div className="mt-5 flex flex-wrap gap-2">
          {presentFamilies.map((family) => (
            <button
              key={family}
              onClick={() => handleFamilyChange(family)}
              className={
                "bip-toggle rounded-full px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.12em] transition-colors " +
                (displayedFamily === family ? "bip-toggle-active" : "")
              }
            >
              {FAMILY_LABELS[family] ?? family}
            </button>
          ))}
        </div>
      </section>

      <section className="bip-panel rounded-[1.8rem] p-6">
        {rows.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">
            No data for {FAMILY_LABELS[displayedFamily] ?? displayedFamily}.
          </p>
        ) : (
          <TrackingTable rows={rows} columns={columns} />
        )}
      </section>
    </div>
  );
}
