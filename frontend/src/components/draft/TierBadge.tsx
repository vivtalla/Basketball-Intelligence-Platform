// Sprint 101 (Stream A) — color-palette anchor for tier labels.
//
// Two distinct tier vocabularies share the same component:
//   * projected_tier: "lottery" | "first_round" | "second_round" | "undrafted" | "unknown"
//     (from compute_projected_tier in draft_analysis_service)
//   * outcome_tier: "bust" | "role_player" | "starter" | "star" | "superstar"
//     (from draft_outcome_classifier; surfaces on historical comps)
//
// One palette, one component: keeps the analyzer visually consistent across
// the board, prospect detail (HistoricalCompsGrid), and the historical
// validation view.

import type { CSSProperties } from "react";

type TierColors = { bg: string; border: string; text: string };

const PALETTE: Record<string, TierColors> = {
  // projected_tier
  lottery:       { bg: "rgba(180,137,61,0.12)",  border: "rgba(180,137,61,0.45)",  text: "#9a6f24" },
  first_round:   { bg: "rgba(33,72,59,0.10)",    border: "rgba(33,72,59,0.40)",    text: "#21483b" },
  second_round:  { bg: "rgba(120,120,120,0.10)", border: "rgba(120,120,120,0.35)", text: "#5b5b5b" },
  undrafted:     { bg: "rgba(120,120,120,0.06)", border: "rgba(120,120,120,0.25)", text: "#878787" },
  unknown:       { bg: "transparent",            border: "rgba(120,120,120,0.25)", text: "#9a9a9a" },
  // outcome_tier
  superstar:     { bg: "rgba(232,91,60,0.12)",   border: "rgba(232,91,60,0.45)",   text: "#c84a26" },
  star:          { bg: "rgba(180,137,61,0.12)",  border: "rgba(180,137,61,0.45)",  text: "#9a6f24" },
  starter:       { bg: "rgba(33,72,59,0.10)",    border: "rgba(33,72,59,0.40)",    text: "#21483b" },
  role_player:   { bg: "rgba(120,120,120,0.10)", border: "rgba(120,120,120,0.35)", text: "#5b5b5b" },
  bust:          { bg: "rgba(190,52,52,0.10)",   border: "rgba(190,52,52,0.35)",   text: "#a13030" },
};

const LABELS: Record<string, string> = {
  lottery: "Lottery",
  first_round: "1st Round",
  second_round: "2nd Round",
  undrafted: "Undrafted",
  unknown: "Unranked",
  superstar: "Superstar",
  star: "Star",
  starter: "Starter",
  role_player: "Role Player",
  bust: "Bust",
};

export interface TierBadgeProps {
  tier: string | null | undefined;
  size?: "sm" | "md";
  className?: string;
}

export default function TierBadge({ tier, size = "sm", className = "" }: TierBadgeProps) {
  if (!tier) return null;
  const colors = PALETTE[tier] ?? PALETTE.unknown;
  const label = LABELS[tier] ?? tier;
  const padding = size === "md" ? "px-2.5 py-1" : "px-2 py-0.5";
  const fontSize = size === "md" ? "text-[12px]" : "text-[10px]";
  const style: CSSProperties = {
    backgroundColor: colors.bg,
    borderColor: colors.border,
    color: colors.text,
  };
  return (
    <span
      className={`inline-flex items-center rounded-full border font-semibold uppercase tracking-wide ${padding} ${fontSize} ${className}`}
      style={style}
    >
      {label}
    </span>
  );
}

// Exported so other components (HistoricalCompsGrid, etc.) can pull the same
// palette without re-deriving.
export { PALETTE as TIER_PALETTE, LABELS as TIER_LABELS };
