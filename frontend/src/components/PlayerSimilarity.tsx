"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { usePlayerSimilarityWithArchetype } from "@/hooks/usePlayerArchetype";
import { MethodologyEvidenceCard } from "@/components/methodology/MethodologyEvidenceCard";
import type {
  ArchetypeConfidence,
  SimilarityMode,
  SimilarPlayerCompWithArchetype,
  TeamFitContext,
} from "@/lib/types";

interface PlayerSimilarityProps {
  playerId: number;
  season: string | null;
}

function ScoreRing({ score }: { score: number }) {
  const r = 14;
  const circ = 2 * Math.PI * r;
  const fill = (score / 100) * circ;
  const color = score >= 75 ? "#21483b" : score >= 55 ? "#b4893d" : "#9c8f7d";

  return (
    <div className="relative w-10 h-10 shrink-0">
      <svg width="40" height="40" className="-rotate-90">
        <circle
          cx="20"
          cy="20"
          r={r}
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
          className="text-[var(--surface-alt)]"
        />
        <circle
          cx="20"
          cy="20"
          r={r}
          fill="none"
          strokeWidth="3"
          stroke={color}
          strokeDasharray={`${fill} ${circ}`}
          strokeLinecap="round"
        />
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

function ArchetypePill({
  label,
  confidence,
}: {
  label: string | null;
  confidence: ArchetypeConfidence | null;
}) {
  if (!label) return null;
  const tone =
    confidence === "high"
      ? "border-[var(--accent-strong)] bg-[var(--accent-soft)] text-[var(--accent-strong)]"
      : confidence === "medium"
      ? "border-[var(--warning-border)] bg-[var(--warning-soft)] text-[var(--warning-ink)]"
      : "border-[var(--border)] bg-[var(--surface-alt)] text-[var(--muted-strong)]";
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.1em] ${tone}`}
    >
      {label}
    </span>
  );
}

function CompCard({ comp }: { comp: SimilarPlayerCompWithArchetype }) {
  const pct = (v: number | null) => (v != null ? `${(v * 100).toFixed(1)}%` : "-");
  const f1 = (v: number | null) => (v != null ? v.toFixed(1) : "-");

  return (
    <Link
      href={`/beta/players/${comp.player_id}`}
      className="bip-panel group flex items-center gap-3 rounded-xl p-3 transition-all hover:border-[rgba(33,72,59,0.28)]"
    >
      <div className="relative h-10 w-10 shrink-0 overflow-hidden rounded-full bg-[var(--surface-alt)]">
        {comp.headshot_url ? (
          <Image
            src={comp.headshot_url}
            alt={comp.player_name}
            fill
            className="object-cover object-top"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = "none";
            }}
          />
        ) : null}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <div className="truncate text-sm font-medium text-[var(--foreground)] transition-colors group-hover:text-[var(--accent)]">
            {comp.player_name}
          </div>
          <ArchetypePill label={comp.archetype_label} confidence={comp.archetype_confidence} />
        </div>
        <div className="text-xs text-[var(--muted)]">
          {comp.season} · {comp.team_abbreviation} · {comp.gp}G
        </div>
      </div>

      <div className="hidden sm:flex gap-3">
        <StatPill label="PTS" value={f1(comp.pts_pg)} />
        <StatPill label="REB" value={f1(comp.reb_pg)} />
        <StatPill label="AST" value={f1(comp.ast_pg)} />
        <StatPill label="TS%" value={pct(comp.ts_pct)} />
        <StatPill label="PER" value={f1(comp.per)} />
      </div>

      <ScoreRing score={comp.similarity_score} />
    </Link>
  );
}

function TeamFitContextPills({ context }: { context: TeamFitContext | null | undefined }) {
  if (!context || context.overlap_flags.length === 0) {
    return (
      <div className="rounded-xl border border-[var(--border)] bg-[rgba(255,255,255,0.62)] px-3 py-2 text-xs text-[var(--muted-strong)]">
        Team-Fit mode found no same-team duplicate role features to soften.
      </div>
    );
  }

  const primary = context.overlap_flags[0];
  const teammateFlags = context.overlap_flags.filter(
    (flag) => flag.teammate_id === primary.teammate_id
  );
  const featureLabels = teammateFlags.slice(0, 3).map((flag) => flag.label.toLowerCase());

  return (
    <div className="rounded-xl border border-[rgba(180,137,61,0.28)] bg-[rgba(180,137,61,0.10)] px-3 py-2">
      <p className="text-xs font-semibold text-[var(--warning-ink)]">
        Covered by {primary.teammate_name}: {featureLabels.join(", ")}
      </p>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {context.overlap_flags.slice(0, 6).map((flag) => (
          <span
            key={`${flag.feature_key}-${flag.teammate_id}`}
            className="rounded-full border border-[rgba(180,137,61,0.28)] bg-[rgba(255,255,255,0.55)] px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.12em] text-[var(--warning-ink)]"
          >
            Penalized: {flag.label}
          </span>
        ))}
      </div>
    </div>
  );
}

const MODE_LABELS: Record<SimilarityMode, string> = {
  season: "This Season",
  age: "Same Age",
  team_fit: "Team Fit",
};

const MODE_DESCRIPTIONS: Record<SimilarityMode, string> = {
  season: "Most similar player-seasons across the league this season.",
  age: "Historical comps within ±1 year of age, pulled across every season.",
  team_fit: "Comps reweighted around the current roster: teammate-covered strengths count less, open role lanes count more.",
};

export default function PlayerSimilarity({ playerId, season }: PlayerSimilarityProps) {
  const [mode, setMode] = useState<SimilarityMode>("season");
  const n = mode === "season" ? 8 : 5;
  const { data, error, isLoading } = usePlayerSimilarityWithArchetype(
    playerId,
    season ?? "",
    mode,
    n
  );

  if (!season) return null;

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="bip-display text-lg font-semibold text-[var(--foreground)]">
            Statistical Comps
          </h2>
          <p className="text-sm text-[var(--muted)]">{MODE_DESCRIPTIONS[mode]}</p>
        </div>

        <div className="flex overflow-hidden rounded-lg border border-[var(--border)] text-sm">
          {(["season", "age", "team_fit"] as SimilarityMode[]).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`px-3 py-1.5 transition-colors ${
                mode === m ? "bip-toggle-active" : "bip-toggle"
              }`}
            >
              {MODE_LABELS[m]}
            </button>
          ))}
        </div>
      </div>

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: n }).map((_, i) => (
            <div
              key={i}
              className="bip-panel flex items-center gap-3 rounded-xl p-3 animate-pulse"
            >
              <div className="h-10 w-10 shrink-0 rounded-full bg-[var(--surface-alt)]" />
              <div className="flex-1 space-y-1.5">
                <div className="h-3.5 w-36 rounded bg-[var(--surface-alt)]" />
                <div className="h-3 w-24 rounded bg-[var(--surface-alt)]" />
              </div>
              <div className="hidden sm:flex gap-3">
                {[1, 2, 3, 4, 5].map((j) => (
                  <div key={j} className="h-8 w-8 rounded bg-[var(--surface-alt)]" />
                ))}
              </div>
              <div className="h-10 w-10 shrink-0 rounded-full bg-[var(--surface-alt)]" />
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="bip-empty rounded-xl p-4 text-center text-sm">
          Not enough stat data to compute comps for this mode.
        </div>
      )}

      {!isLoading && !error && data && mode === "team_fit" && (
        <TeamFitContextPills context={data.team_fit_context} />
      )}

      {!isLoading && !error && data ? (
        <MethodologyEvidenceCard domain="similarity" title="Similarity methodology reliability" compact />
      ) : null}

      {!isLoading && !error && data && data.comps.length > 0 && (
        <div className="space-y-2">
          {data.comps.map((comp, i) => (
            <CompCard key={`${i}-${comp.player_id}-${comp.season}`} comp={comp} />
          ))}
        </div>
      )}

      {!isLoading && !error && data && data.comps.length === 0 && (
        <div className="bip-empty rounded-xl p-4 text-center text-sm">
          No comps available for this player in {MODE_LABELS[mode]} mode.
        </div>
      )}

      {!isLoading && !error && data && data.comps.length > 0 && (
        <p className="text-center text-xs text-[var(--muted)]">
          Distance across 13 z-scored role features (usage, assists/36, 3PA rate, FTr, TS%, steals/36,
          blocks/36, OReb%, OBPM, DBPM, points, rebounds, PER). Each comp carries its own archetype
          label so you can see <em>which kind</em> of player this is like.
        </p>
      )}
    </section>
  );
}
