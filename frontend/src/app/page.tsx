import PlayerSearchBar from "@/components/PlayerSearchBar";
import HomeLeagueLeaders from "@/components/HomeLeagueLeaders";
import FavoritesList from "@/components/FavoritesList";
import Link from "next/link";

const platformAreas = [
  {
    href: "/standings",
    eyebrow: "League Context",
    title: "Check the standings",
    description:
      "Conference standings with W-L records, last 10, home/away splits, and scoring differential.",
  },
  {
    href: "/player-stats",
    eyebrow: "Player Stats",
    title: "Scan player leaderboards",
    description:
      "Advanced, external, and play-by-play-informed leaderboards across every key stat.",
  },
  {
    href: "/metrics",
    eyebrow: "Metrics Workspace",
    title: "Build your own metric",
    description:
      "Load starter presets, share metric links, and rank the player pool through your own weighted model.",
  },
  {
    href: "/teams",
    eyebrow: "Explore Context",
    title: "Browse team intelligence",
    description:
      "Team efficiency ratings, four factors, roster leaders, and player dashboards.",
  },
  {
    href: "/coverage",
    eyebrow: "Operations",
    title: "Audit PBP sync coverage",
    description:
      "See which teams and players are ready, partial, or missing play-by-play-derived data.",
  },
  {
    href: "/compare",
    eyebrow: "Compare Stars",
    title: "Stack careers side by side",
    description:
      "Put two players in the same frame to compare production, efficiency, and arc.",
  },
  {
    href: "/pre-read",
    eyebrow: "Coach Workflow",
    title: "Build a pre-read deck",
    description:
      "Generate a short printable briefing with focus levers, matchup edges, and tactical adjustments.",
  },
];

export default function HomePage() {
  return (
    <div className="space-y-14">
      {/* Hero */}
      <div className="bip-panel-strong relative overflow-hidden rounded-[2.2rem] px-6 py-14 sm:px-10">
        <div className="absolute inset-x-0 top-0 h-56 bg-gradient-to-b from-[rgba(180,137,61,0.18)] via-[rgba(244,236,222,0)] to-transparent" />
        <div className="absolute right-[-4rem] top-[-5rem] h-56 w-56 rounded-full bg-[rgba(33,72,59,0.12)] blur-3xl" />
        <div className="relative text-center">
          <p className="bip-kicker mb-4">
            CourtVue Labs
          </p>
          <h1 className="bip-display text-5xl font-bold tracking-tight mb-4 text-[var(--foreground)] sm:text-6xl">
            Court-side intelligence,
            <br />
            <span className="text-[var(--accent)]">in full view.</span>
          </h1>
          <p className="text-lg text-[var(--muted)] mb-8 max-w-2xl mx-auto leading-8">
            The basketball-IQ lab where strategy, analytics, and decisions are built and tested.
          </p>
          <PlayerSearchBar />
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <span className="bip-pill">Team rotation intelligence</span>
            <span className="bip-pill">Play-by-play context</span>
            <span className="bip-pill">Analyst-first workflows</span>
          </div>
        </div>
      </div>

      {/* Platform areas */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
        {platformAreas.map((area) => (
          <Link
            key={area.href}
            href={area.href}
            className="group bip-panel rounded-[1.85rem] p-6 hover:-translate-y-1 hover:border-[var(--border-strong)]"
          >
            <p className="bip-kicker">
              {area.eyebrow}
            </p>
            <h2 className="bip-display mt-3 text-2xl font-semibold text-[var(--foreground)]">
              {area.title}
            </h2>
            <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
              {area.description}
            </p>
            <div className="mt-6 text-sm font-medium text-[var(--accent)] group-hover:text-[var(--accent-strong)]">
              Open workspace →
            </div>
          </Link>
        ))}
      </div>

      {/* Watchlist */}
      <FavoritesList />

      {/* Live league leaders */}
      <HomeLeagueLeaders />
    </div>
  );
}
