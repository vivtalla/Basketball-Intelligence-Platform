"use client";

import type { ReactNode } from "react";

function cx(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}

type ShotLabTone = "accent" | "signal" | "neutral";

interface ShotLabSurfaceProps {
  kicker?: string;
  title: string;
  subtitle?: string;
  tone?: ShotLabTone;
  className?: string;
  bodyClassName?: string;
  headerAside?: ReactNode;
  stats?: ReactNode;
  children: ReactNode;
  legend?: ReactNode;
}

export function ShotLabSurface({
  kicker = "SHOT LAB",
  title,
  subtitle,
  tone = "accent",
  className,
  bodyClassName,
  headerAside,
  stats,
  children,
  legend,
}: ShotLabSurfaceProps) {
  return (
    <div className={cx("bip-shot-shell bip-shot-animate", `bip-shot-shell-${tone}`, className)}>
      <div className="relative z-10 space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-2xl">
            <p className="bip-shot-kicker">{kicker}</p>
            <h4 className="mt-2 bip-display text-[1.35rem] font-semibold text-[var(--foreground)]">
              {title}
            </h4>
            {subtitle ? (
              <p className="mt-2 text-sm leading-6 text-[var(--muted-strong)]">
                {subtitle}
              </p>
            ) : null}
          </div>
          {headerAside ? <div className="flex flex-wrap gap-2">{headerAside}</div> : null}
        </div>

        {stats ? <div className="flex flex-wrap gap-2.5">{stats}</div> : null}

        <div className={cx("bip-shot-canvas", bodyClassName)}>{children}</div>

        {legend ? <div className="bip-shot-legend">{legend}</div> : null}
      </div>
    </div>
  );
}

export function ShotLabStat({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail?: string;
}) {
  return (
    <div className="bip-shot-stat">
      <div className="text-[0.62rem] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
        {label}
      </div>
      <div className="mt-1 text-base font-semibold text-[var(--foreground)]">{value}</div>
      {detail ? <div className="mt-1 text-[11px] text-[var(--muted)]">{detail}</div> : null}
    </div>
  );
}

export function ShotLabLegendItem({
  swatch,
  label,
}: {
  swatch: ReactNode;
  label: string;
}) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-[rgba(25,52,42,0.1)] bg-[rgba(255,255,255,0.72)] px-3 py-1.5 text-[11px] text-[var(--muted-strong)]">
      {swatch}
      <span>{label}</span>
    </span>
  );
}

