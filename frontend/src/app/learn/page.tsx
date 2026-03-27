import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Learn — Basketball Intelligence Platform",
  description: "Explanations of all metrics and data sources used in the Basketball Intelligence Platform.",
};

// ─── Types ───────────────────────────────────────────────────────────────────

interface MetricEntry {
  name: string;
  abbr: string;
  formula?: string;
  description: string;
  source: "NBA.com" | "Calculated" | "External CSV";
  range?: string;
}

interface MetricGroup {
  title: string;
  description: string;
  metrics: MetricEntry[];
}

// ─── Data ────────────────────────────────────────────────────────────────────

const METRIC_GROUPS: MetricGroup[] = [
  {
    title: "Traditional Stats",
    description: "Box score counting stats pulled directly from NBA.com.",
    metrics: [
      { name: "Games Played", abbr: "GP", description: "Total games a player appeared in during the season.", source: "NBA.com" },
      { name: "Games Started", abbr: "GS", description: "Games in which the player was in the starting lineup.", source: "NBA.com" },
      { name: "Minutes Per Game", abbr: "MIN", description: "Average minutes played per game.", source: "NBA.com" },
      { name: "Points Per Game", abbr: "PTS", description: "Average points scored per game.", source: "NBA.com" },
      { name: "Rebounds Per Game", abbr: "REB", description: "Average total rebounds (offensive + defensive) per game.", source: "NBA.com" },
      { name: "Assists Per Game", abbr: "AST", description: "Average assists per game.", source: "NBA.com" },
      { name: "Steals Per Game", abbr: "STL", description: "Average steals per game.", source: "NBA.com" },
      { name: "Blocks Per Game", abbr: "BLK", description: "Average blocked shots per game.", source: "NBA.com" },
      { name: "Turnovers Per Game", abbr: "TOV", description: "Average turnovers committed per game.", source: "NBA.com" },
      { name: "Field Goal %", abbr: "FG%", description: "Percentage of field goal attempts made (FGM / FGA).", source: "NBA.com", range: "30–55%" },
      { name: "3-Point %", abbr: "3P%", description: "Percentage of 3-point attempts made (FG3M / FG3A).", source: "NBA.com", range: "25–45%" },
      { name: "Free Throw %", abbr: "FT%", description: "Percentage of free throw attempts made (FTM / FTA).", source: "NBA.com", range: "60–95%" },
    ],
  },
  {
    title: "Advanced — from NBA.com",
    description: "Advanced metrics fetched from the NBA Stats API. These account for context like pace and shot type.",
    metrics: [
      {
        name: "True Shooting %",
        abbr: "TS%",
        formula: "PTS / (2 × (FGA + 0.44 × FTA))",
        description: "Overall shooting efficiency that accounts for 2-pointers, 3-pointers, and free throws. The 0.44 factor adjusts for the fact that and-one free throws and technical free throws don't count as possessions.",
        source: "NBA.com",
        range: "45–65%",
      },
      {
        name: "Effective Field Goal %",
        abbr: "eFG%",
        formula: "(FGM + 0.5 × FG3M) / FGA",
        description: "Adjusts FG% to account for 3-pointers being worth 50% more than 2-pointers. A player making all 3s at 40% has the same eFG% as one making all 2s at 60%.",
        source: "NBA.com",
        range: "44–62%",
      },
      {
        name: "Usage Rate",
        abbr: "USG%",
        description: "Estimate of the percentage of team possessions a player uses while on the court (via field goal attempts, free throw attempts, and turnovers). League average is ~20%.",
        source: "NBA.com",
        range: "10–35%",
      },
      {
        name: "Offensive Rating",
        abbr: "ORtg",
        description: "Points scored by the player's team per 100 possessions while the player is on the court. League average is around 110–115.",
        source: "NBA.com",
        range: "95–130",
      },
      {
        name: "Defensive Rating",
        abbr: "DRtg",
        description: "Points allowed by the player's team per 100 possessions while the player is on the court. Lower is better. League average is around 110–115.",
        source: "NBA.com",
        range: "95–120",
      },
      {
        name: "Net Rating",
        abbr: "NRtg",
        formula: "ORtg − DRtg",
        description: "The point differential per 100 possessions while the player is on the court. Positive means the team outscores opponents. Elite players often post +5 or better.",
        source: "NBA.com",
        range: "−15 to +15",
      },
      {
        name: "Pace",
        abbr: "Pace",
        description: "Number of possessions per 48 minutes when the player is on the court. Reflects the tempo of play for a given player's lineups.",
        source: "NBA.com",
        range: "96–105",
      },
      {
        name: "Player Impact Estimate",
        abbr: "PIE",
        description: "A player's share of the team's combined box score events (points, rebounds, assists, etc.). Roughly represents overall box-score contribution relative to teammates and opponents.",
        source: "NBA.com",
        range: "5–20%",
      },
    ],
  },
  {
    title: "Calculated Metrics",
    description: "Metrics computed in our backend from box score data. These don't require team-level context and are updated automatically on every sync.",
    metrics: [
      {
        name: "Player Efficiency Rating",
        abbr: "PER",
        formula: "(PTS + REB×1.2 + AST×1.5 + STL×2 + BLK×2 − TOV − missed FG×0.7 − missed FT×0.5 − PF×0.5) / MIN × 36",
        description: "A per-minute rating that rolls all box-score contributions into a single number, scaled to a per-36-minute basis. League average is 15 by definition. Our version uses a simplified Hollinger formula without pace adjustments.",
        source: "Calculated",
        range: "0–40 (avg: 15)",
      },
      {
        name: "Box Plus/Minus",
        abbr: "BPM",
        formula: "(PER − 15) × 0.36 + STL_pg × 0.45 + BLK_pg × 0.2 − max(0, USG% − 20) × 0.03 − 0.5",
        description: "Estimates points above or below a replacement player per 100 possessions, derived purely from the box score. A BPM of 0 equals league average; −2 is replacement level (the minimum playable player). Stars typically post +4 to +10.",
        source: "Calculated",
        range: "−5 to +10 (avg: 0)",
      },
      {
        name: "Win Shares",
        abbr: "WS",
        formula: "(BPM + 2) × (MIN / 2400)",
        description: "Estimated number of wins a player contributes in a season. An average starter (BPM = 0) playing 2400 minutes produces roughly 2 Win Shares. Career totals are the sum across all seasons.",
        source: "Calculated",
        range: "0–20+ per season",
      },
      {
        name: "Value Over Replacement Player",
        abbr: "VORP",
        formula: "(BPM − (−2)) × (MIN / (GP × 240)) × (GP / 82)",
        description: "Win value above what a replacement-level player (BPM = −2) would provide over the same minutes, scaled to an 82-game season. Career totals are summed. An All-Star season is roughly VORP ≥ 2.",
        source: "Calculated",
        range: "−2 to +15 per season",
      },
      {
        name: "DARKO",
        abbr: "DARKO",
        formula: "PER × 0.15 + TS% × 0.5 + age_factor × 6 − USG% × 0.01",
        description: "A projection metric that rewards young, efficient players. The age factor peaks below 24 and decreases linearly — a 21-year-old earns more credit for the same stats than a 28-year-old. Useful for identifying breakout prospects.",
        source: "Calculated",
      },
    ],
  },
  {
    title: "External Import Metrics",
    description: "Metrics sourced from third-party analytics providers and loaded via CSV import. These require manual updates.",
    metrics: [
      {
        name: "Estimated Plus/Minus",
        abbr: "EPM",
        description: "A regression-based estimate of a player's net impact per 100 possessions, incorporating both box score stats and play-by-play data. Sourced from providers like Dunks & Threes or Nylon Calculus.",
        source: "External CSV",
        range: "−10 to +10",
      },
      {
        name: "Regularized Adjusted Plus/Minus",
        abbr: "RAPM",
        description: "A statistically regularized estimate of player impact derived from lineup data, controlling for teammates and opponents. Considered one of the most context-independent player metrics. Sourced from external analytics models.",
        source: "External CSV",
        range: "−10 to +10",
      },
    ],
  },
];

// ─── Data Sources ─────────────────────────────────────────────────────────────

const DATA_SOURCES = [
  {
    title: "NBA.com",
    subtitle: "via nba_api Python library",
    icon: "🏀",
    color: "blue",
    items: [
      "Player bio — name, position, height, weight, birth date, draft info",
      "Career stats — traditional box score stats by season (regular season + playoffs)",
      "Advanced stats — TS%, eFG%, USG%, Offensive/Defensive/Net Rating, PIE, Pace",
    ],
    note: "Requests are rate-limited and cached for 12–24 hours to avoid hammering the NBA Stats API.",
  },
  {
    title: "Backend Calculations",
    subtitle: "advanced_metrics.py",
    icon: "⚙️",
    color: "purple",
    items: [
      "PER, BPM, Win Shares, VORP, DARKO — computed from box score totals",
      "Applied automatically on every player sync",
      "Missing values are backfilled on the first page load for older records",
    ],
    note: "These formulas are approximations. BPM and VORP in particular require team-level context for full accuracy; ours are box-score-only estimates.",
  },
  {
    title: "External CSV Import",
    subtitle: "epm_rapm_import.py",
    icon: "📄",
    color: "green",
    items: [
      "EPM and RAPM — sourced from third-party analytics providers",
      "Loaded manually via import script: python backend/data/epm_rapm_import.py <file.csv>",
      "Expected CSV columns: player_id, season, epm, rapm",
    ],
    note: "EPM/RAPM values will show as — until a CSV is imported. These metrics are optional and not available for all seasons or players.",
  },
];

// ─── Source badge color map ───────────────────────────────────────────────────

const SOURCE_COLORS: Record<MetricEntry["source"], string> = {
  "NBA.com": "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  "Calculated": "bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300",
  "External CSV": "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300",
};

// ─── Components ───────────────────────────────────────────────────────────────

function MetricCard({ metric }: { metric: MetricEntry }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 flex flex-col gap-2">
      <div className="flex items-start justify-between gap-2">
        <div>
          <span className="font-semibold text-gray-900 dark:text-gray-100">{metric.name}</span>
          <span className="ml-2 font-mono text-sm text-gray-500 dark:text-gray-400">({metric.abbr})</span>
        </div>
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full whitespace-nowrap ${SOURCE_COLORS[metric.source]}`}>
          {metric.source}
        </span>
      </div>

      {metric.formula && (
        <div className="text-xs font-mono bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded px-3 py-2 text-gray-600 dark:text-gray-400 break-all">
          {metric.formula}
        </div>
      )}

      <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">{metric.description}</p>

      {metric.range && (
        <p className="text-xs text-gray-400 dark:text-gray-500">
          Typical range: <span className="font-medium text-gray-600 dark:text-gray-300">{metric.range}</span>
        </p>
      )}
    </div>
  );
}

function DataSourceCard({
  source,
}: {
  source: (typeof DATA_SOURCES)[number];
}) {
  const iconBg: Record<string, string> = {
    blue: "bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800",
    purple: "bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800",
    green: "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800",
  };

  return (
    <div className={`rounded-lg border p-5 flex flex-col gap-3 ${iconBg[source.color]}`}>
      <div className="flex items-center gap-3">
        <span className="text-2xl">{source.icon}</span>
        <div>
          <div className="font-semibold text-gray-900 dark:text-gray-100">{source.title}</div>
          <div className="text-xs font-mono text-gray-500 dark:text-gray-400">{source.subtitle}</div>
        </div>
      </div>
      <ul className="space-y-1.5">
        {source.items.map((item, i) => (
          <li key={i} className="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-300">
            <span className="mt-1 text-gray-400">•</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
      <p className="text-xs text-gray-500 dark:text-gray-400 italic border-t border-current/10 pt-2">
        {source.note}
      </p>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function LearnPage() {
  return (
    <div className="max-w-4xl mx-auto">
      {/* Back link */}
      <div className="mb-6">
        <Link href="/" className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-blue-500 dark:text-gray-400 dark:hover:text-blue-400 transition-colors">
          ← Back to Home
        </Link>
      </div>

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">Learn</h1>
        <p className="text-gray-500 dark:text-gray-400">
          Explanations of every stat in the platform and where the data comes from.
        </p>
      </div>

      {/* Section nav pills */}
      <div className="flex gap-2 mb-10">
        <a
          href="#metrics"
          className="px-4 py-1.5 rounded-full text-sm font-medium bg-blue-50 text-blue-700 hover:bg-blue-100 dark:bg-blue-900/30 dark:text-blue-300 dark:hover:bg-blue-900/50 transition-colors"
        >
          Metrics Glossary
        </a>
        <a
          href="#data-sources"
          className="px-4 py-1.5 rounded-full text-sm font-medium bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700 transition-colors"
        >
          Data Sources
        </a>
      </div>

      {/* ── Metrics Glossary ── */}
      <section id="metrics" className="mb-16 scroll-mt-8">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-1">Metrics Glossary</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-8">
          All stats displayed in player dashboards, grouped by category.
        </p>

        <div className="flex flex-col gap-10">
          {METRIC_GROUPS.map((group) => (
            <div key={group.title}>
              <div className="mb-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{group.title}</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">{group.description}</p>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {group.metrics.map((m) => (
                  <MetricCard key={m.abbr} metric={m} />
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Data Sources ── */}
      <section id="data-sources" className="mb-16 scroll-mt-8">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-1">Data Sources</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-8">
          Where each piece of data originates and how it gets into the platform.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {DATA_SOURCES.map((source) => (
            <DataSourceCard key={source.title} source={source} />
          ))}
        </div>
      </section>
    </div>
  );
}
