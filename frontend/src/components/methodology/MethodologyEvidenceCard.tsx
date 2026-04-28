"use client";

import type { AnalysisMetadata } from "@/lib/types";
import { useMethodologyDomain } from "@/hooks/useMethodology";

function pct(value: number | null | undefined) {
  return value == null ? "n/a" : `${Math.round(value)}%`;
}

export function MethodologyEvidenceCard({
  domain,
  metadata,
  title = "Methodology evidence",
  compact = false,
}: {
  domain?: string;
  metadata?: AnalysisMetadata | null;
  title?: string;
  compact?: boolean;
}) {
  const { data } = useMethodologyDomain(domain);
  const version = metadata?.methodology_version ?? data?.methodology_version ?? "methodology";
  const limitations = metadata?.limitations?.length ? metadata.limitations : data?.known_limitations ?? [];
  const validation = metadata?.validation_notes?.length ? metadata.validation_notes : data?.validation_notes ?? [];
  const drivers = metadata?.driver_breakdown ?? [];
  const band = metadata?.uncertainty_band;

  return (
    <section className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--accent)]">{title}</p>
          <h3 className="mt-1 text-base font-semibold text-[var(--foreground)]">{version}</h3>
          {data?.question_answered ? (
            <p className="mt-1 max-w-3xl text-xs leading-5 text-[var(--muted)]">{data.question_answered}</p>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-2 text-xs">
          <span className="rounded-full border border-[var(--border)] px-2.5 py-1 text-[var(--muted)]">
            Reliability {pct(metadata?.reliability_score)}
          </span>
          <span className="rounded-full border border-[var(--border)] px-2.5 py-1 text-[var(--muted)]">
            Confidence {metadata?.confidence ?? "registry"}
          </span>
        </div>
      </div>

      {metadata?.sample_context ? (
        <div className="mt-3 rounded-lg bg-[var(--surface-alt)] p-3 text-xs text-[var(--muted)]">
          Sample {metadata.sample_context.sample_size ?? "n/a"}
          {metadata.sample_context.minimum_recommended ? ` / target ${metadata.sample_context.minimum_recommended}` : ""}
          {metadata.sample_context.notes.length ? ` · ${metadata.sample_context.notes[0]}` : ""}
        </div>
      ) : null}

      {band?.lower != null && band?.upper != null ? (
        <p className="mt-3 text-xs text-[var(--muted)]">
          Uncertainty band: {band.lower.toFixed(3)} to {band.upper.toFixed(3)} ({Math.round(band.level * 100)}%, {band.method})
        </p>
      ) : null}

      {!compact && drivers.length ? (
        <div className="mt-4 grid gap-2 md:grid-cols-3">
          {drivers.slice(0, 3).map((driver) => (
            <div key={driver.key} className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-3">
              <p className="text-sm font-semibold text-[var(--foreground)]">{driver.label}</p>
              <p className="mt-1 text-xs leading-5 text-[var(--muted)]">{driver.explanation}</p>
            </div>
          ))}
        </div>
      ) : null}

      {!compact && (limitations.length || validation.length) ? (
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {limitations.length ? (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">Limitations</p>
              <ul className="mt-2 space-y-1 text-xs leading-5 text-[var(--muted)]">
                {limitations.slice(0, 3).map((item) => <li key={item}>{item}</li>)}
              </ul>
            </div>
          ) : null}
          {validation.length ? (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">Validation notes</p>
              <ul className="mt-2 space-y-1 text-xs leading-5 text-[var(--muted)]">
                {validation.slice(0, 3).map((item) => <li key={item}>{item}</li>)}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
