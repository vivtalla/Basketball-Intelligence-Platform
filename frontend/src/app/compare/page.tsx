"use client";

import { Suspense, useState, useRef } from "react";
import Link from "next/link";
import Image from "next/image";
import { useRouter, useSearchParams } from "next/navigation";
import { usePlayerSearch } from "@/hooks/usePlayerSearch";
import { usePlayerProfile, usePlayerCareerStats } from "@/hooks/usePlayerStats";
import ComparisonView from "@/components/ComparisonView";
import type { PlayerProfile, CareerStatsResponse } from "@/lib/types";

// ─── Player search slot ───────────────────────────────────────────────────────

interface PlayerSlotProps {
  slotLabel: string;
  selectedId: number | null;
  onSelect: (id: number) => void;
  onClear: () => void;
}

function PlayerSlot({ slotLabel, selectedId, onSelect, onClear }: PlayerSlotProps) {
  const { query, setQuery, results, isLoading } = usePlayerSearch();
  const [isFocused, setIsFocused] = useState(false);
  const { data: profile } = usePlayerProfile(selectedId);

  const showDropdown = isFocused && query.length >= 2;

  if (selectedId && profile) {
    return (
      <div className="flex items-center gap-3 bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 p-4">
        <div className="relative w-14 h-14 rounded-full overflow-hidden bg-gray-100 dark:bg-gray-700 shrink-0 border border-gray-200 dark:border-gray-600">
          <Image
            src={profile.headshot_url}
            alt={profile.full_name}
            fill
            className="object-cover object-top"
            onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
          />
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-gray-900 dark:text-gray-100 truncate">{profile.full_name}</div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            {profile.team_name || "Free Agent"} · {profile.position || "—"}
          </div>
        </div>
        <button
          onClick={onClear}
          className="text-xs text-gray-400 hover:text-red-500 dark:hover:text-red-400 transition-colors shrink-0"
        >
          Change
        </button>
      </div>
    );
  }

  return (
    <div className="relative">
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setTimeout(() => setIsFocused(false), 200)}
          placeholder={`Search ${slotLabel}...`}
          className="w-full pl-4 pr-10 py-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all text-gray-900 dark:text-gray-100"
        />
        {isLoading && (
          <div className="absolute right-4 top-1/2 -translate-y-1/2">
            <div className="w-4 h-4 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
          </div>
        )}
      </div>

      {showDropdown && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-lg overflow-hidden z-50">
          {results.length === 0 && !isLoading ? (
            <div className="px-4 py-3 text-gray-500 text-sm">No players found</div>
          ) : (
            results.slice(0, 6).map((player) => (
              <button
                key={player.id}
                onMouseDown={() => {
                  onSelect(player.id);
                  setQuery("");
                }}
                className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors text-left"
              >
                <span className="font-medium text-gray-900 dark:text-gray-100">{player.full_name}</span>
                <span
                  className={`text-xs px-2 py-0.5 rounded-full ${
                    player.is_active
                      ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
                      : "bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400"
                  }`}
                >
                  {player.is_active ? "Active" : "Retired"}
                </span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}

// ─── Inner page (needs Suspense for useSearchParams) ─────────────────────────

function ComparePageInner() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const p1Id = searchParams.get("p1") ? Number(searchParams.get("p1")) : null;
  const p2Id = searchParams.get("p2") ? Number(searchParams.get("p2")) : null;

  const { data: profile1 } = usePlayerProfile(p1Id);
  const { data: career1 } = usePlayerCareerStats(p1Id);
  const { data: profile2 } = usePlayerProfile(p2Id);
  const { data: career2 } = usePlayerCareerStats(p2Id);

  function selectPlayer(slot: 1 | 2, id: number) {
    const params = new URLSearchParams(searchParams.toString());
    params.set(slot === 1 ? "p1" : "p2", String(id));
    router.push(`/compare?${params.toString()}`);
  }

  function clearPlayer(slot: 1 | 2) {
    const params = new URLSearchParams(searchParams.toString());
    params.delete(slot === 1 ? "p1" : "p2");
    router.push(`/compare?${params.toString()}`);
  }

  const bothReady = profile1 && career1 && profile2 && career2;
  const loadingComparison = (p1Id || p2Id) && (!profile1 || !profile2 || !career1 || !career2);

  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-6">
        <Link href="/" className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-blue-500 dark:text-gray-400 dark:hover:text-blue-400 transition-colors">
          ← Back to Home
        </Link>
      </div>

      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">Compare Players</h1>
        <p className="text-gray-500 dark:text-gray-400">Search for two players to compare their stats side by side.</p>
      </div>

      {/* Search slots */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
        <PlayerSlot
          slotLabel="Player 1"
          selectedId={p1Id}
          onSelect={(id) => selectPlayer(1, id)}
          onClear={() => clearPlayer(1)}
        />
        <PlayerSlot
          slotLabel="Player 2"
          selectedId={p2Id}
          onSelect={(id) => selectPlayer(2, id)}
          onClear={() => clearPlayer(2)}
        />
      </div>

      {/* Loading state */}
      {loadingComparison && !bothReady && (
        <div className="flex items-center justify-center py-16 gap-3 text-gray-400">
          <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm">Loading player data…</span>
        </div>
      )}

      {/* Empty state */}
      {!p1Id && !p2Id && (
        <div className="text-center py-16 text-gray-400 dark:text-gray-500">
          <div className="text-5xl mb-4">⚖️</div>
          <p className="text-lg font-medium">Select two players to compare</p>
          <p className="text-sm mt-1">Search above to get started</p>
        </div>
      )}

      {/* Comparison */}
      {bothReady && (
        <ComparisonView
          playerA={{ profile: profile1, career: career1 }}
          playerB={{ profile: profile2, career: career2 }}
        />
      )}
    </div>
  );
}

// ─── Page export (Suspense required for useSearchParams) ─────────────────────

export default function ComparePage() {
  return (
    <Suspense>
      <ComparePageInner />
    </Suspense>
  );
}
