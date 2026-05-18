// Sprint 101 (Stream B) — international + G League per-season stats table.
//
// Mirrors the existing CollegeStats table layout, with one row per season.
// League column shows the source (Euroleague / EuroCup / Adriatic / French
// LNB / G League). Hides entirely when no rows.

import type { InternationalStatLine } from "@/lib/types";

interface Props {
  rows: InternationalStatLine[] | null | undefined;
}

function leagueAttribution(rows: InternationalStatLine[]): { label: string; url: string | null } | null {
  // Pick the most-recent row's source/source_url for the footer.
  const sorted = [...rows].sort((a, b) => (b.as_of ?? "").localeCompare(a.as_of ?? ""));
  const r = sorted[0];
  if (!r) return null;
  const label = r.source ?? "International leagues";
  return { label, url: r.source_url ?? null };
}

function StatCell({ value, digits = 1, suffix }: { value: number | null | undefined; digits?: number; suffix?: string }) {
  if (value == null) return <span className="text-[var(--muted)]">—</span>;
  return <span>{value.toFixed(digits)}{suffix ?? ""}</span>;
}

function PctCell({ value }: { value: number | null | undefined }) {
  if (value == null) return <span className="text-[var(--muted)]">—</span>;
  return <span>{(value * 100).toFixed(1)}%</span>;
}

export default function InternationalStatsPanel({ rows }: Props) {
  if (!rows || rows.length === 0) return null;

  const sorted = [...rows].sort((a, b) => b.season.localeCompare(a.season));
  const attr = leagueAttribution(rows);

  return (
    <section className="rounded-lg border border-[var(--border)] bg-[var(--surface)] overflow-hidden">
      <div className="px-5 pt-5 pb-3">
        <p className="bip-kicker">International &amp; G League</p>
        <h2 className="bip-display mt-1 text-xl font-bold text-[var(--foreground)]">Pre-NBA seasons abroad</h2>
      </div>
      <table className="w-full text-sm">
        <thead className="bg-[var(--surface-alt)] text-[var(--muted)]">
          <tr>
            <th className="px-4 py-3 text-left font-semibold uppercase tracking-wide text-[11px]">Season</th>
            <th className="px-4 py-3 text-left font-semibold uppercase tracking-wide text-[11px]">League</th>
            <th className="px-4 py-3 text-left font-semibold uppercase tracking-wide text-[11px]">Team</th>
            <th className="px-4 py-3 text-right font-semibold uppercase tracking-wide text-[11px]">GP</th>
            <th className="px-4 py-3 text-right font-semibold uppercase tracking-wide text-[11px]">MIN</th>
            <th className="px-4 py-3 text-right font-semibold uppercase tracking-wide text-[11px]">PPG</th>
            <th className="px-4 py-3 text-right font-semibold uppercase tracking-wide text-[11px]">RPG</th>
            <th className="px-4 py-3 text-right font-semibold uppercase tracking-wide text-[11px]">APG</th>
            <th className="px-4 py-3 text-right font-semibold uppercase tracking-wide text-[11px]">FG%</th>
            <th className="px-4 py-3 text-right font-semibold uppercase tracking-wide text-[11px]">3P%</th>
            <th className="px-4 py-3 text-right font-semibold uppercase tracking-wide text-[11px]">TS%</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, i) => (
            <tr key={`${row.season}-${row.league}-${i}`} className="border-t border-[var(--border)]">
              <td className="px-4 py-2.5 font-medium tabular-nums text-[var(--foreground)]">{row.season}</td>
              <td className="px-4 py-2.5 text-[var(--muted-strong)]">{row.league}</td>
              <td className="px-4 py-2.5 text-[var(--muted)]">{row.team_name ?? "—"}</td>
              <td className="px-4 py-2.5 text-right tabular-nums">{row.games ?? "—"}</td>
              <td className="px-4 py-2.5 text-right tabular-nums"><StatCell value={row.minutes_per_game} /></td>
              <td className="px-4 py-2.5 text-right tabular-nums"><StatCell value={row.ppg} /></td>
              <td className="px-4 py-2.5 text-right tabular-nums"><StatCell value={row.rpg} /></td>
              <td className="px-4 py-2.5 text-right tabular-nums"><StatCell value={row.apg} /></td>
              <td className="px-4 py-2.5 text-right tabular-nums"><PctCell value={row.fg_pct} /></td>
              <td className="px-4 py-2.5 text-right tabular-nums"><PctCell value={row.three_pct} /></td>
              <td className="px-4 py-2.5 text-right tabular-nums"><PctCell value={row.ts_pct} /></td>
            </tr>
          ))}
        </tbody>
      </table>
      {attr ? (
        <div className="px-5 py-3 text-[10px] text-[var(--muted)] border-t border-[var(--border)]">
          Source:{" "}
          {attr.url ? (
            <a href={attr.url} target="_blank" rel="noopener noreferrer" className="bip-link">
              {attr.label} ↗
            </a>
          ) : (
            attr.label
          )}
        </div>
      ) : null}
    </section>
  );
}
