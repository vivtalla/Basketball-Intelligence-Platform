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
    href: "/leaderboards",
    eyebrow: "Find Leaders",
    title: "Scan the league",
    description:
      "Advanced, external, and play-by-play-informed leaderboards across every key stat.",
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
];

export default function HomePage() {
  return (
    <div className="space-y-14">
      {/* Hero */}
      <div className="relative overflow-hidden rounded-[2rem] border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-6 py-14 text-center shadow-sm sm:px-10">
        <div className="absolute inset-x-0 top-0 h-40 bg-gradient-to-b from-blue-100 via-cyan-50 to-transparent dark:from-blue-950/40 dark:via-cyan-950/10 dark:to-transparent" />
        <div className="relative">
          <p className="text-sm font-medium uppercase tracking-[0.28em] text-blue-500 mb-4">
            NBA Intelligence Workspace
          </p>
          <h1 className="text-5xl font-bold tracking-tight mb-4">
            Basketball Intelligence
            <br />
            <span className="text-blue-500">Platform</span>
          </h1>
          <p className="text-lg text-gray-500 mb-8 max-w-2xl mx-auto">
            Explore player analytics, team context, and play-by-play-driven
            insights across one connected research surface.
          </p>
          <PlayerSearchBar />
        </div>
      </div>

      {/* Platform areas */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4">
        {platformAreas.map((area) => (
          <Link
            key={area.href}
            href={area.href}
            className="group rounded-[1.75rem] border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6 hover:border-blue-400 hover:shadow-lg transition-all"
          >
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-blue-500">
              {area.eyebrow}
            </p>
            <h2 className="mt-3 text-xl font-semibold text-gray-900 dark:text-gray-100">
              {area.title}
            </h2>
            <p className="mt-3 text-sm leading-6 text-gray-500 dark:text-gray-400">
              {area.description}
            </p>
            <div className="mt-6 text-sm font-medium text-blue-500 group-hover:text-blue-600">
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
