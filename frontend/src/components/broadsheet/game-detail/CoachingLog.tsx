"use client";

/**
 * Sprint 77 (Stream B / EB3): Coaching log table — empty-state v1.
 * Per-game coaching adjustments aren't yet captured in the database;
 * we render the documented placeholder copy inside a parchment panel.
 */

export default function CoachingLog() {
  return (
    <section
      className="bip-panel rounded-[1.85rem] px-6 py-7"
      style={{ background: "rgba(255,249,241,0.6)" }}
    >
      <div className="mb-4 flex items-end justify-between gap-3">
        <div>
          <p className="bip-kicker">Coaching log</p>
          <h2
            className="bip-display mt-2 font-bold text-[var(--foreground)]"
            style={{ fontSize: "clamp(1.4rem, 2vw, 1.85rem)", letterSpacing: "-0.02em" }}
          >
            Coaching Adjustments
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
          No coaching adjustments captured for this game.
        </p>
        <p
          className="mt-2 text-sm italic"
          style={{ fontFamily: "var(--font-display)", color: "var(--muted)" }}
        >
          (Coming soon.)
        </p>
      </div>
    </section>
  );
}
