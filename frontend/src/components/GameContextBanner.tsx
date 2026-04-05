"use client";

import Link from "next/link";

interface GameContextBannerProps {
  source?: string | null;
  sourceId?: string | null;
  sourceLabel?: string | null;
  team?: string | null;
  opponent?: string | null;
  season?: string | null;
  reason?: string | null;
  returnHref?: string | null;
  claimId?: string | null;
  clipAnchorId?: string | null;
  linkageQuality?: string | null;
}

function chip(value: string) {
  return (
    <span className="rounded-full border border-[var(--border)] bg-[rgba(255,255,255,0.72)] px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--muted-strong)]">
      {value}
    </span>
  );
}

export default function GameContextBanner({
  source,
  sourceId,
  sourceLabel,
  team,
  opponent,
  season,
  reason,
  returnHref,
  claimId,
  clipAnchorId,
  linkageQuality,
}: GameContextBannerProps) {
  if (!source && !team && !season && !reason && !sourceLabel && !clipAnchorId) {
    return null;
  }

  return (
    <section className="rounded-[1.5rem] border border-[var(--border)] bg-[linear-gradient(135deg,rgba(244,238,223,0.88),rgba(255,255,255,0.95))] px-5 py-4 shadow-[0_12px_32px_rgba(47,43,36,0.06)]">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-2">
          <div className="flex flex-wrap gap-2">
            {source ? chip(source) : null}
            {sourceLabel ? chip(sourceLabel) : null}
            {team ? chip(team) : null}
            {opponent ? chip(`vs ${opponent}`) : null}
            {season ? chip(season) : null}
            {sourceId ? chip(sourceId) : null}
            {claimId ? chip(claimId) : null}
            {clipAnchorId ? chip(clipAnchorId) : null}
            {linkageQuality ? chip(`${linkageQuality} link`) : null}
          </div>
          {reason ? (
            <p className="text-sm leading-6 text-[var(--muted-strong)]">
              {reason}
            </p>
          ) : null}
        </div>

        {returnHref ? (
          <Link
            href={returnHref}
            className="rounded-full border border-[var(--border-strong)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]"
          >
            Return to source
          </Link>
        ) : null}
      </div>
    </section>
  );
}
