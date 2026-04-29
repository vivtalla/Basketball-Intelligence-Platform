"use client";

/**
 * Sprint 77 (Stream B / EB3): Three-column score banner for the broadsheet
 * variant. Away card | center status block | home card. Uses parchment
 * cream background and big mono numerals.
 */

import type { GameState } from "./GameStateBanner";

interface TeamCardData {
  abbr: string;
  name: string;
  record: string | null;
  score: number | null;
}

interface BroadsheetScoreBannerProps {
  away: TeamCardData;
  home: TeamCardData;
  state: GameState;
  seriesState: string | null;
  tipoffLabel: string | null;
}

function statusLabel(state: GameState): string {
  if (state === "live") return "Live";
  if (state === "halftime") return "Halftime";
  if (state === "final") return "Final";
  return "Scheduled";
}

function statusPillStyle(state: GameState): React.CSSProperties {
  if (state === "live") {
    return { background: "var(--danger-ink)", color: "#fbf4e9" };
  }
  if (state === "halftime") {
    return { background: "var(--accent)", color: "var(--accent-ink)" };
  }
  if (state === "final") {
    return { background: "var(--accent-strong)", color: "var(--accent-ink)" };
  }
  return { background: "var(--signal-soft)", color: "var(--signal-ink)" };
}

function TeamCard({ team }: { team: TeamCardData }) {
  return (
    <div className="flex flex-col items-center gap-2 px-4 py-2">
      <div
        aria-hidden
        className="flex h-14 w-14 items-center justify-center rounded-full border"
        style={{
          background: "var(--surface-strong)",
          borderColor: "var(--border-strong)",
          fontFamily: "var(--font-geist-mono)",
          fontWeight: 700,
          fontSize: "0.95rem",
          letterSpacing: "0.08em",
          color: "var(--foreground)",
        }}
      >
        {team.abbr}
      </div>
      <div
        className="text-[11px] font-semibold uppercase"
        style={{
          fontFamily: "var(--font-geist-mono)",
          letterSpacing: "0.18em",
          color: "var(--muted)",
        }}
      >
        {team.abbr}
      </div>
      <div
        className="text-center"
        style={{
          fontFamily: "var(--font-display)",
          fontSize: "1.05rem",
          fontWeight: 600,
          color: "var(--foreground)",
        }}
      >
        {team.name}
      </div>
      {team.record && (
        <div
          className="text-[11px]"
          style={{
            fontFamily: "var(--font-geist-mono)",
            letterSpacing: "0.12em",
            color: "var(--muted)",
          }}
        >
          {team.record}
        </div>
      )}
      <div
        className="mt-2 tabular-nums"
        style={{
          fontFamily: "var(--font-geist-mono)",
          fontSize: "clamp(2.6rem, 5vw, 4rem)",
          fontWeight: 700,
          color: "var(--foreground)",
          lineHeight: 1,
        }}
      >
        {team.score == null ? "—" : team.score}
      </div>
    </div>
  );
}

export default function BroadsheetScoreBanner({
  away,
  home,
  state,
  seriesState,
  tipoffLabel,
}: BroadsheetScoreBannerProps) {
  return (
    <section
      className="bip-panel-strong rounded-[1.85rem] px-6 py-7"
      style={{
        background: "var(--surface-strong)",
      }}
    >
      <div className="grid grid-cols-1 items-center gap-6 md:grid-cols-[1fr_auto_1fr]">
        <TeamCard team={away} />

        <div className="flex flex-col items-center gap-3">
          <span
            className="rounded-full px-3 py-1 text-[11px] font-semibold uppercase"
            style={{
              fontFamily: "var(--font-geist-mono)",
              letterSpacing: "0.2em",
              ...statusPillStyle(state),
            }}
          >
            {state === "scheduled" && tipoffLabel ? tipoffLabel : statusLabel(state)}
          </span>
          {seriesState && (
            <span
              className="text-xs"
              style={{
                fontFamily: "var(--font-display)",
                fontStyle: "italic",
                color: "var(--muted)",
              }}
            >
              {seriesState}
            </span>
          )}
          <span
            aria-hidden
            className="block h-px w-12"
            style={{ background: "var(--border-strong)" }}
          />
          <span
            className="text-[10px] uppercase"
            style={{
              fontFamily: "var(--font-geist-mono)",
              letterSpacing: "0.22em",
              color: "var(--muted)",
            }}
          >
            CourtVue
          </span>
        </div>

        <TeamCard team={home} />
      </div>
    </section>
  );
}
