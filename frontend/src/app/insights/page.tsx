"use client";

import { useState } from "react";
import { TrajectoryTracker } from "@/components/TrajectoryTracker";
import UsageEfficiencyDashboard from "@/components/UsageEfficiencyDashboard";

type Mode = "trajectory" | "usage";

export default function InsightsPage() {
  const [mode, setMode] = useState<Mode>("trajectory");

  return (
    <div className="space-y-8">
      <section className="flex rounded-xl overflow-hidden border border-[var(--border)] w-fit text-sm">
        <button
          onClick={() => setMode("trajectory")}
          className={`px-5 py-2 transition-colors ${
            mode === "trajectory"
              ? "bip-toggle-active"
              : "bip-toggle"
          }`}
        >
          Trajectory Tracker
        </button>
        <button
          onClick={() => setMode("usage")}
          className={`px-5 py-2 transition-colors ${
            mode === "usage"
              ? "bip-toggle-active"
              : "bip-toggle"
          }`}
        >
          Usage vs Efficiency
        </button>
      </section>

      {mode === "trajectory" ? <TrajectoryTracker /> : <UsageEfficiencyDashboard />}
    </div>
  );
}
