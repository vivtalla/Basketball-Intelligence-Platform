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
    score >= 75 ? "#3b82f6" : score >= 55 ? "#8b5cf6" : "#94a3b8";

  return (
    <div className="relative w-10 h-10 shrink-0">
      <svg width="40" height="40" className="-rotate-90">
        <circle cx="20" cy="20" r={r} fill="none" stroke="currentColor" strokeWidth="3"
          className="text-gray-200 dark:text-gray-700" />
        <circle cx="20" cy="20" r={r} fill="none" strokeWidth="3"
          stroke={color}
          strokeDasharray={`${fill} ${circ}`}
          strokeLinecap="round" />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-[9px] font-bold text-gray-700 dark:text-gray-300 tabular-nums">
        {score.toFixed(0)}
      </span>
    </div>
  );
}

function StatPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col items-center">
      <span className="text-[10px] text-gray-400 dark:text-gray-500 uppercase tracking-wide">{label}</span>
      <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 tabular-nums">{value}</span>
    </div>
  );
}

function CompCard({ comp }: { comp: SimilarPlayerComp }) {
  const pct = (v: number | null) => v != null ? `${(v * 100).toFixed(1)}%` : "-";
  const f1 = (v: number | null) => v != null ? v.toFixed(1) : "-";

  return (
    <Link
      href={`/players/${comp.player_id}`}
      className="flex items-center gap-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-3 hover:border-blue-400 dark:hover:border-blue-500 hover:shadow-sm transition-all group"
    >
      {/* Headshot */}
      <div className="relative w-10 h-10 rounded-full overflow-hidden bg-gray-100 dark:bg-gray-700 shrink-0">
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
        <div className="font-medium text-sm text-gray-900 dark:text-gray-100 group-hover:text-blue-500 dark:group-hover:text-blue-400 transition-colors truncate">
          {comp.player_name}
        </div>
        <div className="text-xs text-gray-400 dark:text-gray-500">
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
          <h2 className="text-lg font-semibold">Statistical Comps</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Most similar player-seasons by weighted z-score distance.
          </p>
        </div>

        {/* Cross-era toggle */}
        <div className="flex rounded-lg overflow-hidden border border-gray-200 dark:border-gray-600 text-sm">
          <button
            onClick={() => setCrossEra(true)}
            className={`px-3 py-1.5 transition-colors ${
              crossEra
                ? "bg-blue-500 text-white"
                : "bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700"
            }`}
          >
            All eras
          </button>
          <button
            onClick={() => setCrossEra(false)}
            className={`px-3 py-1.5 transition-colors ${
              !crossEra
                ? "bg-blue-500 text-white"
                : "bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700"
            }`}
          >
            Same season
          </button>
        </div>
      </div>

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-3 animate-pulse">
              <div className="w-10 h-10 rounded-full bg-gray-200 dark:bg-gray-700 shrink-0" />
              <div className="flex-1 space-y-1.5">
                <div className="h-3.5 w-36 bg-gray-200 dark:bg-gray-700 rounded" />
                <div className="h-3 w-24 bg-gray-200 dark:bg-gray-700 rounded" />
              </div>
              <div className="hidden sm:flex gap-3">
                {[1, 2, 3, 4, 5].map((j) => <div key={j} className="w-8 h-8 bg-gray-200 dark:bg-gray-700 rounded" />)}
              </div>
              <div className="w-10 h-10 rounded-full bg-gray-200 dark:bg-gray-700 shrink-0" />
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 text-sm text-gray-400 dark:text-gray-500 text-center">
          Not enough stat data to compute comps for this season.
        </div>
      )}

      {!isLoading && !error && data && (
        <div className="space-y-2">
          {data.comps.map((comp) => (
            <CompCard key={`${comp.player_id}-${comp.season}`} comp={comp} />
          ))}
        </div>
      )}

      {!isLoading && !error && data && (
        <p className="text-xs text-gray-400 dark:text-gray-500 text-center">
          Similarity score based on pts, reb, ast, stl, blk, ts%, usg%, per — z-score normalized{crossEra ? " within each season" : ""}.
        </p>
      )}
    </section>
  );
}
