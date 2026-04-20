"use client";

import Link from "next/link";
import { useStyleXRay } from "@/hooks/usePlayerStats";
import { ArchetypeFingerprint } from "./xray/ArchetypeFingerprint";
import { NeighborQualityList } from "./xray/NeighborQualityList";
import { MovementTimeline } from "./xray/MovementTimeline";
import { AdjacentArchetypes } from "./xray/AdjacentArchetypes";
import { XRayMethodologyDrawer } from "./xray/XRayMethodologyDrawer";

interface Props {
  team: string;
  season: string;
  opponent: string | null;
  onModeChange: (mode: "trajectory" | "usage" | "trends" | "xray" | "whatif") => void;
}

const CONFIDENCE_STYLE: Record<string, string> = {
  high: "bg-[var(--accent-strong)]/15 text-[var(--accent-strong)] border-[var(--accent-strong)]/30",
  medium: "bg-[var(--surface-alt)] text-[var(--muted-strong)] border-[var(--border)]",
  low: "bg-[var(--surface-alt)] text-[var(--muted)] border-[var(--border)]",
};

const STABILITY_LABEL: Record<string, string> = {
  stable: "Stable profile",
  watch: "Watch for drift",
  shifted: "Shifted recently",
};

export default function StyleXRayWorkspace({ team, season, opponent, onModeChange }: Props) {
  const { data, error, isLoading } = useStyleXRay(team, season, 10, opponent ?? undefined);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-32 animate-pulse rounded-2xl bg-[var(--surface-alt)]" />
        <div className="h-64 animate-pulse rounded-2xl bg-[var(--surface-alt)]" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 text-sm text-[var(--muted-strong)]">
        Could not load Style X-Ray for {team} · {season}. The warehouse may still be warming up, or
        the season has no qualifying games yet.
      </div>
    );
  }

  const confidence = data.archetype_confidence ?? "medium";

  return (
    <div className="grid gap-5 lg:grid-cols-[360px_1fr]">
      {/* Left rail — archetype hero */}
      <aside className="space-y-4">
        <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5">
          <div className="text-[11px] uppercase tracking-[0.14em] text-[var(--muted)]">
            {data.team_abbreviation} · {data.season}
          </div>
          <h2 className="mt-2 text-2xl font-semibold text-[var(--foreground)]">{data.archetype}</h2>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span
              className={`rounded-full border px-2 py-[2px] text-[10px] font-semibold uppercase tracking-[0.14em] ${
                CONFIDENCE_STYLE[confidence] ?? CONFIDENCE_STYLE.medium
              }`}
              title={`Archetype confidence reflects the strength of the z-score triggers that fired the rule.`}
            >
              {confidence} confidence
            </span>
            <span
              className="rounded-full border border-[var(--border)] bg-[var(--surface-alt)] px-2 py-[2px] text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--muted-strong)]"
              title="Stability compares the current season archetype with the most recent window."
            >
              {STABILITY_LABEL[data.stability] ?? data.stability}
            </span>
          </div>
          <p className="mt-4 text-sm leading-5 text-[var(--muted-strong)]">{data.label_reason}</p>

          <div className="mt-5 flex flex-wrap gap-2">
            {data.nearest_neighbors.length > 0 ? (
              <Link
                href={data.launch_links.compare_url}
                className="rounded-full border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-1 text-[11px] font-medium text-[var(--muted-strong)] hover:border-[var(--accent-strong)] hover:text-[var(--accent-strong)]"
              >
                Compare vs {data.nearest_neighbors[0].team_abbreviation} →
              </Link>
            ) : null}
            {data.launch_links.prep_url ? (
              <Link
                href={data.launch_links.prep_url}
                className="rounded-full border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-1 text-[11px] font-medium text-[var(--muted-strong)] hover:border-[var(--accent-strong)] hover:text-[var(--accent-strong)]"
              >
                Open prep {opponent ? `vs ${opponent}` : ""} →
              </Link>
            ) : null}
            <button
              type="button"
              onClick={() => onModeChange("whatif")}
              className="rounded-full border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-1 text-[11px] font-medium text-[var(--muted-strong)] hover:border-[var(--accent-strong)] hover:text-[var(--accent-strong)]"
            >
              What-If scenarios →
            </button>
          </div>
        </section>

        <XRayMethodologyDrawer />

        {data.warnings.length > 0 ? (
          <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface-alt)] p-4 text-xs text-[var(--muted-strong)]">
            <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
              Coverage notes
            </div>
            <ul className="mt-2 list-disc space-y-1 pl-5">
              {data.warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          </section>
        ) : null}
      </aside>

      {/* Right column — four cards */}
      <div className="grid gap-4 lg:grid-cols-2">
        <ArchetypeFingerprint data={data} />
        <NeighborQualityList neighbors={data.nearest_neighbors} season={data.season} />
        <MovementTimeline movement={data.movement ?? null} />
        <AdjacentArchetypes archetypes={data.adjacent_archetypes} />
      </div>
    </div>
  );
}
