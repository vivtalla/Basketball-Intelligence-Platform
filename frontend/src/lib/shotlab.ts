"use client";

import type { ShotLabDateRange, ShotLabWindowPreset } from "@/lib/types";

function parseIsoDate(value: string): Date {
  return new Date(`${value}T00:00:00`);
}

function formatIsoDate(value: Date): string {
  return value.toISOString().slice(0, 10);
}

export function mergeAvailableShotDates(dateGroups: Array<string[] | undefined | null>): string[] {
  return Array.from(
    new Set(
      dateGroups.flatMap((group) => group ?? []).filter(Boolean)
    )
  ).sort((left, right) => left.localeCompare(right));
}

export function resolveShotLabRange(
  preset: ShotLabWindowPreset,
  availableDates: string[],
  customRange: ShotLabDateRange
): ShotLabDateRange {
  if (preset === "full" || availableDates.length === 0) {
    return { startDate: null, endDate: null };
  }

  const endDate = availableDates[availableDates.length - 1];

  if (preset === "custom") {
    return {
      startDate: customRange.startDate,
      endDate: customRange.endDate,
    };
  }

  if (preset === "last-5-games" || preset === "last-10-games") {
    const gameCount = preset === "last-5-games" ? 5 : 10;
    const startIndex = Math.max(0, availableDates.length - gameCount);
    return {
      startDate: availableDates[startIndex] ?? availableDates[0] ?? null,
      endDate,
    };
  }

  const end = parseIsoDate(endDate);
  end.setDate(end.getDate() - 29);

  return {
    startDate: formatIsoDate(end),
    endDate,
  };
}

export function clampShotLabCustomRange(
  range: ShotLabDateRange,
  availableStartDate?: string | null,
  availableEndDate?: string | null
): ShotLabDateRange {
  let startDate = range.startDate;
  let endDate = range.endDate;

  if (availableStartDate && startDate && startDate < availableStartDate) {
    startDate = availableStartDate;
  }
  if (availableEndDate && endDate && endDate > availableEndDate) {
    endDate = availableEndDate;
  }
  if (startDate && endDate && startDate > endDate) {
    startDate = endDate;
  }

  return { startDate, endDate };
}
