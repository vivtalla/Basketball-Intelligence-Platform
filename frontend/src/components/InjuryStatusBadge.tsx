"use client";

import type { PlayerAvailabilitySlot } from "@/lib/types";

interface InjuryStatusBadgeProps {
  availability: PlayerAvailabilitySlot | null | undefined;
}

function statusVariant(status: string): "out" | "questionable" | "probable" {
  const s = status.toLowerCase();
  if (s === "out" || s === "doubtful") return "out";
  if (s === "probable" || s === "gtd") return "probable";
  return "questionable";
}

export default function InjuryStatusBadge({ availability }: InjuryStatusBadgeProps) {
  if (!availability) return null;

  const { injury_status, injury_type } = availability;
  const variant = statusVariant(injury_status);
  const label = injury_type ? `${injury_status} · ${injury_type}` : injury_status;

  const colorClass =
    variant === "out"
      ? "bg-[rgba(239,68,68,0.1)] text-[#ef4444] border border-[rgba(239,68,68,0.2)]"
      : variant === "probable"
      ? "bg-[rgba(59,130,246,0.1)] text-[#3b82f6] border border-[rgba(59,130,246,0.2)]"
      : "bg-[rgba(234,179,8,0.1)] text-[#ca8a04] border border-[rgba(234,179,8,0.2)]";

  return (
    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${colorClass}`}>
      {label}
    </span>
  );
}
