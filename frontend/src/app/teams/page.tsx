"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useTeams } from "@/hooks/usePlayerStats";
import type { TeamSummary } from "@/lib/types";

// Static conference + color data keyed by abbreviation.
// Conference memberships are fixed; colors are approximate primary brand colors.
const TEAM_META: Record<string, { conf: "E" | "W"; color: string }> = {
  ATL: { conf: "E", color: "#e03a3e" },
  BOS: { conf: "E", color: "#007a33" },
  BKN: { conf: "E", color: "#000000" },
  CHA: { conf: "E", color: "#00788c" },
  CHI: { conf: "E", color: "#ce1141" },
  CLE: { conf: "E", color: "#6f263d" },
  DET: { conf: "E", color: "#c8102e" },
  IND: { conf: "E", color: "#002d62" },
  MIA: { conf: "E", color: "#98002e" },
  MIL: { conf: "E", color: "#00471b" },
  NYK: { conf: "E", color: "#f58426" },
  ORL: { conf: "E", color: "#0077c0" },
  PHI: { conf: "E", color: "#006bb6" },
  TOR: { conf: "E", color: "#ce1141" },
  WAS: { conf: "E", color: "#002b5c" },
  DAL: { conf: "W", color: "#00538c" },
  DEN: { conf: "W", color: "#0e2240" },
  GSW: { conf: "W", color: "#1d428a" },
  HOU: { conf: "W", color: "#ce1141" },
  LAC: { conf: "W", color: "#c8102e" },
  LAL: { conf: "W", color: "#552583" },
  MEM: { conf: "W", color: "#5d76a9" },
  MIN: { conf: "W", color: "#0c2340" },
  NOP: { conf: "W", color: "#0c2340" },
  OKC: { conf: "W", color: "#007ac1" },
  PHX: { conf: "W", color: "#1d1160" },
  POR: { conf: "W", color: "#e03a3e" },
  SAC: { conf: "W", color: "#5a2d81" },
  SAS: { conf: "W", color: "#c4ced4" },
  UTA: { conf: "W", color: "#002b5c" },
};

type SortKey = "name" | "players" | "conf";
type ConfFilter = "all" | "E" | "W";

function TeamRow({
  team,
  selected,
  onSelect,
}: {
  team: TeamSummary;
  selected: boolean;
  onSelect: (t: TeamSummary) => void;
}) {
  const meta = TEAM_META[team.abbreviation];
  const color = meta?.color ?? "var(--accent)";
  const conf = meta?.conf;

  return (
    <button
      onClick={() => onSelect(team)}
      className="w-full text-left transition-colors"
      style={{
        display: "grid",
        gridTemplateColumns: "42px 1fr auto",
        gap: 12,
        alignItems: "center",
        padding: "12px 16px",
        background: selected ? "rgba(33,72,59,0.07)" : "transparent",
        borderLeft: selected ? `3px solid ${color}` : "3px solid transparent",
        borderTop: "1px solid var(--border)",
      }}
    >
      {/* Team badge */}
      <span
        style={{
          width: 36,
          height: 36,
          borderRadius: 10,
          background: color,
          color: "#fff",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "var(--font-geist-mono)",
          fontWeight: 700,
          fontSize: 10,
          letterSpacing: "0.04em",
          flexShrink: 0,
        }}
      >
        {team.abbreviation}
      </span>

      {/* Name + conf */}
      <div className="min-w-0">
        <div
          className="truncate font-semibold text-[var(--foreground)]"
          style={{ fontFamily: "var(--font-display)", fontSize: 14 }}
        >
          {team.name}
        </div>
        <div
          className="text-[var(--muted)]"
          style={{ fontFamily: "var(--font-geist-mono)", fontSize: 10, marginTop: 2, letterSpacing: "0.04em" }}
        >
          {conf === "E" ? "EAST" : conf === "W" ? "WEST" : "NBA"} · {team.player_count} players
        </div>
      </div>

      {/* Arrow */}
      <span className="text-[var(--muted)] text-sm">›</span>
    </button>
  );
}

function TeamDetailPreview({ team }: { team: TeamSummary }) {
  const meta = TEAM_META[team.abbreviation];
  const color = meta?.color ?? "var(--accent)";
  const conf = meta?.conf;

  return (
    <div className="bip-panel rounded-[1.85rem] p-6 space-y-6">
      {/* Header with color accent */}
      <div
        className="rounded-2xl px-6 py-5 relative overflow-hidden"
        style={{ background: `${color}18`, borderLeft: `4px solid ${color}` }}
      >
        <p className="bip-kicker" style={{ color }}>
          {team.abbreviation}
        </p>
        <h2 className="bip-display mt-2 text-3xl font-bold text-[var(--foreground)]">
          {team.name}
        </h2>
        <p className="mt-1 text-sm text-[var(--muted)]">
          {conf === "E" ? "Eastern Conference" : conf === "W" ? "Western Conference" : "NBA"} · {team.player_count} synced players
        </p>
      </div>

      {/* Quick links */}
      <div className="grid grid-cols-2 gap-3">
        {[
          { label: "Team intelligence", tab: "intelligence" },
          { label: "Roster", tab: "roster" },
          { label: "Shot lab", tab: "analytics" },
          { label: "Splits", tab: "splits" },
        ].map(({ label, tab }) => (
          <Link
            key={tab}
            href={`/teams/${team.abbreviation}?tab=${tab}`}
            className="bip-panel rounded-xl px-4 py-3 text-sm font-medium text-[var(--foreground)] hover:border-[var(--accent)] hover:text-[var(--accent)] transition-colors text-center"
          >
            {label}
          </Link>
        ))}
      </div>

      {/* CTA */}
      <Link
        href={`/teams/${team.abbreviation}`}
        className="block w-full rounded-xl text-center px-4 py-3 text-sm font-semibold transition-colors"
        style={{ background: color, color: "#fff" }}
      >
        Open full team dashboard →
      </Link>
    </div>
  );
}

export default function TeamsPage() {
  const { data: teams, error } = useTeams();
  const [confFilter, setConfFilter] = useState<ConfFilter>("all");
  const [sortKey, setSortKey] = useState<SortKey>("name");
  const [selected, setSelected] = useState<TeamSummary | null>(null);

  const filtered = useMemo(() => {
    let list = [...(teams ?? [])];
    if (confFilter !== "all") {
      list = list.filter((t) => TEAM_META[t.abbreviation]?.conf === confFilter);
    }
    list.sort((a, b) => {
      if (sortKey === "players") return b.player_count - a.player_count;
      if (sortKey === "conf") {
        const ca = TEAM_META[a.abbreviation]?.conf ?? "Z";
        const cb = TEAM_META[b.abbreviation]?.conf ?? "Z";
        return ca.localeCompare(cb) || a.name.localeCompare(b.name);
      }
      return a.name.localeCompare(b.name);
    });
    return list;
  }, [teams, confFilter, sortKey]);

  if (error) {
    return (
      <div className="max-w-5xl mx-auto py-16 text-center">
        <h1 className="bip-display text-3xl font-semibold text-[var(--foreground)]">
          Team Explorer
        </h1>
        <p className="mt-4 text-[var(--muted)]">Team data could not be loaded right now.</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="space-y-2">
        <Link href="/" className="bip-link inline-flex items-center gap-1 text-sm">
          ← Back to Home
        </Link>
        <div>
          <p className="bip-kicker">Explore Teams</p>
          <h1 className="bip-display text-4xl font-semibold text-[var(--foreground)]">
            Team Explorer
          </h1>
          <p className="mt-2 max-w-2xl text-[var(--muted)]">
            Browse synced NBA rosters and jump into player-level intelligence from each team context.
          </p>
        </div>
      </div>

      {/* Filter + sort bar */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Conference filter */}
        <div className="flex overflow-hidden rounded-xl border border-[var(--border)] text-sm">
          {(["all", "E", "W"] as ConfFilter[]).map((c) => (
            <button
              key={c}
              onClick={() => setConfFilter(c)}
              className={`px-4 py-2 transition-colors ${confFilter === c ? "bip-toggle-active" : "bip-toggle"}`}
            >
              {c === "all" ? "All" : c === "E" ? "East" : "West"}
            </button>
          ))}
        </div>

        {/* Sort */}
        <label className="flex items-center gap-2 text-sm text-[var(--muted)]">
          Sort:
          <select
            value={sortKey}
            onChange={(e) => setSortKey(e.target.value as SortKey)}
            className="bip-input rounded-lg px-3 py-1.5 text-sm text-[var(--foreground)]"
          >
            <option value="name">Name</option>
            <option value="conf">Conference</option>
            <option value="players">Roster size</option>
          </select>
        </label>
      </div>

      {/* Loading skeleton */}
      {!teams && (
        <div className="bip-panel rounded-[1.85rem] overflow-hidden">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-16 border-t border-[var(--border)] animate-pulse bg-[rgba(33,72,59,0.03)]" />
          ))}
        </div>
      )}

      {teams && teams.length === 0 && (
        <div className="bip-empty rounded-3xl p-10 text-center">
          <h2 className="text-xl font-semibold text-[var(--foreground)]">No teams have been synced yet</h2>
          <p className="mt-2 text-[var(--muted)]">
            Open a few player pages first and their teams will appear here.
          </p>
        </div>
      )}

      {filtered.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-[340px_1fr] gap-6 items-start">
          {/* Directory panel */}
          <div className="bip-panel rounded-[1.85rem] overflow-hidden sticky top-20">
            <div className="px-4 py-3 border-b border-[var(--border)]">
              <p className="bip-kicker">
                {confFilter === "all" ? "All teams" : confFilter === "E" ? "Eastern Conference" : "Western Conference"}
                <span className="ml-2 font-mono text-xs text-[var(--muted)]">({filtered.length})</span>
              </p>
            </div>
            <div className="overflow-y-auto" style={{ maxHeight: "calc(100vh - 220px)" }}>
              {filtered.map((team) => (
                <TeamRow
                  key={team.team_id}
                  team={team}
                  selected={selected?.team_id === team.team_id}
                  onSelect={setSelected}
                />
              ))}
            </div>
          </div>

          {/* Detail panel */}
          <div>
            {selected ? (
              <TeamDetailPreview team={selected} />
            ) : (
              <div className="bip-panel rounded-[1.85rem] p-10 text-center">
                <div className="text-4xl mb-4">🏀</div>
                <p className="text-lg font-semibold text-[var(--foreground)]">Select a team</p>
                <p className="mt-2 text-sm text-[var(--muted)]">
                  Click any team in the directory to see a preview and quick-access links.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
