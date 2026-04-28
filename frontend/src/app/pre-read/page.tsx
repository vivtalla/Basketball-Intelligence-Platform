"use client";

import { Suspense, useState, useTransition } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useSWRConfig } from "swr";
import {
  createPreReadPacketSnapshot,
  getPreReadSnapshotMarkdown,
  updatePreReadPacketSnapshot,
} from "@/lib/api";
import {
  usePreReadDeck,
  usePreReadPacketLibrary,
  usePreReadSnapshot,
  useTeamAnalytics,
  useTeamIntelligence,
  useTeamRotationReport,
  useTeams,
} from "@/hooks/usePlayerStats";
import type { PreReadScoutingPacket } from "@/lib/types";
import AvailabilitySummaryCard from "@/components/AvailabilitySummaryCard";
import ScoutingReportView from "@/components/ScoutingReportView";

const SEASONS = ["2025-26", "2024-25", "2023-24", "2022-23"];
type ViewMode = "briefing" | "scouting";
type LibraryMode = "matchup" | "team";

async function copyText(value: string) {
  if (typeof window === "undefined" || !navigator.clipboard) return;
  await navigator.clipboard.writeText(value);
}

function PreReadPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { mutate } = useSWRConfig();
  const rawMode = searchParams.get("mode");
  const snapshotId = searchParams.get("snapshot_id");

  const [team, setTeam] = useState(searchParams.get("team")?.toUpperCase() ?? "OKC");
  const [opponent, setOpponent] = useState(searchParams.get("opponent")?.toUpperCase() ?? "BOS");
  const [season, setSeason] = useState(searchParams.get("season") ?? "2024-25");
  const inboundSource = searchParams.get("source");
  const inboundClaimTitle = searchParams.get("claim_title");
  const inboundClaimReason = searchParams.get("claim_reason");
  const [mode, setMode] = useState<ViewMode>(rawMode === "scouting" ? "scouting" : "briefing");
  const [libraryMode, setLibraryMode] = useState<LibraryMode>("matchup");
  const [packetMessage, setPacketMessage] = useState<string | null>(null);
  const [packetDraft, setPacketDraft] = useState<PreReadScoutingPacket | null>(null);
  const [packetTitle, setPacketTitle] = useState("");
  const [packetNote, setPacketNote] = useState("");
  const [isSaving, startSaving] = useTransition();
  const [isUpdating, startUpdating] = useTransition();
  const [isExporting, startExporting] = useTransition();

  const { data: teams } = useTeams();
  const { data: snapshot } = usePreReadSnapshot(snapshotId);
  const activeTeam = snapshot?.context.team_abbreviation ?? team;
  const activeOpponent = snapshot?.context.opponent_abbreviation ?? opponent;
  const activeSeason = snapshot?.context.season ?? season;
  const { data, isLoading } = usePreReadDeck(activeTeam, activeOpponent, activeSeason, snapshotId);
  const matchupLibrary = usePreReadPacketLibrary(activeTeam, activeSeason, activeOpponent, 6);
  const teamHistoryLibrary = usePreReadPacketLibrary(activeTeam, activeSeason, null, 10);
  const { data: teamIntelligence } = useTeamIntelligence(activeTeam, activeSeason);
  const { data: rotationReport } = useTeamRotationReport(activeTeam, activeSeason);
  const { data: homeAnalytics } = useTeamAnalytics(activeTeam, activeSeason);
  const { data: awayAnalytics } = useTeamAnalytics(activeOpponent, activeSeason);
  const nextGame = data?.team_availability.next_game ?? null;
  const activePacket = snapshot?.deck.scouting_packet ?? data?.scouting_packet ?? packetDraft;
  const metadataTitle = snapshot ? (packetTitle || snapshot.title || "") : packetTitle;
  const metadataNote = snapshot ? (packetNote || snapshot.note || "") : packetNote;
  const snapshotShareUrl = data?.snapshot?.share_url ?? null;

  async function refreshPacketViews() {
    await mutate((key) => typeof key === "string" && key.startsWith("pre-read"));
  }

  function handleSaveSnapshot(sourceView: "pre-read-briefing" | "pre-read-scouting") {
    startSaving(async () => {
      try {
        const response = await createPreReadPacketSnapshot({
          team: activeTeam,
          opponent: activeOpponent,
          season: activeSeason,
          game_id: data?.prep_context?.prep_item?.game_id ?? undefined,
          source_view: sourceView,
          source_snapshot_id: snapshotId ?? undefined,
          packet_selection: activePacket?.selection,
          context: {
            mode,
            xray_url: data?.prep_context?.xray_url ?? "",
            replay_url: data?.prep_context?.replay_url ?? "",
            shot_profile_label: data?.prep_context?.shot_profile_driver?.label ?? "",
            shot_profile_family: data?.prep_context?.shot_profile_driver?.split_family ?? "",
            shot_profile_value: data?.prep_context?.shot_profile_driver?.split_value ?? "",
          },
        });
        setPacketTitle(response.title ?? "");
        setPacketNote(response.note ?? "");
        setPacketMessage(`Saved packet ${response.snapshot_id.slice(0, 8)}.`);
        await refreshPacketViews();
        router.replace(response.share_url);
      } catch {
        setPacketMessage("Packet save failed.");
      }
    });
  }

  function handleUpdateSnapshot() {
    if (!snapshotId) return;
    startUpdating(async () => {
      try {
        const response = await updatePreReadPacketSnapshot(snapshotId, {
          title: metadataTitle,
          note: metadataNote,
        });
        setPacketTitle(response.title ?? "");
        setPacketNote(response.note ?? "");
        setPacketMessage("Packet details updated.");
        await refreshPacketViews();
      } catch {
        setPacketMessage("Packet update failed.");
      }
    });
  }

  function handleCopyShareLink(shareUrl: string) {
    startExporting(async () => {
      try {
        if (typeof window !== "undefined") {
          await copyText(new URL(shareUrl, window.location.origin).toString());
        }
        setPacketMessage("Packet link copied.");
      } catch {
        setPacketMessage("Could not copy the packet link.");
      }
    });
  }

  function handleExportMarkdown(targetSnapshotId: string) {
    startExporting(async () => {
      try {
        const markdown = await getPreReadSnapshotMarkdown(targetSnapshotId);
        await copyText(markdown);
        setPacketMessage("Packet markdown copied.");
      } catch {
        setPacketMessage("Markdown export failed.");
      }
    });
  }

  const libraryItems =
    libraryMode === "matchup"
      ? matchupLibrary.data?.items ?? []
      : teamHistoryLibrary.data?.items ?? [];

  return (
    <div className="mx-auto max-w-6xl space-y-8 print:space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="bip-kicker">Pregame Briefing</p>
          <h1 className="bip-display mt-3 text-4xl font-semibold text-[var(--foreground)]">
            Game-Day Pre-Read
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--muted-strong)]">
            Make Pre-Read the canonical coaching packet: focus levers, tactical adjustments, packet-ready scouting claims, and the fastest path into compare or replay when the staff wants more detail.
          </p>
        </div>
        <div className="flex flex-wrap justify-end gap-3 print:hidden">
          <button
            type="button"
            onClick={() => window.print()}
            className="bip-btn-primary rounded-full px-4 py-2 text-sm font-medium"
          >
            Print deck
          </button>
          {snapshotId ? (
            <button
              type="button"
              onClick={() => handleExportMarkdown(snapshotId)}
              className="rounded-full border border-[var(--border-strong)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]"
            >
              {isExporting ? "Exporting..." : "Export markdown"}
            </button>
          ) : null}
        </div>
      </div>

      {data?.snapshot ? (
        <div className="rounded-[1.5rem] border border-[rgba(33,72,59,0.18)] bg-[rgba(216,228,221,0.28)] px-5 py-4 text-sm text-[var(--muted-strong)]">
          Frozen packet: <span className="font-semibold text-[var(--foreground)]">{data.snapshot.title ?? data.snapshot.snapshot_id.slice(0, 8)}</span> · created {new Date(data.snapshot.created_at).toLocaleString()}
        </div>
      ) : null}

      {inboundSource === "scouting" && inboundClaimTitle ? (
        <div className="rounded-[1.5rem] border border-[rgba(181,145,78,0.22)] bg-[rgba(181,145,78,0.10)] px-5 py-4 text-sm leading-6 text-[var(--muted-strong)]">
          From <span className="font-semibold text-[var(--foreground)]">Scouting</span>: {decodeURIComponent(inboundClaimTitle)}.
          {inboundClaimReason ? ` ${decodeURIComponent(inboundClaimReason)}` : ""}
        </div>
      ) : null}

      <section className="flex rounded-xl overflow-hidden border border-[var(--border)] w-fit text-sm print:hidden">
        <button
          type="button"
          onClick={() => setMode("briefing")}
          className={`px-5 py-2 transition-colors ${mode === "briefing" ? "bip-toggle-active" : "bip-toggle"}`}
        >
          Briefing
        </button>
        <button
          type="button"
          onClick={() => setMode("scouting")}
          className={`px-5 py-2 transition-colors ${mode === "scouting" ? "bip-toggle-active" : "bip-toggle"}`}
        >
          Scouting Report
        </button>
      </section>

      <section className="bip-panel rounded-[1.8rem] p-6 print:hidden">
        <div className="grid gap-4 md:grid-cols-3">
          <label className="space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Team</span>
            <select
              value={team}
              onChange={(event) => {
                setTeam(event.target.value);
                setPacketDraft(null);
              }}
              className="bip-input w-full rounded-2xl px-4 py-3 text-sm"
            >
              {(teams ?? []).map((entry) => (
                <option key={entry.abbreviation} value={entry.abbreviation}>
                  {entry.abbreviation} · {entry.name}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Opponent</span>
            <select
              value={opponent}
              onChange={(event) => {
                setOpponent(event.target.value);
                setPacketDraft(null);
              }}
              className="bip-input w-full rounded-2xl px-4 py-3 text-sm"
            >
              {(teams ?? []).map((entry) => (
                <option key={entry.abbreviation} value={entry.abbreviation}>
                  {entry.abbreviation} · {entry.name}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Season</span>
            <select
              value={season}
              onChange={(event) => {
                setSeason(event.target.value);
                setPacketDraft(null);
              }}
              className="bip-input w-full rounded-2xl px-4 py-3 text-sm"
            >
              {SEASONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="mt-5 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => handleSaveSnapshot(mode === "scouting" ? "pre-read-scouting" : "pre-read-briefing")}
            className="rounded-full border border-[var(--border-strong)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]"
          >
            {isSaving ? "Saving packet..." : "Save frozen packet"}
          </button>
          {snapshotId && snapshotShareUrl ? (
            <button
              type="button"
              onClick={() => handleCopyShareLink(snapshotShareUrl)}
              className="rounded-full border border-[var(--border)] px-4 py-2 text-sm font-medium text-[var(--foreground)] transition hover:bg-[rgba(255,255,255,0.5)]"
            >
              Copy share link
            </button>
          ) : null}
          <div className="text-sm text-[var(--muted-strong)]">
            {activePacket?.claims.length
              ? `${activePacket.claims.length} scouting claim${activePacket.claims.length === 1 ? "" : "s"} attached to this packet.`
              : "No scouting claims pinned yet."}
          </div>
        </div>

        {snapshotId ? (
          <div className="mt-5 grid gap-4 lg:grid-cols-[1fr,1.2fr,auto]">
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Packet title</span>
              <input
                value={metadataTitle}
                onChange={(event) => setPacketTitle(event.target.value)}
                className="bip-input w-full rounded-2xl px-4 py-3 text-sm"
                placeholder="Packet title"
              />
            </label>
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Coach note</span>
              <textarea
                value={metadataNote}
                onChange={(event) => setPacketNote(event.target.value)}
                className="bip-input min-h-[92px] w-full rounded-2xl px-4 py-3 text-sm"
                placeholder="Add the handoff note that should travel with this packet."
              />
            </label>
            <div className="flex items-end">
              <button
                type="button"
                onClick={handleUpdateSnapshot}
                className="bip-btn-secondary rounded-full px-4 py-2 text-sm font-medium"
              >
                {isUpdating ? "Updating..." : "Save packet details"}
              </button>
            </div>
          </div>
        ) : null}

        {packetMessage ? <div className="mt-4 text-sm text-[var(--muted-strong)]">{packetMessage}</div> : null}
      </section>

      {data?.prep_context?.urgency ? (
        <div className="flex justify-center">
          <span
            className="inline-flex items-center gap-2 rounded-full border px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.16em]"
            style={(() => {
              const u = data.prep_context.urgency.toLowerCase();
              if (u.includes("urgent") || u.includes("critical") || u.includes("high")) {
                return {
                  color: "var(--danger-ink)",
                  borderColor: "rgba(176,70,70,0.4)",
                  background: "rgba(176,70,70,0.10)",
                };
              }
              if (u.includes("monitor") || u.includes("watch") || u.includes("medium")) {
                return {
                  color: "var(--signal)",
                  borderColor: "rgba(180,137,61,0.4)",
                  background: "rgba(180,137,61,0.10)",
                };
              }
              return {
                color: "var(--accent)",
                borderColor: "rgba(33,72,59,0.32)",
                background: "rgba(33,72,59,0.08)",
              };
            })()}
          >
            <span className="h-2 w-2 rounded-full" style={{ background: "currentColor" }} />
            {data.prep_context.urgency}
          </span>
        </div>
      ) : null}

      {/* Matchup header card — visual preview of the selected matchup */}
      {activeTeam && activeOpponent ? (
        <section className="bip-panel-strong rounded-[1.8rem] p-8">
          <div className="grid grid-cols-[1fr_auto_1fr] gap-6 items-center">
            {/* Home team */}
            <div className="text-right flex items-center justify-end gap-4">
              <div>
                <div className="bip-display text-3xl font-bold text-[var(--foreground)]">
                  {teams?.find((t) => t.abbreviation === activeTeam)?.name ?? activeTeam}
                </div>
                <div className="mt-1 text-xs text-[var(--muted)]" style={{ fontFamily: "var(--font-geist-mono)", letterSpacing: "0.05em" }}>
                  {activeTeam} · Home
                </div>
              </div>
              <div
                className="flex items-center justify-center rounded-[18px] text-white font-bold shrink-0"
                style={{
                  width: 64,
                  height: 64,
                  background: "var(--accent)",
                  fontFamily: "var(--font-display)",
                  fontSize: 20,
                }}
              >
                {activeTeam}
              </div>
            </div>

            {/* VS center */}
            <div className="text-center px-2">
              <div className="bip-kicker" style={{ color: "var(--signal)" }}>Tip-off</div>
              <div className="bip-display text-5xl font-bold text-[var(--foreground)] my-1">vs</div>
              <div className="text-xs text-[var(--muted)]">{activeSeason}</div>
            </div>

            {/* Away team */}
            <div className="text-left flex items-center gap-4">
              <div
                className="flex items-center justify-center rounded-[18px] font-bold shrink-0"
                style={{
                  width: 64,
                  height: 64,
                  background: "var(--surface-alt)",
                  border: "1px solid var(--border)",
                  fontFamily: "var(--font-display)",
                  fontSize: 20,
                  color: "var(--foreground)",
                }}
              >
                {activeOpponent}
              </div>
              <div>
                <div className="bip-display text-3xl font-bold text-[var(--foreground)]">
                  {teams?.find((t) => t.abbreviation === activeOpponent)?.name ?? activeOpponent}
                </div>
                <div className="mt-1 text-xs text-[var(--muted)]" style={{ fontFamily: "var(--font-geist-mono)", letterSpacing: "0.05em" }}>
                  {activeOpponent} · Away
                </div>
              </div>
            </div>
          </div>

          {/* MatchupBar bilateral comparison bars (5 metrics) */}
          {homeAnalytics && awayAnalytics ? (
            <div className="mt-8 pt-6 border-t border-[var(--border)] grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-5">
              {[
                { label: "OFFENSIVE RTG", home: homeAnalytics.off_rating, away: awayAnalytics.off_rating, max: 130, decimals: 1, higherBetter: true },
                { label: "DEFENSIVE RTG", home: homeAnalytics.def_rating, away: awayAnalytics.def_rating, max: 130, decimals: 1, higherBetter: false },
                { label: "PACE", home: homeAnalytics.pace, away: awayAnalytics.pace, max: 110, decimals: 1, higherBetter: true },
                { label: "EFG%", home: (homeAnalytics.efg_pct ?? 0) * 100, away: (awayAnalytics.efg_pct ?? 0) * 100, max: 70, decimals: 1, higherBetter: true },
                { label: "TS%", home: (homeAnalytics.ts_pct ?? 0) * 100, away: (awayAnalytics.ts_pct ?? 0) * 100, max: 70, decimals: 1, higherBetter: true },
                { label: "NET RTG", home: homeAnalytics.net_rating, away: awayAnalytics.net_rating, max: 20, decimals: 1, higherBetter: true, signed: true },
              ].map((row) => {
                if (row.home == null || row.away == null) return null;
                const homePct = (Math.abs(row.home) / row.max) * 100;
                const awayPct = (Math.abs(row.away) / row.max) * 100;
                const homeWins = row.higherBetter ? row.home > row.away : row.home < row.away;
                const sign = row.signed && row.home > 0 ? "+" : "";
                const signAway = row.signed && row.away > 0 ? "+" : "";
                return (
                  <div key={row.label}>
                    <div className="flex justify-between items-baseline mb-1.5 text-xs">
                      <span
                        className="font-bold tabular-nums"
                        style={{
                          fontFamily: "var(--font-geist-mono)",
                          fontVariantNumeric: "tabular-nums",
                          color: homeWins ? "var(--accent)" : "var(--muted)",
                        }}
                      >
                        {sign}{row.home.toFixed(row.decimals)}
                      </span>
                      <span className="font-mono text-[10px] tracking-[0.1em] text-[var(--muted)]">{row.label}</span>
                      <span
                        className="font-bold tabular-nums"
                        style={{
                          fontFamily: "var(--font-geist-mono)",
                          fontVariantNumeric: "tabular-nums",
                          color: !homeWins ? "var(--accent)" : "var(--muted)",
                        }}
                      >
                        {signAway}{row.away.toFixed(row.decimals)}
                      </span>
                    </div>
                    <div className="flex h-2 gap-0.5">
                      <div className="flex-1 relative bg-[#f2e8d4] rounded-l-full overflow-hidden">
                        <div
                          className="absolute top-0 bottom-0 right-0 rounded-l-full transition-all duration-300"
                          style={{
                            width: `${Math.min(homePct, 100)}%`,
                            background: homeWins ? "var(--accent)" : "rgba(53,41,33,0.35)",
                          }}
                        />
                      </div>
                      <div className="flex-1 relative bg-[#f2e8d4] rounded-r-full overflow-hidden">
                        <div
                          className="absolute top-0 bottom-0 left-0 rounded-r-full transition-all duration-300"
                          style={{
                            width: `${Math.min(awayPct, 100)}%`,
                            background: !homeWins ? "var(--accent)" : "rgba(53,41,33,0.35)",
                          }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : null}
        </section>
      ) : null}

      <section className="rounded-[1.8rem] border border-[var(--border)] bg-[var(--surface)] p-6 print:hidden">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Packet library</div>
            <h2 className="mt-2 text-2xl font-semibold text-[var(--foreground)]">Saved packets for this staff flow</h2>
          </div>
          <div className="flex rounded-xl overflow-hidden border border-[var(--border)] text-sm">
            <button
              type="button"
              onClick={() => setLibraryMode("matchup")}
              className={`px-4 py-2 transition-colors ${libraryMode === "matchup" ? "bip-toggle-active" : "bip-toggle"}`}
            >
              This Matchup
            </button>
            <button
              type="button"
              onClick={() => setLibraryMode("team")}
              className={`px-4 py-2 transition-colors ${libraryMode === "team" ? "bip-toggle-active" : "bip-toggle"}`}
            >
              Team History
            </button>
          </div>
        </div>
        <div className="mt-5 grid gap-3">
          {libraryItems.length ? (
            libraryItems.map((item) => (
              <article key={item.snapshot_id} className="rounded-[1.4rem] border border-[var(--border)] bg-white/70 p-4">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <div className="font-semibold text-[var(--foreground)]">{item.title ?? `${item.team_abbreviation} vs ${item.opponent_abbreviation}`}</div>
                    <div className="mt-1 text-xs uppercase tracking-[0.16em] text-[var(--muted)]">
                      {item.team_abbreviation} vs {item.opponent_abbreviation} · {item.created_at.slice(0, 16).replace("T", " ")} · {item.saved_from ?? "packet"}
                    </div>
                    {item.prep_headline ? (
                      <p className="mt-2 text-sm leading-6 text-[var(--muted-strong)]">{item.prep_headline}</p>
                    ) : null}
                    {item.note ? <p className="mt-2 text-sm leading-6 text-[var(--muted)]">{item.note}</p> : null}
                  </div>
                  {item.packet_summary ? (
                    <div className="rounded-2xl border border-[var(--border)] bg-[rgba(216,228,221,0.34)] px-4 py-3 text-right">
                      <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Packet summary</div>
                      <div className="mt-2 text-sm font-semibold text-[var(--foreground)]">
                        {item.packet_summary.claim_count} claims · {item.packet_summary.clip_count} clips
                      </div>
                    </div>
                  ) : null}
                </div>
                <div className="mt-4 flex flex-wrap gap-3">
                  <Link href={item.share_url} className="bip-btn-primary rounded-full px-4 py-2 text-sm font-medium">
                    Open
                  </Link>
                  <button
                    type="button"
                    onClick={() => handleCopyShareLink(item.share_url)}
                    className="rounded-full border border-[var(--border)] px-4 py-2 text-sm font-medium text-[var(--foreground)] transition hover:bg-[rgba(255,255,255,0.5)]"
                  >
                    Copy share link
                  </button>
                  <button
                    type="button"
                    onClick={() => handleExportMarkdown(item.snapshot_id)}
                    className="rounded-full border border-[var(--border)] px-4 py-2 text-sm font-medium text-[var(--foreground)] transition hover:bg-[rgba(255,255,255,0.5)]"
                  >
                    Export markdown
                  </button>
                </div>
              </article>
            ))
          ) : (
            <div className="rounded-[1.4rem] border border-[var(--border)] bg-white/70 px-4 py-5 text-sm text-[var(--muted-strong)]">
              No saved packets yet for this view.
            </div>
          )}
        </div>
      </section>

      {data ? (
        <section className="grid gap-4 lg:grid-cols-2">
          <AvailabilitySummaryCard availability={data.team_availability} compact />
          <AvailabilitySummaryCard availability={data.opponent_availability} compact />
        </section>
      ) : null}

      {/* Focus levers — three things to win, in design's FocusLever card style */}
      {data?.focus_levers && data.focus_levers.length > 0 ? (
        <section data-print-break-before>
          <p className="bip-kicker">Focus levers</p>
          <h2 className="bip-display mt-1 text-2xl font-semibold text-[var(--foreground)]">
            Three things to win.
          </h2>
          <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-3">
            {data.focus_levers.slice(0, 3).map((lever, i) => {
              const tone = i === 0 ? "accent" : i === 1 ? "signal" : "accent";
              const dotColor = tone === "accent" ? "var(--accent)" : "var(--signal)";
              return (
                <div
                  key={`${lever.factor_id}-${i}`}
                  className="rounded-[1.4rem] border border-[var(--border)] p-5"
                  style={{ background: "rgba(255,249,241,0.86)" }}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <span
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: "50%",
                        background: dotColor,
                        flexShrink: 0,
                      }}
                    />
                    <p
                      className="bip-kicker"
                      style={{ color: dotColor, margin: 0 }}
                    >
                      {lever.title}
                    </p>
                  </div>
                  <p className="text-sm leading-6 text-[var(--foreground)]">
                    {lever.summary}
                  </p>
                  {lever.coaching_prompt ? (
                    <p className="mt-3 text-xs italic text-[var(--muted)]">
                      {lever.coaching_prompt}
                    </p>
                  ) : null}
                </div>
              );
            })}
          </div>
        </section>
      ) : null}

      {data?.prep_context?.headline ? (
        <section className="rounded-[1.5rem] border border-[var(--border)] bg-[rgba(255,249,241,0.86)] px-5 py-4">
          <p className="bip-kicker mb-1" style={{ color: "var(--signal)" }}>Headline</p>
          <p className="text-base leading-7 text-[var(--foreground)]">{data.prep_context.headline}</p>
        </section>
      ) : null}

      {data?.prep_context ? (
        <section className="rounded-[1.5rem] border border-[var(--border)] bg-[rgba(255,255,255,0.72)] p-5 text-sm leading-6 text-[var(--muted-strong)]">
          <div className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Prep context</div>
          <div className="mt-2 font-semibold text-[var(--foreground)]">
            {data.prep_context.first_adjustment_label ?? data.prep_context.best_edge_label ?? data.prep_context.headline ?? "Prep context loaded"}
          </div>
          {data.prep_context.urgency_rationale ? (
            <p className="mt-2">{data.prep_context.urgency_rationale}</p>
          ) : null}
          {data.prep_context.first_adjustment_rationale ? (
            <p className="mt-2">{data.prep_context.first_adjustment_rationale}</p>
          ) : null}
          {data.prep_context.shot_profile_driver ? (
            <div className="mt-3 rounded-2xl border border-[var(--border)] bg-[rgba(255,255,255,0.68)] p-4">
              <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                Shot-profile frame
              </div>
              <div className="mt-2 text-sm font-semibold text-[var(--foreground)]">
                {data.prep_context.shot_profile_driver.label}
              </div>
              <p className="mt-2 text-sm leading-6 text-[var(--muted-strong)]">
                {data.prep_context.shot_profile_driver.summary}
              </p>
              {data.prep_context.shot_profile_driver.trust_note ? (
                <p className="mt-2 text-xs leading-5 text-[var(--muted)]">
                  {data.prep_context.shot_profile_driver.trust_note}
                </p>
              ) : null}
            </div>
          ) : null}
        </section>
      ) : null}

      {activePacket?.claims.length ? (
        <section className="rounded-[1.8rem] border border-[var(--border)] bg-[var(--surface)] p-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Scouting packet</p>
              <h2 className="mt-2 text-2xl font-semibold text-[var(--foreground)]">Claims carried into the staff packet</h2>
            </div>
            <div className="text-sm text-[var(--muted-strong)]">
              {activePacket.claims.length} claim{activePacket.claims.length === 1 ? "" : "s"} · {activePacket.claims.reduce((total, claim) => total + claim.clip_anchors.length, 0)} clip links
            </div>
          </div>
          <div className="mt-5 grid gap-4 lg:grid-cols-2">
            {activePacket.claims.map((claim) => (
              <article key={claim.claim_id} className="rounded-[1.4rem] border border-[var(--border)] bg-white/70 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="font-semibold text-[var(--foreground)]">{claim.title}</div>
                  {claim.inference_confidence ? (
                    <span className="rounded-full bg-[rgba(33,72,59,0.12)] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--accent-strong)]">
                      {claim.inference_confidence.level}
                    </span>
                  ) : null}
                </div>
                <p className="mt-3 text-sm leading-6 text-[var(--muted-strong)]">{claim.summary}</p>
                {claim.inference_confidence?.reasons.length ? (
                  <p className="mt-2 text-xs leading-5 text-[var(--muted)]">
                    {claim.inference_confidence.reasons.join(" · ")}
                  </p>
                ) : null}
                {claim.clip_anchors.length ? (
                  <div className="mt-4 flex flex-wrap gap-2">
                    {claim.clip_anchors.map((anchor) => (
                      <Link
                        key={anchor.clip_anchor_id}
                        href={anchor.deep_link_url}
                        className="rounded-full bg-[rgba(216,228,221,0.4)] px-3 py-2 text-xs font-semibold uppercase tracking-[0.12em] text-[var(--accent-strong)] transition hover:bg-[rgba(216,228,221,0.62)]"
                      >
                        {anchor.game_date ?? "Game"} · {anchor.evidence_summary}
                      </Link>
                    ))}
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        </section>
      ) : null}

      {data?.warnings?.length ? (
        <section className="rounded-[1.5rem] border border-[var(--border)] bg-[var(--surface)] p-5 text-sm leading-6 text-[var(--muted-strong)]">
          <div className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Readiness</div>
          <div className="mt-2">
            {data.data_status} via {data.canonical_source}
          </div>
          <ul className="mt-3 space-y-2">
            {data.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="h-64 animate-pulse rounded-[1.75rem] bg-[var(--surface-alt)]" />
          ))}
        </div>
      ) : data ? (
        mode === "briefing" ? (
          <>
            <div className="grid gap-4 md:grid-cols-2">
              {data.slides.map((slide) => (
                <article key={`${slide.eyebrow}-${slide.title}`} className="rounded-[1.8rem] border border-[var(--border)] bg-[var(--surface)] p-6 break-inside-avoid print:shadow-none">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                    {slide.eyebrow}
                  </p>
                  <h2 className="mt-3 text-2xl font-semibold text-[var(--foreground)]">
                    {slide.title}
                  </h2>
                  <ul className="mt-5 space-y-3 text-sm leading-6 text-[var(--muted-strong)]">
                    {slide.bullets.map((bullet) => (
                      <li key={bullet}>{bullet}</li>
                    ))}
                  </ul>
                </article>
              ))}
            </div>

            <section className="rounded-[1.8rem] border border-[var(--border)] bg-[var(--surface)] p-6 print:hidden">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Follow-through</p>
              {nextGame ? (
                <p className="mt-3 text-sm leading-6 text-[var(--muted-strong)]">
                  Next synced game: {nextGame.is_home ? "vs" : "at"} {nextGame.opponent_abbreviation ?? nextGame.opponent_name ?? "Opponent TBD"} on {nextGame.game_date ?? "TBD"}.
                </p>
              ) : null}
              <div className="mt-4 flex flex-wrap gap-3">
                <Link href={data.launch_links.follow_through_url} className="bip-btn-primary rounded-full px-4 py-2 text-sm font-medium">
                  Open team decision tools
                </Link>
                {data.launch_links.style_xray_url ? (
                  <Link href={data.launch_links.style_xray_url} className="rounded-full border border-[var(--border-strong)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]">
                    Open Style X-Ray
                  </Link>
                ) : null}
                {data.launch_links.replay_url ? (
                  <Link href={data.launch_links.replay_url} className="rounded-full border border-[var(--border-strong)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]">
                    Review replay
                  </Link>
                ) : null}
                <Link href={`/teams/${activeTeam}?tab=roster`} className="rounded-full border border-[var(--border-strong)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]">
                  Open availability board
                </Link>
                <Link href={`/compare?mode=teams&team_a=${activeTeam}&team_b=${activeOpponent}&season=${activeSeason}&return_to=${encodeURIComponent(`/pre-read?team=${activeTeam}&opponent=${activeOpponent}&season=${activeSeason}&mode=${mode}`)}`} className="rounded-full border border-[var(--border-strong)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]">
                  Open comparison sandbox
                </Link>
                <Link href={data.launch_links.follow_through_url} className="rounded-full border border-[var(--border-strong)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]">
                  Open follow-through
                </Link>
              </div>
            </section>
          </>
        ) : (
          <ScoutingReportView
            teamAbbreviation={activeTeam}
            opponentAbbreviation={activeOpponent}
            season={activeSeason}
            deck={data}
            intelligence={teamIntelligence ?? null}
            rotationReport={rotationReport ?? null}
            packet={activePacket}
            onPacketChange={snapshotId ? undefined : setPacketDraft}
            readOnlyPacket={Boolean(snapshotId)}
          />
        )
      ) : null}
    </div>
  );
}

export default function PreReadPage() {
  return (
    <Suspense>
      <PreReadPageInner />
    </Suspense>
  );
}
