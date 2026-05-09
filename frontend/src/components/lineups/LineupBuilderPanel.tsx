"use client";

import { useState, useRef, useEffect } from "react";
import { usePlayerSearch } from "@/hooks/usePlayerSearch";
import type { PlayerSearchResult } from "@/lib/types";

interface SlotProps {
  index: number;
  selected: PlayerSearchResult | null;
  onSelect: (p: PlayerSearchResult | null) => void;
}

function PlayerSlot({ index, selected, onSelect }: SlotProps) {
  const { query, setQuery, results, isLoading } = usePlayerSearch();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  function handleSelect(p: PlayerSearchResult) {
    onSelect(p);
    setQuery("");
    setOpen(false);
  }

  function handleClear() {
    onSelect(null);
    setQuery("");
  }

  return (
    <div ref={ref} className="relative">
      <label className="block text-[10px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-1">
        Slot {index + 1}
      </label>
      {selected ? (
        <div className="flex items-center justify-between rounded-lg border border-teal-300 dark:border-teal-700 bg-teal-50 dark:bg-teal-900/20 px-3 py-2">
          <span className="text-sm font-medium text-gray-800 dark:text-gray-200">{selected.full_name}</span>
          <button
            type="button"
            onClick={handleClear}
            className="ml-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 text-xs"
            aria-label="Remove player"
          >
            ×
          </button>
        </div>
      ) : (
        <div>
          <input
            type="text"
            value={query}
            onChange={(e) => { setQuery(e.target.value); setOpen(true); }}
            onFocus={() => setOpen(true)}
            placeholder="Search player…"
            className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-800 dark:text-gray-200 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-teal-500"
          />
          {open && (query.length >= 2) && (
            <div className="absolute left-0 right-0 top-full z-50 mt-1 max-h-48 overflow-y-auto rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-lg">
              {isLoading && (
                <p className="px-3 py-2 text-xs text-gray-400 dark:text-gray-500">Searching…</p>
              )}
              {!isLoading && results.length === 0 && (
                <p className="px-3 py-2 text-xs text-gray-400 dark:text-gray-500">No players found.</p>
              )}
              {results.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => handleSelect(p)}
                  className="block w-full px-3 py-2 text-left text-sm text-gray-800 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                  {p.full_name}
                  {!p.is_active && <span className="ml-1 text-[10px] text-gray-400">(inactive)</span>}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

interface Props {
  onSubmit: (playerIds: number[]) => void;
  isLoading: boolean;
}

export default function LineupBuilderPanel({ onSubmit, isLoading }: Props) {
  // Pre-allocate exactly 5 slots at top level — never conditional
  const [slot0, setSlot0] = useState<PlayerSearchResult | null>(null);
  const [slot1, setSlot1] = useState<PlayerSearchResult | null>(null);
  const [slot2, setSlot2] = useState<PlayerSearchResult | null>(null);
  const [slot3, setSlot3] = useState<PlayerSearchResult | null>(null);
  const [slot4, setSlot4] = useState<PlayerSearchResult | null>(null);

  const slots = [slot0, slot1, slot2, slot3, slot4];
  const setters = [setSlot0, setSlot1, setSlot2, setSlot3, setSlot4];

  const filledSlots = slots.filter(Boolean);
  const canSubmit = filledSlots.length >= 2 && !isLoading;

  function handleReset() {
    setters.forEach((s) => s(null));
  }

  function handleSubmit() {
    const ids = slots.filter((s): s is PlayerSearchResult => s !== null).map((s) => s.id);
    onSubmit(ids);
  }

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 space-y-4">
      <div>
        <h2 className="text-sm font-semibold text-gray-800 dark:text-gray-200">What-If Studio</h2>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
          Select 2–5 players to find matching lineups and discover player removal impacts.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {slots.map((slot, i) => (
          <PlayerSlot
            key={i}
            index={i}
            selected={slot}
            onSelect={setters[i]}
          />
        ))}
      </div>

      <div className="flex items-center gap-3 pt-1">
        <button
          type="button"
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {isLoading ? "Searching…" : "Build Lineup"}
        </button>
        <button
          type="button"
          onClick={handleReset}
          className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
        >
          Reset
        </button>
        {filledSlots.length > 0 && (
          <span className="text-xs text-gray-400 dark:text-gray-500">
            {filledSlots.length}/5 players selected
          </span>
        )}
      </div>
    </div>
  );
}
