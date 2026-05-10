"use client";

/**
 * Sprint 78 — FO2 Free Agency Workspace
 *
 * League-wide expiring-contract leaderboard with tier/position/age filters.
 * Click a row to see the top-10 team-fit ranking with rationale chips.
 * Empty `player_contracts` renders an explicit empty-state instead of a
 * blank table — FO1's salary ingestion can lag this surface.
 */

import { useMemo, useState } from "react";
import Link from "next/link";
import useSWR from "swr";
import { getFreeAgents, getFreeAgentFits } from "@/lib/api";
import type {
  ExpiringContract,
  FreeAgencyResponse,
  FreeAgentFitsResponse,
  FreeAgentTier,
} from "@/lib/types";

const DEFAULT_SEASON = "2025-26";

const TIER_OPTIONS: { value: "" | FreeAgentTier; label: string }[] = [
  { value: "", label: "All tiers" },
  { value: "max", label: "Max" },
  { value: "above_mid", label: "Above-MLE" },
  { value: "mid_level", label: "Mid-Level" },
  { value: "minimum", label: "Vet Min" },
  { value: "two_way", label: "Two-Way" },
];

const POSITION_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "All positions" },
  { value: "guard", label: "Guards" },
  { value: "forward", label: "Forwards" },
  { value: "center", label: "Centers" },
];

const TIER_LABEL: Record<FreeAgentTier, string> = {
  max: "Max",
  above_mid: "Above-MLE",
  mid_level: "Mid-Level",
  minimum: "Vet Min",
  two_way: "Two-Way",
};

function formatSalary(value: number | null): string {
  if (value == null || value <= 0) return "—";
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  return `$${(value / 1000).toFixed(0)}K`;
}

function formatNumber(value: number | null, digits = 1): string {
  if (value == null) return "—";
  return value.toFixed(digits);
}

function formatPct(value: number | null): string {
  if (value == null) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

export default function FreeAgencyPage() {
  const [season] = useState<string>(DEFAULT_SEASON);
  const [tier, setTier] = useState<"" | FreeAgentTier>("");
  const [position, setPosition] = useState<string>("");
  const [ageMax, setAgeMax] = useState<number>(40);
  const [showMethodology, setShowMethodology] = useState<boolean>(false);
  const [expandedPlayerId, setExpandedPlayerId] = useState<number | null>(null);

  const swrKey = useMemo(
    () => ["free-agency", season, tier, position, ageMax] as const,
    [season, tier, position, ageMax]
  );

  const { data, error, isLoading } = useSWR<FreeAgencyResponse>(
    swrKey,
    () =>
      getFreeAgents({
        season,
        tier: tier || null,
        position: position || null,
        age_max: ageMax,
      }),
    { revalidateOnFocus: false }
  );

  const contracts = data?.contracts ?? [];
  const isEmpty = data?.is_empty_dataset ?? false;

  return (
    <main className="mx-auto max-w-7xl px-6 py-10">
      <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="bip-kicker mb-1">Front Office</p>
          <h1
            className="bip-display font-bold text-[var(--foreground)]"
            style={{ fontSize: "2.2rem", letterSpacing: "-0.02em" }}
          >
            Free Agency Workspace
          </h1>
          <p className="text-sm text-[var(--muted)] mt-1">
            League-wide expiring contracts with tier filters and team-fit
            rankings. Click any row to see the top-10 fits with rationale
            chips.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowMethodology((s) => !s)}
          className="text-xs font-mono uppercase tracking-[0.14em] text-[var(--muted)] hover:text-[var(--accent)] transition-colors"
          aria-expanded={showMethodology}
        >
          {showMethodology ? "Hide" : "ⓘ"} Methodology
        </button>
      </header>

      {showMethodology && data?.methodology ? (
        <section className="bip-panel rounded-[1.25rem] p-5 mb-6 text-sm text-[var(--muted)]">
          <h2 className="bip-display font-semibold text-[var(--foreground)] mb-2">
            How this is computed
          </h2>
          <p className="mb-2">
            Methodology version{" "}
            <code className="font-mono">{data.methodology.version}</code>.
          </p>
          <ul className="list-disc pl-5 space-y-1">
            {data.methodology.notes.map((note, idx) => (
              <li key={idx}>{note}</li>
            ))}
          </ul>
          <div className="mt-3">
            <p className="font-semibold text-[var(--foreground)] mb-1">
              Tier thresholds (USD)
            </p>
            <ul className="font-mono text-xs grid grid-cols-2 md:grid-cols-3 gap-x-6 gap-y-1">
              {Object.entries(data.methodology.tier_thresholds_usd).map(
                ([key, val]) => (
                  <li key={key}>
                    <span className="text-[var(--muted)]">{key}:</span>{" "}
                    <span className="text-[var(--foreground)]">
                      ${val.toLocaleString()}
                    </span>
                  </li>
                )
              )}
            </ul>
          </div>
        </section>
      ) : null}

      {/* Filter bar */}
      <section
        className="bip-panel rounded-[1.5rem] p-4 mb-5 flex flex-wrap items-center gap-4"
        aria-label="Free agency filters"
      >
        <div>
          <label className="block text-[10px] font-mono uppercase tracking-[0.16em] text-[var(--muted)] mb-1">
            Tier
          </label>
          <select
            value={tier}
            onChange={(e) => setTier(e.target.value as "" | FreeAgentTier)}
            className="bg-transparent border border-[var(--border)] rounded-md px-3 py-1.5 text-sm font-medium text-[var(--foreground)]"
          >
            {TIER_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-[10px] font-mono uppercase tracking-[0.16em] text-[var(--muted)] mb-1">
            Position
          </label>
          <select
            value={position}
            onChange={(e) => setPosition(e.target.value)}
            className="bg-transparent border border-[var(--border)] rounded-md px-3 py-1.5 text-sm font-medium text-[var(--foreground)]"
          >
            {POSITION_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-end gap-3">
          <div>
            <label className="block text-[10px] font-mono uppercase tracking-[0.16em] text-[var(--muted)] mb-1">
              Max age: {ageMax}
            </label>
            <input
              type="range"
              min={20}
              max={45}
              value={ageMax}
              onChange={(e) => setAgeMax(Number(e.target.value))}
              className="w-40"
            />
          </div>
        </div>

        <div className="ml-auto text-xs text-[var(--muted)] tabular-nums">
          {data ? (
            <>
              <span className="font-mono">{data.filtered_count}</span> of{" "}
              <span className="font-mono">{data.total_count}</span> contracts
              {tier || position || ageMax < 45 ? " (filtered)" : ""}
            </>
          ) : null}
        </div>
      </section>

      {/* Body */}
      {isLoading ? (
        <div className="bip-panel rounded-[1.5rem] p-6 animate-pulse space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <div
              key={i}
              className="h-9 rounded bg-[var(--surface-alt)]"
            />
          ))}
        </div>
      ) : error ? (
        <div className="bip-panel rounded-[1.5rem] p-8 text-center">
          <p className="text-[var(--muted)] italic">
            Couldn&rsquo;t load free agents for {season}.
          </p>
        </div>
      ) : isEmpty ? (
        <div className="bip-panel rounded-[1.5rem] p-10 text-center">
          <p
            className="bip-display text-[var(--foreground)] mb-2"
            style={{ fontSize: "1.4rem", letterSpacing: "-0.015em" }}
          >
            Salary data not yet ingested.
          </p>
          <p className="text-sm text-[var(--muted)] max-w-xl mx-auto">
            The Free Agency Workspace populates once the FO1 salary
            ingestion pipeline lands its first nightly sync. Until then,
            this surface stays empty rather than guessing at contract
            structure.
          </p>
        </div>
      ) : contracts.length === 0 ? (
        <div className="bip-panel rounded-[1.5rem] p-10 text-center">
          <p className="text-[var(--muted)] italic">
            No expiring contracts match the current filters.
          </p>
        </div>
      ) : (
        <FreeAgentTable
          contracts={contracts}
          season={season}
          expandedPlayerId={expandedPlayerId}
          onToggle={(id) =>
            setExpandedPlayerId((current) => (current === id ? null : id))
          }
        />
      )}
    </main>
  );
}

interface FreeAgentTableProps {
  contracts: ExpiringContract[];
  season: string;
  expandedPlayerId: number | null;
  onToggle: (playerId: number) => void;
}

function FreeAgentTable({
  contracts,
  season,
  expandedPlayerId,
  onToggle,
}: FreeAgentTableProps) {
  return (
    <section className="bip-panel rounded-[1.5rem] overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr
            className="text-[10px] uppercase border-b border-[var(--border)]"
            style={{
              fontFamily: "var(--font-geist-mono)",
              letterSpacing: "0.16em",
              color: "var(--muted)",
            }}
          >
            <th className="text-left px-4 py-2 w-10">#</th>
            <th className="text-left px-2 py-2">Player</th>
            <th className="text-left px-2 py-2 w-16">Team</th>
            <th className="text-left px-2 py-2 w-24">Tier</th>
            <th className="text-right px-2 py-2 w-24">Salary</th>
            <th className="text-right px-2 py-2 w-14">Age</th>
            <th className="text-right px-2 py-2 w-16">PPG</th>
            <th className="text-right px-2 py-2 w-16">RPG</th>
            <th className="text-right px-2 py-2 w-16">APG</th>
            <th className="text-right px-2 py-2 w-16">TS%</th>
            <th className="text-right px-4 py-2 w-20">Fits →</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--border)]">
          {contracts.map((contract, idx) => {
            const isExpanded = expandedPlayerId === contract.player_id;
            return (
              <FreeAgentRow
                key={contract.player_id}
                rank={idx + 1}
                contract={contract}
                isExpanded={isExpanded}
                onToggle={() => onToggle(contract.player_id)}
                season={season}
              />
            );
          })}
        </tbody>
      </table>
    </section>
  );
}

interface FreeAgentRowProps {
  rank: number;
  contract: ExpiringContract;
  isExpanded: boolean;
  onToggle: () => void;
  season: string;
}

function FreeAgentRow({
  rank,
  contract,
  isExpanded,
  onToggle,
  season,
}: FreeAgentRowProps) {
  return (
    <>
      <tr
        className={`hover:bg-[rgba(33,72,59,0.05)] transition-colors cursor-pointer ${
          isExpanded ? "bg-[rgba(33,72,59,0.06)]" : ""
        }`}
        onClick={onToggle}
        aria-expanded={isExpanded}
      >
        <td className="px-4 py-2.5 text-[var(--muted)] tabular-nums">{rank}</td>
        <td className="px-2 py-2.5">
          <Link
            href={`/players/${contract.player_id}`}
            className="font-semibold text-[var(--foreground)] hover:text-[var(--accent)] transition-colors"
            style={{
              fontFamily: "var(--font-display)",
              letterSpacing: "-0.01em",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {contract.player_name}
          </Link>
          {contract.position ? (
            <span
              className="ml-2 text-[11px] text-[var(--muted)] uppercase"
              style={{ fontFamily: "var(--font-geist-mono)" }}
            >
              {contract.position}
            </span>
          ) : null}
        </td>
        <td
          className="px-2 py-2.5 text-[var(--muted)] font-mono"
          style={{ letterSpacing: "0.06em" }}
        >
          {contract.team_abbreviation ?? "—"}
        </td>
        <td className="px-2 py-2.5">
          <TierPill tier={contract.tier} />
        </td>
        <td className="px-2 py-2.5 text-right tabular-nums">
          {formatSalary(contract.salary)}
          {contract.is_player_option ? (
            <span className="ml-1 text-[10px] text-[var(--muted)]">PO</span>
          ) : null}
          {contract.is_team_option ? (
            <span className="ml-1 text-[10px] text-[var(--muted)]">TO</span>
          ) : null}
        </td>
        <td className="px-2 py-2.5 text-right tabular-nums text-[var(--muted)]">
          {contract.age ?? "—"}
        </td>
        <td className="px-2 py-2.5 text-right tabular-nums">
          {formatNumber(contract.pts_pg)}
        </td>
        <td className="px-2 py-2.5 text-right tabular-nums">
          {formatNumber(contract.reb_pg)}
        </td>
        <td className="px-2 py-2.5 text-right tabular-nums">
          {formatNumber(contract.ast_pg)}
        </td>
        <td className="px-2 py-2.5 text-right tabular-nums">
          {formatPct(contract.ts_pct)}
        </td>
        <td
          className="px-4 py-2.5 text-right tabular-nums font-bold text-[11px] uppercase"
          style={{
            fontFamily: "var(--font-geist-mono)",
            letterSpacing: "0.14em",
            color: "var(--accent)",
          }}
        >
          {isExpanded ? "Hide" : "Show"}
        </td>
      </tr>
      {isExpanded ? (
        <tr>
          <td colSpan={11} className="bg-[var(--surface-alt)] px-6 py-5">
            <FreeAgentFitsPanel
              playerId={contract.player_id}
              playerName={contract.player_name}
              season={season}
            />
          </td>
        </tr>
      ) : null}
    </>
  );
}

function TierPill({ tier }: { tier: FreeAgentTier }) {
  return (
    <span
      className="inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-mono uppercase tracking-[0.12em]"
      style={{
        background: tier === "max" ? "var(--accent)" : "transparent",
        color: tier === "max" ? "var(--accent-ink)" : "var(--muted)",
        borderColor: tier === "max" ? "var(--accent)" : "var(--border)",
      }}
    >
      {TIER_LABEL[tier]}
    </span>
  );
}

interface FreeAgentFitsPanelProps {
  playerId: number;
  playerName: string;
  season: string;
}

function FreeAgentFitsPanel({
  playerId,
  playerName,
  season,
}: FreeAgentFitsPanelProps) {
  const { data, error, isLoading } = useSWR<FreeAgentFitsResponse>(
    ["free-agency-fits", playerId, season],
    () => getFreeAgentFits(playerId, { season, k: 10 }),
    { revalidateOnFocus: false }
  );

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="h-12 rounded bg-[var(--surface)] border border-[var(--border)]"
          />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <p className="text-sm text-[var(--muted)] italic">
        Couldn&rsquo;t load team fits for {playerName}.
      </p>
    );
  }

  if (!data || data.fits.length === 0) {
    const reason = data?.warnings?.[0] ?? "No qualified team-fit rankings yet.";
    return <p className="text-sm text-[var(--muted)] italic">{reason}</p>;
  }

  return (
    <div>
      <p
        className="bip-kicker mb-3 text-[10px]"
        style={{ letterSpacing: "0.16em" }}
      >
        Top {data.fits.length} team fits for {data.player_name}
      </p>
      <div className="space-y-2">
        {data.fits.map((fit) => (
          <div
            key={fit.team_abbreviation}
            className="flex flex-wrap items-center gap-3 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-4 py-2.5"
          >
            <span className="text-xs font-mono text-[var(--muted)] tabular-nums w-6">
              #{fit.rank}
            </span>
            <span
              className="font-semibold text-[var(--foreground)]"
              style={{
                fontFamily: "var(--font-display)",
                letterSpacing: "-0.01em",
              }}
            >
              {fit.team_abbreviation}
            </span>
            {fit.team_name ? (
              <span className="text-xs text-[var(--muted)]">
                {fit.team_name}
              </span>
            ) : null}
            <span
              className="text-xs font-mono uppercase tracking-[0.12em] text-[var(--accent)]"
            >
              fit {fit.fit_score.toFixed(1)}
            </span>
            {fit.confidence ? (
              <span className="text-[10px] font-mono uppercase tracking-[0.12em] text-[var(--muted)]">
                {fit.confidence}
              </span>
            ) : null}
            <div className="flex flex-wrap gap-1.5 ml-auto">
              {fit.rationale_chips.slice(0, 4).map((chip, idx) => (
                <span
                  key={idx}
                  className="inline-flex items-center rounded-full border border-[var(--border)] bg-transparent px-2 py-0.5 text-[10px] text-[var(--muted)]"
                  title={chip.detail ?? undefined}
                >
                  {chip.label}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
      {data.warnings.length > 0 ? (
        <ul className="mt-3 space-y-1 text-[11px] italic text-[var(--muted)]">
          {data.warnings.map((w, idx) => (
            <li key={idx}>{w}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
