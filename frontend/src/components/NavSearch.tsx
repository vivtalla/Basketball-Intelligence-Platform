"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { usePlayerSearch } from "@/hooks/usePlayerSearch";

export default function NavSearch() {
  const router = useRouter();
  const { query, setQuery, results, isLoading } = usePlayerSearch();
  const [isFocused, setIsFocused] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const showDropdown = isFocused && query.length >= 2;

  function selectPlayer(id: number) {
    setQuery("");
    setIsExpanded(false);
    router.push(`/players/${id}`);
  }

  return (
    <div className="flex-1 max-w-xs relative">
      {/* Mobile: icon button that expands */}
      <button
        onClick={() => {
          setIsExpanded(true);
          setTimeout(() => inputRef.current?.focus(), 50);
        }}
        className="sm:hidden p-2 text-[var(--muted)] hover:text-[var(--accent)]"
        aria-label="Search players"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      </button>

      {/* Desktop: always-visible compact input; Mobile: conditionally visible */}
      <div className={`${isExpanded ? "flex" : "hidden"} sm:flex relative`}>
        <div className="relative w-full">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none"
            fill="none" stroke="currentColor" viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => setIsFocused(true)}
            onBlur={() => {
              setTimeout(() => {
                setIsFocused(false);
                setIsExpanded(false);
              }, 200);
            }}
            placeholder="Search players…"
            className="bip-input w-full pl-9 pr-3 py-2 text-sm rounded-xl placeholder:text-[var(--muted)]"
          />
          {isLoading && (
            <div className="absolute right-2 top-1/2 -translate-y-1/2">
              <div className="w-3.5 h-3.5 border-2 border-[var(--surface-alt)] border-t-[var(--accent)] rounded-full animate-spin" />
            </div>
          )}
        </div>

        {showDropdown && (
          <div className="absolute top-full left-0 right-0 mt-2 bip-panel overflow-hidden rounded-2xl z-50">
            {results.length === 0 && !isLoading ? (
              <div className="px-4 py-3 text-[var(--muted)] text-sm">No players found</div>
            ) : (
              results.slice(0, 6).map((player) => (
                <button
                  key={player.id}
                  onMouseDown={() => selectPlayer(player.id)}
                  className="w-full flex items-center justify-between px-4 py-3 hover:bg-[rgba(33,72,59,0.08)] text-left"
                >
                  <span className="text-sm font-medium text-[var(--foreground)] truncate">{player.full_name}</span>
                  <span className={`ml-2 text-xs px-1.5 py-0.5 rounded-full shrink-0 ${
                    player.is_active
                      ? "bip-success"
                      : "bg-[var(--surface-alt)] text-[var(--muted)]"
                  }`}>
                    {player.is_active ? "Active" : "Retired"}
                  </span>
                </button>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}
