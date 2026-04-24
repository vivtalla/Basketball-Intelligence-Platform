"use client";

import Link from "next/link";
import { useState, useTransition } from "react";
import { postScoutingClipExport } from "@/lib/api";
import { usePlayTypeScoutingReport } from "@/hooks/usePlayerStats";
import type {
  PlayTypeScoutingReportResponse,
  PreReadDeckResponse,
  PreReadScoutingPacket,
  ScoutingClaim,
  ScoutingClipAnchor,
  TeamIntelligence,
  TeamRotationReport,
} from "@/lib/types";

interface ScoutingReportViewProps {
  teamAbbreviation: string;
  opponentAbbreviation: string;
  season: string;
  deck: PreReadDeckResponse;
  intelligence?: TeamIntelligence | null;
  rotationReport?: TeamRotationReport | null;
  packet: PreReadScoutingPacket | null;
  onPacketChange?: (packet: PreReadScoutingPacket | null) => void;
  readOnlyPacket?: boolean;
}

function confidenceTone(level: "high" | "medium" | "low" | null | undefined) {
  if (level === "high") return "bg-[rgba(33,72,59,0.12)] text-[var(--accent-strong)]";
  if (level === "medium") return "bg-[rgba(181,145,78,0.16)] text-[rgb(123,93,42)]";
  return "bg-[rgba(47,43,36,0.08)] text-[var(--muted-strong)]";
}

function buildPacketPreview(
  report: PlayTypeScoutingReportResponse,
  claimIds: string[],
  clipAnchorIds: string[]
): PreReadScoutingPacket | null {
  if (!claimIds.length) {
    return null;
  }
  const claimsById = new Map<string, ScoutingClaim>();
  report.sections.forEach((section) => {
    section.claims.forEach((claim) => {
      claimsById.set(claim.claim_id, claim);
    });
  });

  const packetClaims = claimIds
    .map((claimId) => {
      const claim = claimsById.get(claimId);
      if (!claim) return null;
      const rankedAnchors = report.clip_anchors.filter((anchor) => anchor.claim_id === claimId);
      const preferredAnchors = rankedAnchors.filter((anchor) => clipAnchorIds.includes(anchor.clip_anchor_id));
      const clipAnchors = [...preferredAnchors];
      if (clipAnchors.length < 2) {
        rankedAnchors.forEach((anchor) => {
          if (clipAnchors.some((candidate) => candidate.clip_anchor_id === anchor.clip_anchor_id)) {
            return;
          }
          if (clipAnchors.length < 2) {
            clipAnchors.push(anchor);
          }
        });
      }
      return {
        claim_id: claim.claim_id,
        title: claim.title,
        summary: claim.summary,
        evidence: claim.evidence,
        inference_confidence: claim.inference_confidence ?? null,
        clip_anchors: clipAnchors,
      };
    })
    .filter(Boolean) as PreReadScoutingPacket["claims"];

  if (!packetClaims.length) {
    return null;
  }

  return {
    selection: {
      claim_ids: packetClaims.map((claim) => claim.claim_id),
      clip_anchor_ids: packetClaims.flatMap((claim) =>
        claim.clip_anchors.slice(0, 2).map((anchor) => anchor.clip_anchor_id)
      ),
    },
    claims: packetClaims,
    generated_at: new Date().toISOString(),
    source_url: report.launch_context.scouting_url,
  };
}

function anchorsForClaim(claimId: string, anchors: ScoutingClipAnchor[]) {
  return anchors.filter((anchor) => anchor.claim_id === claimId);
}

export default function ScoutingReportView({
  teamAbbreviation,
  opponentAbbreviation,
  season,
  packet,
  onPacketChange,
  readOnlyPacket = false,
}: ScoutingReportViewProps) {
  const { data: report, isLoading } = usePlayTypeScoutingReport(teamAbbreviation, opponentAbbreviation, season);
  const [exportMessage, setExportMessage] = useState<string | null>(null);
  const [packetMessage, setPacketMessage] = useState<string | null>(null);
  const [isExporting, startExport] = useTransition();

  function toggleClaim(claimId: string) {
    if (!report || readOnlyPacket || !onPacketChange) {
      return;
    }
    const currentClaimIds = packet?.selection.claim_ids ?? [];
    const currentAnchorIds = packet?.selection.clip_anchor_ids ?? [];
    const alreadySelected = currentClaimIds.includes(claimId);
    if (!alreadySelected && currentClaimIds.length >= 3) {
      setPacketMessage("Packets stay capped at 3 claims so the coaching handoff remains readable.");
      return;
    }

    if (alreadySelected) {
      const nextClaimIds = currentClaimIds.filter((candidate) => candidate !== claimId);
      const nextAnchorIds = currentAnchorIds.filter(
        (anchorId) => !anchorsForClaim(claimId, report.clip_anchors).some((anchor) => anchor.clip_anchor_id === anchorId)
      );
      onPacketChange(buildPacketPreview(report, nextClaimIds, nextAnchorIds));
      setPacketMessage("Removed from packet.");
      return;
    }

    const topAnchorIds = anchorsForClaim(claimId, report.clip_anchors)
      .slice(0, 2)
      .map((anchor) => anchor.clip_anchor_id);
    const nextPacket = buildPacketPreview(
      report,
      [...currentClaimIds, claimId],
      [...currentAnchorIds, ...topAnchorIds]
    );
    onPacketChange(nextPacket);
    setPacketMessage("Added to packet.");
  }

  function handleExport() {
    startExport(async () => {
      try {
        const response = await postScoutingClipExport({
          team: teamAbbreviation,
          opponent: opponentAbbreviation,
          season,
          claim_ids: packet?.selection.claim_ids ?? undefined,
          clip_anchor_ids: packet?.selection.clip_anchor_ids ?? undefined,
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
  const selectedClaimIds = new Set(packet?.selection.claim_ids ?? []);

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
          <div className="space-y-2 text-right">
            <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
              Packet selections
            </div>
            <div className="text-2xl font-semibold text-[var(--foreground)]">
              {packet?.claims.length ?? 0} / 3
            </div>
            <div className="flex flex-wrap justify-end gap-3">
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
        </div>
        {packetMessage ? <div className="mt-4 text-sm text-[var(--muted-strong)]">{packetMessage}</div> : null}
        {exportMessage ? <div className="mt-2 text-sm text-[var(--muted-strong)]">{exportMessage}</div> : null}
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
                  const anchors = anchorsForClaim(claim.claim_id, report.clip_anchors);
                  const conf = claim.inference_confidence ?? null;
                  const compareHref =
                    `/compare?mode=teams&team_a=${encodeURIComponent(report.team_abbreviation)}` +
                    `&team_b=${encodeURIComponent(report.opponent_abbreviation)}` +
                    `&season=${encodeURIComponent(report.season)}` +
                    `&source=scouting` +
                    `&claim_title=${encodeURIComponent(claim.title)}` +
                    `&claim_reason=${encodeURIComponent(claim.summary.slice(0, 120))}`;
                  const isSelected = selectedClaimIds.has(claim.claim_id);
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
                              className={`rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] ${confidenceTone(conf.level)}`}
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
                        <button
                          type="button"
                          onClick={() => toggleClaim(claim.claim_id)}
                          disabled={readOnlyPacket}
                          className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
                            isSelected
                              ? "border-[rgba(33,72,59,0.24)] bg-[rgba(216,228,221,0.52)] text-[var(--accent-strong)]"
                              : "border-[var(--border)] bg-[var(--surface)] text-[var(--muted-strong)] hover:border-[var(--accent-strong)] hover:text-[var(--accent-strong)]"
                          } ${readOnlyPacket ? "cursor-default opacity-70" : ""}`}
                        >
                          {readOnlyPacket
                            ? isSelected
                              ? "Included in packet"
                              : "Snapshot packet"
                            : isSelected
                            ? "Remove from packet"
                            : "Add to packet"}
                        </button>
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
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Packet picks</p>
            <h3 className="mt-2 text-2xl font-semibold text-[var(--foreground)]">Claims saved into the packet</h3>
            <div className="mt-4 space-y-3">
              {packet?.claims.length ? (
                packet.claims.map((claim) => (
                  <div key={claim.claim_id} className="rounded-2xl border border-[var(--border)] bg-white/70 p-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="font-semibold text-[var(--foreground)]">{claim.title}</div>
                      {claim.inference_confidence ? (
                        <span className={`rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] ${confidenceTone(claim.inference_confidence.level)}`}>
                          {claim.inference_confidence.level}
                        </span>
                      ) : null}
                    </div>
                    <div className="mt-2 text-sm leading-6 text-[var(--muted-strong)]">{claim.summary}</div>
                    <div className="mt-3 text-xs text-[var(--muted)]">
                      {claim.clip_anchors.length} clip link{claim.clip_anchors.length === 1 ? "" : "s"} attached
                    </div>
                  </div>
                ))
              ) : (
                <div className="rounded-2xl border border-[var(--border)] px-4 py-4 text-sm text-[var(--muted-strong)]">
                  Pin up to 3 claims to carry the strongest scouting story into the packet.
                </div>
              )}
            </div>
          </article>

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
