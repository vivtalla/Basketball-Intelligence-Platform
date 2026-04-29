"use client";

/**
 * Sprint 77 (Stream B / EB3): Win-probability hero block — wraps the
 * Sprint 70 `<WinProbabilityChart>` and converts the backend
 * `WinProbPoint[]` (`{seconds_elapsed, wp_home, event}`) into the chart's
 * expected `{t, prob, event}` shape (t in minutes).
 */

import WinProbabilityChart from "@/components/WinProbabilityChart";
import type { WinProbPoint as ApiWinProbPoint } from "@/lib/types";

interface WinProbabilityHeroProps {
  points: ApiWinProbPoint[] | null | undefined;
  homeAbbr: string | null;
  awayAbbr: string | null;
}

export default function WinProbabilityHero({
  points,
  homeAbbr,
  awayAbbr,
}: WinProbabilityHeroProps) {
  const ready = Array.isArray(points) && points.length >= 2;

  const chartPoints = ready
    ? (points as ApiWinProbPoint[]).map((p) => ({
        t: p.seconds_elapsed / 60,
        prob: Math.max(0, Math.min(1, p.wp_home)),
        event: p.event ?? undefined,
      }))
    : [];

  return (
    <section
      className="bip-panel rounded-[1.85rem] px-6 py-7"
      style={{ background: "rgba(255,249,241,0.6)" }}
    >
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="bip-kicker">Hero chart · Win probability</p>
          <h2
            className="bip-display mt-2 font-bold text-[var(--foreground)]"
            style={{ fontSize: "clamp(1.6rem, 2.4vw, 2.2rem)", letterSpacing: "-0.02em" }}
          >
            Win Probability
          </h2>
          <p
            className="mt-2 italic text-[var(--muted)]"
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "1rem",
              maxWidth: "44rem",
              lineHeight: 1.55,
            }}
          >
            How tonight breathed — every swing labelled, every quarter dividers
            drawn. {homeAbbr ?? "Home"} above the line; {awayAbbr ?? "Away"} below.
          </p>
        </div>
        <span
          className="rounded-full bg-[var(--accent-soft)] px-3 py-1 text-[10px] font-semibold uppercase text-[var(--accent-strong)]"
          style={{
            fontFamily: "var(--font-geist-mono)",
            letterSpacing: "0.22em",
          }}
        >
          {chartPoints.length} points
        </span>
      </div>

      {ready ? (
        <WinProbabilityChart data={chartPoints} />
      ) : (
        <div
          className="rounded-[1.4rem] border border-dashed px-5 py-10 text-center"
          style={{
            borderColor: "var(--border-strong)",
            background: "rgba(252,255,253,0.4)",
          }}
        >
          <p
            className="text-sm italic"
            style={{ fontFamily: "var(--font-display)", color: "var(--muted)" }}
          >
            Win-probability trace not yet available for this game.
          </p>
        </div>
      )}
    </section>
  );
}
