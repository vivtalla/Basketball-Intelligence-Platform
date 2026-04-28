"use client";

import useSWR from "swr";
import { useMemo } from "react";
import { getPlayoffsToday } from "@/lib/api";
import { useSeasonPhase } from "@/hooks/useSeasonPhase";
import type { PlayoffSeriesGameWithMatchup, PlayoffTodayResponse } from "@/lib/types";

type TickerGame = {
  home: { abbr: string; color: string; score: number | null };
  away: { abbr: string; color: string; score: number | null };
  status: string;
  live: boolean;
};

// Inline team-color map (matches the TEAM_TINT pattern from Sprint 70/72/73).
const TEAM_COLOR: Record<string, string> = {
  ATL: "#e03a3e", BOS: "#007a33", BKN: "#000000", CHA: "#00788c",
  CHI: "#ce1141", CLE: "#6f263d", DET: "#c8102e", IND: "#002d62",
  MIA: "#98002e", MIL: "#00471b", NYK: "#f58426", ORL: "#0077c0",
  PHI: "#006bb6", TOR: "#ce1141", WAS: "#002b5c",
  DAL: "#00538c", DEN: "#0e2240", GSW: "#1d428a", HOU: "#ce1141",
  LAC: "#c8102e", LAL: "#552583", MEM: "#5d76a9", MIN: "#0c2340",
  NOP: "#0c2340", OKC: "#007ac1", PHX: "#1d1160", POR: "#e03a3e",
  SAC: "#5a2d81", SAS: "#bac3c9", UTA: "#002b5c",
};

// Demo fallback when there are no live/recent games (off-season or empty slate).
const DEMO_GAMES: TickerGame[] = [
  { home: { abbr: "OKC", color: "#0072ce", score: 84 }, away: { abbr: "DEN", color: "#0e2240", score: 79 }, status: "Q3 4:12", live: true },
  { home: { abbr: "BOS", color: "#007a33", score: 32 }, away: { abbr: "NYK", color: "#f58426", score: 28 }, status: "Q2 1:48", live: true },
  { home: { abbr: "DAL", color: "#00538c", score: 112 }, away: { abbr: "LAL", color: "#552583", score: 119 }, status: "FINAL", live: false },
  { home: { abbr: "GSW", color: "#1d428a", score: 56 }, away: { abbr: "MIN", color: "#0c2340", score: 61 }, status: "Q3 9:22", live: true },
];

function formatStatus(g: PlayoffSeriesGameWithMatchup): { status: string; live: boolean } {
  if (g.home_pts != null && g.away_pts != null) {
    return { status: `FINAL · G${g.series_game_num} · R${g.round}`, live: false };
  }
  // No score yet — game is scheduled.
  const tipoff = g.game_date ? new Date(`${g.game_date}T19:30:00-07:00`) : null;
  if (tipoff) {
    const fmt = new Intl.DateTimeFormat("en-US", {
      hour: "numeric",
      minute: "2-digit",
      timeZone: "America/Los_Angeles",
    });
    return { status: `${fmt.format(tipoff)} PT · G${g.series_game_num}`, live: false };
  }
  return { status: `G${g.series_game_num} · TBD`, live: false };
}

function mapPlayoffGames(data: PlayoffTodayResponse | undefined): TickerGame[] {
  if (!data || !data.games || data.games.length === 0) return [];
  return data.games.map((g) => {
    const { status, live } = formatStatus(g);
    return {
      home: {
        abbr: g.home_team_abbr ?? "",
        color: TEAM_COLOR[g.home_team_abbr ?? ""] ?? "var(--muted)",
        score: g.home_pts ?? null,
      },
      away: {
        abbr: g.away_team_abbr ?? "",
        color: TEAM_COLOR[g.away_team_abbr ?? ""] ?? "var(--muted)",
        score: g.away_pts ?? null,
      },
      status,
      live,
    };
  });
}

export default function LiveTicker() {
  const { isPlayoffs } = useSeasonPhase();

  const { data: today } = useSWR<PlayoffTodayResponse>(
    isPlayoffs ? ["playoffs-today-ticker"] : null,
    () => getPlayoffsToday(),
    { refreshInterval: 60_000, revalidateOnFocus: true }
  );

  const games = useMemo<TickerGame[]>(() => {
    const live = mapPlayoffGames(today);
    if (live.length > 0) return live;
    return DEMO_GAMES;
  }, [today]);

  // Double the games array so the marquee scrolls seamlessly.
  const doubled = [...games, ...games];

  return (
    <div
      style={{
        position: "sticky",
        top: 0,
        zIndex: 50,
        background: "linear-gradient(180deg, #1d1612 0%, #2a201a 100%)",
        borderBottom: "1px solid rgba(180,137,61,0.32)",
        overflow: "hidden",
        height: 36,
      }}
    >
      <style>{`
        @keyframes cv-ticker-scroll { from { transform: translateX(0); } to { transform: translateX(-50%); } }
        @keyframes cv-live-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }
        .cv-ticker-track { animation: cv-ticker-scroll 90s linear infinite; }
        .cv-ticker-track:hover { animation-play-state: paused; }
        .cv-live-dot { animation: cv-live-pulse 1.4s ease-in-out infinite; }
      `}</style>
      <div
        className="cv-ticker-track"
        style={{ display: "flex", whiteSpace: "nowrap", height: "100%", alignItems: "center", width: "fit-content" }}
      >
        {doubled.map((g, i) => {
          const homeScore = g.home.score;
          const awayScore = g.away.score;
          const homeWins = homeScore != null && awayScore != null && homeScore > awayScore;
          const awayWins = homeScore != null && awayScore != null && awayScore > homeScore;
          return (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "0 22px",
                borderRight: "1px solid rgba(180,137,61,0.16)",
                height: "100%",
                color: "#f4ecde",
                fontFamily: "var(--font-geist-mono)",
                fontSize: 11.5,
                letterSpacing: "0.04em",
              }}
            >
              {g.live && (
                <span
                  className="cv-live-dot"
                  style={{ width: 6, height: 6, borderRadius: "50%", background: "#e85b3c", marginRight: 2, flexShrink: 0 }}
                />
              )}
              <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                <span style={{ width: 8, height: 8, borderRadius: 2, background: g.away.color }} />
                <span style={{ fontWeight: 700 }}>{g.away.abbr}</span>
                <span
                  style={{
                    color: awayWins ? "#f4ecde" : awayScore == null ? "rgba(244,236,222,0.45)" : "rgba(244,236,222,0.55)",
                    fontVariantNumeric: "tabular-nums",
                    fontWeight: 700,
                    minWidth: 26,
                    textAlign: "right",
                  }}
                >
                  {awayScore != null ? awayScore : "—"}
                </span>
              </span>
              <span style={{ opacity: 0.4 }}>·</span>
              <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                <span style={{ width: 8, height: 8, borderRadius: 2, background: g.home.color }} />
                <span style={{ fontWeight: 700 }}>{g.home.abbr}</span>
                <span
                  style={{
                    color: homeWins ? "#f4ecde" : homeScore == null ? "rgba(244,236,222,0.45)" : "rgba(244,236,222,0.55)",
                    fontVariantNumeric: "tabular-nums",
                    fontWeight: 700,
                    minWidth: 26,
                    textAlign: "right",
                  }}
                >
                  {homeScore != null ? homeScore : "—"}
                </span>
              </span>
              <span
                style={{
                  marginLeft: 10,
                  color: g.live ? "#b4893d" : "rgba(244,236,222,0.55)",
                  fontSize: 10,
                  letterSpacing: "0.1em",
                  fontWeight: 700,
                }}
              >
                {g.status}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
