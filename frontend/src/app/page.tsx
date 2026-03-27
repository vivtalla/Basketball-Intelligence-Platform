import PlayerSearchBar from "@/components/PlayerSearchBar";
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

export default function HomePage() {
  return (
    <div className="space-y-12">
      {/* Hero */}
      <div className="text-center pt-12 pb-8">
        <h1 className="text-5xl font-bold tracking-tight mb-4">
          Basketball Intelligence
          <br />
          <span className="text-blue-500">Platform</span>
        </h1>
        <p className="text-lg text-gray-500 mb-8 max-w-xl mx-auto">
          Explore NBA player analytics with advanced statistics, efficiency
          metrics, and career trends.
        </p>
        <PlayerSearchBar />
      </div>

      {/* Featured Players */}
      <div>
        <h2 className="text-xl font-semibold mb-4">Featured Players</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
          {featuredPlayers.map((player) => (
            <Link
              key={player.id}
              href={`/players/${player.id}`}
              className="group bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 hover:border-blue-400 hover:shadow-md transition-all"
            >
              <div className="w-full aspect-square rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-700 mb-3">
                <img
                  src={`https://cdn.nba.com/headshots/nba/latest/1040x760/${player.id}.png`}
                  alt={player.name}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform"
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
