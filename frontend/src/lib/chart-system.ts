export type DataStatus = "ready" | "stale" | "missing";

export interface DataStatusTone {
  label: string;
  className: string;
  panelClassName: string;
}

export const chartPalette = {
  ink: "#19342a",
  accent: "#21483b",
  accentSoft: "rgba(33,72,59,0.14)",
  signal: "#b5914e",
  signalSoft: "rgba(181,145,78,0.16)",
  warning: "#c27a2c",
  warningSoft: "rgba(194,122,44,0.14)",
  danger: "#9f3f31",
  dangerSoft: "rgba(159,63,49,0.12)",
  grid: "rgba(25,52,42,0.12)",
  surface: "rgba(255,255,255,0.82)",
  surfaceAlt: "rgba(216,228,221,0.28)",
} as const;

export function getDataStatusTone(status: DataStatus): DataStatusTone {
  if (status === "stale") {
    return {
      label: "Cached",
      className: "bg-[rgba(194,122,44,0.14)] text-[rgb(143,87,30)]",
      panelClassName: "border-[rgba(194,122,44,0.2)] bg-[rgba(194,122,44,0.06)]",
    };
  }
  if (status === "missing") {
    return {
      label: "Not Synced",
      className: "bg-[rgba(148,163,184,0.16)] text-[var(--muted)]",
      panelClassName: "border-[rgba(148,163,184,0.2)] bg-[rgba(148,163,184,0.06)]",
    };
  }
  return {
    label: "Ready",
    className: "bg-[rgba(33,72,59,0.12)] text-[var(--accent-strong)]",
    panelClassName: "border-[rgba(33,72,59,0.18)] bg-[rgba(33,72,59,0.05)]",
  };
}
