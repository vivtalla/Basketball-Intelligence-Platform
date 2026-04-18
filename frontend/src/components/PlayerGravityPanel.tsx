"use client";

import type { MvpGravityProfile } from "@/lib/types";

function fmt(value: number | null | undefined, digits = 1): string {
  if (value == null || Number.isNaN(value)) return "-";
  return value.toFixed(digits);
}

function confidenceClass(confidence: string | null | undefined): string {
  if (confidence === "high") return "text-[var(--success-ink)]";
  if (confidence === "medium") return "text-[var(--accent)]";
  return "text-[var(--muted)]";
}

function GravityTile({ label, value, sub }: { label: string; value: number | null | undefined; sub?: string }) {
  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-3">
      <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--muted)]">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums text-[var(--foreground)]">{fmt(value)}</p>
      {sub ? <p className="mt-1 text-xs leading-5 text-[var(--muted)]">{sub}</p> : null}
    </div>
  );
}

export default function PlayerGravityPanel({
  profile,
  isLoading,
  season,
}: {
  profile?: MvpGravityProfile | null;
  isLoading?: boolean;
  season: string | null;
}) {
  if (isLoading) {
    return (
      <section className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5">
        <div className="h-4 w-36 rounded bg-[var(--border)]" />
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="h-24 rounded-lg bg-[var(--surface-alt)]" />
          ))}
        </div>
      </section>
    );
  }

  return (
    <section className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase text-[var(--accent)]">Gravity</p>
          <h2 className="bip-display mt-1 text-2xl font-semibold text-[var(--foreground)]">Floor-bending context</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--muted)]">
            Gravity captures how much attention a player draws beyond the box score. Official NBA Gravity is used when persisted; otherwise this is a CourtVue proxy derived from local shot, play-type, tracking, hustle, and on/off context.
          </p>
        </div>
        <div className="rounded border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-2 text-xs text-[var(--muted)]">
          {season ?? "Current season"} · <span className={confidenceClass(profile?.gravity_confidence)}>{profile?.gravity_confidence ?? "low"} confidence</span>
        </div>
      </div>

      {profile ? (
        <>
          <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <GravityTile label="Overall" value={profile.overall_gravity} sub={profile.source_label} />
            <GravityTile label="Shooting" value={profile.shooting_gravity} sub="perimeter attention" />
            <GravityTile label="Rim" value={profile.rim_gravity} sub="paint pressure" />
            <GravityTile label="Creation" value={profile.creation_gravity} sub="on-ball load" />
            <GravityTile label="Off Ball" value={profile.off_ball_gravity} sub="movement and spacing" />
            <GravityTile label="Roll/Screen" value={profile.roll_or_screen_gravity} sub="screen and roll pressure" />
            <GravityTile label="Spacing Lift" value={profile.spacing_lift} sub="lineup value signal" />
            <GravityTile label="Gravity Minutes" value={profile.gravity_minutes} sub="sample size" />
          </div>
          <p className="mt-4 text-xs leading-5 text-[var(--muted)]">{profile.source_note}</p>
          {profile.warnings.length > 0 ? (
            <div className="mt-3 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-3">
              <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--muted)]">Coverage Notes</p>
              <ul className="mt-2 space-y-1 text-xs leading-5 text-[var(--muted)]">
                {profile.warnings.slice(0, 4).map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </>
      ) : (
        <p className="mt-5 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-3 text-sm text-[var(--muted)]">
          Gravity context is not available for this player and season yet.
        </p>
      )}
    </section>
  );
}
