"use client";

/**
 * Sprint 77 (Stream B / EB3): Shared game-detail module body. The 12-module
 * stack BELOW the chrome (state banner + headline + score banner) is shared
 * between the Broadsheet and Scoreboard variants. Only the chrome changes
 * between variants — these modules stay identical.
 *
 * Modules included (in order):
 *   4. WinProbabilityHero          (full width)
 *   5. LeadTracker                 (full width)
 *   6. DualShotCharts              (2-col)
 *   7. LineupGrid                  (full width)
 *   8. PlayerImpactCards           (auto-fit grid)
 *   9. PossessionDiary             (full width)
 *   10. CoachingLog + HustleStats  (2-col)
 *   11. SeriesOddsCard             (full width, only if data present)
 *   12. QuoteRibbon                (full width)
 */

import type { GameDetailResponse } from "@/lib/types";
import WinProbabilityHero from "./WinProbabilityHero";
import LeadTracker from "./LeadTracker";
import DualShotCharts from "./DualShotCharts";
import LineupGrid from "./LineupGrid";
import PlayerImpactCards from "./PlayerImpactCards";
import PossessionDiary from "./PossessionDiary";
import CoachingLog from "./CoachingLog";
import HustleStats from "./HustleStats";
import SeriesOddsCard from "./SeriesOddsCard";
import QuoteRibbon from "./QuoteRibbon";

interface SharedGameModulesProps {
  data: GameDetailResponse;
}

const SECTIONS = [
  { id: "wp", label: "Win prob" },
  { id: "lead", label: "Lead" },
  { id: "shots", label: "Shots" },
  { id: "lineups", label: "Lineups" },
  { id: "impact", label: "Impact" },
  { id: "diary", label: "Diary" },
  { id: "coach-hustle", label: "Coach / Hustle" },
  { id: "odds", label: "Series odds" },
  { id: "boxscore", label: "Box score" },
] as const;

export default function SharedGameModules({ data }: SharedGameModulesProps) {
  return (
    <div className="space-y-7">
      {/* Anchor-link sub-nav */}
      <nav
        aria-label="Game-detail section quick nav"
        className="flex flex-wrap gap-2 rounded-full bg-[rgba(255,249,241,0.5)] p-2"
        style={{ border: "1px solid var(--border)" }}
      >
        {SECTIONS.map((section) => (
          <a
            key={section.id}
            href={`#bs-${section.id}`}
            className="bip-pill"
            style={{
              fontSize: 11,
              fontFamily: "var(--font-geist-mono)",
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              padding: "0.35rem 0.8rem",
              cursor: "pointer",
            }}
          >
            {section.label}
          </a>
        ))}
      </nav>

      <div id="bs-wp">
        <WinProbabilityHero
          points={data.win_probability}
          homeAbbr={data.home_team_abbreviation}
          awayAbbr={data.away_team_abbreviation}
        />
      </div>

      <div id="bs-lead">
        <LeadTracker
          points={data.lead_tracker}
          homeAbbr={data.home_team_abbreviation}
          awayAbbr={data.away_team_abbreviation}
        />
      </div>

      <div id="bs-shots">
        <DualShotCharts
          awayAbbr={data.away_team_abbreviation}
          homeAbbr={data.home_team_abbreviation}
        />
      </div>

      <div id="bs-lineups">
        <LineupGrid
          season={data.season ?? null}
          awayTeamId={data.away_team_id ?? null}
          awayAbbr={data.away_team_abbreviation}
          homeTeamId={data.home_team_id ?? null}
          homeAbbr={data.home_team_abbreviation}
        />
      </div>

      <div id="bs-impact">
        <PlayerImpactCards impacts={data.player_quarter_impact} />
      </div>

      <div id="bs-diary">
        <PossessionDiary diary={data.possession_diary} />
      </div>

      <div id="bs-coach-hustle" className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <CoachingLog />
        <HustleStats />
      </div>

      <div id="bs-odds">
        <SeriesOddsCard history={data.series_odds_history} />
      </div>

      <QuoteRibbon storyline={null} />
    </div>
  );
}
