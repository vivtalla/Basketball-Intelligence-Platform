// Sprint 105 (Stream A) — /draft/compare?a=X&b=Y
//
// Side-by-side comparison of two prospects. URL-driven via ?a + ?b query
// params. Empty state surfaces two searchable pickers. Pattern mirrors
// /beta/compare but for prospects only.

"use client";

import Link from "next/link";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { getDraftBoard, getProspectDetail } from "@/lib/api";
import type { DraftProspectSummary, ProspectDetail, ProspectBoardResponse } from "@/lib/types";
import HeroHardwood from "@/components/HeroHardwood";
import Reveal from "@/components/Reveal";
import ProspectCompareView from "@/components/draft/ProspectCompareView";

interface DetailState {
  detail: ProspectDetail | null;
  loading: boolean;
  error: string | null;
}

function useDetail(id: number | null): DetailState {
  // Track state by id so when id changes, we don't leak stale detail from
  // a previous prospect — and we don't need a synchronous setState inside
  // the effect (eslint react-hooks/set-state-in-effect).
  const [state, setState] = useState<DetailState & { forId: number | null }>({
    detail: null,
    loading: false,
    error: null,
    forId: null,
  });

  useEffect(() => {
    if (id == null) return;
    let cancelled = false;
    getProspectDetail(id)
      .then((d) => {
        if (!cancelled) setState({ detail: d, loading: false, error: null, forId: id });
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : String(err);
          setState({ detail: null, loading: false, error: message, forId: id });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  // Only return state when it matches the current id; otherwise show a
  // synthetic loading state (or null for no id).
  if (id == null) {
    return { detail: null, loading: false, error: null };
  }
  if (state.forId !== id) {
    return { detail: null, loading: true, error: null };
  }
  return { detail: state.detail, loading: state.loading, error: state.error };
}

function ProspectPicker({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: number | null;
  onChange: (id: number | null) => void;
  options: DraftProspectSummary[];
}) {
  return (
    <label className="block">
      <span className="text-xs text-[var(--muted)]">{label}</span>
      <select
        value={value ?? ""}
        onChange={(e) => {
          const v = e.target.value;
          onChange(v ? Number(v) : null);
        }}
        className="mt-1 w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--foreground)]"
      >
        <option value="">Choose a prospect…</option>
        {options.map((p) => (
          <option key={p.prospect_id} value={p.prospect_id}>
            {p.consensus_rank ? `#${p.consensus_rank} ` : ""}
            {p.full_name}
            {p.school ? ` · ${p.school}` : ""}
          </option>
        ))}
      </select>
    </label>
  );
}

function DraftCompareWorkspaceInner() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // URL → state.
  const rawA = searchParams.get("a");
  const rawB = searchParams.get("b");
  const aId = rawA && !Number.isNaN(Number(rawA)) ? Number(rawA) : null;
  const bId = rawB && !Number.isNaN(Number(rawB)) ? Number(rawB) : null;

  // Pre-allocated hooks for both detail fetches.
  const aState = useDetail(aId);
  const bState = useDetail(bId);

  // Picker dataset — current draft board, top 60.
  const [board, setBoard] = useState<ProspectBoardResponse | null>(null);
  const [boardError, setBoardError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getDraftBoard(2026, { limit: 90 })
      .then((b) => {
        if (!cancelled) setBoard(b);
      })
      .catch((err: unknown) => {
        if (!cancelled) setBoardError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const options = useMemo(() => board?.prospects ?? [], [board]);

  function pushIds(nextA: number | null, nextB: number | null) {
    const sp = new URLSearchParams();
    if (nextA != null) sp.set("a", String(nextA));
    if (nextB != null) sp.set("b", String(nextB));
    const qs = sp.toString();
    router.push(qs ? `/draft/compare?${qs}` : "/draft/compare");
  }

  const bothReady = aState.detail != null && bState.detail != null;

  return (
    <div className="space-y-6">
      <nav className="text-xs">
        <Link href="/draft" className="text-[var(--muted)] hover:text-[var(--accent)] bip-link">
          ← Back to draft board
        </Link>
      </nav>

      <Reveal>
        <header className="bip-panel-strong relative overflow-hidden rounded-[2.2rem] p-6 sm:p-8">
          <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 rounded-[2.2rem] overflow-hidden">
            <HeroHardwood opacity={0.10} />
          </div>
          <p className="bip-kicker">Draft compare</p>
          <h1 className="bip-display mt-2 text-3xl sm:text-4xl font-bold tracking-tight text-[var(--foreground)]">
            Compare prospects
          </h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--muted)]">
            Two-up scout view. Pick any two 2026 prospects to see per-game, translated NBA per-100,
            archetype, strengths/weaknesses, top NBA comp, and best team fit side-by-side.
          </p>

          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            <ProspectPicker
              label="Prospect A"
              value={aId}
              onChange={(id) => pushIds(id, bId)}
              options={options}
            />
            <ProspectPicker
              label="Prospect B"
              value={bId}
              onChange={(id) => pushIds(aId, id)}
              options={options}
            />
          </div>

          {boardError ? (
            <p className="mt-3 text-xs text-[var(--danger-ink)]">
              Could not load prospect list: {boardError}
            </p>
          ) : null}
        </header>
      </Reveal>

      {aState.error || bState.error ? (
        <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4 text-sm text-[var(--danger-ink)]">
          {aState.error ? `A: ${aState.error}` : ""}
          {aState.error && bState.error ? " · " : ""}
          {bState.error ? `B: ${bState.error}` : ""}
        </div>
      ) : null}

      {aId == null || bId == null ? (
        <div className="bip-panel rounded-[1.85rem] p-8 text-center">
          <p className="text-sm text-[var(--muted)]">
            Choose two prospects above to start comparing.
          </p>
        </div>
      ) : aState.loading || bState.loading || !bothReady ? (
        <div className="space-y-4 animate-pulse">
          <div className="h-32 rounded-[1.85rem] bg-[var(--surface-alt)]" />
          <div className="h-64 rounded-[1.85rem] bg-[var(--surface-alt)]" />
        </div>
      ) : (
        <Reveal delay={120}>
          <ProspectCompareView a={aState.detail!} b={bState.detail!} />
        </Reveal>
      )}
    </div>
  );
}

// Suspense boundary required around useSearchParams() in Next.js 16 — see
// https://nextjs.org/docs/messages/missing-suspense-with-csr-bailout
export default function DraftCompareWorkspacePage() {
  return (
    <Suspense
      fallback={
        <div className="space-y-4 animate-pulse">
          <div className="h-32 rounded-[2.2rem] bg-[var(--surface-alt)]" />
        </div>
      }
    >
      <DraftCompareWorkspaceInner />
    </Suspense>
  );
}
