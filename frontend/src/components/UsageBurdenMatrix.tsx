"use client";

import { ResponsiveContainer, Scatter, ScatterChart, ReferenceArea, ReferenceLine, Tooltip, XAxis, YAxis, ZAxis } from "recharts";
import type { UsageEfficiencyPlayerRow } from "@/lib/types";

interface UsageBurdenMatrixProps {
  players: UsageEfficiencyPlayerRow[];
}

function pointColor(category: UsageEfficiencyPlayerRow["category"]) {
  return category === "overused" ? "#9f3f31" : "#21483b";
}

function quadrantLabelTone(tone: "good" | "warn" | "neutral") {
  if (tone === "good") return "border-[rgba(33,72,59,0.12)] bg-[rgba(33,72,59,0.08)] text-[var(--accent-strong)]";
  if (tone === "warn") return "border-[rgba(159,63,49,0.14)] bg-[rgba(159,63,49,0.08)] text-[var(--danger-ink)]";
  return "border-[rgba(181,145,78,0.14)] bg-[rgba(181,145,78,0.08)] text-[rgb(123,93,42)]";
}

function median(values: number[]) {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0
    ? (sorted[middle - 1] + sorted[middle]) / 2
    : sorted[middle];
}

function paddedDomain(values: number[]) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (min === max) {
    const pad = Math.max(5, Math.abs(min) * 0.12 || 5);
    return [min - pad, max + pad] as [number, number];
  }
  const spread = max - min;
  const pad = Math.max(spread * 0.18, 2.5);
  return [min - pad, max + pad] as [number, number];
}

export default function UsageBurdenMatrix({ players }: UsageBurdenMatrixProps) {
  const chartData = players
    .filter((player) => player.burden_score != null && player.efficiency_score != null)
    .map((player) => ({
      x: player.burden_score as number,
      y: player.efficiency_score as number,
      z: Math.max(8, (player.minutes_pg ?? 20) * 0.8),
      player_name: player.player_name,
      team_abbreviation: player.team_abbreviation,
      category: player.category,
      ts_pct: player.ts_pct,
      usg_pct: player.usg_pct,
      minutes_pg: player.minutes_pg,
    }));

  const xValues = chartData.map((player) => player.x);
  const yValues = chartData.map((player) => player.y);
  const xMedian = median(xValues);
  const yMedian = median(yValues);
  const [xMin, xMax] = paddedDomain(xValues);
  const [yMin, yMax] = paddedDomain(yValues);

  const underusedTarget = [...chartData]
    .filter((player) => player.category === "underused")
    .sort((a, b) => (b.y - b.x) - (a.y - a.x))[0] ?? null;

  const overusedRisk = [...chartData]
    .filter((player) => player.category === "overused")
    .sort((a, b) => (b.x - b.y) - (a.x - a.y))[0] ?? null;

  if (!chartData.length) {
    return (
      <div className="rounded-[1.5rem] border border-[var(--border)] bg-[rgba(255,255,255,0.72)] p-6 text-sm text-[var(--muted)]">
        No burden-efficiency points are available for the current filter set.
      </div>
    );
  }

  return (
    <div className="rounded-[1.75rem] border border-[var(--border)] bg-[linear-gradient(145deg,rgba(247,243,232,0.92),rgba(228,236,232,0.94))] p-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Burden Matrix
          </p>
          <h2 className="mt-1 text-2xl font-semibold text-[var(--foreground)]">
            Where usage and efficiency split apart
          </h2>
          <p className="mt-2 max-w-2xl text-sm text-[var(--muted-strong)]">
            Read it like this: move right for more offensive burden, move up for better efficiency.
            The strongest opportunities live top-left. The biggest strain risks live bottom-right.
            This view is now scaled to the current filtered player pool, so spacing reflects real separation inside this group.
          </p>
        </div>
        <div className="text-right text-[11px] text-[var(--muted)]">
          <div>Green = underused efficient</div>
          <div>Red = overused inefficient</div>
          <div>Bigger dots = more minutes</div>
        </div>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <div className={`rounded-2xl border px-4 py-3 text-sm ${quadrantLabelTone("good")}`}>
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em]">Top-left</div>
          <div className="mt-1 font-semibold">Feature more</div>
          <div className="mt-1 text-[var(--muted-strong)]">Efficient players carrying lighter burden.</div>
        </div>
        <div className={`rounded-2xl border px-4 py-3 text-sm ${quadrantLabelTone("neutral")}`}>
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em]">Top-right</div>
          <div className="mt-1 font-semibold">Keep feeding</div>
          <div className="mt-1 text-[var(--muted-strong)]">High-burden players who are still converting.</div>
        </div>
        <div className={`rounded-2xl border px-4 py-3 text-sm ${quadrantLabelTone("neutral")}`}>
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em]">Bottom-left</div>
          <div className="mt-1 font-semibold">Low leverage</div>
          <div className="mt-1 text-[var(--muted-strong)]">Lower-burden players who are not forcing decisions.</div>
        </div>
        <div className={`rounded-2xl border px-4 py-3 text-sm ${quadrantLabelTone("warn")}`}>
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em]">Bottom-right</div>
          <div className="mt-1 font-semibold">Monitor closely</div>
          <div className="mt-1 text-[var(--muted-strong)]">Heavy burden with weak efficiency return.</div>
        </div>
      </div>

      <div className="mt-5 rounded-[1.5rem] border border-[rgba(25,52,42,0.12)] bg-[rgba(255,255,255,0.66)] px-4 py-3 text-sm text-[var(--muted-strong)]">
        Midlines mark the current pool median, not a fixed league frame.
        Above the horizontal line means more efficient than this player pool&apos;s midpoint.
        Right of the vertical line means heavier burden than this player pool&apos;s midpoint.
      </div>

      <div className="mt-5 h-[320px]">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 12, right: 16, bottom: 20, left: 10 }}>
            <ReferenceArea x1={xMin} x2={xMedian} y1={yMin} y2={yMedian} fill="rgba(181,145,78,0.06)" />
            <ReferenceArea x1={xMedian} x2={xMax} y1={yMin} y2={yMedian} fill="rgba(159,63,49,0.06)" />
            <ReferenceArea x1={xMin} x2={xMedian} y1={yMedian} y2={yMax} fill="rgba(33,72,59,0.07)" />
            <ReferenceArea x1={xMedian} x2={xMax} y1={yMedian} y2={yMax} fill="rgba(181,145,78,0.08)" />
            <ReferenceLine x={xMedian} stroke="rgba(25,52,42,0.18)" />
            <ReferenceLine y={yMedian} stroke="rgba(25,52,42,0.18)" />
            <XAxis
              type="number"
              dataKey="x"
              domain={[xMin, xMax]}
              tickLine={false}
              axisLine={false}
              tick={{ fill: "#5f6f68", fontSize: 12 }}
              tickFormatter={(value) => value.toFixed(0)}
            />
            <YAxis
              type="number"
              dataKey="y"
              domain={[yMin, yMax]}
              tickLine={false}
              axisLine={false}
              tick={{ fill: "#5f6f68", fontSize: 12 }}
              tickFormatter={(value) => value.toFixed(0)}
            />
            <ZAxis type="number" dataKey="z" range={[60, 260]} />
            <Tooltip
              cursor={{ stroke: "rgba(25,52,42,0.18)", strokeDasharray: "4 6" }}
              contentStyle={{
                borderRadius: 18,
                border: "1px solid rgba(25,52,42,0.12)",
                background: "rgba(255,255,255,0.96)",
              }}
              formatter={(value, name) => [
                typeof value === "number" ? value.toFixed(1) : String(value ?? "—"),
                name === "x" ? "Burden" : name === "y" ? "Efficiency" : name,
              ]}
              labelFormatter={(_, payload) => {
                const point = payload?.[0]?.payload;
                return point ? `${point.player_name} · ${point.team_abbreviation}` : "";
              }}
            />
            <text x={18} y={18} fill="#21483b" fontSize="11" fontWeight="700">
              More efficient
            </text>
            <text x={18} y={302} fill="#5f6f68" fontSize="11" fontWeight="600">
              Less efficient
            </text>
            <text x={208} y={312} fill="#5f6f68" fontSize="11" fontWeight="600">
              Less burden
            </text>
            <text x={430} y={312} fill="#9f3f31" fontSize="11" fontWeight="700">
              More burden
            </text>
            <Scatter
              data={chartData}
              shape={(props: { cx?: number; cy?: number; payload?: { category: UsageEfficiencyPlayerRow["category"] } }) => {
                const { cx = 0, cy = 0, payload } = props;
                const fill = pointColor(payload?.category ?? "underused");
                return (
                  <g>
                    <circle cx={cx} cy={cy} r="11" fill={fill} fillOpacity="0.18" />
                    <circle cx={cx} cy={cy} r="5.5" fill={fill} />
                  </g>
                );
              }}
            />
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <div className="rounded-[1.5rem] border border-[rgba(33,72,59,0.12)] bg-[rgba(33,72,59,0.06)] p-4">
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--accent-strong)]">
            Best feature-more candidate
          </div>
          {underusedTarget ? (
            <>
              <div className="mt-2 text-lg font-semibold text-[var(--foreground)]">
                {underusedTarget.player_name} · {underusedTarget.team_abbreviation}
              </div>
              <div className="mt-1 text-sm text-[var(--muted-strong)]">
                Strong efficiency with lighter burden. This is the clearest “give him a little more” signal on the chart.
              </div>
              <div className="mt-3 grid grid-cols-3 gap-2 text-[11px] text-[var(--muted)]">
                <div>Efficiency {underusedTarget.y.toFixed(1)}</div>
                <div>Burden {underusedTarget.x.toFixed(1)}</div>
                <div>{underusedTarget.minutes_pg?.toFixed(1) ?? "—"} MPG</div>
              </div>
            </>
          ) : (
            <div className="mt-2 text-sm text-[var(--muted)]">No clear underused-efficient signal in the current filter set.</div>
          )}
        </div>

        <div className="rounded-[1.5rem] border border-[rgba(159,63,49,0.14)] bg-[rgba(159,63,49,0.06)] p-4">
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--danger-ink)]">
            Biggest burden-risk candidate
          </div>
          {overusedRisk ? (
            <>
              <div className="mt-2 text-lg font-semibold text-[var(--foreground)]">
                {overusedRisk.player_name} · {overusedRisk.team_abbreviation}
              </div>
              <div className="mt-1 text-sm text-[var(--muted-strong)]">
                Heavy burden without matching efficiency. This is the clearest “too much on his plate” signal on the chart.
              </div>
              <div className="mt-3 grid grid-cols-3 gap-2 text-[11px] text-[var(--muted)]">
                <div>Efficiency {overusedRisk.y.toFixed(1)}</div>
                <div>Burden {overusedRisk.x.toFixed(1)}</div>
                <div>{overusedRisk.minutes_pg?.toFixed(1) ?? "—"} MPG</div>
              </div>
            </>
          ) : (
            <div className="mt-2 text-sm text-[var(--muted)]">No clear overused-inefficient signal in the current filter set.</div>
          )}
        </div>
      </div>
    </div>
  );
}
