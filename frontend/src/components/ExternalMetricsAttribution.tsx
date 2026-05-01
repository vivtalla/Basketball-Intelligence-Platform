import { legendBullets } from "@/lib/external-metrics";

interface Props {
  /** Metric keys actually displayed in the surface (e.g., ["epm", "raptor"]). */
  keys: string[];
  /** "footer" = subtle muted text for end-of-table attribution.
   *  "banner" = prominent amber callout for surfaces that *use* the metrics in formulas. */
  variant?: "footer" | "banner";
  className?: string;
}

export default function ExternalMetricsAttribution({
  keys,
  variant = "footer",
  className = "",
}: Props) {
  const bullets = legendBullets(keys);
  if (bullets.length === 0) return null;

  if (variant === "banner") {
    return (
      <div
        className={
          "rounded-xl border-l-4 border-amber-500 bg-amber-50/60 px-4 py-3 " +
          "text-xs text-[var(--foreground)] " +
          className
        }
        role="note"
      >
        <p className="font-semibold uppercase tracking-[0.12em] text-amber-700 mb-1.5">
          External metrics in use
        </p>
        <p className="text-[var(--muted-strong)]">
          This view includes metrics imported from third-party sources, not platform-original.
        </p>
        <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
          {bullets.map((b) => (
            <li key={b.label}>
              <span className="font-semibold text-[var(--foreground)]">{b.label}</span>
              <span className="text-[var(--muted)]"> — </span>
              <a
                href={b.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[var(--accent)] hover:underline"
              >
                {b.source}
              </a>
            </li>
          ))}
        </ul>
      </div>
    );
  }

  // footer variant
  return (
    <p
      className={
        "mt-3 text-[11px] leading-relaxed text-[var(--muted-strong)] " +
        className
      }
    >
      <span className="font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">
        External metrics:{" "}
      </span>
      {bullets.map((b, i) => (
        <span key={b.label}>
          <span className="font-medium text-[var(--foreground)]">{b.label}</span>
          {" — "}
          <a
            href={b.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[var(--accent)] hover:underline"
          >
            {b.source}
          </a>
          {i < bullets.length - 1 ? " · " : ""}
        </span>
      ))}
    </p>
  );
}
