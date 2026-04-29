"use client";

/**
 * Sprint 77 (Stream B / EB3): State-dependent gradient banner for the
 * broadsheet game-detail surface. The gradient + copy shifts with the
 * game's state (live / halftime / final / scheduled) and surfaces the
 * series, venue, and date.
 */

export type GameState = "live" | "halftime" | "final" | "scheduled";

interface GameStateBannerProps {
  state: GameState;
  series: string;
  venue: string;
  date: string;
}

interface BannerStyle {
  background: string;
  borderColor: string;
  kicker: string;
  kickerColor: string;
  showPulse: boolean;
}

function styleFor(state: GameState): BannerStyle {
  if (state === "live") {
    return {
      background:
        "linear-gradient(135deg, #2b1c14 0%, #4f2a1d 55%, #7f332b 100%)",
      borderColor: "rgba(127,51,43,0.5)",
      kicker: "Live · in progress",
      kickerColor: "#fbe7d8",
      showPulse: true,
    };
  }
  if (state === "halftime") {
    return {
      background:
        "linear-gradient(135deg, #14241d 0%, #1d3a2f 55%, #21483b 100%)",
      borderColor: "rgba(33,72,59,0.55)",
      kicker: "Halftime",
      kickerColor: "#d8e4dd",
      showPulse: false,
    };
  }
  if (state === "final") {
    return {
      background:
        "linear-gradient(135deg, #1f1c19 0%, #2d2925 55%, #3a342e 100%)",
      borderColor: "rgba(58,52,46,0.5)",
      kicker: "Final",
      kickerColor: "#eadbb7",
      showPulse: false,
    };
  }
  return {
    background:
      "linear-gradient(135deg, rgba(234,219,183,0.55) 0%, rgba(255,249,241,0.85) 55%, rgba(216,228,221,0.55) 100%)",
    borderColor: "rgba(180,137,61,0.32)",
    kicker: "Scheduled",
    kickerColor: "var(--signal-ink)",
    showPulse: false,
  };
}

export default function GameStateBanner({
  state,
  series,
  venue,
  date,
}: GameStateBannerProps) {
  const style = styleFor(state);
  const isMuted = state === "scheduled";

  return (
    <section
      className="rounded-[1.85rem] border px-7 py-6"
      style={{
        background: style.background,
        borderColor: style.borderColor,
        boxShadow: "var(--shadow)",
      }}
      aria-label={`Game state: ${state}`}
    >
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-3">
          {style.showPulse && (
            <span
              aria-hidden
              className="relative inline-flex h-3 w-3"
            >
              <span
                className="absolute inline-flex h-full w-full animate-ping rounded-full"
                style={{ backgroundColor: "#e85440", opacity: 0.55 }}
              />
              <span
                className="relative inline-flex h-3 w-3 rounded-full"
                style={{ backgroundColor: "#e85440" }}
              />
            </span>
          )}
          <span
            className="text-[11px] font-semibold uppercase"
            style={{
              fontFamily: "var(--font-geist-mono)",
              letterSpacing: "0.22em",
              color: style.kickerColor,
            }}
          >
            {style.kicker}
          </span>
        </div>
        <span
          aria-hidden
          className="hidden h-4 w-px sm:inline-block"
          style={{
            backgroundColor: isMuted
              ? "rgba(53,41,33,0.18)"
              : "rgba(252,255,253,0.25)",
          }}
        />
        <p
          className="text-sm"
          style={{
            color: isMuted ? "var(--foreground)" : "#fbf4e9",
            fontFamily: "var(--font-display)",
            fontStyle: "italic",
          }}
        >
          <span style={{ fontWeight: 600 }}>{series}</span>
          <span aria-hidden> · </span>
          <span>{venue}</span>
          <span aria-hidden> · </span>
          <span>{date}</span>
        </p>
      </div>
    </section>
  );
}
