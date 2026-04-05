"use client";

import type { ShotLabDateRange, ShotLabWindowPreset } from "@/lib/types";

const PRESET_OPTIONS: Array<{ id: ShotLabWindowPreset; label: string }> = [
  { id: "full", label: "Full season" },
  { id: "last-5-games", label: "Last 5" },
  { id: "last-10-games", label: "Last 10" },
  { id: "last-30-days", label: "Last 30 days" },
  { id: "custom", label: "Custom" },
];

interface ShotLabControlsProps {
  seasons: string[];
  selectedSeason: string;
  onSeasonChange: (season: string) => void;
  seasonType: "Regular Season" | "Playoffs";
  onSeasonTypeChange: (seasonType: "Regular Season" | "Playoffs") => void;
  preset: ShotLabWindowPreset;
  onPresetChange: (preset: ShotLabWindowPreset) => void;
  customRange: ShotLabDateRange;
  onCustomRangeChange: (range: ShotLabDateRange) => void;
  availableStartDate?: string | null;
  availableEndDate?: string | null;
  seasonLabel?: string;
}

export default function ShotLabControls({
  seasons,
  selectedSeason,
  onSeasonChange,
  seasonType,
  onSeasonTypeChange,
  preset,
  onPresetChange,
  customRange,
  onCustomRangeChange,
  availableStartDate,
  availableEndDate,
  seasonLabel = "Season",
}: ShotLabControlsProps) {
  return (
    <div className="space-y-4 rounded-[1.6rem] border border-[rgba(25,52,42,0.12)] bg-[linear-gradient(180deg,rgba(255,252,247,0.9),rgba(244,238,228,0.72))] p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.7)]">
      <div className="flex flex-wrap items-center gap-3">
        <label className="space-y-1">
          <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
            {seasonLabel}
          </span>
          <select
            value={selectedSeason}
            onChange={(event) => onSeasonChange(event.target.value)}
            className="bip-input rounded-xl px-3 py-2 text-sm"
          >
            {seasons.map((season) => (
              <option key={season} value={season}>
                {season}
              </option>
            ))}
          </select>
        </label>

        <div className="space-y-1">
          <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
            Season Type
          </span>
          <div className="flex overflow-hidden rounded-xl border border-[var(--border)] bg-[rgba(255,255,255,0.56)] p-1 text-xs">
            {(["Regular Season", "Playoffs"] as const).map((type) => (
              <button
                key={type}
                onClick={() => onSeasonTypeChange(type)}
                className={`rounded-lg px-3 py-2 transition-colors ${
                  seasonType === type ? "bip-toggle-active" : "bip-toggle"
                }`}
              >
                {type}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="space-y-1">
        <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
          Shot Window
        </span>
        <div className="flex flex-wrap gap-2">
          {PRESET_OPTIONS.map((option) => (
            <button
              key={option.id}
              onClick={() => onPresetChange(option.id)}
              className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                preset === option.id ? "bip-toggle-active" : "bip-toggle"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {preset === "custom" && (
        <div className="grid gap-3 md:grid-cols-2">
          <label className="space-y-1">
            <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
              Start Date
            </span>
            <input
              type="date"
              value={customRange.startDate ?? ""}
              min={availableStartDate ?? undefined}
              max={customRange.endDate ?? availableEndDate ?? undefined}
              onChange={(event) =>
                onCustomRangeChange({
                  ...customRange,
                  startDate: event.target.value || null,
                })
              }
              className="bip-input w-full rounded-xl px-3 py-2 text-sm"
            />
          </label>
          <label className="space-y-1">
            <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
              End Date
            </span>
            <input
              type="date"
              value={customRange.endDate ?? ""}
              min={customRange.startDate ?? availableStartDate ?? undefined}
              max={availableEndDate ?? undefined}
              onChange={(event) =>
                onCustomRangeChange({
                  ...customRange,
                  endDate: event.target.value || null,
                })
              }
              className="bip-input w-full rounded-xl px-3 py-2 text-sm"
            />
          </label>
        </div>
      )}

      {availableStartDate && availableEndDate ? (
        <p className="text-xs text-[var(--muted)]">
          Available shot dates: {availableStartDate} to {availableEndDate}
        </p>
      ) : (
        <p className="text-xs text-[var(--muted)]">
          Date windows activate once persisted shot dates are available for this selection.
        </p>
      )}
    </div>
  );
}
