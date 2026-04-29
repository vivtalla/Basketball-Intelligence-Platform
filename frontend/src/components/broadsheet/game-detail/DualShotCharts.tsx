"use client";

/**
 * Sprint 77 (Stream B / EB3): Two side-by-side team-level shot-chart slots.
 * The existing `<ShotChart>` component is keyed on `playerId`, not team or
 * game, and the spec explicitly says we should NOT extend the backend API
 * here. We render a parchment empty-state per team with the documented
 * caveat. When game-level shot data lands we can swap the body to a
 * filtered shot chart without changing the wrapper API.
 */

interface DualShotChartsProps {
  awayAbbr: string | null;
  homeAbbr: string | null;
}

function ShotPanel({ abbr, side }: { abbr: string | null; side: "away" | "home" }) {
  return (
    <div
      className="bip-panel rounded-[1.6rem] px-5 py-6"
      style={{ background: "rgba(255,249,241,0.55)" }}
    >
      <div className="mb-3 flex items-center justify-between gap-3">
        <p className="bip-kicker">{side === "away" ? "Away" : "Home"} · shot map</p>
        <span
          className="rounded-full px-2 py-1 text-[10px] font-semibold uppercase"
          style={{
            background: "var(--surface-alt)",
            color: "var(--foreground)",
            fontFamily: "var(--font-geist-mono)",
            letterSpacing: "0.18em",
          }}
        >
          {abbr ?? "—"}
        </span>
      </div>
      <div
        className="rounded-[1.2rem] border border-dashed px-5 py-12 text-center"
        style={{
          borderColor: "var(--border-strong)",
          background: "rgba(252,255,253,0.4)",
        }}
      >
        <p
          className="bip-display text-base font-semibold"
          style={{ color: "var(--foreground)" }}
        >
          Game-level shot chart not yet wired
        </p>
        <p
          className="mt-2 text-sm italic"
          style={{ fontFamily: "var(--font-display)", color: "var(--muted)" }}
        >
          Per-game team shot maps require a new endpoint. Season-level shot
          maps remain available on each player&rsquo;s profile.
        </p>
      </div>
    </div>
  );
}

export default function DualShotCharts({ awayAbbr, homeAbbr }: DualShotChartsProps) {
  return (
    <section className="space-y-4">
      <div>
        <p className="bip-kicker">Shot maps · both ends</p>
        <h2
          className="bip-display mt-2 font-bold text-[var(--foreground)]"
          style={{ fontSize: "clamp(1.5rem, 2.2vw, 2rem)", letterSpacing: "-0.02em" }}
        >
          Where the shots came from
        </h2>
      </div>
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <ShotPanel abbr={awayAbbr} side="away" />
        <ShotPanel abbr={homeAbbr} side="home" />
      </div>
    </section>
  );
}
