"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useSimilarPlayers } from "@/hooks/usePlayerStats";
import type { SimilarPlayerComp } from "@/lib/types";

interface PlayerSimilarityProps {
  playerId: number;
  season: string | null;
}

function ScoreRing({ score }: { score: number }) {
  // SVG ring that fills proportionally to score
  const r = 14;
  const circ = 2 * Math.PI * r;
  const fill = (score / 100) * circ;
  const color =
    score >= 75 ? "#21483b" : score >= 55 ? "#b4893d" : "#9c8f7d";

  return (
    <div className="relative w-10 h-10 shrink-0">
      <svg width="40" height="40" className="-rotate-90">
        <circle cx="20" cy="20" r={r} fill="none" stroke="currentColor" strokeWidth="3"
          className="text-[var(--surface-alt)]" />
        <circle cx="20" cy="20" r={r} fill="none" strokeWidth="3"
          stroke={color}
          strokeDasharray={`${fill} ${circ}`}
          strokeLinecap="round" />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-[9px] font-bold tabular-nums text-[var(--foreground)]">
        {score.toFixed(0)}
      </span>
    </div>
  );
}

function StatPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col items-center">
      <span className="text-[10px] uppercase tracking-wide text-[var(--muted)]">{label}</span>
      <span className="text-xs font-semibold tabular-nums text-[var(--foreground)]">{value}</span>
    </div>
  );
}

function CompCard({ comp }: { comp: SimilarPlayerComp }) {
  const pct = (v: number | null) => v != null ? `${(v * 100).toFixed(1)}%` : "-";
  const f1 = (v: number | null) => v != null ? v.toFixed(1) : "-";

  return (
    <Link
      href={`/players/${comp.player_id}`}
      className="bip-panel group flex items-center gap-3 rounded-xl p-3 transition-all hover:border-[rgba(33,72,59,0.28)]"
    >
      {/* Headshot */}
      <div className="relative h-10 w-10 shrink-0 overflow-hidden rounded-full bg-[var(--surface-alt)]">
        {comp.headshot_url ? (
          <Image
            src={comp.headshot_url}
            alt={comp.player_name}
            fill
            className="object-cover object-top"
            onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
          />
        ) : null}
      </div>

      {/* Name + season */}
      <div className="flex-1 min-w-0">
        <div className="truncate text-sm font-medium text-[var(--foreground)] transition-colors group-hover:text-[var(--accent)]">
          {comp.player_name}
        </div>
        <div className="text-xs text-[var(--muted)]">
          {comp.season} · {comp.team_abbreviation} · {comp.gp}G
        </div>
      </div>

      {/* Key stats */}
      <div className="hidden sm:flex gap-3">
        <StatPill label="PTS" value={f1(comp.pts_pg)} />
        <StatPill label="REB" value={f1(comp.reb_pg)} />
        <StatPill label="AST" value={f1(comp.ast_pg)} />
        <StatPill label="TS%" value={pct(comp.ts_pct)} />
        <StatPill label="PER" value={f1(comp.per)} />
      </div>

      {/* Similarity ring */}
      <ScoreRing score={comp.similarity_score} />
    </Link>
  );
}

export default function PlayerSimilarity({ playerId, season }: PlayerSimilarityProps) {
  const [crossEra, setCrossEra] = useState(true);
  const { data, error, isLoading } = useSimilarPlayers(playerId, season, 8, crossEra);

  if (!season) return null;

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="bip-display text-lg font-semibold text-[var(--foreground)]">Statistical Comps</h2>
          <p className="text-sm text-[var(--muted)]">
            Most similar player-seasons by weighted z-score distance.
          </p>
        </div>

        {/* Cross-era toggle */}
        <div className="flex overflow-hidden rounded-lg border border-[var(--border)] text-sm">
          <button
            onClick={() => setCrossEra(true)}
            className={`px-3 py-1.5 transition-colors ${
              crossEra
                ? "bip-toggle-active"
                : "bip-toggle"
            }`}
          >
            All eras
          </button>
          <button
            onClick={() => setCrossEra(false)}
            className={`px-3 py-1.5 transition-colors ${
              !crossEra
                ? "bip-toggle-active"
                : "bip-toggle"
            }`}
          >
            Same season
          </button>
        </div>
      </div>

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="bip-panel flex items-center gap-3 rounded-xl p-3 animate-pulse">
              <div className="h-10 w-10 shrink-0 rounded-full bg-[var(--surface-alt)]" />
              <div className="flex-1 space-y-1.5">
                <div className="h-3.5 w-36 rounded bg-[var(--surface-alt)]" />
                <div className="h-3 w-24 rounded bg-[var(--surface-alt)]" />
              </div>
              <div className="hidden sm:flex gap-3">
                {[1, 2, 3, 4, 5].map((j) => <div key={j} className="h-8 w-8 rounded bg-[var(--surface-alt)]" />)}
              </div>
              <div className="h-10 w-10 shrink-0 rounded-full bg-[var(--surface-alt)]" />
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="bip-empty rounded-xl p-4 text-center text-sm">
          Not enough stat data to compute comps for this season.
        </div>
      )}

      {!isLoading && !error && data && (
        <div className="space-y-2">
          {data.comps.map((comp, i) => (
            <CompCard key={`${i}-${comp.player_id}-${comp.season}`} comp={comp} />
          ))}
        </div>
      )}

      {!isLoading && !error && data && (
        <p className="text-center text-xs text-[var(--muted)]">
          Similarity score based on pts, reb, ast, stl, blk, ts%, usg%, per — z-score normalized{crossEra ? " within each season" : ""}.
        </p>
      )}
    </section>
  );
}
