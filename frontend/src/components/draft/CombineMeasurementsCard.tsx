// Sprint 101 (Stream B) — NBA Draft Combine measurement card.
//
// Renders the Sprint 100 `combine_measurements` payload split into two
// blocks: anthropometrics (size/length) and athletic testing (vert + agility
// + sprint + bench). Hides entirely when the payload is null. When some
// fields are present but others null (combine typically doesn't include
// every test for every prospect) we show "—" so the layout doesn't shift.

import type { CombineMeasurement } from "@/lib/types";

interface Props {
  measurement: CombineMeasurement | null | undefined;
}

function inches(value: number | null | undefined): string {
  if (value == null) return "—";
  // Display as "6'8.5\"" for height; raw inches for everything else.
  return `${value.toFixed(2)}"`;
}

function footAndInches(value: number | null | undefined): string {
  if (value == null) return "—";
  const ft = Math.floor(value / 12);
  const remaining = value - ft * 12;
  return `${ft}' ${remaining.toFixed(2)}"`;
}

function pounds(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${value.toFixed(1)} lb`;
}

function seconds(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${value.toFixed(2)}s`;
}

function percent(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${value.toFixed(1)}%`;
}

function reps(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${value} reps`;
}

function formatAsOf(asOf: string | null | undefined): string | null {
  if (!asOf) return null;
  try {
    return new Date(asOf).toLocaleDateString("en-US", { month: "long", year: "numeric" });
  } catch {
    return asOf;
  }
}

function MeasurementRow({ label, value }: { label: string; value: string }) {
  const isMissing = value === "—";
  return (
    <div className="flex items-baseline justify-between border-b border-[var(--border)] py-2 last:border-b-0">
      <span className="text-[11px] uppercase tracking-wide text-[var(--muted)]">{label}</span>
      <span
        className={`tabular-nums font-medium ${isMissing ? "text-[var(--muted)]" : "text-[var(--foreground)]"}`}
      >
        {value}
      </span>
    </div>
  );
}

export default function CombineMeasurementsCard({ measurement }: Props) {
  if (!measurement) return null;

  // All-null check — if nothing's populated, don't render an empty card.
  const hasAnyData =
    measurement.height_no_shoes != null ||
    measurement.height_with_shoes != null ||
    measurement.weight != null ||
    measurement.wingspan != null ||
    measurement.standing_reach != null ||
    measurement.standing_vert != null ||
    measurement.max_vert != null ||
    measurement.lane_agility_seconds != null ||
    measurement.three_quarter_sprint_seconds != null;
  if (!hasAnyData) return null;

  const asOfLabel = formatAsOf(measurement.as_of);

  return (
    <section className="bip-panel rounded-[1.85rem] p-5 sm:p-6">
      <p className="bip-kicker">NBA Draft Combine</p>
      <h2 className="bip-display mt-1 text-xl font-bold text-[var(--foreground)]">Anthropometrics &amp; athletic testing</h2>

      <div className="mt-4 grid gap-x-8 gap-y-1 md:grid-cols-2">
        <div>
          <div className="text-[10px] uppercase tracking-wider text-[var(--muted)] mb-1">Size &amp; length</div>
          <MeasurementRow label="Height (no shoes)" value={footAndInches(measurement.height_no_shoes)} />
          <MeasurementRow label="Height (with shoes)" value={footAndInches(measurement.height_with_shoes)} />
          <MeasurementRow label="Weight" value={pounds(measurement.weight)} />
          <MeasurementRow label="Wingspan" value={inches(measurement.wingspan)} />
          <MeasurementRow label="Standing reach" value={inches(measurement.standing_reach)} />
          <MeasurementRow label="Body fat" value={percent(measurement.body_fat_pct)} />
          <MeasurementRow label="Hand length" value={inches(measurement.hand_length)} />
          <MeasurementRow label="Hand width" value={inches(measurement.hand_width)} />
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wider text-[var(--muted)] mb-1">Athletic testing</div>
          <MeasurementRow label="Standing vert" value={inches(measurement.standing_vert)} />
          <MeasurementRow label="Max vert" value={inches(measurement.max_vert)} />
          <MeasurementRow label="Lane agility" value={seconds(measurement.lane_agility_seconds)} />
          <MeasurementRow label="3/4 court sprint" value={seconds(measurement.three_quarter_sprint_seconds)} />
          <MeasurementRow label="Bench press (135 lb)" value={reps(measurement.bench_press_135)} />
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between text-[10px] text-[var(--muted)]">
        <span>
          Source:{" "}
          {measurement.source_url ? (
            <a
              href={measurement.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="bip-link"
            >
              {measurement.source ?? "nba_combine"} ↗
            </a>
          ) : (
            measurement.source ?? "nba_combine"
          )}
        </span>
        {asOfLabel ? <span>As of {asOfLabel}</span> : null}
      </div>
    </section>
  );
}
