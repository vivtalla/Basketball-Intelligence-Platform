"use client";

import { useEffect, useMemo, useState } from "react";
import useSWR from "swr";
import {
  getTeamContracts,
  getTradeImpact,
  validateTrade,
} from "@/lib/api";
import { useTeams } from "@/hooks/usePlayerStats";
import type {
  TeamContractEntry,
  TeamContractsResponse,
  TeamImpactProjection,
  TeamSalaryLine,
  TradeImpactResult,
  TradePackage,
  TradeRequest,
  TradeValidationResult,
  TradeWarning,
} from "@/lib/types";
import { Kicker, Pill, Stat } from "@/components/brand";

const DEFAULT_SEASON = "2025-26";
const SLOT_LABELS = ["Team A", "Team B", "Team C", "Team D"];

// ---------- helpers -------------------------------------------------------

function formatUsd(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  if (Math.abs(value) >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(1)}M`;
  }
  if (Math.abs(value) >= 1_000) {
    return `$${(value / 1_000).toFixed(0)}K`;
  }
  return `$${value}`;
}

function severityTone(severity: TradeWarning["severity"]):
  | "default"
  | "accent"
  | "signal"
  | "positive"
  | "negative" {
  if (severity === "hard_block") return "negative";
  if (severity === "warning") return "signal";
  return "default";
}

function ruleLabel(rule: string): string {
  const labels: Record<string, string> = {
    salary_match: "Salary Match",
    tax_line: "Luxury Tax",
    first_apron: "First Apron",
    second_apron: "Second Apron",
    byc: "BYC",
    traded_player_exception: "TPE",
    structure: "Structure",
  };
  return labels[rule] ?? rule;
}

// ---------- methodology popover ------------------------------------------

function MethodologyTooltip() {
  return (
    <span
      className="group relative inline-flex items-center"
      tabIndex={0}
      aria-label="How the trade machine evaluates trades"
    >
      <span
        aria-hidden
        className="inline-flex items-center justify-center rounded-full border text-[11px] font-bold cursor-help transition-colors hover:bg-[var(--accent)] hover:text-[var(--accent-ink)] hover:border-[var(--accent)] group-focus:bg-[var(--accent)] group-focus:text-[var(--accent-ink)]"
        style={{
          width: 18,
          height: 18,
          borderColor: "var(--border-strong)",
          color: "var(--muted)",
          fontFamily: "var(--font-display)",
        }}
      >
        i
      </span>
      <span
        role="tooltip"
        className="absolute left-0 top-full mt-2 z-30 w-[340px] max-w-[calc(100vw-2rem)] p-4 rounded-xl border shadow-lg opacity-0 pointer-events-none translate-y-1 transition-all duration-150 group-hover:opacity-100 group-hover:pointer-events-auto group-hover:translate-y-0 group-focus:opacity-100 group-focus:pointer-events-auto group-focus:translate-y-0"
        style={{
          background: "var(--surface)",
          borderColor: "var(--border-strong)",
          boxShadow: "var(--shadow)",
        }}
      >
        <p className="bip-kicker mb-2" style={{ color: "var(--accent)" }}>
          Trade Machine · Methodology
        </p>
        <ul
          className="text-[12px] leading-5 space-y-1.5 text-[var(--foreground)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          <li>
            <strong>Salary match:</strong> outgoing must be within 125% of
            incoming (CBA rule). Hard block when violated.
          </li>
          <li>
            <strong>Apron / tax flags:</strong> tax line ($170.8M), 1st apron
            ($178.1M), 2nd apron ($188.9M). Surfaced as warnings — never
            enforced.
          </li>
          <li>
            <strong>BYC + TPE:</strong> info-only flags for Bird-rights timing
            and Trade-Player Exception eligibility.
          </li>
          <li>
            <strong>Net rating delta:</strong> baseline + Σ (incoming on/off ×
            mpg/48) − Σ (outgoing on/off × mpg/48), clipped at ±12.
          </li>
          <li>
            <strong>Rotation health:</strong> fraction of 9 ≥20mpg slots
            remaining post-trade. Below 0.6 is a roster flag.
          </li>
          <li>
            <strong>Confidence:</strong> "thin_sample" when on/off rows are
            missing for some players.
          </li>
        </ul>
      </span>
    </span>
  );
}

// ---------- per-team package builder -------------------------------------

interface TeamSlotProps {
  index: number;
  teamAbbr: string | null;
  outgoingIds: number[];
  incomingDescriptors: { fromTeam: string; player: TeamContractEntry }[];
  onPickTeam: (abbr: string | null) => void;
  onToggleOutgoing: (playerId: number) => void;
  onRemove?: () => void;
  availableTeams: { abbr: string; name: string }[];
}

function TeamSlot({
  index,
  teamAbbr,
  outgoingIds,
  incomingDescriptors,
  onPickTeam,
  onToggleOutgoing,
  onRemove,
  availableTeams,
}: TeamSlotProps) {
  const { data: contractsData, isLoading } = useSWR<TeamContractsResponse>(
    teamAbbr ? ["trade-contracts", teamAbbr, DEFAULT_SEASON] : null,
    () => getTeamContracts(teamAbbr as string, DEFAULT_SEASON)
  );

  const contracts = contractsData?.contracts ?? [];

  return (
    <section
      className="bip-panel rounded-2xl p-5 flex flex-col gap-4"
      style={{ minHeight: 360 }}
    >
      <header className="flex items-start justify-between gap-3">
        <div>
          <Kicker>{SLOT_LABELS[index] ?? `Team ${index + 1}`}</Kicker>
          <select
            className="mt-1 w-full bip-input bg-transparent text-base font-semibold text-[var(--foreground)] border-0 border-b border-[var(--border-strong)] focus:outline-none focus:border-[var(--accent)]"
            style={{ fontFamily: "var(--font-display)" }}
            value={teamAbbr ?? ""}
            onChange={(e) => onPickTeam(e.target.value || null)}
            aria-label={`${SLOT_LABELS[index]} team picker`}
          >
            <option value="">Pick a team…</option>
            {availableTeams.map((t) => (
              <option key={t.abbr} value={t.abbr}>
                {t.abbr} · {t.name}
              </option>
            ))}
          </select>
        </div>
        {onRemove && (
          <button
            type="button"
            onClick={onRemove}
            className="text-xs text-[var(--muted)] hover:text-[var(--danger-ink)]"
            aria-label="Remove team slot"
          >
            Remove
          </button>
        )}
      </header>

      {!teamAbbr && (
        <p
          className="text-sm italic text-[var(--muted)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Pick a team to see its contracts.
        </p>
      )}

      {teamAbbr && isLoading && (
        <p className="text-sm text-[var(--muted)]">Loading contracts…</p>
      )}

      {teamAbbr && !isLoading && contracts.length === 0 && (
        <p
          className="text-sm italic text-[var(--muted)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          No contracts yet for {teamAbbr}. Run salary sync.
        </p>
      )}

      {teamAbbr && contracts.length > 0 && (
        <>
          <div className="flex items-center justify-between text-xs">
            <span className="text-[var(--muted)] uppercase tracking-wider">
              Outgoing — pick players to send
            </span>
            <span className="text-[var(--muted)] tabular-nums">
              Cap: {formatUsd(contractsData?.total_salary)}
            </span>
          </div>

          <ul className="flex flex-col gap-1 max-h-[260px] overflow-y-auto">
            {contracts.map((c) => {
              const checked = outgoingIds.includes(c.player_id);
              return (
                <li key={`${c.player_id}-${c.season}`}>
                  <label
                    className="flex items-center justify-between gap-2 px-2 py-1.5 rounded-md cursor-pointer hover:bg-[rgba(33,72,59,0.05)]"
                    style={{
                      background: checked ? "rgba(33,72,59,0.08)" : "transparent",
                    }}
                  >
                    <span className="flex items-center gap-2 min-w-0">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => onToggleOutgoing(c.player_id)}
                        className="shrink-0"
                      />
                      <span className="truncate text-sm">
                        {c.player_name}
                        {c.contract_type && (
                          <span className="ml-1 text-[10px] uppercase text-[var(--muted)]">
                            · {c.contract_type}
                          </span>
                        )}
                      </span>
                    </span>
                    <span className="tabular-nums text-sm text-[var(--muted)] shrink-0">
                      {formatUsd(c.salary)}
                    </span>
                  </label>
                </li>
              );
            })}
          </ul>

          {incomingDescriptors.length > 0 && (
            <div className="mt-1 pt-3 border-t border-[var(--border)]">
              <p className="text-xs uppercase tracking-wider text-[var(--muted)] mb-2">
                Incoming
              </p>
              <ul className="flex flex-col gap-1">
                {incomingDescriptors.map((entry) => (
                  <li
                    key={`${entry.player.player_id}-in`}
                    className="flex items-center justify-between gap-2 text-sm"
                  >
                    <span className="truncate">
                      {entry.player.player_name}
                      <span className="ml-1 text-[10px] uppercase text-[var(--muted)]">
                        · from {entry.fromTeam}
                      </span>
                    </span>
                    <span className="tabular-nums text-[var(--muted)] shrink-0">
                      {formatUsd(entry.player.salary)}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </section>
  );
}

// ---------- validation card ----------------------------------------------

function ValidationCard({
  validation,
  loading,
}: {
  validation: TradeValidationResult | null;
  loading: boolean;
}) {
  if (loading) {
    return (
      <section className="bip-panel rounded-2xl p-5">
        <p className="text-sm text-[var(--muted)]">Validating…</p>
      </section>
    );
  }
  if (!validation) {
    return (
      <section className="bip-panel rounded-2xl p-5">
        <Kicker>Validation</Kicker>
        <p
          className="mt-2 text-sm italic text-[var(--muted)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Configure at least two teams with outgoing players to evaluate.
        </p>
      </section>
    );
  }

  const tone: "positive" | "negative" = validation.valid ? "positive" : "negative";
  return (
    <section className="bip-panel rounded-2xl p-5 flex flex-col gap-4">
      <header className="flex items-center justify-between gap-3">
        <div>
          <Kicker>Validation</Kicker>
          <h3
            className="bip-display text-2xl font-bold mt-1"
            style={{ letterSpacing: "-0.015em" }}
          >
            {validation.valid ? "Trade is legal" : "Trade is blocked"}
          </h3>
        </div>
        <Pill tone={tone}>{validation.valid ? "VALID" : "BLOCKED"}</Pill>
      </header>

      {validation.summary && (
        <p
          className="text-sm text-[var(--muted)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          {validation.summary}
        </p>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {validation.team_salary_lines.map((line: TeamSalaryLine) => (
          <div
            key={line.team_abbr}
            className="rounded-lg border border-[var(--border)] p-3"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-semibold text-sm">{line.team_abbr}</span>
              <span className="text-xs text-[var(--muted)] tabular-nums">
                ratio{" "}
                {line.salary_match_ratio
                  ? line.salary_match_ratio.toFixed(2)
                  : "—"}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <div className="text-[var(--muted)] uppercase">Out</div>
                <div className="tabular-nums font-semibold">
                  {formatUsd(line.outgoing_salary)}
                </div>
              </div>
              <div>
                <div className="text-[var(--muted)] uppercase">In</div>
                <div className="tabular-nums font-semibold">
                  {formatUsd(line.incoming_salary)}
                </div>
              </div>
            </div>
            <div className="text-[11px] text-[var(--muted)] mt-2 tabular-nums">
              Δ {line.delta >= 0 ? "+" : ""}
              {formatUsd(line.delta)}
            </div>
          </div>
        ))}
      </div>

      {validation.warnings.length > 0 && (
        <div>
          <p className="text-xs uppercase tracking-wider text-[var(--muted)] mb-2">
            Flags
          </p>
          <ul className="flex flex-col gap-1.5">
            {validation.warnings.map((w, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <Pill tone={severityTone(w.severity)}>
                  {w.team_abbr || "TRADE"} · {ruleLabel(w.rule)}
                </Pill>
                <span
                  className="text-xs text-[var(--foreground)] flex-1"
                  style={{ fontFamily: "var(--font-display)" }}
                >
                  {w.message}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

// ---------- impact card ---------------------------------------------------

function ImpactCard({
  impact,
  loading,
}: {
  impact: TradeImpactResult | null;
  loading: boolean;
}) {
  if (loading) {
    return (
      <section className="bip-panel rounded-2xl p-5">
        <p className="text-sm text-[var(--muted)]">Projecting impact…</p>
      </section>
    );
  }
  if (!impact || impact.teams.length === 0) {
    return null;
  }

  return (
    <section className="bip-panel rounded-2xl p-5 flex flex-col gap-4">
      <header className="flex items-center gap-2">
        <Kicker>Impact Projection</Kicker>
        <Pill tone="default">{impact.methodology_version}</Pill>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {impact.teams.map((team: TeamImpactProjection) => {
          const deltaIsPos = (team.net_rating_delta ?? 0) > 0;
          const deltaIsNeg = (team.net_rating_delta ?? 0) < 0;
          return (
            <div
              key={team.team_abbr}
              className="rounded-lg border border-[var(--border)] p-4 flex flex-col gap-3"
            >
              <div className="flex items-center justify-between">
                <span
                  className="text-lg font-bold"
                  style={{ fontFamily: "var(--font-display)" }}
                >
                  {team.team_abbr}
                </span>
                <Pill
                  tone={
                    team.confidence === "ready"
                      ? "accent"
                      : team.confidence === "thin_sample"
                      ? "signal"
                      : "default"
                  }
                >
                  {team.confidence}
                </Pill>
              </div>

              <div className="grid grid-cols-3 gap-2">
                <Stat
                  label="Baseline"
                  value={
                    team.baseline_net_rating !== null &&
                    team.baseline_net_rating !== undefined
                      ? team.baseline_net_rating.toFixed(1)
                      : "—"
                  }
                  size="sm"
                />
                <Stat
                  label="Projected"
                  value={
                    team.projected_net_rating !== null &&
                    team.projected_net_rating !== undefined
                      ? team.projected_net_rating.toFixed(1)
                      : "—"
                  }
                  size="sm"
                />
                <Stat
                  label="Δ Net"
                  value={
                    team.net_rating_delta !== null &&
                    team.net_rating_delta !== undefined
                      ? `${team.net_rating_delta > 0 ? "+" : ""}${team.net_rating_delta.toFixed(1)}`
                      : "—"
                  }
                  tone={deltaIsPos ? "soft" : deltaIsNeg ? "signal" : "default"}
                  size="sm"
                />
              </div>

              {team.rotation_health_score !== null &&
                team.rotation_health_score !== undefined && (
                  <div className="text-xs text-[var(--muted)]">
                    Rotation health{" "}
                    <span className="text-[var(--foreground)] font-semibold tabular-nums">
                      {(team.rotation_health_score * 100).toFixed(0)}%
                    </span>
                  </div>
                )}

              {team.archetype_gaps.length > 0 && (
                <ul className="flex flex-wrap gap-1.5">
                  {team.archetype_gaps.map((g, i) => (
                    <li key={i}>
                      <Pill
                        tone={g.direction === "added" ? "positive" : "negative"}
                      >
                        {g.note}
                      </Pill>
                    </li>
                  ))}
                </ul>
              )}

              {team.notes.length > 0 && (
                <ul
                  className="text-[11px] text-[var(--muted)] space-y-0.5"
                  style={{ fontFamily: "var(--font-geist-mono)" }}
                >
                  {team.notes.map((note, i) => (
                    <li key={i}>· {note}</li>
                  ))}
                </ul>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

// ---------- main page ----------------------------------------------------

export default function TradeMachinePage() {
  const { data: teams } = useTeams();
  const teamOptions = useMemo(
    () =>
      (teams ?? []).map((t) => ({
        abbr: t.abbreviation,
        name: t.name ?? t.abbreviation,
      })),
    [teams]
  );

  // Up to 4 team slots, default 2 visible.
  const [slotCount, setSlotCount] = useState<number>(2);
  const [teamSlots, setTeamSlots] = useState<(string | null)[]>([null, null, null, null]);
  const [outgoingBySlot, setOutgoingBySlot] = useState<number[][]>([[], [], [], []]);

  // Per-slot contract cache so we can echo incoming entries back.
  const [contractsByTeam, setContractsByTeam] = useState<
    Record<string, TeamContractsResponse | null>
  >({});

  // Watcher: whenever a team is picked, fetch its contracts once and cache.
  // We piggyback on `useSWR` inside <TeamSlot>, but ALSO mirror the data here
  // so we can construct the "incoming" list for a partner slot. Cheap fetch
  // since SWR will dedupe.
  useEffect(() => {
    let cancelled = false;
    teamSlots.slice(0, slotCount).forEach((abbr) => {
      if (!abbr || contractsByTeam[abbr]) return;
      getTeamContracts(abbr, DEFAULT_SEASON)
        .then((resp) => {
          if (!cancelled) {
            setContractsByTeam((prev) => ({ ...prev, [abbr]: resp }));
          }
        })
        .catch(() => {
          if (!cancelled) {
            setContractsByTeam((prev) => ({ ...prev, [abbr]: null }));
          }
        });
    });
    return () => {
      cancelled = true;
    };
  }, [teamSlots, slotCount, contractsByTeam]);

  // Build the request packages.
  const packages: TradePackage[] = useMemo(() => {
    const slots = teamSlots.slice(0, slotCount);
    const out: TradePackage[] = [];
    for (let i = 0; i < slots.length; i++) {
      const abbr = slots[i];
      if (!abbr) continue;
      // Round-robin redistribute outgoing players across other slots.
      const otherSlots = slots
        .map((s, idx) => ({ s, idx }))
        .filter((row) => row.s && row.idx !== i)
        .map((row) => row.idx);
      const incomingIds: number[] = [];
      otherSlots.forEach((idx) => {
        outgoingBySlot[idx].forEach((pid, posIdx) => {
          // Distribute by index modulo the number of receivers.
          const receivers = otherSlots.length;
          const targetSlot = otherSlots[posIdx % receivers];
          if (targetSlot === i) {
            incomingIds.push(pid);
          }
        });
      });
      out.push({
        team_abbr: abbr,
        outgoing_player_ids: outgoingBySlot[i] ?? [],
        incoming_player_ids: incomingIds,
      });
    }
    return out;
  }, [teamSlots, outgoingBySlot, slotCount]);

  // Eligible to fire? Need 2+ teams w/ at least one outgoing player each.
  const requestEligible = useMemo(() => {
    if (packages.length < 2) return false;
    const movers = packages.filter((p) => p.outgoing_player_ids.length > 0);
    return movers.length >= 2;
  }, [packages]);

  const tradeRequest: TradeRequest = useMemo(
    () => ({ season: DEFAULT_SEASON, packages }),
    [packages]
  );

  const { data: validation, isLoading: validationLoading } = useSWR<TradeValidationResult>(
    requestEligible ? ["trade-validate", JSON.stringify(tradeRequest)] : null,
    () => validateTrade(tradeRequest)
  );

  const { data: impact, isLoading: impactLoading } = useSWR<TradeImpactResult>(
    requestEligible ? ["trade-impact", JSON.stringify(tradeRequest)] : null,
    () => getTradeImpact(tradeRequest)
  );

  // Build incoming descriptors for each slot from the cached contracts.
  function descriptorsFor(slotIdx: number): {
    fromTeam: string;
    player: TeamContractEntry;
  }[] {
    const incomingIds = packages[slotIdx]?.incoming_player_ids ?? [];
    if (!incomingIds.length) return [];
    const out: { fromTeam: string; player: TeamContractEntry }[] = [];
    teamSlots.slice(0, slotCount).forEach((abbr, idx) => {
      if (!abbr || idx === slotIdx) return;
      const cached = contractsByTeam[abbr];
      if (!cached) return;
      cached.contracts.forEach((c) => {
        if (incomingIds.includes(c.player_id)) {
          out.push({ fromTeam: abbr, player: c });
        }
      });
    });
    return out;
  }

  function pickTeam(slotIdx: number, abbr: string | null) {
    setTeamSlots((prev) => {
      const next = [...prev];
      next[slotIdx] = abbr;
      return next;
    });
    setOutgoingBySlot((prev) => {
      const next = [...prev];
      next[slotIdx] = [];
      return next;
    });
  }

  function toggleOutgoing(slotIdx: number, playerId: number) {
    setOutgoingBySlot((prev) => {
      const next = [...prev];
      const cur = new Set(next[slotIdx] ?? []);
      if (cur.has(playerId)) cur.delete(playerId);
      else cur.add(playerId);
      next[slotIdx] = Array.from(cur);
      return next;
    });
  }

  function addSlot() {
    if (slotCount < 4) setSlotCount(slotCount + 1);
  }
  function removeSlot(idx: number) {
    if (slotCount <= 2) return;
    setTeamSlots((prev) => {
      const next = [...prev];
      // Shift the removed slot's data out and pad with null at the tail.
      next.splice(idx, 1);
      next.push(null);
      return next;
    });
    setOutgoingBySlot((prev) => {
      const next = [...prev];
      next.splice(idx, 1);
      next.push([]);
      return next;
    });
    setSlotCount(slotCount - 1);
  }

  return (
    <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8 flex flex-col gap-6">
      <header className="flex items-end justify-between gap-4 flex-wrap">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <Kicker>Sprint 78 · Front Office</Kicker>
            <MethodologyTooltip />
          </div>
          <h1
            className="bip-display font-bold text-3xl sm:text-4xl"
            style={{ letterSpacing: "-0.015em" }}
          >
            Trade Machine
          </h1>
          <p
            className="text-sm text-[var(--muted)]"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Build legal trades. Two to four teams. Salary match enforced; tax /
            apron / BYC / TPE flagged.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {slotCount < 4 && (
            <button
              type="button"
              onClick={addSlot}
              className="text-xs px-3 py-1.5 rounded-md border border-[var(--border-strong)] hover:bg-[rgba(33,72,59,0.08)]"
            >
              + Add team
            </button>
          )}
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {teamSlots.slice(0, slotCount).map((abbr, idx) => (
          <TeamSlot
            key={`slot-${idx}`}
            index={idx}
            teamAbbr={abbr}
            outgoingIds={outgoingBySlot[idx] ?? []}
            incomingDescriptors={descriptorsFor(idx)}
            onPickTeam={(next) => pickTeam(idx, next)}
            onToggleOutgoing={(pid) => toggleOutgoing(idx, pid)}
            onRemove={slotCount > 2 ? () => removeSlot(idx) : undefined}
            availableTeams={teamOptions}
          />
        ))}
      </div>

      <ValidationCard validation={validation ?? null} loading={validationLoading} />
      <ImpactCard impact={impact ?? null} loading={impactLoading} />
    </main>
  );
}
