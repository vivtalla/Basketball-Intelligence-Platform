"use client";

/**
 * Sprint 77 (Stream B / EB3): Two-column blockquote pull quote for the
 * broadsheet game-detail surface. v1 hardcoded "Editor's note" copy with
 * an optional headline-derived storyline override.
 */

interface QuoteRibbonProps {
  storyline?: string | null;
}

const FALLBACK = "Tonight's storyline tipped on a 12-2 swing from the bench.";

export default function QuoteRibbon({ storyline }: QuoteRibbonProps) {
  const body =
    storyline && storyline.trim().length > 0 ? storyline.trim() : FALLBACK;
  return (
    <section
      className="bip-panel rounded-[1.85rem] px-6 py-7"
      style={{
        background:
          "linear-gradient(180deg, rgba(234,219,183,0.55) 0%, rgba(255,249,241,0.85) 100%)",
        borderColor: "rgba(180,137,61,0.28)",
      }}
    >
      <div className="grid gap-6 lg:grid-cols-[1fr_2fr]">
        <div>
          <p className="bip-kicker">Editor&rsquo;s note</p>
          <p
            className="mt-3 text-xs"
            style={{
              fontFamily: "var(--font-geist-mono)",
              letterSpacing: "0.16em",
              textTransform: "uppercase",
              color: "var(--muted)",
            }}
          >
            From the desk
          </p>
        </div>
        <blockquote
          className="text-[var(--foreground)]"
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "1.15rem",
            lineHeight: 1.55,
          }}
        >
          <span
            aria-hidden
            className="block text-[var(--signal)]"
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "3rem",
              lineHeight: 0.6,
              marginBottom: "0.4rem",
            }}
          >
            &ldquo;
          </span>
          <em>{body}</em>
          <p
            className="mt-4 text-xs"
            style={{
              fontFamily: "var(--font-geist-mono)",
              letterSpacing: "0.16em",
              textTransform: "uppercase",
              color: "var(--muted)",
              fontStyle: "normal",
            }}
          >
            — The Editors
          </p>
        </blockquote>
      </div>
    </section>
  );
}
