"use client";

import LiveShotPulse from "@/components/LiveShotPulse";
import Parallax from "@/components/Parallax";
import StandingsLadder, { type LadderTeam } from "@/components/StandingsLadder";
import WinProbabilityChart, { type WinProbPoint } from "@/components/WinProbabilityChart";

const DEMO_LADDER: LadderTeam[] = [
  { rank: 1, name: "Oklahoma City Thunder", abbr: "OKC", color: "#0072ce", w: 58, l: 14, change: 0 },
  { rank: 2, name: "Boston Celtics", abbr: "BOS", color: "#007a33", w: 55, l: 17, change: 1 },
  { rank: 3, name: "Denver Nuggets", abbr: "DEN", color: "#0e2240", w: 52, l: 20, change: -1 },
  { rank: 4, name: "Minnesota Timberwolves", abbr: "MIN", color: "#0c2340", w: 49, l: 23, change: 2 },
  { rank: 5, name: "Dallas Mavericks", abbr: "DAL", color: "#00538c", w: 47, l: 25, change: 0 },
  { rank: 6, name: "New York Knicks", abbr: "NYK", color: "#f58426", w: 46, l: 26, change: 1 },
  { rank: 7, name: "Milwaukee Bucks", abbr: "MIL", color: "#00471b", w: 44, l: 28, change: -2 },
  { rank: 8, name: "Philadelphia 76ers", abbr: "PHI", color: "#006bb6", w: 41, l: 31, change: 0 },
];

const DEMO_WP: WinProbPoint[] = [
  { t: 0, prob: 0.5 },
  { t: 4, prob: 0.55 },
  { t: 8, prob: 0.62, event: "+8 RUN" },
  { t: 12, prob: 0.58 },
  { t: 16, prob: 0.51 },
  { t: 20, prob: 0.46 },
  { t: 24, prob: 0.49 },
  { t: 28, prob: 0.55 },
  { t: 32, prob: 0.63 },
  { t: 36, prob: 0.71, event: "TIMEOUT" },
  { t: 40, prob: 0.66 },
  { t: 44, prob: 0.78, event: "CLUTCH 3" },
  { t: 48, prob: 0.92 },
];

export default function HomeLiveCourt() {
  return (
    <section className="bip-panel rounded-[1.85rem] p-6 sm:p-10 space-y-8">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <p className="bip-kicker">Live Court</p>
          <h2 className="bip-display mt-2 text-3xl font-semibold text-[var(--foreground)]">
            What&apos;s happening across the league
          </h2>
          <p className="mt-2 text-sm text-[var(--muted)] max-w-xl">
            Live shot tracker, real-time conference race, and momentum charts wired straight into our pipeline.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-8 items-start">
        {/* Live shot pulse */}
        <div className="space-y-3">
          <p className="bip-kicker">Live shots · OKC v DEN</p>
          <Parallax strength={10} style={{ width: 280, height: 200 }}>
            <LiveShotPulse width={280} height={200} />
          </Parallax>
          <p className="text-xs text-[var(--muted)] leading-5">
            Each circle pulses on a made or missed attempt. Forest = make, terracotta = miss.
          </p>
        </div>

        {/* Win probability */}
        <div className="space-y-3">
          <p className="bip-kicker">Win probability · BOS v NYK</p>
          <div className="bip-shot-canvas !p-3">
            <WinProbabilityChart data={DEMO_WP} />
          </div>
        </div>
      </div>

      {/* Standings ladder */}
      <div className="space-y-3">
        <p className="bip-kicker">Western Conference race</p>
        <StandingsLadder teams={DEMO_LADDER} />
      </div>
    </section>
  );
}
