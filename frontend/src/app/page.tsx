import PlayerSearchBar from "@/components/PlayerSearchBar";
import Image from "next/image";
import Link from "next/link";

const featuredPlayers = [
  { id: 2544, name: "LeBron James", team: "LAL" },
  { id: 201939, name: "Stephen Curry", team: "GSW" },
  { id: 203999, name: "Nikola Jokic", team: "DEN" },
  { id: 1629029, name: "Luka Doncic", team: "DAL" },
  { id: 203507, name: "Giannis Antetokounmpo", team: "MIL" },
  { id: 1628369, name: "Jayson Tatum", team: "BOS" },
  { id: 203954, name: "Joel Embiid", team: "PHI" },
  { id: 1629627, name: "Zion Williamson", team: "NOP" },
];

const platformAreas = [
  {
    href: "/leaderboards",
    eyebrow: "Find Leaders",
    title: "Scan the league",
    description:
      "Jump into advanced, external, and play-by-play-informed leaderboards.",
  },
  {
    href: "/teams",
    eyebrow: "Explore Context",
    title: "Browse team intelligence",
    description:
      "View synced rosters, identify team leaders, and branch into player dashboards.",
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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {platformAreas.map((area) => (
          <Link
            key={area.href}
            href={area.href}
            className="group rounded-[1.75rem] border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6 hover:border-blue-400 hover:shadow-lg transition-all"
          >
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-blue-500">
              {area.eyebrow}
            </p>
            <h2 className="mt-3 text-2xl font-semibold text-gray-900 dark:text-gray-100">
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

      {/* Featured Players */}
      <div>
        <div className="mb-4 flex items-end justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold">Featured Players</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Quick-entry stars for demos, comparisons, and play-by-play deep dives.
            </p>
          </div>
          <Link
            href="/teams"
            className="text-sm text-blue-500 hover:text-blue-600 transition-colors"
          >
            Browse teams →
          </Link>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
          {featuredPlayers.map((player) => (
            <Link
              key={player.id}
              href={`/players/${player.id}`}
              className="group bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 hover:border-blue-400 hover:shadow-md transition-all"
            >
              <div className="relative w-full aspect-square rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-700 mb-3">
                <Image
                  src={`https://cdn.nba.com/headshots/nba/latest/1040x760/${player.id}.png`}
                  alt={player.name}
                  fill
                  className="object-cover group-hover:scale-105 transition-transform"
                />
              </div>
              <p className="font-semibold text-sm">{player.name}</p>
              <p className="text-xs text-gray-500">{player.team}</p>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
