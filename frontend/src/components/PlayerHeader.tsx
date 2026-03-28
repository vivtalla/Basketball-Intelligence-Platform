import Image from "next/image";
import type { PlayerProfile, SeasonStats } from "@/lib/types";
import StatCard from "./StatCard";
import { usePlayerPercentiles } from "@/hooks/usePlayerStats";

interface PlayerHeaderProps {
  profile: PlayerProfile;
  currentSeason?: SeasonStats | null;
}

const PERCENTILE_LABELS: Record<string, string> = {
  pts_pg: "PPG",
  reb_pg: "RPG",
  ast_pg: "APG",
  ts_pct: "TS%",
  per: "PER",
  bpm: "BPM",
};

function pctColor(pct: number): string {
  if (pct >= 90) return "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300";
  if (pct >= 75) return "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300";
  if (pct >= 50) return "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300";
  return "bg-red-50 text-red-500 dark:bg-red-900/20 dark:text-red-400";
}

function ordinal(n: number): string {
  if (n >= 11 && n <= 13) return `${n}th`;
  const s = ["th", "st", "nd", "rd"];
  return `${n}${s[n % 10] ?? "th"}`;
}

export default function PlayerHeader({
  profile,
  currentSeason,
}: PlayerHeaderProps) {
  const { data: pctData } = usePlayerPercentiles(
    profile.id,
    currentSeason?.season ?? null
  );

  const draftInfo =
    profile.draft_year && profile.draft_year !== "Undrafted"
      ? `${profile.draft_year} Round ${profile.draft_round}, Pick ${profile.draft_number}`
      : "Undrafted";

  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 p-6 mb-6">
      <div className="flex flex-col md:flex-row gap-6">
        {/* Headshot */}
        <div className="flex-shrink-0">
          <div className="relative w-40 h-40 rounded-2xl overflow-hidden bg-gray-100 dark:bg-gray-700">
            <Image
              src={
                profile.headshot_url ||
                "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect fill='%23374151' width='100' height='100'/%3E%3Ctext x='50' y='55' text-anchor='middle' fill='%239CA3AF' font-size='40'%3E%3F%3C/text%3E%3C/svg%3E"
              }
              alt={profile.full_name}
              fill
              className="object-cover"
              unoptimized
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

          {/* Percentile badges */}
          {pctData && (
            <div className="flex flex-wrap gap-1.5 mb-4">
              {Object.entries(PERCENTILE_LABELS).map(([stat, label]) => {
                const pct = pctData.percentiles[stat];
                if (pct == null) return null;
                return (
                  <span
                    key={stat}
                    title={`${label}: ${ordinal(pct)} percentile vs players in ${pctData.season}`}
                    className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${pctColor(pct)}`}
                  >
                    {label}
                    <span className="font-semibold">{ordinal(pct)}</span>
                  </span>
                );
              })}
            </div>
          )}

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
