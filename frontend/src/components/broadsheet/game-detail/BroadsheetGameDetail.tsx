"use client";

/**
 * Sprint 77 (Stream B / EB3): Composed broadsheet game-detail wrapper.
 *
 * Renders the Broadsheet chrome triplet (StateBanner + Headline +
 * ScoreBanner) followed by the shared 12-module body (delegated to
 * `<SharedGameModules>`). The variant gate (Broadsheet vs Scoreboard,
 * EB4) flips ONLY the chrome — the module bodies are shared between
 * variants and live in `SharedGameModules`.
 */

import type { GameDetailResponse } from "@/lib/types";
import GameStateBanner, { type GameState } from "./GameStateBanner";
import BroadsheetHeadline from "./BroadsheetHeadline";
import BroadsheetScoreBanner from "./BroadsheetScoreBanner";
import GameStoryTimeline from "./GameStoryTimeline";
import SharedGameModules from "./SharedGameModules";
import ShareCardButton from "@/components/share/ShareCardButton";

interface BroadsheetGameDetailProps {
  data: GameDetailResponse;
  /**
   * If `true`, the chrome is suppressed and only the shared module body
   * is rendered. Useful when the parent (e.g. the Scoreboard variant)
   * provides its own chrome but still wants the shared modules below.
   */
  modulesOnly?: boolean;
}

function deriveState(data: GameDetailResponse): GameState {
  const hasFinalScore = data.home_score != null && data.away_score != null;
  if (hasFinalScore) return "final";
  return "scheduled";
}

function deriveSeries(data: GameDetailResponse): string {
  const matchup =
    data.matchup ??
    (data.away_team_abbreviation && data.home_team_abbreviation
      ? `${data.away_team_abbreviation} @ ${data.home_team_abbreviation}`
      : "NBA Game");
  if (data.season) {
    return `${data.season} · ${matchup}`;
  }
  return matchup;
}

function deriveVenue(data: GameDetailResponse): string {
  if (data.home_team_name) {
    return `${data.home_team_name} home floor`;
  }
  if (data.home_team_abbreviation) {
    return `${data.home_team_abbreviation} home floor`;
  }
  return "Venue TBD";
}

function deriveDate(data: GameDetailResponse): string {
  return data.game_date ?? "Date pending";
}

function pickWinner(data: GameDetailResponse): {
  winner: string | null;
  diff: number | null;
} {
  if (data.home_score == null || data.away_score == null) {
    return { winner: null, diff: null };
  }
  const diff = Math.abs(data.home_score - data.away_score);
  if (data.home_score > data.away_score) {
    return { winner: data.home_team_name ?? data.home_team_abbreviation, diff };
  }
  if (data.away_score > data.home_score) {
    return { winner: data.away_team_name ?? data.away_team_abbreviation, diff };
  }
  return { winner: null, diff };
}

function pickTopScorer(data: GameDetailResponse) {
  if (!data.top_players || data.top_players.length === 0) {
    return { name: null as string | null, pts: null as number | null };
  }
  const top = [...data.top_players].sort(
    (a, b) => (b.pts ?? 0) - (a.pts ?? 0)
  )[0];
  return { name: top.player_name, pts: top.pts };
}

export default function BroadsheetGameDetail({
  data,
  modulesOnly = false,
}: BroadsheetGameDetailProps) {
  if (modulesOnly) {
    return <SharedGameModules data={data} />;
  }

  const state = deriveState(data);
  const series = deriveSeries(data);
  const venue = deriveVenue(data);
  const date = deriveDate(data);
  const { winner, diff } = pickWinner(data);
  const top = pickTopScorer(data);

  const fallbackTitle =
    data.away_team_abbreviation && data.home_team_abbreviation
      ? `${data.away_team_abbreviation} at ${data.home_team_abbreviation}`
      : data.matchup ?? "The night, in full";

  const subhead =
    "Possession by possession, swing by swing — the night decoded for the desk.";

  return (
    <div className="space-y-7">
      {/* Sprint 78 (CF1): Share-card button — top-right, parallel to the
          state banner so it stays accessible without crowding the chrome. */}
      <div className="flex justify-end -mb-3">
        <ShareCardButton kind="game" id={data.game_id} />
      </div>

      {/* 1. State banner */}
      <GameStateBanner state={state} series={series} venue={venue} date={date} />

      {/* 2. Headline */}
      <BroadsheetHeadline
        kicker={`The ${data.season ?? "Season"} Edition`}
        winner={winner}
        scoreDiff={diff}
        topScorerName={top.name}
        topScorerPts={top.pts}
        fallbackTitle={fallbackTitle}
        subhead={subhead}
      />

      {/* 3. Score banner */}
      <BroadsheetScoreBanner
        away={{
          abbr: data.away_team_abbreviation ?? "AWY",
          name: data.away_team_name ?? "Away",
          record: null,
          score: data.away_score,
        }}
        home={{
          abbr: data.home_team_abbreviation ?? "HOM",
          name: data.home_team_name ?? "Home",
          record: null,
          score: data.home_score,
        }}
        state={state}
        seriesState={data.matchup ?? null}
        tipoffLabel={null}
      />

      {/* Sprint 78 (CF4): Game Story timeline — top narrative moments,
          mounted between the score banner and the WP hero so users see
          the recap before the deep modules. Renders nothing when the
          page lacks PBP-derived data, so pre-game pages stay calm. */}
      <GameStoryTimeline data={data} />

      {/* 4-12. Shared module body */}
      <SharedGameModules data={data} />
    </div>
  );
}
