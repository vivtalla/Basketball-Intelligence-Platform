"use client";

import { useMvpSnapshotFreshness } from "@/hooks/usePlayerStats";

function tone(status?: string) {
  if (status === "ready") return "border-emerald-200 bg-emerald-50 text-emerald-800";
  if (status === "partial") return "border-amber-200 bg-amber-50 text-amber-800";
  return "border-gray-200 bg-gray-50 text-gray-600";
}

export default function MvpSnapshotFreshnessBadge({ season }: { season: string | null }) {
  const { data } = useMvpSnapshotFreshness(season);
  if (!season) return null;
  return (
    <div className={`rounded-lg border px-3 py-2 text-xs ${tone(data?.status)}`}>
      <span className="font-semibold">Daily snapshot:</span>{" "}
      {data?.latest_snapshot_date
        ? `${data.latest_snapshot_date} | ${data.profiles.join(", ") || "profiles pending"}`
        : "not captured yet"}
    </div>
  );
}
