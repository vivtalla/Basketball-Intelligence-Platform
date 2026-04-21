export type ShotConfidenceBand = "high" | "medium" | "low" | "insufficient";

export function confidenceBand(attempts: number): ShotConfidenceBand {
  if (attempts >= 30) return "high";
  if (attempts >= 10) return "medium";
  if (attempts >= 5) return "low";
  return "insufficient";
}

export const CONFIDENCE_LABEL: Record<ShotConfidenceBand, string> = {
  high: "High confidence",
  medium: "Medium confidence",
  low: "Low confidence",
  insufficient: "Thin sample",
};

export const CONFIDENCE_SHORT: Record<ShotConfidenceBand, string> = {
  high: "High",
  medium: "Medium",
  low: "Low",
  insufficient: "Thin",
};

export const CONFIDENCE_TONE: Record<
  ShotConfidenceBand,
  { bg: string; text: string }
> = {
  high: { bg: "rgba(22,163,74,0.14)", text: "#166534" },
  medium: { bg: "rgba(234,179,8,0.18)", text: "#854d0e" },
  low: { bg: "rgba(249,115,22,0.18)", text: "#9a3412" },
  insufficient: { bg: "rgba(120,120,128,0.18)", text: "#52525b" },
};

export function formatPct(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

export function formatPctDelta(delta: number | null | undefined): string {
  if (delta === null || delta === undefined || Number.isNaN(delta)) return "—";
  const sign = delta >= 0 ? "+" : "";
  return `${sign}${(delta * 100).toFixed(1)}%`;
}

export function formatValueDelta(
  value: number | null | undefined,
  suffix = " pts/shot",
): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}${suffix}`;
}
