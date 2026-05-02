"use client";

import { useEffect } from "react";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // eslint-disable-next-line no-console
    console.error("Route error boundary caught:", error);
  }, [error]);

  return (
    <main className="mx-auto max-w-7xl px-4 py-16">
      <div className="bip-panel-strong rounded-[2rem] p-10 text-center">
        <p className="bip-kicker">Something broke</p>
        <h1 className="bip-display mt-4 text-3xl font-semibold text-[var(--foreground)]">
          We hit an unexpected error
        </h1>
        <p className="mt-3 text-sm text-[var(--muted-strong)]">
          The team&apos;s been notified. Try reloading, or head back home.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <button
            onClick={reset}
            className="bip-toggle bip-toggle-active rounded-full px-5 py-2 text-sm font-semibold uppercase tracking-[0.12em]"
          >
            Try again
          </button>
          <a
            href="/"
            className="bip-toggle rounded-full px-5 py-2 text-sm font-semibold uppercase tracking-[0.12em]"
          >
            Home
          </a>
        </div>
      </div>
    </main>
  );
}
