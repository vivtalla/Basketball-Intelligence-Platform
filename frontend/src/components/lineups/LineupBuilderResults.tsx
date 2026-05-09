"use client";

import type { LineupBuilderResult, LineupLeaderboardEntry } from "@/lib/types";
import LineupArchetypePill from "./LineupArchetypePill";
import LineupConfidenceBadge from "./LineupConfidenceBadge";

function fmtSigned(v: number | null | undefined, digits = 1): string {
  if (v == null) return "—";
  return `${v >= 0 ? "+" : ""}${v.toFixed(digits)}`;
}

function signColor(v: number | null | undefined): string {
  if (v == null) return "text-gray-500 dark:text-gray-400";
  return v >= 0 ? "text-green-600 dark:text-green-400" : "text-red-500 dark:text-red-400";
}

function MatchQualityBanner({ quality }: { quality: LineupBuilderResult["match_quality"] }) {
  const styles: Record<string, { bg: string; text: string; label: string }> = {
    exact: { bg: "bg-green-50 dark:bg-green-900/20 border-green-300 dark:border-green-700", text: "text-green-700 dark:text-green-400", label: "Exact match found" },
    partial: { bg: "bg-yellow-50 dark:bg-yellow-900/20 border-yellow-300 dark:border-yellow-700", text: "text-yellow-700 dark:text-yellow-400", label: "No exact match — showing closest lineups" },
    none: { bg: "bg-red-50 dark:bg-red-900/20 border-red-300 dark:border-red-700", text: "text-red-600 dark:text-red-400", label: "No matching lineups found in database" },
  };
  const s = styles[quality] ?? styles.none;
  return (
    <div className={`rounded-lg border px-3 py-2 text-sm font-semibold ${s.bg} ${s.text}`}>
      {s.label}
    </div>
  );
}

function LineupCard({ entry, label }: { entry: LineupLeaderboardEntry; label?: string }) {
  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 space-y-3">
      {label && (
        <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">{label}</p>
      )}
      <div className="flex flex-wrap gap-1">
        {entry.player_names.map((n, i) => (
          <span key={i} className="rounded bg-gray-100 dark:bg-gray-700 px-2 py-0.5 text-xs text-gray-700 dark:text-gray-300">
            {n}
          </span>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-3 text-xs">
        <span className="text-gray-500 dark:text-gray-400">
          Team: <span className="font-medium text-gray-700 dark:text-gray-200">{entry.team_abbreviation ?? "—"}</span>
        </span>
        <span className="text-gray-500 dark:text-gray-400">
          {entry.possessions?.toLocaleString() ?? "—"} poss
        </span>
        <span className="text-gray-500 dark:text-gray-400">
          {entry.minutes != null ? `${entry.minutes.toFixed(0)} min` : "—"}
        </span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {[
          { label: "Net Rtg", value: fmtSigned(entry.net_rating), color: signColor(entry.net_rating) },
          { label: "Shrunk Net", value: fmtSigned(entry.shrunk_net_rating), color: signColor(entry.shrunk_net_rating) },
          { label: "vs Team", value: fmtSigned(entry.net_vs_baseline), color: signColor(entry.net_vs_baseline) },
          { label: "ORTG / DRTG", value: `${entry.ortg?.toFixed(1) ?? "—"} / ${entry.drtg?.toFixed(1) ?? "—"}`, color: "text-gray-700 dark:text-gray-200" },
        ].map(({ label, value, color }) => (
          <div key={label} className="flex flex-col rounded-lg bg-gray-50 dark:bg-gray-800/60 px-2 py-1.5 text-center">
            <span className="text-[9px] uppercase tracking-wide text-gray-400 dark:text-gray-500">{label}</span>
            <span className={`text-sm font-bold tabular-nums ${color}`}>{value}</span>
          </div>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <LineupArchetypePill archetype={entry.archetype} size="md" />
        <LineupConfidenceBadge confidence={entry.confidence} possessions={entry.possessions} />
      </div>
    </div>
  );
}

function PlayerRemovalGrid({ result }: { result: LineupBuilderResult }) {
  const { player_removal_impacts } = result;
  if (player_removal_impacts.length === 0) return null;

  return (
    <div className="space-y-2">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
        Player removal impact — what happens when each player sits
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
        {player_removal_impacts.map((imp) => (
          <div
            key={imp.player_id}
            className="rounded-lg border border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60 px-3 py-2"
          >
            <p className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">{imp.player_name}</p>
            <div className="flex items-center gap-3 text-xs">
              {imp.avg_net_rating_without != null ? (
                <>
                  <span className="text-gray-500 dark:text-gray-400">
                    Without: <span className={`font-semibold ${signColor(imp.avg_net_rating_without)}`}>{fmtSigned(imp.avg_net_rating_without)}</span>
                  </span>
                  {imp.delta_vs_full != null && (
                    <span className={`font-semibold ${signColor(imp.delta_vs_full)}`}>
                      Δ {fmtSigned(imp.delta_vs_full)}
                    </span>
                  )}
                  <span className="text-gray-400 dark:text-gray-500 text-[10px]">
                    {imp.lineups_without_count} lineup{imp.lineups_without_count !== 1 ? "s" : ""}
                  </span>
                </>
              ) : (
                <span className="text-gray-400 dark:text-gray-500 italic text-[10px]">
                  {imp.note || "No data"}
                </span>
              )}
            </div>
            {imp.note && imp.avg_net_rating_without != null && (
              <p className="text-[10px] text-gray-400 dark:text-gray-500 mt-0.5 italic">{imp.note}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

interface Props {
  result: LineupBuilderResult;
}

export default function LineupBuilderResults({ result }: Props) {
  return (
    <div className="space-y-4">
      <MatchQualityBanner quality={result.match_quality} />

      {result.warnings.length > 0 && (
        <div className="rounded-lg border border-yellow-200 dark:border-yellow-800 bg-yellow-50 dark:bg-yellow-900/10 px-3 py-2 space-y-1">
          {result.warnings.map((w, i) => (
            <p key={i} className="text-xs text-yellow-700 dark:text-yellow-400">{w}</p>
          ))}
        </div>
      )}

      {result.exact_match && (
        <LineupCard entry={result.exact_match} label="Your lineup" />
      )}

      {result.closest_matches.length > 0 && (
        <div className="space-y-3">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
            Closest matching lineups in database
          </p>
          {result.closest_matches.map((m, i) => (
            <LineupCard key={i} entry={m} />
          ))}
        </div>
      )}

      <PlayerRemovalGrid result={result} />
    </div>
  );
}
