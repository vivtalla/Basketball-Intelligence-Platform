"use client";

/**
 * Sprint 77 (Stream B / EB3): Hustle stats table — empty-state v1.
 * Per-game hustle stats aren't surfaced by the NBA API; season-aggregate
 * hustle is available on each player's profile. We render the documented
 * placeholder copy inside a parchment panel.
 */

export default function HustleStats() {
  return (
    <section
      className="bip-panel rounded-[1.85rem] px-6 py-7"
      style={{ background: "rgba(255,249,241,0.6)" }}
    >
      <div className="mb-4 flex items-end justify-between gap-3">
        <div>
          <p className="bip-kicker">Hustle</p>
          <h2
            className="bip-display mt-2 font-bold text-[var(--foreground)]"
            style={{ fontSize: "clamp(1.4rem, 2vw, 1.85rem)", letterSpacing: "-0.02em" }}
          >
            Hustle Stats
          </h2>
        </div>
      </div>

      <div
        className="rounded-[1.4rem] border border-dashed px-5 py-10 text-center"
        style={{
          borderColor: "var(--border-strong)",
          background: "rgba(252,255,253,0.4)",
        }}
      >
        <p
          className="bip-display text-base font-semibold"
          style={{ color: "var(--foreground)" }}
        >
          Per-game hustle stats not available from the NBA API.
        </p>
        <p
          className="mt-2 text-sm italic"
          style={{ fontFamily: "var(--font-display)", color: "var(--muted)" }}
        >
          (Season aggregates available on /players/[id].)
        </p>
      </div>
    </section>
  );
}
