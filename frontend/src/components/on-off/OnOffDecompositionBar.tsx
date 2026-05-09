"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Cell,
} from "recharts";
import type { OnOffDecomposition } from "@/lib/types";

interface Props {
  decomposition: OnOffDecomposition | null;
  teamNetRating: number | null;
}

interface TooltipProps {
  active?: boolean;
  payload?: Array<{ value: number; name: string }>;
  label?: string;
}

function CustomTooltip({ active, payload, label }: TooltipProps) {
  if (!active || !payload?.length) return null;
  const v = payload[0].value;
  return (
    <div className="rounded border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-2.5 py-1.5 text-xs shadow">
      <p className="font-semibold text-gray-800 dark:text-gray-200">{label}</p>
      <p className={v >= 0 ? "text-green-600 dark:text-green-400" : "text-red-500"}>
        {v >= 0 ? "+" : ""}{v.toFixed(1)} pts/100
      </p>
    </div>
  );
}

export default function OnOffDecompositionBar({ decomposition, teamNetRating }: Props) {
  if (!decomposition) {
    return (
      <div className="flex h-24 items-center justify-center text-xs text-gray-400 dark:text-gray-500">
        No decomposition data
      </div>
    );
  }

  const data = [
    { name: "ORTG Δ", value: decomposition.ortg_impact ?? 0 },
    { name: "DRTG Δ", value: decomposition.drtg_impact ?? 0 },
  ];

  const hasData = decomposition.ortg_impact != null || decomposition.drtg_impact != null;
  if (!hasData) {
    return (
      <div className="flex h-24 items-center justify-center text-xs text-gray-400 dark:text-gray-500">
        No decomposition data
      </div>
    );
  }

  return (
    <div>
      <ResponsiveContainer width="100%" height={130}>
        <BarChart data={data} margin={{ top: 8, right: 16, bottom: 4, left: 8 }} barSize={28}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(107,114,128,0.2)" vertical={false} />
          <XAxis dataKey="name" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontSize: 10 }} axisLine={false} tickLine={false} width={30} />
          <ReferenceLine y={0} stroke="rgba(107,114,128,0.5)" />
          <ReferenceLine y={3} stroke="rgba(13,148,136,0.4)" strokeDasharray="4 2" label={{ value: "Elite", position: "right", fontSize: 9, fill: "#0d9488" }} />
          <ReferenceLine y={-3} stroke="rgba(220,38,38,0.3)" strokeDasharray="4 2" />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(107,114,128,0.08)" }} />
          <Bar dataKey="value" isAnimationActive={false} radius={[3, 3, 0, 0]}>
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.value >= 0 ? "#16a34a" : "#dc2626"} fillOpacity={0.85} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      {decomposition.marginal_net != null && (
        <p className="mt-1 text-center text-[10px] text-gray-500 dark:text-gray-400">
          vs team net:{" "}
          <span className={`font-semibold ${decomposition.marginal_net >= 0 ? "text-green-600 dark:text-green-400" : "text-red-500"}`}>
            {decomposition.marginal_net >= 0 ? "+" : ""}{decomposition.marginal_net.toFixed(1)}
          </span>
          {teamNetRating != null && (
            <span className="ml-1 opacity-60">(team baseline: {teamNetRating >= 0 ? "+" : ""}{teamNetRating.toFixed(1)})</span>
          )}
        </p>
      )}
    </div>
  );
}
