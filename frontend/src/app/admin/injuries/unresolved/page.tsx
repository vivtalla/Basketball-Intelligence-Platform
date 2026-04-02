"use client";

import { useState } from "react";
import Link from "next/link";
import useSWR, { mutate } from "swr";
import { usePlayerSearch } from "@/hooks/usePlayerSearch";
import {
  getUnresolvedInjuries,
  resolveUnresolvedInjury,
  dismissUnresolvedInjury,
} from "@/lib/api";
import type { InjurySyncUnresolvedEntry } from "@/lib/types";

const SEASON = "2024-25";
const SWR_KEY = `unresolved-injuries-${SEASON}`;

function ResolveModal({
  row,
  onClose,
  onResolved,
}: {
  row: InjurySyncUnresolvedEntry;
  onClose: () => void;
  onResolved: () => void;
}) {
  const { query, setQuery, results, isLoading: searchLoading } = usePlayerSearch();
  const [selectedPlayer, setSelectedPlayer] = useState<{ id: number; name: string } | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isFocused, setIsFocused] = useState(false);

  const showDropdown = isFocused && query.length >= 2;

  async function handleResolve() {
    if (!selectedPlayer) return;
    setSubmitting(true);
    setError(null);
    try {
      await resolveUnresolvedInjury(row.id, selectedPlayer.id);
      onResolved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Resolve failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bip-panel w-full max-w-md rounded-2xl p-6 shadow-xl">
        <h2 className="text-lg font-semibold text-[var(--foreground)]">Resolve Injury Row</h2>
        <div className="mt-3 space-y-1 text-sm text-[var(--muted)]">
          <p>
            <span className="font-medium text-[var(--foreground)]">{row.player_name}</span>
            {" · "}{row.team_abbreviation}
          </p>
          <p>{row.injury_status}{row.injury_type ? ` · ${row.injury_type}` : ""}</p>
          <p className="text-xs">{row.detail}</p>
          <p className="text-xs">Report date: {row.report_date}</p>
        </div>

        <div className="relative mt-4">
          <input
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedPlayer(null);
            }}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setTimeout(() => setIsFocused(false), 200)}
            placeholder="Search player to match…"
            className="bip-input w-full rounded-xl px-4 py-3 text-sm"
          />
          {searchLoading ? (
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-[var(--surface-alt)] border-t-[var(--accent)]" />
            </div>
          ) : null}
          {showDropdown ? (
            <div className="bip-panel absolute left-0 right-0 top-full z-10 mt-1 max-h-48 overflow-y-auto rounded-xl">
              {results.length === 0 ? (
                <div className="px-4 py-3 text-sm text-[var(--muted)]">No players found</div>
              ) : (
                results.slice(0, 8).map((p) => (
                  <button
                    key={p.id}
                    onMouseDown={() => {
                      setSelectedPlayer({ id: p.id, name: p.full_name });
                      setQuery(p.full_name);
                    }}
                    className="w-full px-4 py-2.5 text-left text-sm transition-colors hover:bg-[rgba(216,228,221,0.34)]"
                  >
                    <span className="font-medium text-[var(--foreground)]">{p.full_name}</span>
                    {!p.is_active ? (
                      <span className="ml-2 text-xs text-[var(--muted)]">Retired</span>
                    ) : null}
                  </button>
                ))
              )}
            </div>
          ) : null}
        </div>

        {selectedPlayer ? (
          <p className="mt-2 text-xs text-[var(--muted)]">
            Will match to: <span className="font-medium text-[var(--foreground)]">{selectedPlayer.name}</span> (ID {selectedPlayer.id})
          </p>
        ) : null}

        {error ? (
          <p className="mt-2 text-xs text-[#ef4444]">{error}</p>
        ) : null}

        <div className="mt-5 flex justify-end gap-3">
          <button
            onClick={onClose}
            disabled={submitting}
            className="rounded-full border border-[var(--border)] px-4 py-2 text-sm text-[var(--muted)] transition hover:bg-[var(--surface-alt)]"
          >
            Cancel
          </button>
          <button
            onClick={handleResolve}
            disabled={!selectedPlayer || submitting}
            className="bip-btn-primary rounded-full px-4 py-2 text-sm font-medium disabled:opacity-40"
          >
            {submitting ? "Resolving…" : "Confirm match"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function UnresolvedInjuriesPage() {
  const { data: rows, isLoading } = useSWR<InjurySyncUnresolvedEntry[]>(
    SWR_KEY,
    () => getUnresolvedInjuries(SEASON)
  );

  const [resolveTarget, setResolveTarget] = useState<InjurySyncUnresolvedEntry | null>(null);
  const [dismissingId, setDismissingId] = useState<number | null>(null);

  async function handleDismiss(row: InjurySyncUnresolvedEntry) {
    setDismissingId(row.id);
    try {
      await dismissUnresolvedInjury(row.id);
      mutate(SWR_KEY);
    } finally {
      setDismissingId(null);
    }
  }

  function handleResolved() {
    setResolveTarget(null);
    mutate(SWR_KEY);
  }

  return (
    <div className="mx-auto max-w-5xl">
      {resolveTarget ? (
        <ResolveModal
          row={resolveTarget}
          onClose={() => setResolveTarget(null)}
          onResolved={handleResolved}
        />
      ) : null}

      <div className="mb-6">
        <Link href="/" className="bip-link inline-flex items-center gap-1 text-sm">
          ← Back to Home
        </Link>
      </div>

      <div className="bip-panel-strong mb-8 rounded-[2rem] p-8">
        <p className="bip-kicker">Ops</p>
        <h1 className="bip-display mt-3 text-3xl font-semibold text-[var(--foreground)]">
          Unresolved Injury Rows
        </h1>
        <p className="mt-2 text-sm text-[var(--muted)]">
          Injury report entries where player identity resolution failed during sync.
          Resolve by matching to a player, or dismiss if the player is not on an NBA roster.
        </p>
        <p className="mt-1 text-xs text-[var(--muted)]">Season: {SEASON}</p>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center gap-3 py-16 text-[var(--muted)]">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-[var(--accent)] border-t-transparent" />
          <span className="text-sm">Loading…</span>
        </div>
      ) : !rows || rows.length === 0 ? (
        <div className="bip-empty rounded-[2rem] py-16 text-center">
          <p className="text-lg font-medium text-[var(--foreground)]">No unresolved rows</p>
          <p className="mt-1 text-sm">All injury entries were successfully matched to players.</p>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-sm text-[var(--muted)]">{rows.length} unresolved {rows.length === 1 ? "row" : "rows"}</p>
          {rows.map((row) => (
            <div
              key={row.id}
              className="bip-panel flex items-start justify-between gap-4 rounded-2xl p-5"
            >
              <div className="min-w-0 flex-1 space-y-0.5">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold text-[var(--foreground)]">{row.player_name}</span>
                  <span className="rounded-full bg-[var(--surface-alt)] px-2 py-0.5 text-xs text-[var(--muted)]">
                    {row.team_abbreviation}
                  </span>
                  <span className="rounded-full bg-[rgba(239,68,68,0.1)] px-2 py-0.5 text-xs font-medium text-[#ef4444]">
                    {row.injury_status}
                  </span>
                  {row.injury_type ? (
                    <span className="text-xs text-[var(--muted)]">{row.injury_type}</span>
                  ) : null}
                </div>
                {row.detail ? (
                  <p className="text-xs text-[var(--muted)]">{row.detail}</p>
                ) : null}
                <p className="text-xs text-[var(--muted)]">
                  Report: {row.report_date} · Key: <code className="text-[10px]">{row.normalized_lookup_key}</code>
                </p>
              </div>
              <div className="flex shrink-0 gap-2">
                <button
                  onClick={() => setResolveTarget(row)}
                  className="bip-btn-primary rounded-full px-3 py-1.5 text-xs font-medium"
                >
                  Resolve
                </button>
                <button
                  onClick={() => handleDismiss(row)}
                  disabled={dismissingId === row.id}
                  className="rounded-full border border-[var(--border)] px-3 py-1.5 text-xs text-[var(--muted)] transition hover:bg-[var(--surface-alt)] disabled:opacity-40"
                >
                  {dismissingId === row.id ? "…" : "Dismiss"}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
