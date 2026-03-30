"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { usePlayerSearch } from "@/hooks/usePlayerSearch";

export default function PlayerSearchBar() {
  const { query, setQuery, results, isLoading } = usePlayerSearch();
  const [isFocused, setIsFocused] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const showDropdown = isFocused && query.length >= 2;

  return (
    <div ref={containerRef} className="relative w-full max-w-xl mx-auto">
      <div className="relative">
        <svg
          className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setTimeout(() => setIsFocused(false), 200)}
          placeholder="Search for an NBA player..."
          className="bip-input w-full pl-12 pr-4 py-4 text-lg rounded-[1.4rem] shadow-[var(--shadow)] placeholder:text-[var(--muted)]"
        />
        {isLoading && (
          <div className="absolute right-4 top-1/2 -translate-y-1/2">
            <div className="w-5 h-5 border-2 border-[var(--surface-alt)] border-t-[var(--accent)] rounded-full animate-spin" />
          </div>
        )}
      </div>

      {showDropdown && (
        <div className="absolute top-full left-0 right-0 mt-3 bip-panel rounded-2xl overflow-hidden z-50">
          {results.length === 0 && !isLoading ? (
            <div className="px-4 py-3 text-[var(--muted)] text-sm">
              No players found
            </div>
          ) : (
            results.slice(0, 8).map((player) => (
              <Link
                key={player.id}
                href={`/players/${player.id}`}
                className="flex items-center justify-between px-4 py-3 hover:bg-[rgba(33,72,59,0.08)]"
              >
                <span className="font-medium text-[var(--foreground)]">{player.full_name}</span>
                <span
                  className={`text-xs px-2 py-0.5 rounded-full ${
                    player.is_active
                      ? "bip-success"
                      : "bg-[var(--surface-alt)] text-[var(--muted)]"
                  }`}
                >
                  {player.is_active ? "Active" : "Retired"}
                </span>
              </Link>
            ))
          )}
        </div>
      )}
    </div>
  );
}
