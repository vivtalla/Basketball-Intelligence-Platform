"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { useRouter, useSearchParams } from "next/navigation";
import { usePlayerSearch } from "@/hooks/usePlayerSearch";
import { usePlayerProfile, usePlayerCareerStats } from "@/hooks/usePlayerStats";
import ComparisonView from "@/components/ComparisonView";

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
      <div className="bip-panel flex items-center gap-3 rounded-2xl p-4">
        <div className="relative h-14 w-14 shrink-0 overflow-hidden rounded-full border border-[var(--border)] bg-[var(--surface-alt)]">
          <Image
            src={profile.headshot_url}
            alt={profile.full_name}
            fill
            className="object-cover object-top"
            onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
          />
        </div>
        <div className="flex-1 min-w-0">
          <div className="truncate font-semibold text-[var(--foreground)]">{profile.full_name}</div>
          <div className="text-xs text-[var(--muted)]">
            {profile.team_name || "Free Agent"} · {profile.position || "—"}
          </div>
        </div>
        <button
          onClick={onClear}
          className="bip-link shrink-0 text-xs"
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
          className="bip-input w-full rounded-2xl px-4 py-4 pr-10 text-[var(--foreground)]"
        />
        {isLoading && (
          <div className="absolute right-4 top-1/2 -translate-y-1/2">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-[var(--surface-alt)] border-t-[var(--accent)]" />
          </div>
        )}
      </div>

      {showDropdown && (
        <div className="bip-panel absolute left-0 right-0 top-full z-50 mt-1 overflow-hidden rounded-xl">
          {results.length === 0 && !isLoading ? (
            <div className="px-4 py-3 text-sm text-[var(--muted)]">No players found</div>
          ) : (
            results.slice(0, 6).map((player) => (
              <button
                key={player.id}
                onMouseDown={() => {
                  onSelect(player.id);
                  setQuery("");
                }}
                className="w-full px-4 py-3 text-left transition-colors hover:bg-[rgba(216,228,221,0.34)]"
              >
                <span className="font-medium text-[var(--foreground)]">{player.full_name}</span>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs ${
                    player.is_active
                      ? "bip-success"
                      : "bg-[var(--surface-alt)] text-[var(--muted)]"
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
        <Link href="/" className="bip-link inline-flex items-center gap-1 text-sm">
          ← Back to Home
        </Link>
      </div>

      <div className="bip-panel-strong mb-8 rounded-[2rem] p-8">
        <p className="bip-kicker">Compare</p>
        <h1 className="bip-display mt-3 text-3xl font-semibold text-[var(--foreground)]">Compare Players</h1>
        <p className="mt-2 text-[var(--muted)]">Search for two players to compare their stats side by side.</p>
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
        <div className="flex items-center justify-center gap-3 py-16 text-[var(--muted)]">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-[var(--accent)] border-t-transparent" />
          <span className="text-sm">Loading player data…</span>
        </div>
      )}

      {/* Empty state */}
      {!p1Id && !p2Id && (
        <div className="bip-empty py-16 text-center rounded-[2rem]">
          <div className="text-5xl mb-4">⚖️</div>
          <p className="text-lg font-medium text-[var(--foreground)]">Select two players to compare</p>
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
