"use client";

import { usePlayerShotDiagnosis } from "@/hooks/usePlayerShotDiagnosis";
import { humanizeMethodologyVersion } from "@/lib/methodology";
import type {
  ShotDiagnosisGrade,
  ShotDiagnosisSentiment,
  ShotDiagnosisTag,
} from "@/lib/types";

interface Props {
  playerId: number;
  season: string | null;
}

function gradeClasses(grade: ShotDiagnosisGrade, sentiment: ShotDiagnosisSentiment): string {
  if (grade === "green") {
    return "border-[var(--accent-strong)] bg-[var(--accent-soft)] text-[var(--accent-strong)]";
  }
  if (grade === "red") {
    return "border-[var(--danger-border)] bg-[var(--danger-soft)] text-[var(--danger-ink)]";
  }
  if (sentiment === "strength") {
    return "border-[var(--warning-border)] bg-[var(--warning-soft)] text-[var(--warning-ink)]";
  }
  return "border-[var(--border)] bg-[var(--surface-alt)] text-[var(--muted-strong)]";
}

function TagChip({ tag }: { tag: ShotDiagnosisTag }) {
  const ev = tag.evidence[0];
  const evText = ev
    ? ev.delta != null
      ? `Δ ${ev.delta >= 0 ? "+" : ""}${ev.delta.toFixed(2)}${ev.zone ? ` · ${ev.zone}` : ""}`
      : ev.value != null
      ? `${ev.value.toFixed(2)}${ev.zone ? ` · ${ev.zone}` : ""}`
      : ev.note ?? ""
    : "";
  return (
    <li
      className={`flex items-start gap-2 rounded-xl border p-3 text-xs ${gradeClasses(
        tag.grade,
        tag.sentiment
      )}`}
    >
      <span className="flex h-2 w-2 shrink-0 translate-y-[5px] rounded-full bg-current" />
      <div className="flex-1 min-w-0">
        <div className="font-semibold uppercase tracking-[0.1em]">{tag.label}</div>
        {evText && <div className="mt-0.5 text-[11px] opacity-80">{evText}</div>}
      </div>
      <span className="text-[10px] uppercase tracking-[0.1em] opacity-70">
        {tag.sample_confidence}
      </span>
    </li>
  );
}

export function ShotDiagnosisPanel({ playerId, season }: Props) {
  const { data, error, isLoading } = usePlayerShotDiagnosis(playerId, season ?? "");

  if (!season) return null;

  if (isLoading) {
    return (
      <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5 text-sm text-[var(--muted)]">
        Loading shot diagnosis…
      </section>
    );
  }

  if (error || !data) {
    return (
      <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5 text-sm text-[var(--muted)]">
        Shot diagnosis unavailable for this season.
      </section>
    );
  }

  return (
    <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5">
      <header className="flex items-baseline justify-between gap-4">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
            Shot Profile Diagnosis
          </div>
          <h3 className="mt-0.5 text-base font-semibold text-[var(--foreground)]">
            {data.headline}
          </h3>
        </div>
        <div className="shrink-0 text-right text-[11px] text-[var(--muted)]">
          <div>
            <span className="font-semibold text-[var(--foreground)]">{data.sustainability}</span>
          </div>
          <div>{data.creation_burden}</div>
        </div>
      </header>

      {data.tags.length > 0 ? (
        <ul className="mt-4 grid gap-2 sm:grid-cols-2">
          {data.tags.map((tag) => (
            <TagChip key={tag.key} tag={tag} />
          ))}
        </ul>
      ) : (
        <p className="mt-4 text-sm text-[var(--muted)]">
          No tag triggers fired. Shot profile is balanced with no red flags or
          breakout strengths.
        </p>
      )}

      <p className="mt-4 text-[11px] leading-4 text-[var(--muted)]">
        {data.total_shots} shots analyzed · {data.sample_confidence} sample confidence ·
        {" "}{humanizeMethodologyVersion(data.methodology_version)}
      </p>
    </section>
  );
}
