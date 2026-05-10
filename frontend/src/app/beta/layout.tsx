/**
 * Sprint 96: /beta section layout.
 *
 * Wraps every page under /beta/ with a small banner so users know these
 * surfaces are stable in their data outputs but actively being reworked
 * UI-by-UI. Pages graduate out of /beta as each one gets a focused
 * rework sprint and lands at its root URL.
 */
export default function BetaLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <div
        className="border-b border-[var(--border)] bg-[var(--surface-alt)] px-4 py-2 text-center text-xs"
        style={{
          fontFamily: "var(--font-geist-mono)",
          letterSpacing: "0.06em",
          color: "var(--muted)",
        }}
      >
        <span className="font-semibold text-[var(--foreground)]">Beta</span>
        {" — "}
        these surfaces are being rebuilt for clarity and speed. Outputs are
        stable; UI may change.
      </div>
      {children}
    </>
  );
}
