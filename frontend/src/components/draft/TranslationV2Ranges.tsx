// Sprint 101 (Stream B) — translation v2 with point-and-CI range bars.
//
// Renders each metric that has a PointInterval (pts/reb/ast/TS%) as a
// horizontal bar: the lower-upper extent as the bar, a tick mark at the
// point estimate. Shows confidence_factors as a list at the bottom.
//
// Co-exists with the existing v1 translation panel on the prospect-detail
// page — the user sees both until a future sprint deprecates v1.

import type { NbaTranslationV2, PointInterval } from "@/lib/types";

interface Props {
  translation: NbaTranslationV2 | null | undefined;
}

interface MetricSpec {
  key: keyof NbaTranslationV2;
  label: string;
  axisMin: number;
  axisMax: number;
  format: (v: number) => string;
}

const METRICS: MetricSpec[] = [
  { key: "pts_per100", label: "PTS / 100", axisMin: 0,    axisMax: 50,  format: (v) => v.toFixed(1) },
  { key: "reb_per100", label: "REB / 100", axisMin: 0,    axisMax: 20,  format: (v) => v.toFixed(1) },
  { key: "ast_per100", label: "AST / 100", axisMin: 0,    axisMax: 15,  format: (v) => v.toFixed(1) },
  { key: "ts_pct",     label: "TS%",       axisMin: 0.40, axisMax: 0.70, format: (v) => `${(v * 100).toFixed(1)}%` },
];

function clamp01(v: number): number {
  return Math.max(0, Math.min(1, v));
}

function MetricRow({ spec, interval }: { spec: MetricSpec; interval: PointInterval }) {
  const range = spec.axisMax - spec.axisMin;
  const lowerPct = clamp01((interval.lower - spec.axisMin) / range);
  const upperPct = clamp01((interval.upper - spec.axisMin) / range);
  const pointPct = clamp01((interval.point - spec.axisMin) / range);

  return (
    <div className="grid grid-cols-[100px_1fr_auto] items-center gap-3">
      <span className="text-[12px] uppercase tracking-wide text-[var(--muted)]">{spec.label}</span>
      <div className="relative h-6">
        {/* Track */}
        <svg viewBox="0 0 100 24" preserveAspectRatio="none" className="absolute inset-0 w-full h-full">
          <line x1="0" y1="12" x2="100" y2="12" stroke="rgba(180,137,61,0.20)" strokeWidth="0.7" />
          {/* 95% CI range bar */}
          <rect
            x={lowerPct * 100}
            y={9}
            width={Math.max(1, (upperPct - lowerPct) * 100)}
            height={6}
            rx={1}
            fill="rgba(33,72,59,0.20)"
            stroke="rgba(33,72,59,0.40)"
            strokeWidth="0.4"
          />
          {/* Point estimate tick */}
          <line
            x1={pointPct * 100}
            y1={5}
            x2={pointPct * 100}
            y2={19}
            stroke="#21483b"
            strokeWidth="1.5"
          />
        </svg>
      </div>
      <span className="tabular-nums text-right text-[12px] font-semibold text-[var(--foreground)] whitespace-nowrap">
        {spec.format(interval.point)}
        <span className="ml-1 text-[10px] font-normal text-[var(--muted)]">
          ({spec.format(interval.lower)} – {spec.format(interval.upper)})
        </span>
      </span>
    </div>
  );
}

export default function TranslationV2Ranges({ translation }: Props) {
  if (!translation) return null;

  // Filter to metrics whose interval is non-null on this prospect.
  const rendered = METRICS.flatMap<{ spec: MetricSpec; interval: PointInterval }>((spec) => {
    const raw = translation[spec.key];
    if (raw && typeof raw === "object" && "point" in raw) {
      return [{ spec, interval: raw as unknown as PointInterval }];
    }
    return [];
  });
  if (rendered.length === 0) return null;

  return (
    <section className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5">
      <p className="bip-kicker">NBA translation v2</p>
      <h2 className="bip-display mt-1 text-xl font-bold text-[var(--foreground)]">
        Projected NBA per-100 (point + 95% CI)
      </h2>
      <p className="mt-1 text-xs text-[var(--muted)]">
        Pace-adjusted with shooting haircut, league strength, and age curve.
        Wider intervals mean the model has less to lean on — small samples,
        weaker league, or younger projections.
      </p>

      <div className="mt-4 space-y-3">
        {rendered.map(({ spec, interval }) => (
          <MetricRow key={String(spec.key)} spec={spec} interval={interval} />
        ))}
      </div>

      {/* Volume multiplier breakdown */}
      <div className="mt-4 grid gap-2 text-[11px] sm:grid-cols-3">
        {translation.pace_multiplier != null ? (
          <div>
            <div className="uppercase tracking-wide text-[var(--muted)]">Pace mult</div>
            <div className="tabular-nums font-semibold text-[var(--foreground)]">
              ×{translation.pace_multiplier.toFixed(2)}
            </div>
          </div>
        ) : null}
        {translation.league_strength_multiplier != null ? (
          <div>
            <div className="uppercase tracking-wide text-[var(--muted)]">League strength</div>
            <div className="tabular-nums font-semibold text-[var(--foreground)]">
              ×{translation.league_strength_multiplier.toFixed(2)}
              {translation.league_strength_key ? (
                <span className="ml-1 text-[10px] font-normal text-[var(--muted)]">
                  ({translation.league_strength_key.replace(/_/g, " ")})
                </span>
              ) : null}
            </div>
          </div>
        ) : null}
        {translation.age_multiplier != null ? (
          <div>
            <div className="uppercase tracking-wide text-[var(--muted)]">Age curve</div>
            <div className="tabular-nums font-semibold text-[var(--foreground)]">
              ×{translation.age_multiplier.toFixed(2)}
            </div>
          </div>
        ) : null}
      </div>

      {translation.confidence_factors.length > 0 ? (
        <details className="mt-3 text-[11px]">
          <summary className="cursor-pointer text-[var(--muted)] hover:text-[var(--accent)]">
            Confidence factors
          </summary>
          <ul className="mt-2 space-y-1 pl-4 list-disc text-[var(--muted-strong)]">
            {translation.confidence_factors.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ul>
        </details>
      ) : null}
    </section>
  );
}
