"use client";

import Link from "next/link";
import { useState, useTransition } from "react";
import { postScoutingClipExport } from "@/lib/api";
import { usePlayTypeScoutingReport } from "@/hooks/usePlayerStats";
import type { PreReadDeckResponse, TeamIntelligence, TeamRotationReport } from "@/lib/types";

interface ScoutingReportViewProps {
  teamAbbreviation: string;
  opponentAbbreviation: string;
  season: string;
  deck: PreReadDeckResponse;
  intelligence?: TeamIntelligence | null;
  rotationReport?: TeamRotationReport | null;
}

export default function ScoutingReportView({
  teamAbbreviation,
  opponentAbbreviation,
  season,
}: ScoutingReportViewProps) {
  const { data: report, isLoading } = usePlayTypeScoutingReport(teamAbbreviation, opponentAbbreviation, season);
  const [exportMessage, setExportMessage] = useState<string | null>(null);
  const [isExporting, startExport] = useTransition();

  function handleExport() {
    startExport(async () => {
      try {
        const response = await postScoutingClipExport({
          team: teamAbbreviation,
          opponent: opponentAbbreviation,
          season,
          return_to: `/pre-read?team=${teamAbbreviation}&opponent=${opponentAbbreviation}&season=${season}&mode=scouting`,
        });
        setExportMessage(`Exported ${response.clip_count} clip anchors for ${response.export_title}.`);
      } catch {
        setExportMessage("Clip export failed.");
      }
    });
  }

  if (isLoading || !report) {
    return <div className="h-[28rem] animate-pulse rounded-[1.75rem] bg-[var(--surface-alt)]" />;
  }

  const derivedAnchorCount = report.clip_anchors.filter((anchor) => anchor.linkage_quality === "derived").length;

  return (
    <section className="space-y-6">
      <section className="rounded-[1.75rem] border border-[var(--border)] bg-[var(--surface)] p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Scouting workflow</p>
            <h2 className="mt-2 text-3xl font-semibold text-[var(--foreground)]">
              Evidence-backed claims with clip anchors
            </h2>
            <p className="mt-3 text-sm leading-6 text-[var(--muted-strong)]">
              {report.data_status} via synced scouting, style, comparison, and event data. Claims now carry linked film targets instead of stopping at narrative output.
            </p>
            <p className="mt-2 text-xs uppercase tracking-[0.16em] text-[var(--muted)]">
              {derivedAnchorCount} event-backed anchors · {report.clip_anchors.length - derivedAnchorCount} timeline-context anchors
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link href={report.launch_context.compare_url} className="rounded-full border border-[var(--border-strong)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]">
              Open compare
            </Link>
            <button
              type="button"
              onClick={handleExport}
              className="bip-btn-primary rounded-full px-4 py-2 text-sm font-medium"
            >
              {isExporting ? "Exporting..." : "Export clip list"}
            </button>
          </div>
        </div>
        {exportMessage ? <div className="mt-4 text-sm text-[var(--muted-strong)]">{exportMessage}</div> : null}
        {report.warnings.length ? (
          <div className="mt-4 rounded-2xl border border-[var(--border)] bg-white/70 p-4 text-sm leading-6 text-[var(--muted-strong)]">
            {report.warnings.join(" ")}
          </div>
        ) : null}
      </section>

      <div className="grid gap-4 xl:grid-cols-[1.2fr,0.8fr]">
        <div className="space-y-4">
          {report.sections.map((section) => (
            <article key={section.title} className="rounded-[1.75rem] border border-[var(--border)] bg-[var(--surface)] p-6">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">{section.eyebrow}</p>
              <h3 className="mt-2 text-2xl font-semibold text-[var(--foreground)]">{section.title}</h3>
              <div className="mt-4 space-y-4">
                {section.claims.map((claim) => {
                  const anchors = report.clip_anchors.filter((anchor) => anchor.claim_id === claim.claim_id);
                  const conf = claim.inference_confidence;
                  const confPillTone =
                    conf?.level === "high"
                      ? "bg-[rgba(33,72,59,0.12)] text-[var(--accent-strong)]"
                      : conf?.level === "medium"
                      ? "bg-[rgba(181,145,78,0.16)] text-[rgb(123,93,42)]"
                      : "bg-[rgba(47,43,36,0.08)] text-[var(--muted-strong)]";
                  const compareHref =
                    `/compare?mode=teams&team_a=${encodeURIComponent(report.team_abbreviation)}` +
                    `&team_b=${encodeURIComponent(report.opponent_abbreviation)}` +
                    `&season=${encodeURIComponent(report.season)}` +
                    `&source=scouting` +
                    `&claim_title=${encodeURIComponent(claim.title)}` +
                    `&claim_reason=${encodeURIComponent(claim.summary.slice(0, 120))}`;
                  return (
                    <div key={claim.claim_id} className="rounded-[1.35rem] border border-[var(--border)] bg-white/70 p-4">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <div className="font-semibold text-[var(--foreground)]">{claim.title}</div>
                          <p className="mt-2 text-sm leading-6 text-[var(--muted-strong)]">{claim.summary}</p>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                          {conf ? (
                            <span
                              className={`rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] ${confPillTone}`}
                              title={conf.reasons.join(" · ") || "Inference confidence"}
                            >
                              {conf.level} · {conf.anchored_event_count} plays
                              {conf.opponent_specific_event_count > 0 ? ` · ${conf.opponent_specific_event_count} vs opp` : ""}
                            </span>
                          ) : null}
                          <div className="rounded-full bg-[rgba(33,72,59,0.08)] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--accent-strong)]">
                            {claim.claim_id}
                          </div>
                        </div>
                      </div>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {claim.evidence.map((item) => (
                          <span key={`${claim.claim_id}-${item.label}`} className="rounded-full border border-[var(--border)] px-3 py-1 text-xs text-[var(--muted-strong)]">
                            {item.label}: {item.value ?? item.context ?? "—"}
                          </span>
                        ))}
                        <Link
                          href={compareHref}
                          className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1 text-xs font-medium text-[var(--muted-strong)] transition hover:border-[var(--accent-strong)] hover:text-[var(--accent-strong)]"
                        >
                          Compare with this claim →
                        </Link>
                      </div>
                      {anchors.length ? (
                        <div className="mt-4 flex flex-wrap gap-2">
                          {anchors.map((anchor) => (
                            <Link
                              key={anchor.clip_anchor_id}
                              href={anchor.deep_link_url}
                              className="rounded-full bg-[rgba(216,228,221,0.4)] px-3 py-2 text-xs font-semibold uppercase tracking-[0.12em] text-[var(--accent-strong)] transition hover:bg-[rgba(216,228,221,0.62)]"
                            >
                              {anchor.game_date ?? "Game"} · {anchor.linkage_quality === "derived" ? "Event-backed" : "Timeline"} · {anchor.evidence_summary}
                            </Link>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            </article>
          ))}
        </div>

        <aside className="space-y-4">
          <article className="rounded-[1.75rem] border border-[var(--border)] bg-[var(--surface)] p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Clip anchors</p>
            <h3 className="mt-2 text-2xl font-semibold text-[var(--foreground)]">Film-ready targets</h3>
            <div className="mt-4 space-y-3">
              {report.clip_anchors.length ? (
                report.clip_anchors.map((anchor) => (
                  <Link
                    key={anchor.clip_anchor_id}
                    href={anchor.deep_link_url}
                    className="block rounded-2xl border border-[var(--border)] bg-white/70 p-4 transition hover:border-[rgba(33,72,59,0.28)]"
                  >
                    <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                      {anchor.game_date ?? "Date unavailable"} · {anchor.opponent_abbreviation ?? "Opponent TBD"}
                    </div>
                    <div className="mt-2 font-semibold text-[var(--foreground)]">{anchor.title}</div>
                    <div className="mt-2 text-sm leading-6 text-[var(--muted-strong)]">{anchor.reason}</div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <span className="rounded-full border border-[var(--border)] px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--muted-strong)]">
                        {anchor.linkage_quality === "derived" ? "Event-backed" : "Timeline context"}
                      </span>
                      {anchor.action_family ? (
                        <span className="rounded-full border border-[var(--border)] px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--muted-strong)]">
                          {anchor.action_family}
                        </span>
                      ) : null}
                    </div>
                    <div className="mt-2 text-xs text-[var(--muted)]">
                      {anchor.period ? `Q${anchor.period}` : "Event"} {anchor.clock ? `· ${anchor.clock}` : ""} {anchor.action_number ? `· action ${anchor.action_number}` : ""}
                    </div>
                    {anchor.event_description ? (
                      <div className="mt-2 text-sm leading-6 text-[var(--muted-strong)]">
                        {anchor.event_description}
                      </div>
                    ) : null}
                  </Link>
                ))
              ) : (
                <div className="rounded-2xl border border-[var(--border)] px-4 py-4 text-sm text-[var(--muted-strong)]">
                  Clip anchors are limited for this matchup, so the report stays narrative-first.
                </div>
              )}
            </div>
          </article>
        </aside>
      </div>
    </section>
  );
}
