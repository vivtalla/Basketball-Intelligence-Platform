// Sprint 101 (Stream B) — five-axis risk indicators (each 0..1).
//
// Pure SVG, no charting library. Follows the Sprint 70 Sparkline.tsx
// philosophy. Each axis renders as a horizontal bar with color gradient
// muted→red as the value increases. Labeled + value-text to the right.

import type { RiskIndicators } from "@/lib/types";

interface Props {
  risk: RiskIndicators | null | undefined;
}

const AXES: { key: keyof RiskIndicators; label: string; tooltip: string }[] = [
  { key: "age_risk",         label: "Age",          tooltip: "Older prospects bust at higher rates" },
  { key: "sample_risk",      label: "Sample",       tooltip: "Games played thinness; small samples are noisier" },
  { key: "level_risk",       label: "Level",        tooltip: "Strength of conference / international league" },
  { key: "athleticism_risk", label: "Athleticism",  tooltip: "Bottom-decile flags from combine measurements" },
  { key: "shooting_risk",    label: "Shooting",     tooltip: "Career college TS%/3P% relative to NBA shooters" },
];

function riskColor(value: number): { bar: string; track: string } {
  // 0.0 → forest green; 0.5 → amber; 1.0 → red
  if (value < 0.3) return { bar: "#21483b", track: "rgba(33,72,59,0.10)" };
  if (value < 0.55) return { bar: "#b4893d", track: "rgba(180,137,61,0.10)" };
  if (value < 0.75) return { bar: "#cc7a3a", track: "rgba(204,122,58,0.10)" };
  return { bar: "#c4423a", track: "rgba(196,66,58,0.10)" };
}

export default function RiskIndicatorsBars({ risk }: Props) {
  if (!risk) return null;

  return (
    <section className="bip-panel rounded-[1.85rem] p-5 sm:p-6">
      <p className="bip-kicker">Risk indicators</p>
      <h2 className="bip-display mt-1 text-xl font-bold text-[var(--foreground)]">
        Where this prospect could break
      </h2>
      <p className="mt-1 text-xs text-[var(--muted)]">
        Each axis is 0..1, higher = greater risk. Used by the analyzer to dim
        confidence on projections.
      </p>

      <div className="mt-4 space-y-3">
        {AXES.map(({ key, label, tooltip }) => {
          const value = risk[key];
          const pct = Math.round(value * 100);
          const colors = riskColor(value);
          return (
            <div key={key} className="grid grid-cols-[110px_1fr_50px] items-center gap-3" title={tooltip}>
              <span className="text-[12px] uppercase tracking-wide text-[var(--muted)]">
                {label}
              </span>
              <svg viewBox="0 0 100 8" preserveAspectRatio="none" className="h-2 w-full">
                <rect x="0" y="0" width="100" height="8" rx="2" fill={colors.track} />
                <rect x="0" y="0" width={pct} height="8" rx="2" fill={colors.bar} />
              </svg>
              <span className="tabular-nums text-right text-[12px] font-semibold text-[var(--foreground)]">
                {pct}
              </span>
            </div>
          );
        })}
      </div>
    </section>
  );
}
