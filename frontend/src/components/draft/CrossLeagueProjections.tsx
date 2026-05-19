// Sprint 104 (Stream B) — cross-league projection variants.
//
// "What if this prospect was producing the same per-game line in the
// G League / Euroleague instead of their actual source league?" Renders
// a compact triptych comparing the primary projection vs alternates.

import { useState } from "react";
import type { NbaTranslationV2 } from "@/lib/types";

interface Props {
  translation: NbaTranslationV2 | null | undefined;
}

function cell(value: number | null | undefined, digits = 1) {
  if (value == null) return <span className="text-[var(--muted)]">—</span>;
  return <span className="tabular-nums">{value.toFixed(digits)}</span>;
}

function pct(value: number | null | undefined) {
  if (value == null) return <span className="text-[var(--muted)]">—</span>;
  return <span className="tabular-nums">{(value * 100).toFixed(1)}%</span>;
}

// USG comes through the API as an already-percentage value (e.g. 26.4
// means 26.4%), while TS% is a fraction (0.61 means 61%). Render USG
// without the *100.
function usg(value: number | null | undefined) {
  if (value == null) return <span className="text-[var(--muted)]">—</span>;
  return <span className="tabular-nums">{value.toFixed(1)}%</span>;
}

export default function CrossLeagueProjections({ translation }: Props) {
  const [open, setOpen] = useState(false);

  if (!translation || !translation.alternate_paths || translation.alternate_paths.length === 0) {
    return null;
  }

  const primary = {
    league: translation.source_league || "Source league",
    pts: translation.pts_per100?.point ?? null,
    reb: translation.reb_per100?.point ?? null,
    ast: translation.ast_per100?.point ?? null,
    ts: translation.ts_pct?.point ?? null,
    usg: translation.usg_pct ?? null,
  };

  return (
    <section className="bip-panel rounded-[1.85rem] overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-[var(--surface-alt)] transition-colors"
      >
        <div>
          <p className="bip-kicker">Alternate developmental paths</p>
          <h2 className="bip-display mt-1 text-xl font-bold text-[var(--foreground)]">
            Cross-league projections
          </h2>
        </div>
        <span className="text-xs text-[var(--muted)]">{open ? "Hide" : "Show"}</span>
      </button>

      {open ? (
        <div className="px-6 pb-6 pt-0">
          <p className="text-xs text-[var(--muted)] mb-3">
            Same per-game production, scaled by each league&apos;s strength + shooting haircut.
            A decision tool for &quot;G League vs Europe vs straight to NBA.&quot;
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-[var(--muted)]">
                <tr>
                  <th className="px-3 py-2 text-left font-semibold uppercase tracking-wide text-[11px]">League</th>
                  <th className="px-3 py-2 text-right font-semibold uppercase tracking-wide text-[11px]">PTS/100</th>
                  <th className="px-3 py-2 text-right font-semibold uppercase tracking-wide text-[11px]">REB/100</th>
                  <th className="px-3 py-2 text-right font-semibold uppercase tracking-wide text-[11px]">AST/100</th>
                  <th className="px-3 py-2 text-right font-semibold uppercase tracking-wide text-[11px]">TS%</th>
                  <th className="px-3 py-2 text-right font-semibold uppercase tracking-wide text-[11px]">USG%</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-t border-[var(--border)] bg-[rgba(33,72,59,0.05)]">
                  <td className="px-3 py-2 font-semibold text-[var(--foreground)]">
                    {primary.league}{" "}
                    <span className="text-[10px] uppercase text-[var(--muted)] ml-1">primary</span>
                  </td>
                  <td className="px-3 py-2 text-right">{cell(primary.pts)}</td>
                  <td className="px-3 py-2 text-right">{cell(primary.reb)}</td>
                  <td className="px-3 py-2 text-right">{cell(primary.ast)}</td>
                  <td className="px-3 py-2 text-right">{pct(primary.ts)}</td>
                  <td className="px-3 py-2 text-right">{usg(primary.usg)}</td>
                </tr>
                {translation.alternate_paths.map((p) => (
                  <tr key={p.league_strength_key} className="border-t border-[var(--border)]">
                    <td className="px-3 py-2 text-[var(--muted-strong)]">
                      if {p.league}
                      <span className="text-[10px] text-[var(--muted)] ml-2">×{p.league_strength_multiplier.toFixed(2)}</span>
                    </td>
                    <td className="px-3 py-2 text-right">{cell(p.projected_pts_per100)}</td>
                    <td className="px-3 py-2 text-right">{cell(p.projected_reb_per100)}</td>
                    <td className="px-3 py-2 text-right">{cell(p.projected_ast_per100)}</td>
                    <td className="px-3 py-2 text-right">{pct(p.projected_ts_pct)}</td>
                    <td className="px-3 py-2 text-right">{usg(p.projected_usg_pct)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </section>
  );
}
