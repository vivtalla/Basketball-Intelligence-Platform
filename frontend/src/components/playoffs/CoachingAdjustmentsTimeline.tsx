"use client";

import type { PreReadAdjustment } from "@/lib/types";

interface CoachingAdjustmentsTimelineProps {
  adjustments: PreReadAdjustment[];
  /**
   * The 1-indexed game number marked as "current" in the series. Defaults to
   * the last entry. The dot for that index is painted gold; all others are
   * painted forest-green.
   */
  currentGameNum?: number;
}

/**
 * Sprint 73B — horizontal coaching-adjustments timeline rendered on the
 * Pre-Read page when a series_id is present in the URL. Surfaces adjustments
 * already returned by `/api/pre-read` (`PreReadDeckResponse.adjustments`)
 * that were previously not rendered anywhere on the page.
 *
 * The timeline treats each adjustment as a series-level recommendation
 * indexed in order. Numbered dots are connected by a line; expanding cards
 * below show the label + recommendation.
 */
export default function CoachingAdjustmentsTimeline({
  adjustments,
  currentGameNum,
}: CoachingAdjustmentsTimelineProps) {
  if (!adjustments.length) {
    return null;
  }

  const activeIndex =
    currentGameNum != null
      ? Math.min(Math.max(currentGameNum, 1), adjustments.length) - 1
      : adjustments.length - 1;

  return (
    <section className="bip-panel rounded-[1.8rem] p-6">
      <p className="bip-kicker">Coaching adjustments</p>
      <h2 className="bip-display mt-1 text-2xl font-semibold text-[var(--foreground)]">
        Series adjustment timeline
      </h2>
      <p className="mt-2 text-sm leading-6 text-[var(--muted-strong)]">
        Sequenced staff adjustments across the series. The highlighted dot
        marks the current game.
      </p>

      {/* Timeline strip */}
      <div className="mt-6 relative">
        <div
          aria-hidden
          className="absolute left-0 right-0 h-px"
          style={{
            top: 11,
            background: "var(--border)",
          }}
        />
        <ol
          role="list"
          className="relative flex items-start justify-between gap-2 overflow-x-auto pb-1"
        >
          {adjustments.map((adjustment, index) => {
            const isCurrent = index === activeIndex;
            const dotColor = isCurrent ? "var(--signal)" : "var(--accent)";
            const ringColor = isCurrent
              ? "rgba(180,137,61,0.22)"
              : "rgba(33,72,59,0.16)";
            return (
              <li
                key={`${adjustment.label}-${index}`}
                className="flex flex-col items-center min-w-[72px] flex-1"
              >
                <span
                  aria-hidden
                  className="inline-flex items-center justify-center rounded-full text-[10px] font-bold text-[var(--accent-ink)]"
                  style={{
                    width: 22,
                    height: 22,
                    background: dotColor,
                    boxShadow: `0 0 0 4px ${ringColor}`,
                    fontFamily: "var(--font-geist-mono)",
                    letterSpacing: "0.04em",
                  }}
                >
                  {index + 1}
                </span>
                <span
                  className="mt-2 text-[10px] font-semibold uppercase tracking-[0.14em]"
                  style={{ color: isCurrent ? "var(--signal)" : "var(--muted)" }}
                >
                  Game {index + 1}
                </span>
              </li>
            );
          })}
        </ol>
      </div>

      {/* Detail cards */}
      <div className="mt-5 grid gap-3 md:grid-cols-2 lg:grid-cols-3">
        {adjustments.map((adjustment, index) => {
          const isCurrent = index === activeIndex;
          const accentColor = isCurrent ? "var(--signal)" : "var(--accent)";
          return (
            <article
              key={`${adjustment.label}-card-${index}`}
              className="rounded-[1.4rem] border p-4"
              style={{
                borderColor: isCurrent
                  ? "rgba(180,137,61,0.32)"
                  : "var(--border)",
                background: isCurrent
                  ? "rgba(234,219,183,0.32)"
                  : "rgba(255,249,241,0.86)",
              }}
            >
              <div className="flex items-center gap-2">
                <span
                  aria-hidden
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    background: accentColor,
                    flexShrink: 0,
                  }}
                />
                <p
                  className="bip-kicker"
                  style={{ color: accentColor, margin: 0 }}
                >
                  Game {index + 1} · {adjustment.label}
                </p>
              </div>
              <p className="mt-3 text-sm leading-6 text-[var(--foreground)]">
                {adjustment.recommendation}
              </p>
            </article>
          );
        })}
      </div>
    </section>
  );
}
