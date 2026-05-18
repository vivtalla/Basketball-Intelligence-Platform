"use client";

// Sprint 101 (Stream C) — client component for a specific historical year.
//
// Wrapped by a server-component page that exports `dynamic = "force-dynamic"`
// so the route always SSRs fresh — historical-class API data can update as
// the seed CSV grows.

import Link from "next/link";
import { useEffect, useState } from "react";
import { getHistoricalDraftClass } from "@/lib/api";
import type { HistoricalClassResponse } from "@/lib/types";
import HistoricalClassTable from "@/components/draft/HistoricalClassTable";

interface Props {
  year: number;
}

export default function HistoricalClassClient({ year }: Props) {
  const [state, setState] = useState<{
    data: HistoricalClassResponse | null;
    error: string | null;
    notFound: boolean;
    isLoading: boolean;
  }>({ data: null, error: null, notFound: false, isLoading: true });

  useEffect(() => {
    // No synchronous reset here — each /draft/historical/[year] route is its
    // own segment, so the component remounts on year navigation and the
    // initial useState value already covers the loading state.
    let cancelled = false;
    getHistoricalDraftClass(year)
      .then((data) => {
        if (cancelled) return;
        setState({ data, error: null, notFound: false, isLoading: false });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : String(err);
        // The API returns 404 for years outside [2016, 2025].
        const isNotFound =
          message.includes("404") || message.toLowerCase().includes("not found");
        setState({
          data: null,
          error: isNotFound ? null : message,
          notFound: isNotFound,
          isLoading: false,
        });
      });
    return () => {
      cancelled = true;
    };
  }, [year]);

  if (state.notFound) {
    return (
      <div className="space-y-4">
        <Link href="/draft/historical" className="bip-link text-sm">
          ← All historical classes
        </Link>
        <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-8 text-center">
          <p className="bip-kicker">Out of range</p>
          <h1 className="bip-display mt-2 text-2xl font-bold text-[var(--foreground)]">
            No historical data for {year}
          </h1>
          <p className="mt-3 text-sm text-[var(--muted-strong)]">
            Historical draft classes are supported for 2016 through 2025. Newer
            classes haven&apos;t finished their first NBA season yet; older
            classes haven&apos;t been curated for this analyzer.
          </p>
        </div>
      </div>
    );
  }

  if (state.error) {
    return (
      <div className="space-y-4">
        <Link href="/draft/historical" className="bip-link text-sm">
          ← All historical classes
        </Link>
        <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-6 text-sm text-[var(--danger-ink)]">
          Could not load class {year}: {state.error}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <Link href="/draft/historical" className="bip-link text-sm">
          ← All historical classes
        </Link>
      </div>
      <header className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5">
        <p className="bip-kicker">Historical draft class</p>
        <h1 className="bip-display mt-2 text-3xl font-bold tracking-tight text-[var(--foreground)]">
          {year} Draft outcomes
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--muted)]">
          NBA career outcome per prospect, classified into{" "}
          <span className="font-semibold text-[var(--foreground)]">bust</span>,{" "}
          <span className="font-semibold text-[var(--foreground)]">role player</span>,{" "}
          <span className="font-semibold text-[var(--foreground)]">starter</span>,{" "}
          <span className="font-semibold text-[var(--foreground)]">star</span>, and{" "}
          <span className="font-semibold text-[var(--foreground)]">superstar</span>{" "}
          tiers. The analyzer&apos;s comp service uses these outcomes to weight
          the similarity score for current prospects.
        </p>
        {state.data?.as_of ? (
          <p className="mt-2 text-[10px] uppercase tracking-wider text-[var(--muted)]">
            As of {state.data.as_of}
          </p>
        ) : null}
      </header>

      {state.isLoading ? (
        <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-8 text-center text-[var(--muted)]">
          Loading…
        </div>
      ) : (
        <HistoricalClassTable prospects={state.data?.prospects ?? []} />
      )}
    </div>
  );
}
