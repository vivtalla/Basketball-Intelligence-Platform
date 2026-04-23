"use client";

import { useH2HHistory } from "@/hooks/usePlayerStats";
import type { H2HGame } from "@/lib/types";

interface H2HHistoryCardProps {
  teamAbbreviation: string;
  opponentAbbreviation: string;
  season: string;
}

export default function H2HHistoryCard({
  teamAbbreviation,
  opponentAbbreviation,
  season,
}: H2HHistoryCardProps) {
  const { data, isLoading, error } = useH2HHistory(
    teamAbbreviation,
    opponentAbbreviation,
    season
  );

  if (error || !data) {
    return null;
  }

  if (isLoading) {
    return (
      <div className="p-3 bg-[var(--surface-alt)] rounded border border-[var(--border-color)] text-xs text-[var(--muted)]">
        Loading head-to-head history...
      </div>
    );
  }

  return (
    <div className="p-3 bg-[var(--surface-alt)] rounded border border-[var(--border-color)] space-y-2">
      <div className="flex items-center justify-between">
        <div className="text-xs font-semibold text-[var(--text-secondary)]">H2H Series</div>
        <div className="flex items-center gap-2">
          <span className="px-2 py-1 bg-[var(--surface)] rounded text-xs font-bold">
            {data.series_record}
          </span>
          {data.avg_margin !== null && (
            <span
              className={`text-xs font-medium ${
                data.avg_margin > 0 ? "text-green-600" : data.avg_margin < 0 ? "text-red-600" : ""
              }`}
            >
              {data.avg_margin > 0 ? "+" : ""}{data.avg_margin.toFixed(1)} avg
            </span>
          )}
        </div>
      </div>

      {data.games && data.games.length > 0 && (
        <div className="flex gap-1">
          {data.games.slice(0, 5).map((game: H2HGame) => (
            <div
              key={game.game_id}
              className={`w-6 h-6 rounded text-xs font-bold flex items-center justify-center ${
                game.result === "W"
                  ? "bg-green-600 text-white"
                  : game.result === "L"
                  ? "bg-red-600 text-white"
                  : "bg-gray-600 text-white"
              }`}
              title={`${game.game_date || "TBD"}: ${game.result}`}
            >
              {game.result}
            </div>
          ))}
        </div>
      )}

      {data.last_meeting_date && (
        <div className="text-xs text-[var(--muted)]">
          Last meeting: {data.last_meeting_date} ({data.last_meeting_result})
        </div>
      )}
    </div>
  );
}
