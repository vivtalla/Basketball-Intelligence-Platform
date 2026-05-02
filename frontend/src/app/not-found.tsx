import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto max-w-7xl px-4 py-16">
      <div className="bip-panel-strong rounded-[2rem] p-10 text-center">
        <p className="bip-kicker">404 · Out of bounds</p>
        <h1 className="bip-display mt-4 text-4xl font-semibold text-[var(--foreground)]">
          This page doesn&apos;t exist
        </h1>
        <p className="mt-3 text-sm text-[var(--muted-strong)]">
          The URL might be misspelled, or the resource was moved or deleted.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Link
            href="/"
            className="bip-toggle bip-toggle-active rounded-full px-5 py-2 text-sm font-semibold uppercase tracking-[0.12em]"
          >
            Home
          </Link>
          <Link
            href="/player-stats"
            className="bip-toggle rounded-full px-5 py-2 text-sm font-semibold uppercase tracking-[0.12em]"
          >
            Player stats
          </Link>
          <Link
            href="/teams"
            className="bip-toggle rounded-full px-5 py-2 text-sm font-semibold uppercase tracking-[0.12em]"
          >
            Teams
          </Link>
        </div>
      </div>
    </main>
  );
}
