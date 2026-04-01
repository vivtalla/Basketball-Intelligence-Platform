"use client";

import type { TeamAnalytics, TeamComparisonResponse } from "@/lib/types";

interface StyleComparisonViewProps {
  teamAAbbr: string;
  teamBAbbr: string;
  teamAName: string;
  teamBName: string;
  season: string;
  analyticsA?: TeamAnalytics | null;
  analyticsB?: TeamAnalytics | null;
  comparison?: TeamComparisonResponse | null;
}

type ComparisonEdge = "team_a" | "team_b" | "even";

function fmt(value: number | null | undefined, digits = 1) {
  return value == null ? "—" : value.toFixed(digits);
}

function pct(value: number | null | undefined, digits = 1) {
  return value == null ? "—" : `${(value * 100).toFixed(digits)}%`;
}

function signed(value: number | null | undefined, digits = 1) {
  if (value == null) return "—";
  return `${value > 0 ? "+" : ""}${value.toFixed(digits)}`;
}

function styleTone(edge: ComparisonEdge, side: "team_a" | "team_b") {
  if (edge === "even") return "text-[var(--foreground)]";
  if (edge === side) return "text-[var(--accent-strong)]";
  return "text-[var(--muted)]";
}

function styleSummary(analytics: TeamAnalytics | null | undefined) {
  if (!analytics) return "Style profile unavailable.";
  const pace = analytics.pace ?? 0;
  const ts = analytics.ts_pct ?? 0;
  const tov = analytics.tov_pct ?? 0;
  const oreb = analytics.oreb_pct ?? 0;
  const tags = [
    pace >= 99 ? "fast pace" : pace <= 96 ? "controlled pace" : "balanced pace",
    ts >= 0.57 ? "efficient shot profile" : "inconsistent shot profile",
    tov <= 0.13 ? "clean ball security" : "turnover pressure",
    oreb >= 0.29 ? "second-chance pressure" : "limited glass pressure",
  ];
  return tags.join(" · ");
}

export default function StyleComparisonView({
  teamAAbbr,
  teamBAbbr,
  teamAName,
  teamBName,
  season,
  analyticsA,
  analyticsB,
  comparison,
}: StyleComparisonViewProps) {
  if (!analyticsA || !analyticsB) {
    return (
      <section className="rounded-[1.75rem] border border-[var(--border)] bg-[var(--surface)] p-6">
        <div className="bip-kicker">Style Compare</div>
        <h2 className="bip-display mt-3 text-3xl font-semibold text-[var(--foreground)]">
          Compare team style for {season}
        </h2>
        <div className="bip-empty mt-6 rounded-3xl p-6 text-sm leading-6">
          Style compare needs both team analytics snapshots. Pick two synced teams and the page will expose pace, shot quality, turnover pressure, and glass control.
        </div>
      </section>
    );
  }

  const rows: Array<{
    label: string;
    a: number | null | undefined;
    b: number | null | undefined;
    higherBetter: boolean;
    format: "number" | "percent" | "signed";
    edge: ComparisonEdge;
  }> = [
    {
      label: "Pace",
      a: analyticsA.pace,
      b: analyticsB.pace,
      higherBetter: true,
      format: "number" as const,
      edge:
        analyticsA.pace == null || analyticsB.pace == null
          ? "even"
          : analyticsA.pace > analyticsB.pace
          ? "team_a"
          : analyticsA.pace < analyticsB.pace
          ? "team_b"
          : "even",
    },
    {
      label: "TS%",
      a: analyticsA.ts_pct,
      b: analyticsB.ts_pct,
      higherBetter: true,
      format: "percent" as const,
      edge:
        analyticsA.ts_pct == null || analyticsB.ts_pct == null
          ? "even"
          : analyticsA.ts_pct > analyticsB.ts_pct
          ? "team_a"
          : analyticsA.ts_pct < analyticsB.ts_pct
          ? "team_b"
          : "even",
    },
    {
      label: "eFG%",
      a: analyticsA.efg_pct,
      b: analyticsB.efg_pct,
      higherBetter: true,
      format: "percent" as const,
      edge:
        analyticsA.efg_pct == null || analyticsB.efg_pct == null
          ? "even"
          : analyticsA.efg_pct > analyticsB.efg_pct
          ? "team_a"
          : analyticsA.efg_pct < analyticsB.efg_pct
          ? "team_b"
          : "even",
    },
    {
      label: "Turnovers",
      a: analyticsA.tov_pct,
      b: analyticsB.tov_pct,
      higherBetter: false,
      format: "percent" as const,
      edge:
        analyticsA.tov_pct == null || analyticsB.tov_pct == null
          ? "even"
          : analyticsA.tov_pct < analyticsB.tov_pct
          ? "team_a"
          : analyticsA.tov_pct > analyticsB.tov_pct
          ? "team_b"
          : "even",
    },
    {
      label: "OREB%",
      a: analyticsA.oreb_pct,
      b: analyticsB.oreb_pct,
      higherBetter: true,
      format: "percent" as const,
      edge:
        analyticsA.oreb_pct == null || analyticsB.oreb_pct == null
          ? "even"
          : analyticsA.oreb_pct > analyticsB.oreb_pct
          ? "team_a"
          : analyticsA.oreb_pct < analyticsB.oreb_pct
          ? "team_b"
          : "even",
    },
    {
      label: "Net rating",
      a: analyticsA.net_rating,
      b: analyticsB.net_rating,
      higherBetter: true,
      format: "signed" as const,
      edge:
        analyticsA.net_rating == null || analyticsB.net_rating == null
          ? "even"
          : analyticsA.net_rating > analyticsB.net_rating
          ? "team_a"
          : analyticsA.net_rating < analyticsB.net_rating
          ? "team_b"
          : "even",
    },
  ];

  return (
    <section className="space-y-6 rounded-[1.75rem] border border-[var(--border)] bg-[var(--surface)] p-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="bip-kicker">Style Compare</div>
          <h2 className="bip-display mt-3 text-3xl font-semibold text-[var(--foreground)]">
            How these teams play is the story
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--muted)]">
            This mode compares pace, shot quality, turnover pressure, and glass control so coaches can see the style edge without hunting through multiple pages.
          </p>
        </div>
        <div className="rounded-full border border-[var(--border)] bg-[rgba(255,255,255,0.72)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted-strong)]">
          {teamAAbbr} vs {teamBAbbr} · {season}
        </div>
      </div>

      <section className="grid gap-4 lg:grid-cols-2">
        <article className="bip-panel rounded-[1.5rem] p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">{teamAAbbr}</p>
          <h3 className="mt-2 text-2xl font-semibold text-[var(--foreground)]">{teamAName}</h3>
          <p className="mt-3 text-sm leading-6 text-[var(--muted-strong)]">{styleSummary(analyticsA)}</p>
        </article>
        <article className="bip-panel rounded-[1.5rem] p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">{teamBAbbr}</p>
          <h3 className="mt-2 text-2xl font-semibold text-[var(--foreground)]">{teamBName}</h3>
          <p className="mt-3 text-sm leading-6 text-[var(--muted-strong)]">{styleSummary(analyticsB)}</p>
        </article>
      </section>

      <section className="space-y-3">
        {rows.map((row) => (
          <div
            key={row.label}
            className="grid grid-cols-[1fr_auto_1fr] items-center gap-4 rounded-2xl border border-[var(--border)] bg-[rgba(255,255,255,0.72)] px-4 py-3"
          >
            <div className={`text-right text-lg font-semibold tabular-nums ${styleTone(row.edge, "team_a")}`}>
              {row.format === "percent"
                ? pct(row.a)
                : row.format === "signed"
                ? signed(row.a)
                : fmt(row.a)}
            </div>
            <div className="text-center text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
              {row.label}
            </div>
            <div className={`text-left text-lg font-semibold tabular-nums ${styleTone(row.edge, "team_b")}`}>
              {row.format === "percent"
                ? pct(row.b)
                : row.format === "signed"
                ? signed(row.b)
                : fmt(row.b)}
            </div>
          </div>
        ))}
      </section>

      {comparison?.stories?.length ? (
        <section className="grid gap-4 lg:grid-cols-2">
          {comparison.stories.map((story) => (
            <article
              key={story.summary}
              className="rounded-[1.5rem] border border-[var(--border)] bg-[rgba(255,255,255,0.72)] p-5"
            >
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                {story.label}
              </p>
              <p className="mt-3 text-sm leading-6 text-[var(--muted-strong)]">
                {story.summary}
              </p>
            </article>
          ))}
        </section>
      ) : null}
    </section>
  );
}
