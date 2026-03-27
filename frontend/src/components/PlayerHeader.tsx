import type { PlayerProfile, SeasonStats } from "@/lib/types";
import StatCard from "./StatCard";

interface PlayerHeaderProps {
  profile: PlayerProfile;
  currentSeason?: SeasonStats | null;
}

export default function PlayerHeader({
  profile,
  currentSeason,
}: PlayerHeaderProps) {
  const draftInfo =
    profile.draft_year && profile.draft_year !== "Undrafted"
      ? `${profile.draft_year} Round ${profile.draft_round}, Pick ${profile.draft_number}`
      : "Undrafted";

  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 p-6 mb-6">
      <div className="flex flex-col md:flex-row gap-6">
        {/* Headshot */}
        <div className="flex-shrink-0">
          <div className="w-40 h-40 rounded-2xl overflow-hidden bg-gray-100 dark:bg-gray-700">
            <img
              src={profile.headshot_url}
              alt={profile.full_name}
              className="w-full h-full object-cover"
              onError={(e) => {
                (e.target as HTMLImageElement).src =
                  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect fill='%23374151' width='100' height='100'/%3E%3Ctext x='50' y='55' text-anchor='middle' fill='%239CA3AF' font-size='40'%3E%3F%3C/text%3E%3C/svg%3E";
              }}
            />
          </div>
        </div>

        {/* Bio */}
        <div className="flex-grow">
          <div className="flex items-baseline gap-3 mb-2">
            <h1 className="text-3xl font-bold">{profile.full_name}</h1>
            {profile.jersey && (
              <span className="text-2xl text-gray-400">#{profile.jersey}</span>
            )}
          </div>

          <div className="flex flex-wrap gap-2 mb-4">
            <span className="px-3 py-1 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded-full text-sm font-medium">
              {profile.team_name || "Free Agent"}
            </span>
            {profile.position && (
              <span className="px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-full text-sm">
                {profile.position}
              </span>
            )}
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-2 text-sm text-gray-600 dark:text-gray-400">
            <div>
              <span className="text-gray-400">Height:</span>{" "}
              <span className="text-foreground">{profile.height}</span>
            </div>
            <div>
              <span className="text-gray-400">Weight:</span>{" "}
              <span className="text-foreground">{profile.weight} lbs</span>
            </div>
            <div>
              <span className="text-gray-400">Country:</span>{" "}
              <span className="text-foreground">{profile.country}</span>
            </div>
            <div>
              <span className="text-gray-400">Draft:</span>{" "}
              <span className="text-foreground">{draftInfo}</span>
            </div>
          </div>
        </div>

        {/* Quick Stats */}
        {currentSeason && (
          <div className="grid grid-cols-3 gap-3 flex-shrink-0">
            <StatCard label="PPG" value={currentSeason.pts_pg} />
            <StatCard label="RPG" value={currentSeason.reb_pg} />
            <StatCard label="APG" value={currentSeason.ast_pg} />
          </div>
        )}
      </div>
    </div>
  );
}
