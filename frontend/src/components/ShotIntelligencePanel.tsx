"use client";

import type {
  ShotCreationResponse,
  ShotIdentityResponse,
  ShotIntelligenceCoverage,
  ShotQualityBin,
  ShotQualityResponse,
} from "@/lib/types";

type ShotIntelligenceMode = "quality" | "making" | "creation" | "summary";

interface ShotIntelligencePanelProps {
  mode: ShotIntelligenceMode;
  quality?: ShotQualityResponse | null;
  creation?: ShotCreationResponse | null;
  identity?: ShotIdentityResponse | null;
  label: string;
  contextLabel?: string;
  isLoading?: boolean;
}

function pct(value?: number | null, digits = 1): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "N/A";
  return `${(value * 100).toFixed(digits)}%`;
}

function num(value?: number | null, digits = 3): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "N/A";
  return value.toFixed(digits);
}

function signed(value?: number | null, digits = 3): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "N/A";
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(digits)}`;
}

function CoverageBadge({ coverage }: { coverage?: ShotIntelligenceCoverage | null }) {
  if (!coverage) return null;
  const tone =
    coverage.state === "ready"
      ? "border-emerald-200 bg-emerald-50 text-emerald-800"
      : coverage.state === "partial" || coverage.state === "stale"
        ? "border-amber-200 bg-amber-50 text-amber-800"
        : "border-[rgba(25,52,42,0.12)] bg-white text-[var(--muted-strong)]";
  return (
    <span className={`rounded-full border px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] ${tone}`}>
      {coverage.state}
    </span>
  );
}

function Methodology({ notes }: { notes?: Array<{ title: string; body: string }> }) {
  if (!notes || notes.length === 0) return null;
  return (
    <div className="rounded-[1rem] border border-[rgba(25,52,42,0.1)] bg-[rgba(255,255,255,0.62)] px-4 py-3 text-xs leading-5 text-[var(--muted-strong)]">
      {notes.map((note) => (
        <p key={note.title}>
          <span className="font-semibold text-[var(--foreground)]">{note.title}:</span> {note.body}
        </p>
      ))}
    </div>
  );
}

function WhyItMatters({ mode }: { mode: ShotIntelligenceMode }) {
  const copy =
    mode === "quality"
      ? "Quality asks whether the shot diet itself is favorable before makes and misses are credited."
      : mode === "making"
        ? "Making shows conversion above or below expectation, separating skill and hot shooting from shot selection."
        : mode === "creation"
          ? "Creation labels are useful scouting proxies from action, shot type, clock, and linked context; they are not official assisted/self-created truth."
          : "Scout Summary condenses the shot profile into role language so the chart supports a faster basketball read.";
  return (
    <div className="rounded-[1rem] border border-[rgba(25,52,42,0.1)] bg-[rgba(255,255,255,0.66)] px-4 py-3 text-xs leading-5 text-[var(--muted-strong)]">
      <span className="font-semibold text-[var(--foreground)]">Why this matters:</span> {copy}
    </div>
  );
}

function SummaryCards({ quality }: { quality?: ShotQualityResponse | null }) {
  const summary = quality?.summary;
  const items = [
    { label: "Actual eFG", value: pct(summary?.actual_efg_pct) },
    { label: "Expected eFG", value: pct(summary?.expected_efg_pct) },
    { label: "eFG delta", value: signed(summary?.efg_pct_delta) },
    { label: "PPS delta", value: signed(summary?.pps_delta) },
  ];
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {items.map((item) => (
        <div key={item.label} className="rounded-[1rem] border border-[rgba(25,52,42,0.1)] bg-[rgba(255,255,255,0.68)] px-4 py-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">{item.label}</p>
          <p className="mt-1 text-xl font-semibold text-[var(--foreground)]">{item.value}</p>
        </div>
      ))}
    </div>
  );
}

function BinRows({ bins, mode }: { bins: ShotQualityBin[]; mode: "quality" | "making" }) {
  const sorted = [...bins]
    .sort((a, b) =>
      mode === "quality"
        ? (b.expected_pps ?? 0) - (a.expected_pps ?? 0)
        : Math.abs(b.pps_delta ?? 0) - Math.abs(a.pps_delta ?? 0)
    )
    .slice(0, 8);
  return (
    <div className="space-y-2">
      {sorted.map((bin) => {
        const delta = mode === "quality" ? bin.expected_pps : bin.pps_delta;
        const width = `${Math.max(7, Math.min(100, bin.frequency * 260))}%`;
        const positive = (bin.pps_delta ?? 0) >= 0;
        return (
          <div key={bin.bin_key} className="rounded-[1rem] border border-[rgba(25,52,42,0.1)] bg-[rgba(255,255,255,0.58)] p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="text-sm font-semibold text-[var(--foreground)]">{bin.label}</p>
                <p className="text-xs text-[var(--muted)]">
                  {bin.attempts} attempts · actual {num(bin.actual_pps)} PPS · expected {num(bin.expected_pps)} PPS
                </p>
              </div>
              <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${
                positive ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-red-200 bg-red-50 text-red-800"
              }`}>
                {mode === "quality" ? `${num(delta)} exp PPS` : `${signed(delta)} PPS`}
              </span>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-[rgba(25,52,42,0.08)]">
              <div
                className={positive ? "h-full rounded-full bg-emerald-500" : "h-full rounded-full bg-red-400"}
                style={{ width }}
              />
            </div>
            <p className="mt-2 text-[11px] text-[var(--muted)]">{bin.coverage_note}</p>
          </div>
        );
      })}
    </div>
  );
}

function CreationSplits({ creation }: { creation?: ShotCreationResponse | null }) {
  const splits = creation?.splits ?? [];
  const palette = ["#21483b", "#6e7f52", "#b25b4f", "#7c6bb0", "#d79b55", "#537f8d"];
  return (
    <div className="grid gap-3 md:grid-cols-2">
      {splits.map((split, index) => (
        <div key={split.split_key} className="rounded-[1rem] border border-[rgba(25,52,42,0.1)] bg-[rgba(255,255,255,0.62)] p-4">
          <div className="mb-3 h-1.5 rounded-full" style={{ backgroundColor: palette[index % palette.length] }} />
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-[var(--foreground)]">{split.label}</p>
              <p className="mt-1 text-xs leading-5 text-[var(--muted-strong)]">{split.description}</p>
            </div>
            <span className="rounded-full border border-[rgba(25,52,42,0.1)] bg-white px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">
              {split.precision.replace("_", " ")}
            </span>
          </div>
          <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
            <span>{split.attempts} att</span>
            <span>{pct(split.frequency)} freq</span>
            <span>{num(split.pps)} PPS</span>
          </div>
          <p className="mt-3 text-[11px] text-[var(--muted)]">{split.coverage_note}</p>
        </div>
      ))}
    </div>
  );
}

function IdentityCards({ identity }: { identity?: ShotIdentityResponse | null }) {
  const cards = identity?.cards?.slice(0, 6) ?? [];
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {cards.map((card) => (
        <div key={card.identity_key} className="rounded-[1rem] border border-[rgba(25,52,42,0.1)] bg-[rgba(255,255,255,0.64)] p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-[var(--foreground)]">{card.label}</p>
              <p className="mt-1 text-xs leading-5 text-[var(--muted-strong)]">{card.summary}</p>
            </div>
            <span className="rounded-full border border-[rgba(25,52,42,0.1)] bg-white px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">
              {card.tier}
            </span>
          </div>
          <ul className="mt-3 space-y-1 text-xs text-[var(--muted)]">
            {card.evidence.slice(0, 2).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

export default function ShotIntelligencePanel({
  mode,
  quality,
  creation,
  identity,
  label,
  contextLabel,
  isLoading,
}: ShotIntelligencePanelProps) {
  const coverage = quality?.coverage ?? creation?.coverage ?? identity?.coverage ?? null;
  const methodology = mode === "creation" ? creation?.methodology : mode === "summary" ? identity?.methodology : quality?.methodology;

  if (isLoading) {
    return (
      <div className="flex min-h-[260px] items-center justify-center rounded-[1.5rem] border border-[rgba(25,52,42,0.1)] bg-[rgba(255,255,255,0.62)]">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-[var(--accent)] border-t-transparent" />
      </div>
    );
  }

  if (!quality && mode !== "creation" && mode !== "summary") {
    return (
      <div className="rounded-[1.5rem] border border-dashed border-[rgba(25,52,42,0.16)] bg-[rgba(255,255,255,0.62)] px-4 py-5 text-sm text-[var(--muted-strong)]">
        Shot intelligence is not available for this selection yet.
      </div>
    );
  }

  return (
    <div className="space-y-4 rounded-[1.5rem] border border-[rgba(25,52,42,0.12)] bg-[rgba(255,255,255,0.5)] p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">{contextLabel ?? "Shot Intelligence"}</p>
          <h4 className="mt-1 text-lg font-semibold text-[var(--foreground)]">{label}</h4>
          <p className="mt-1 text-sm leading-6 text-[var(--muted-strong)]">
            {mode === "quality"
              ? "Expected shot quality separates the favorability of the diet from the final result."
              : mode === "making"
                ? "Shot making isolates where actual conversion rises above or falls below expectation."
                : mode === "creation"
                  ? "Creation context groups shots by practical proxy labels and always shows trust level."
                  : "Scout Summary turns the shot diet into quick identity cards and takeaways."}
          </p>
        </div>
        <CoverageBadge coverage={coverage} />
      </div>

      {coverage?.note ? (
        <div className="rounded-[1rem] border border-[rgba(25,52,42,0.1)] bg-white/70 px-4 py-3 text-xs leading-5 text-[var(--muted-strong)]">
          {coverage.note}
        </div>
      ) : null}

      <WhyItMatters mode={mode} />

      {(mode === "quality" || mode === "making") && quality ? (
        <>
          <SummaryCards quality={quality} />
          <BinRows bins={quality.bins} mode={mode} />
        </>
      ) : null}

      {mode === "creation" ? <CreationSplits creation={creation} /> : null}
      {mode === "summary" ? <IdentityCards identity={identity} /> : null}

      <Methodology notes={methodology} />
    </div>
  );
}
